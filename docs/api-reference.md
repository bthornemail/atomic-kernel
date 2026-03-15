# API Reference

Version: v1.0  
Status: Implemented in `api_server.py`

## Normative Source
Wire semantics and artifact requirements are normative in:
- [Canonical Algorithms Specification](./algorithms.md)

Base URL: `http://127.0.0.1:8080`

## POST `/replay`
Returns full replay artifact.

Request:
```json
{ "mode": "16d", "width": 32, "seed": "0x0B7406AC", "steps": 8, "hash_algo": "sha3_256" }
```

Response fields:
- `mode`, `law_version`, `width`, `seed_hex`, `steps`
- `hash_algo`, `digest`
- `states[]`
- `replay_hash`, `canonical_json`

## POST `/replay/hash`
Returns digest-focused replay artifact.

```bash
curl -s -X POST http://127.0.0.1:8080/replay/hash \
  -H 'content-type: application/json' \
  -d '{"mode":"16d","width":16,"seed":"0x06AC","steps":8,"hash_algo":"sha3_256"}'
```

## POST `/control-plane/validate`
Validates control stream and returns canonicalization output.

```json
{
  "mode": "kernel",
  "hash_algo": "sha3_256",
  "canonicalization": "stream-sign-value-v1",
  "payload": "alpha\u001cbeta\u001dgamma\u001edelta\u001funit"
}
```

## POST `/stream/canonicalize`
Runs in-band parser + mixed-radix escape decoding + orbit reduction.

```json
{ "payload": "\u0027\u0002\u001f\u0001\u0000", "hash_algo": "sha3_256" }
```

## POST `/identity/verify`
Verifies deterministic SID/OID chain records.

```json
{
  "mode": "kernel",
  "seed": "0x0001",
  "ticks": [0, 8, 16],
  "hash_algo": "sha3_256",
  "allow_legacy_untagged": false
}
```

## POST `/authority/check`
Returns deterministic allow/deny authority decision.

```json
{
  "mode": "kernel",
  "operation": "override",
  "layer": 20,
  "artifact_hash": "sha3_256:abcd...",
  "hash_algo": "sha3_256"
}
```

## POST `/oracle/parity`
Compares Python output with Haskell oracle + fixture parity.

```json
{ "width": 16, "seed": "0x06AC", "steps": 8, "hash_algo": "sha3_256" }
```

## Failure Codes (Examples)
- Common: `UNKNOWN_HASH_ALGO`, `UNTAGGED_DIGEST`
- Replay: `INVALID_MODE`, `INVALID_WIDTH_FOR_MODE`, `INVALID_STEPS`, `INVALID_SEED`
- Control plane: `INVALID_MODE`, `UNKNOWN_TOKEN`, `OUT_OF_ORDER_SEPARATOR`, `EMPTY_REQUIRED_SEGMENT`, `UNSUPPORTED_CANONICALIZATION`
- Stream parser: `INVALID_CONTROL_CODE_RANGE`, `SIGN_VALUE_DECODE_ERROR`, `INCOMPLETE_ESCAPE_SEQUENCE`
- Authority: `INVALID_LAYER`, `AUTHORITY_ESCALATION_BLOCKED`, `UNKNOWN_OPERATION`
- Oracle: `ORACLE_ERROR`, `PARITY_MISMATCH`

All deterministic endpoint outputs include tagged digest material.
