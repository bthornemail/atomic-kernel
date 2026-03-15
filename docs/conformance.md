# Conformance and Oracle Workflow

Version: v1.0  
Status: Implemented and required for parity verification

## Normative Source
Conformance targets are defined by:
- [Canonical Algorithms Specification](./algorithms.md)

## Conformance Contract
```text
OracleCase {
  conformance_version,
  mode,
  width,
  seed,
  steps,
  context,
  hash_algo,
  canonicalization
} -> {
  states,
  projections,
  replay_hash,
  result_hash
}
```

Current lock:
- `conformance_version`: `ak-v1-2026-03-15`
- `hash_algo`: `sha3_256`
- `canonicalization`: `stream-sign-value-v1`
- Cases file: `dev-docs/haskell/conformance_cases.json`

## Gate Command
```bash
python3 conformance.py
```

Expected success shape:
- `"ok": true`
- `"failures": []`
- deterministic tagged `"result_hash"`

## Data Sources Used by the Gate
- Fixture corpus: `dev-docs/haskell/replay-16.json` ... `replay-256.json`
- Python runtime: `replay_engine.py` (`mode=16d`)
- Haskell oracle: `dev-docs/haskell/oracle.hs`

## Failure Artifact
If mismatches occur, deterministic diff output is written to:
- `dev-docs/haskell/conformance_diff.json`

## Claim Labels
- `Implemented`: Conformance gate script and oracle endpoint exist.
- `Verified`: Local pass of `python3 conformance.py`.
