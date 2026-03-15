# Getting Started

Version: v1.0  
Status: Implemented and verified locally

## Normative Source
For protocol behavior and artifact fields, use:
- [Canonical Algorithms Specification](./algorithms.md)

## Requirements
- Python 3.8+
- GHC / runhaskell (for oracle parity and conformance)

## Quick Start
```bash
cd atomic-kernel
./ak all
```

Open the dashboard at `http://127.0.0.1:8080`.

## What You Should See
- `/replay` and `/replay/hash` return deterministic artifacts with tagged digests (default `sha3_256:`).
- `/control-plane/validate` and `/stream/canonicalize` return `stream-sign-value-v1` canonicalization outputs.
- `conformance.py` prints `Conformance passed` when Python/Haskell/fixtures agree.

## Common Commands
```bash
# Full verification gate
./ak verify

# API + dashboard
./ak serve

# Verify, then start server
./ak all

# Optional direct suite
python3 tests/test_v1.py

# Cross-language parity gate
python3 conformance.py
```
