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
API-backed message demo: `http://127.0.0.1:8080/message-demo`  
Static serverless demo: open `message-demo-static.html` directly, or use `http://127.0.0.1:8080/message-demo-static`.

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

# Offline message artifact generation (no server)
./ak message-artifact --message "Hello, world" --outdir message-artifact

# Package API (no server)
python3 - <<'PY'
from atomic_kernel import canonicalize
print(canonicalize("Hello, world")["stream_digest"])
PY

# Create Aztec chunk payloads from a replay artifact
./ak aztec-pack --mode 16d --width 32 --seed 0x0B7406AC --steps 64 --outdir aztec-bundle

# Create proof-layer payload sets (control codes, algorithms, full artifact)
./ak aztec-proof --outdir aztec-proof

# One-time renderer setup
python3 -m venv .venv
.venv/bin/pip install aztec-code-generator pillow

# Render proof PNG images for README/docs
./ak aztec-images --proof-dir aztec-proof

# Reconstruct artifact from chunk files
./ak aztec-unpack --indir aztec-bundle --output aztec-bundle/recovered.json

# Optional direct suite
python3 tests/test_v1.py

# Cross-language parity gate
python3 conformance.py
```
