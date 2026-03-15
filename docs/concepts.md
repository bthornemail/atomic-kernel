# Concepts and Normative Boundaries

Version: v1.0  
Status: Canonical implementation reference

## Normative Source
The normative protocol and artifact behavior is defined in:
- [Canonical Algorithms Specification](./algorithms.md)

This page is informative and summarizes runtime behavior.

## Runtime Modes

### `mode=kernel`
Claim label: `Implemented`, `Verified`
- Normative law version: `kernel-v1`
- Width: `16`

### `mode=16d`
Claim label: `Implemented`, `Verified`
- Normative law version: `16d-v1`
- Widths: `16, 32, 64, 128, 256`

## Deterministic Artifact Rules
Claim label: `Implemented`, `Verified`
- Canonical JSON serialization uses sorted keys and compact separators.
- Canonical bytes are UTF-8.
- Artifact digests are tagged (`<algo>:<hex>`), default `sha3_256`.
- `mode`, `law_version`, `hash_algo`, and `canonicalization` are included in artifacts.

## Identity Contract (SID/OID)
Claim label: `Implemented`, `Verified`
- `SID = hash(type:canonical_form)`
- `OID = hash(clock:sid:prev_oid)`
- Hash algorithm is tagged and configurable (`sha256`, `sha3_256`).

## Control-Plane Contract
Claim label: `Implemented`, `Verified`
- Basis separators: `FS(0x1C)`, `GS(0x1D)`, `RS(0x1E)`, `US(0x1F)`.
- Canonicalization: `stream-sign-value-v1`.
- Orbit base: `36`.
- Validation is fail-closed on malformed ordering/token/state.

## Authority Boundary
Claim label: `Implemented`, `Verified`
- Layers `1..8` are normative surfaces.
- Layers `9..32` are advisory by policy.
- Advisory layers cannot `mutate/write/override` canonical artifacts.

## Compatibility Statement
Claim label: `Implemented`, `Verified`
- Current conformance lock: `ak-v1-2026-03-15`.
- Conformance metadata includes `hash_algo` and `canonicalization`.

## Open / Conjecture Surfaces
Claim label: `Conjecture/Open`
- Higher-dimensional theoretical mappings in `dev-docs/state-machine/*` beyond implemented runtime contracts.
