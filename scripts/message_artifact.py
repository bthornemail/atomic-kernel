#!/usr/bin/env python3
"""Build deterministic message artifacts locally (no HTTP server required)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aztec_bundle import build_bundle
from canonical import DEFAULT_HASH_ALGO
from identity import ObjectChain
from replay_engine import replay_artifact
from stream_sign_value import canonicalize_stream

VENV_PY = ROOT / ".venv" / "bin" / "python"
RENDERER = ROOT / "render_aztec_payload.py"


def _cp_to_digits(cp: int) -> List[int]:
    if cp == 0:
        return [0]
    out: List[int] = []
    n = cp
    while n > 0:
        n, d = divmod(n, 60)
        out.append(d)
    return list(reversed(out))


def encode_message(message: str) -> Dict[str, Any]:
    digits: List[int] = []
    for ch in message:
        cp = ord(ch)
        digits.extend(_cp_to_digits(cp))
        digits.append(0x1C)  # FS separator
    if digits and digits[-1] == 0x1C:
        digits.pop()
    payload = "".join(chr(d) for d in digits)
    return {"digits": digits, "payload": payload}


def render_chunk_png(chunk_payload: Dict[str, Any], out_path: Path) -> bool:
    if not (VENV_PY.exists() and RENDERER.exists()):
        return False
    text = json.dumps(chunk_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    proc = subprocess.run(
        [str(VENV_PY), str(RENDERER), "--ec-percent", "23", "--module-size", "4", "--border", "2"],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return False
    out_path.write_bytes(proc.stdout)
    return True


def build_message_artifact(
    message: str,
    *,
    tick: int = 8,
    hash_algo: str = DEFAULT_HASH_ALGO,
) -> Dict[str, Any]:
    enc = encode_message(message)
    stream = canonicalize_stream(enc["payload"], hash_algo=hash_algo)
    seed = (int(stream.pattern_number) % 65535) + 1

    chain = ObjectChain(seed, hash_algo=hash_algo)
    rec = chain.step(tick)
    replay = replay_artifact("kernel", 16, seed, 8, hash_algo=hash_algo)

    return {
        "message": message,
        "control_digits": enc["digits"],
        "canonicalization": stream.canonicalization,
        "hash_algo": hash_algo,
        "stream_digest": stream.stream_digest,
        "pattern_number": stream.pattern_number,
        "frame_values": stream.frame_values,
        "seed_hex": f"0x{seed:04X}",
        "tick": tick,
        "sid": rec["sid"],
        "clock": rec["clock"],
        "oid": rec["oid"],
        "replay_hash": replay.replay_hash,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Create local message artifact and optional Aztec PNGs")
    p.add_argument("--message", required=True)
    p.add_argument("--outdir", default="message-artifact")
    p.add_argument("--tick", type=int, default=8)
    p.add_argument("--hash-algo", default=DEFAULT_HASH_ALGO)
    p.add_argument("--chunk-bytes", type=int, default=900)
    args = p.parse_args()

    outdir = Path(args.outdir)
    (outdir / "chunks").mkdir(parents=True, exist_ok=True)

    artifact = build_message_artifact(args.message, tick=args.tick, hash_algo=args.hash_algo)
    (outdir / "artifact.json").write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest, chunks = build_bundle(artifact, hash_algo=args.hash_algo, chunk_bytes=args.chunk_bytes)
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for c in chunks:
        path = outdir / "chunks" / f"chunk-{int(c['index']):04d}.json"
        path.write_text(json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

    rendered = 0
    for c in chunks:
        png = outdir / "chunks" / f"chunk-{int(c['index']):04d}.png"
        if render_chunk_png(c, png):
            rendered += 1

    print(
        json.dumps(
            {
                "ok": True,
                "artifact": str(outdir / "artifact.json"),
                "manifest": str(outdir / "manifest.json"),
                "chunks": len(chunks),
                "png_rendered": rendered,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
