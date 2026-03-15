# Canonical Algorithms Specification

Version: v1.0  
Status: **Normative**

## How To Read This Spec
- `Normative`: required for conformance.
- `Informative`: implementation notes and examples.

All conforming implementations must use the same algorithm IDs and derive the same artifact for the same input bitstream.

## Global Normative Constants
- `spec_version`: `ak.spec.v1`
- `AK-ALG-01`: `extract_control_stream.v1`
- `AK-ALG-02`: `parse_orbit_channels.v1`
- `AK-ALG-03`: `reduce_orbit36.v1`
- `AK-ALG-04`: `emit_propagation_artifact.v1`
- `canonicalization`: `stream-sign-value-v1`
- `hash default`: `sha3_256`
- `orbit base`: `36`

## Bit-Level Contract (Normative)
- Bit ordering: `MSB-first` within each octet.
- Octet boundary: parser consumes complete bytes only.
- Trailing partial byte: `INVALID_TRAILING_BITS`.
- Byte domain:
  - `0x00..0x3B`: valid control/digit domain.
  - `0x3C..0x3F`: reserved control bytes.
  - `0x40..0xFF`: extension payload, ignored by the canonical control parser unless an extension profile defines behavior.

## AK-ALG-01: extract_control_stream.v1

### Purpose
Convert input bitstream to canonical control-byte stream.

### Input Schema
```json
{
  "bitstream": "...",
  "bit_order": "MSB-first"
}
```

### Output Schema
```json
{
  "bytes": [0, 28, 31, 39],
  "errors": []
}
```

### Errors
- `INVALID_BIT_ORDER`
- `INVALID_TRAILING_BITS`
- `INVALID_OCTET_ALIGNMENT`

### Invariants
- Same bitstream and bit-order yields identical byte sequence.
- Output bytes preserve input order.

### Pseudocode
```text
if bit_order != MSB-first: error INVALID_BIT_ORDER
if len(bitstream) % 8 != 0: error INVALID_TRAILING_BITS
bytes = chunk_8_bits_msb_first(bitstream)
return bytes
```

## AK-ALG-02: parse_orbit_channels.v1

### Purpose
Parse extracted bytes into deterministic in-band control/data events.

### Input Schema
```json
{
  "bytes": [..],
  "state": "CONTROL"
}
```

### Output Schema
```json
{
  "events": [
    {"type": "operator", "code": 28},
    {"type": "escaped_literal", "radix": 60, "digits": [1,0], "charcode": 60}
  ],
  "errors": []
}
```

### State Machine (Normative)
States:
- `CONTROL`
- `ESC_LEN`
- `ESC_RADIX`
- `ESC_DATA`

Rules:
- `0x1C..0x1F` are control operators by default in `CONTROL`.
- `NUL (0x00)` is identity/no-op event.
- `ESC (0x27)` enters escaped-literal parsing.
- Reserved bytes `0x3C..0x3F` emit reserved events and reset parser to `CONTROL`.

### Errors
- `INVALID_CONTROL_CODE_RANGE`
- `RESERVED_CONTROL_CODE` (if profile requires hard rejection)
- `SIGN_VALUE_DECODE_ERROR`
- `INCOMPLETE_ESCAPE_SEQUENCE`

### Invariants
- Parser behavior is deterministic for the same byte stream.
- Operator/digit disambiguation is state-based only.

### Pseudocode
```text
for each byte b:
  if state == CONTROL:
    if b == ESC: state = ESC_LEN
    elif b in [FS,GS,RS,US]: emit operator
    elif b == NUL: emit null
    elif b in control-domain: emit data_digit
    elif b in reserved: emit reserved; state=CONTROL
    else: error INVALID_CONTROL_CODE_RANGE
  elif state == ESC_LEN:
    esc_len = b; state = ESC_RADIX
  elif state == ESC_RADIX:
    esc_radix = radix_from_channel(b); state = ESC_DATA
  elif state == ESC_DATA:
    collect esc_len digits; decode mixed-radix; emit escaped_literal; state=CONTROL
if state != CONTROL: error INCOMPLETE_ESCAPE_SEQUENCE
```

## AK-ALG-03: reduce_orbit36.v1

### Purpose
Reduce parsed events into canonical orbit residues and pattern number.

### Input Schema
```json
{
  "events": [...],
  "orbit_base": 36
}
```

### Output Schema
```json
{
  "frame_values": [28, 18, 7],
  "frame_residues": [28, 18, 7],
  "pattern_number": 9736
}
```

### Normative Equations
- `frame_value_j = Σ sign(code_i) * value(code_i)` with BEL parity toggle.
- `frame_residue_j = frame_value_j mod 36`
- `pattern_number = Σ frame_residue_j * 36^j`

### Errors
- `SIGN_VALUE_DECODE_ERROR`
- `INVALID_FRAME_VALUE`

### Invariants
- Deterministic canonicalization is guaranteed.
- Reversibility is not guaranteed without reconstruction metadata.

### Pseudocode
```text
for each frame:
  compute signed sum with BEL toggle
  residue = sum mod 36
pattern_number = weighted_sum(residue_j, 36^j)
return residues, pattern_number
```

## AK-ALG-04: emit_propagation_artifact.v1

### Purpose
Emit canonical, hash-tagged propagation artifact with identity chain fields.

### Input Schema
```json
{
  "pattern_number": 9736,
  "hash_algo": "sha3_256",
  "mode": "kernel|16d",
  "clock": "frame.tick.control",
  "prev_oid": "..."
}
```

### Output Schema
```json
{
  "spec_version": "ak.spec.v1",
  "algorithms": {
    "extract": "extract_control_stream.v1",
    "parse": "parse_orbit_channels.v1",
    "reduce": "reduce_orbit36.v1",
    "emit": "emit_propagation_artifact.v1"
  },
  "hash_algo": "sha3_256",
  "canonicalization": "stream-sign-value-v1",
  "law_version": "kernel-v1|16d-v1",
  "canonical_payload": {...},
  "digest": "sha3_256:<hex>",
  "sid": "sha3_256:<hex>",
  "oid": "sha3_256:<hex>"
}
```

### Errors
- `UNKNOWN_HASH_ALGO`
- `UNTAGGED_DIGEST`
- `INVALID_ARTIFACT_SCHEMA`

### Invariants
- Canonical payload uses stable key order and UTF-8 encoding.
- Digest tagging is mandatory (`<algo>:<hex>`).

### Collision Language (Normative)
- Deterministic canonicalization is guaranteed.
- Collision resistance is assumed from selected cryptographic hash.
- No claim of global collision impossibility beyond corpus evidence.

## Reconstruction Contract (Normative when reversibility is required)
If full stream reconstruction is required, include metadata:
- `frame_count`
- `frame_lengths`
- `operator_sequences` (or equivalent framing markers)
- `original_stream_hash`

Without this metadata, canonical form is deterministic but not guaranteed lossless.
