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

# Build scan-ready Aztec chunk payloads from replay artifact
./ak aztec-pack --mode 16d --width 32 --seed 0x0B7406AC --steps 64 --outdir aztec-bundle

# Build proof-layer bundles (control codes, algorithms, full artifact)
./ak aztec-proof --outdir aztec-proof

# Reconstruct artifact from scanned chunk files
./ak aztec-unpack --indir aztec-bundle --output aztec-bundle/recovered.json
```

## Canonical Artifacts - Scannable Proof
Use `./ak aztec-proof --outdir aztec-proof` to generate three deterministic payload sets:

- `aztec-proof/control-codes/` : UTF-EBCDIC control-plane contract payload
- `aztec-proof/algorithms/` : `AK-ALG-01..04` algorithm IDs and spec metadata
- `aztec-proof/full/` : full replay artifact payload

Each set contains:
- `manifest.json` with `aztec_profile`, ordering, descriptor parity, and digests
- `chunks/chunk-*.json` (one payload per Aztec symbol)
- `chunks.ndjson` (line-delimited chunk payloads for batch encoding)

Encode each chunk JSON as one Aztec symbol with your encoder of choice, then scan/decode back to JSON and run `./ak aztec-unpack` to verify reconstruction and digest integrity.

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
