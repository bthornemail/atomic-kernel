#!/usr/bin/env python3
"""Coq/Python parity gate for selected vectors and golden artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from replay_engine import replay_artifact
from scripts.coq_pipeline import MODULE_NAME, build_artifact, compile_and_check, extract_states_from_coq

VECTORS_PATH = ROOT / "coq" / "parity_vectors.json"
GOLDEN_PATH = ROOT / "golden" / "coq" / "artifact-16-0x0001-8.json"

THEOREMS = [
    f"{MODULE_NAME}.delta_deterministic",
    f"{MODULE_NAME}.replay_deterministic",
    f"{MODULE_NAME}.replay_len",
]


def _print_assumptions_closed(theorem: str) -> bool:
    script = f"From AK Require Import AtomicKernelCoq.\nPrint Assumptions {theorem}.\n"
    proc = subprocess.run(
        ["coqtop", "-Q", "coq", "AK", "-quiet"],
        cwd=str(ROOT),
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return "Closed under the global context" in out and "Axioms:" not in out


def check_assumptions() -> None:
    failed = [th for th in THEOREMS if not _print_assumptions_closed(th)]
    if failed:
        raise RuntimeError(f"ASSUMPTION_LEAK:{','.join(failed)}")


def _python_states(width: int, seed: int, steps: int) -> list[int]:
    art = replay_artifact("16d", width, seed, steps)
    out = []
    for st in art.states:
        out.append(int(str(st["state_hex"]), 16))
    return out


def check_vectors() -> None:
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    for v in vectors:
        width = int(v["width"])
        seed = int(str(v["seed"]), 0)
        steps = int(v["steps"])
        coq_states = extract_states_from_coq(width, seed, steps)
        py_states = _python_states(width, seed, steps)
        if coq_states != py_states:
            raise RuntimeError(
                f"PARITY_MISMATCH:width={width}:seed={hex(seed)}:steps={steps}"
            )


def write_golden() -> None:
    artifact = build_artifact(16, int("0x0001", 0), 8, "sha3_256")
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n"
    GOLDEN_PATH.write_text(payload, encoding="utf-8")


def check_golden() -> None:
    if not GOLDEN_PATH.exists():
        raise RuntimeError("MISSING_GOLDEN")
    artifact = build_artifact(16, int("0x0001", 0), 8, "sha3_256")
    current = (json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    expected = GOLDEN_PATH.read_bytes()
    if current != expected:
        raise RuntimeError("GOLDEN_MISMATCH")


def main() -> int:
    p = argparse.ArgumentParser(description="Coq parity gate")
    p.add_argument("command", choices=["check", "write-golden"])
    args = p.parse_args()

    compile_and_check()
    check_assumptions()
    check_vectors()

    if args.command == "write-golden":
        write_golden()
        print(json.dumps({"ok": True, "golden": str(GOLDEN_PATH)}, separators=(",", ":")))
        return 0

    check_golden()
    print(
        json.dumps(
            {"ok": True, "vectors": str(VECTORS_PATH), "golden": str(GOLDEN_PATH), "module": MODULE_NAME},
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
