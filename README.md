# Atomic Kernel

Deterministic replay substrate with mode-aware runtime laws, canonical hashing, and cross-language conformance checks.

For full docs, start at [docs/README.md](./docs/README.md).

## Quick Start
```bash
./ak all
```

Open dashboard: `http://127.0.0.1:8080`

## What Is Implemented
- Mode-aware replay: `mode=kernel` and `mode=16d`
- Deterministic canonical artifacts (`sha3_256:` digests)
- SID/OID verification path
- Fail-closed control-plane validation
- Authority decision gate
- Haskell oracle parity endpoint and conformance gate

## Key Commands
```bash
# API + dashboard
./ak serve

# Full verification gate
./ak verify

# Verify, then start server
./ak all
```

## API Surface
- `POST /replay`
- `POST /replay/hash`
- `POST /control-plane/validate`
- `POST /identity/verify`
- `POST /authority/check`
- `POST /oracle/parity`

See [docs/api-reference.md](./docs/api-reference.md) for contracts and examples.

## Publication Notes
- Normative implementation guidance: [docs/concepts.md](./docs/concepts.md)
- Conformance contract: [docs/conformance.md](./docs/conformance.md)
- Claim policy: [docs/publication-claims.md](./docs/publication-claims.md)
