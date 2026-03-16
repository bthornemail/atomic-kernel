#!/usr/bin/env python3
"""Render a single Aztec code PNG from stdin text payload.

Reads UTF-8 text from stdin and writes PNG bytes to stdout.
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO

from aztec_code_generator import AztecCode


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Aztec PNG from stdin payload")
    parser.add_argument("--ec-percent", type=int, default=23)
    parser.add_argument("--module-size", type=int, default=4)
    parser.add_argument("--border", type=int, default=2)
    args = parser.parse_args()

    data = sys.stdin.buffer.read().decode("utf-8")
    code = AztecCode(data, ec_percent=args.ec_percent)
    image = code.image(module_size=args.module_size, border=args.border)
    buf = BytesIO()
    image.save(buf, format="PNG")
    sys.stdout.buffer.write(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
