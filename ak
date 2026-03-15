#!/usr/bin/env python3
"""Atomic Kernel one-command entrypoint.

Usage:
  ./ak              # serve API + dashboard
  ./ak serve        # serve API + dashboard
  ./ak verify       # run tests + conformance gate
  ./ak all          # verify then serve
  ./ak aztec-pack   # create Aztec chunk bundle from replay artifact
  ./ak aztec-proof  # create control/algorithms/full proof bundles
  ./ak aztec-unpack # reconstruct artifact from Aztec chunk bundle
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def cmd_serve() -> int:
    return run([sys.executable, "api_server.py"])


def cmd_verify() -> int:
    steps = [
        [sys.executable, "tests/test_all.py"],
        [sys.executable, "tests/test_v1.py"],
        [sys.executable, "conformance.py"],
    ]
    for step in steps:
        rc = run(step)
        if rc != 0:
            return rc
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomic Kernel entrypoint")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["serve", "verify", "all", "aztec-pack", "aztec-proof", "aztec-unpack"],
        help="serve, verify, run all, or use Aztec bundle pack/unpack",
    )
    parser.add_argument("--mode", default="16d", choices=["kernel", "16d"])
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--seed", default="0x0B7406AC")
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--chunk-bytes", type=int, default=1200)
    parser.add_argument("--ordering", default="spiral_ccw_outer_to_core")
    parser.add_argument("--layers-mode", default="auto", choices=["compact", "full", "auto"])
    parser.add_argument("--ecc-ratio", type=float, default=0.23)
    parser.add_argument("--min-check-words", type=int, default=3)
    parser.add_argument("--codeword-bits", type=int, default=8, choices=[6, 8, 10, 12])
    parser.add_argument("--no-stuffing", action="store_true")
    parser.add_argument("--outdir", default="aztec-bundle")
    parser.add_argument("--indir", default="aztec-bundle")
    parser.add_argument("--output", default="aztec-bundle/recovered.json")
    args = parser.parse_args()

    if args.command == "serve":
        return cmd_serve()
    if args.command == "verify":
        return cmd_verify()
    if args.command == "aztec-pack":
        return run(
            [
                sys.executable,
                "aztec_bundle.py",
                "pack-replay",
                "--mode",
                args.mode,
                "--width",
                str(args.width),
                "--seed",
                args.seed,
                "--steps",
                str(args.steps),
                "--chunk-bytes",
                str(args.chunk_bytes),
                "--ordering",
                args.ordering,
                "--layers-mode",
                args.layers_mode,
                "--ecc-ratio",
                str(args.ecc_ratio),
                "--min-check-words",
                str(args.min_check_words),
                "--codeword-bits",
                str(args.codeword_bits),
                *((["--no-stuffing"]) if args.no_stuffing else []),
                "--outdir",
                args.outdir,
            ]
        )
    if args.command == "aztec-proof":
        return run(
            [
                sys.executable,
                "aztec_bundle.py",
                "pack-proof",
                "--mode",
                args.mode,
                "--width",
                str(args.width),
                "--seed",
                args.seed,
                "--steps",
                str(args.steps),
                "--chunk-bytes",
                str(args.chunk_bytes),
                "--ordering",
                args.ordering,
                "--layers-mode",
                args.layers_mode,
                "--ecc-ratio",
                str(args.ecc_ratio),
                "--min-check-words",
                str(args.min_check_words),
                "--codeword-bits",
                str(args.codeword_bits),
                *((["--no-stuffing"]) if args.no_stuffing else []),
                "--outdir",
                args.outdir,
            ]
        )
    if args.command == "aztec-unpack":
        return run(
            [
                sys.executable,
                "aztec_bundle.py",
                "unpack",
                "--indir",
                args.indir,
                "--output",
                args.output,
            ]
        )

    rc = cmd_verify()
    if rc != 0:
        return rc
    return cmd_serve()


if __name__ == "__main__":
    raise SystemExit(main())
