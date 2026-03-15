#!/usr/bin/env python3
"""Atomic Kernel one-command entrypoint.

Usage:
  ./ak              # serve API + dashboard
  ./ak serve        # serve API + dashboard
  ./ak verify       # run tests + conformance gate
  ./ak all          # verify then serve
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
        choices=["serve", "verify", "all"],
        help="serve API, verify suites, or run all (verify then serve)",
    )
    args = parser.parse_args()

    if args.command == "serve":
        return cmd_serve()
    if args.command == "verify":
        return cmd_verify()

    rc = cmd_verify()
    if rc != 0:
        return rc
    return cmd_serve()


if __name__ == "__main__":
    raise SystemExit(main())
