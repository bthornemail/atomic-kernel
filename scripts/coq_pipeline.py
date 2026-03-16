#!/usr/bin/env python3
"""Compile/check Coq core and emit replay artifacts derived from Coq vm_compute."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COQ_DIR = ROOT / "coq"
COQ_MAIN = COQ_DIR / "AtomicKernelCoq.v"
MODULE_NAME = "AK.AtomicKernelCoq"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical import DEFAULT_HASH_ALGO, canonical_hash, canonical_math_id  # noqa: E402

ALGORITHM_IDS = {
    "extract": "AK-ALG-01 extract_control_stream.v1",
    "parse": "AK-ALG-02 parse_orbit_channels.v1",
    "reduce": "AK-ALG-03 reduce_orbit36.v1",
    "emit": "AK-ALG-04 emit_propagation_artifact.v1",
}


def run(cmd: list[str], *, cwd: Path = ROOT, capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=capture_output,
    )


def ensure_no_admitted_or_axiom() -> None:
    for path in sorted(COQ_DIR.rglob("*.v")):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("(*"):
                continue
            if re.search(r"\bAdmitted\b", stripped):
                raise RuntimeError(f"{path}:{i}: contains Admitted")
            if re.search(r"\bAxiom\b", stripped):
                raise RuntimeError(f"{path}:{i}: contains Axiom")


def compile_and_check() -> None:
    ensure_no_admitted_or_axiom()

    coqc = run(["coqc", "-Q", "coq", "AK", str(COQ_MAIN)], capture_output=True)
    if coqc.returncode != 0:
        detail = (coqc.stderr or coqc.stdout or "").strip().splitlines()
        tail = detail[-5:] if detail else []
        msg = "coqc failed" + (": " + " | ".join(tail) if tail else "")
        raise RuntimeError(msg)

    coqchk = run(["coqchk", "-Q", "coq", "AK", MODULE_NAME], capture_output=True)
    if coqchk.returncode != 0:
        detail = (coqchk.stderr or coqchk.stdout or "").strip().splitlines()
        tail = detail[-5:] if detail else []
        msg = "coqchk failed" + (": " + " | ".join(tail) if tail else "")
        raise RuntimeError(msg)


def extract_states_from_coq(width: int, seed: int, steps: int) -> list[int]:
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        query_path = tdir / "ArtifactQuery.v"

        query_path.write_text(
            "\n".join(
                [
                    "From AK Require Import AtomicKernelCoq.",
                    "Require Import Coq.NArith.NArith.",
                    "Open Scope N_scope.",
                    f"Eval vm_compute in (replay {width}%N {seed}%N {steps}%nat).",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        q = run(["coqc", "-Q", "coq", "AK", str(query_path)], capture_output=True)
        if q.returncode != 0:
            detail = (q.stderr or q.stdout or "").strip().splitlines()
            tail = detail[-5:] if detail else []
            msg = "coq query failed" + (": " + " | ".join(tail) if tail else "")
            raise RuntimeError(msg)

        raw = q.stdout
        nums = [int(x) for x in re.findall(r"\d+", raw)]
        if not nums and steps > 0:
            raise RuntimeError("coq query produced no states")
        if len(nums) < steps:
            raise RuntimeError(f"coq query produced {len(nums)} states, expected {steps}")
        return nums[:steps]


def build_artifact(width: int, seed: int, steps: int, hash_algo: str) -> dict:
    states = extract_states_from_coq(width, seed, steps)
    payload = {
        "spec_version": "ak.spec.v1",
        "coq_module": MODULE_NAME,
        "mode": "kernel",
        "law_version": "ak-law-coq-v1",
        "canonicalization": "coq-vm-compute-v1",
        "algorithms": ALGORITHM_IDS,
        "width": width,
        "seed": f"0x{seed:X}",
        "steps": steps,
        "states": states,
    }
    digest = canonical_hash(payload, hash_algo=hash_algo)
    payload["hash_algo"] = hash_algo
    payload["artifact_digest"] = digest
    payload["math_id_v2"] = canonical_math_id(payload)
    return payload


def cmd_verify() -> int:
    compile_and_check()
    print(json.dumps({"ok": True, "module": MODULE_NAME, "checked": True}, separators=(",", ":")))
    return 0


def cmd_artifact(width: int, seed_text: str, steps: int, out: Path, hash_algo: str) -> int:
    seed = int(seed_text, 0)
    compile_and_check()
    artifact = build_artifact(width, seed, steps, hash_algo)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "digest": artifact["artifact_digest"]}, separators=(",", ":")))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Coq pipeline for Atomic Kernel")
    p.add_argument("command", choices=["verify", "artifact"])
    p.add_argument("--width", type=int, default=16, choices=[16, 32, 64, 128, 256])
    p.add_argument("--seed", default="0x0001")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--out", default="coq-artifact/artifact.json")
    p.add_argument("--hash-algo", default=DEFAULT_HASH_ALGO)
    args = p.parse_args()

    try:
        if args.command == "verify":
            return cmd_verify()
        return cmd_artifact(args.width, args.seed, args.steps, Path(args.out), args.hash_algo)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
