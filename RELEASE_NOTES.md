# Atomic Kernel v1.0.0

Release date: 2026-03-15  
Status: public release candidate for open review

## Scope
- Deterministic runtime with `mode=kernel` and `mode=16d`.
- Canonical artifact hashing with tagged digests (default `sha3_256`).
- Fail-closed control-plane validation and authority checks.
- Cross-language conformance gate (Python + Haskell fixtures/oracle path).
- Aztec artifact bundling + rendering workflow.
- Serverless paths:
  - offline CLI message artifact generation
  - static browser demo
  - importable Python package API (`atomic_kernel.canonicalize`)

## Verification Commands
Run these exactly:

```bash
python3 scripts/check_claims.py
./ak verify
./ak aztec-proof --outdir aztec-proof
./ak aztec-images --proof-dir aztec-proof
./ak message-artifact --message "Hello, world" --outdir message-artifact
```

Expected:
- `docs-claims check passed`
- full test suites pass
- `conformance.py` reports `"ok": true`
- proof bundles and images are generated
- local message artifact files are generated

## Public Entry Points
- Main docs hub: `docs/README.md`
- API-backed demo: `http://127.0.0.1:8080/message-demo`
- Static serverless demo: `message-demo-static.html`

## Proof Boundary
- Implemented and verified claims are constrained by repository commands/tests.
- Anything beyond current reproducible evidence remains `Conjecture/Open`.
