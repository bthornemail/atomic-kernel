import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from canonical import DEFAULT_HASH_ALGO, canonical_hash

SPEC_PATH = Path(__file__).resolve().parent / "spec_v0_utf_ebcdic_layout.json"
_SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

CONTROL_START = int(_SPEC["control_range"]["start"])
CONTROL_END = int(_SPEC["control_range"]["end"])
DIGIT_START = int(_SPEC["data_digit_range"]["start"])
DIGIT_END = int(_SPEC["data_digit_range"]["end"])
RESERVED_START = int(_SPEC["reserved_range"]["start"])
RESERVED_END = int(_SPEC["reserved_range"]["end"])
BEL_CODE = int(_SPEC["sign_rules"]["bel_toggle_code"])
NUL_CODE = int(_SPEC["sign_rules"]["nul_code"])
FS_CODE = int(_SPEC["channels"]["FS"])
GS_CODE = int(_SPEC["channels"]["GS"])
RS_CODE = int(_SPEC["channels"]["RS"])
US_CODE = int(_SPEC["channels"]["US"])
ESC_CODE = 0x27

CANONICALIZATION = "stream-sign-value-v1"
ORBIT_BASE = int(_SPEC["orbit_weight"])
MAX_UNICODE = 0x10FFFF
RADIX_BY_CHANNEL = {
    FS_CODE: 2,
    GS_CODE: 4,
    RS_CODE: 16,
    US_CODE: 60,
}


def _sign_for_code(code: int) -> int:
    if code == BEL_CODE:
        return 0
    for start, end in _SPEC["sign_rules"]["plus_ranges"]:
        if start <= code <= end:
            return 1
    for start, end in _SPEC["sign_rules"]["minus_ranges"]:
        if start <= code <= end:
            return -1
    raise ValueError("SIGN_VALUE_DECODE_ERROR")


@dataclass(frozen=True)
class StreamCanonicalResult:
    canonicalization: str
    frame_values: List[int]
    pattern_number: int
    stream_digest: str
    hash_algo: str
    parser_events: List[Dict[str, object]]

    def as_dict(self) -> Dict[str, object]:
        return {
            "canonicalization": self.canonicalization,
            "frame_values": self.frame_values,
            "pattern_number": self.pattern_number,
            "stream_digest": self.stream_digest,
            "hash_algo": self.hash_algo,
            "parser_events": self.parser_events,
        }


def frame_value(codes: Sequence[int]) -> int:
    total = 0
    bel_count = 0
    for code in codes:
        if code < CONTROL_START or code > CONTROL_END:
            raise ValueError("INVALID_CONTROL_CODE_RANGE")
        if RESERVED_START <= code <= RESERVED_END:
            raise ValueError("RESERVED_CONTROL_CODE")
        if code == BEL_CODE:
            sign = 1 if (bel_count % 2 == 0) else -1
            total += sign * BEL_CODE
            bel_count += 1
            continue
        sign = _sign_for_code(code)
        total += sign * code
    # Residue ties directly to crystal orbit weight W=36.
    return total % ORBIT_BASE


def _decode_digits(digits: Sequence[int], radix: int) -> int:
    value = 0
    for d in digits:
        if d < 0 or d >= radix:
            raise ValueError("SIGN_VALUE_DECODE_ERROR")
        value = value * radix + d
    if value > MAX_UNICODE:
        raise ValueError("SIGN_VALUE_DECODE_ERROR")
    return value


def pattern_number(frame_values: Sequence[int], base: int = ORBIT_BASE) -> int:
    total = 0
    for j, val in enumerate(frame_values):
        if val < 0 or val >= base:
            raise ValueError("SIGN_VALUE_DECODE_ERROR")
        total += val * (base ** j)
    return total


def decode_pattern(value: int, frame_count: int, base: int = ORBIT_BASE) -> List[int]:
    if value < 0 or frame_count < 0:
        raise ValueError("SIGN_VALUE_DECODE_ERROR")
    out: List[int] = []
    rem = value
    for _ in range(frame_count):
        out.append(rem % base)
        rem //= base
    return out


def extract_control_frames(payload: str) -> List[List[int]]:
    # Process only UTF-EBCDIC control plane region (0x00..0x3F).
    frames: List[List[int]] = [[]]
    for ch in payload:
        code = ord(ch)
        if code > CONTROL_END:
            continue
        if code < CONTROL_START:
            raise ValueError("INVALID_CONTROL_CODE_RANGE")
        if RESERVED_START <= code <= RESERVED_END:
            raise ValueError("RESERVED_CONTROL_CODE")
        if code > DIGIT_END:
            raise ValueError("INVALID_CONTROL_CODE_RANGE")
        frames[-1].append(code)
        if code == FS_CODE:
            frames.append([])
    if len(frames) > 1 and frames[-1] == []:
        frames.pop()
    if not frames:
        return [[]]
    return frames


def parse_inband_stream(payload: str) -> List[Dict[str, object]]:
    """
    In-band parser with explicit state machine:
    CONTROL -> ESC_LEN -> ESC_RADIX -> ESC_DATA -> CONTROL
    """
    state = "CONTROL"
    events: List[Dict[str, object]] = []
    esc_len = 0
    esc_radix = 0
    esc_digits: List[int] = []

    for ch in payload:
        code = ord(ch)
        if code > CONTROL_END:
            # Extension bytes are carried but ignored by canonical control parser.
            continue
        if RESERVED_START <= code <= RESERVED_END:
            events.append({"type": "reserved", "code": code})
            state = "CONTROL"
            continue

        if state == "CONTROL":
            if code == NUL_CODE:
                events.append({"type": "null", "code": code})
            elif code == ESC_CODE:
                state = "ESC_LEN"
            elif code in {FS_CODE, GS_CODE, RS_CODE, US_CODE}:
                events.append({"type": "operator", "code": code})
            elif DIGIT_START <= code <= DIGIT_END:
                events.append({"type": "data_digit", "code": code})
            else:
                raise ValueError("INVALID_CONTROL_CODE_RANGE")
            continue

        if state == "ESC_LEN":
            if not (DIGIT_START <= code <= DIGIT_END):
                raise ValueError("SIGN_VALUE_DECODE_ERROR")
            esc_len = code
            state = "ESC_RADIX"
            continue

        if state == "ESC_RADIX":
            if code not in RADIX_BY_CHANNEL:
                raise ValueError("SIGN_VALUE_DECODE_ERROR")
            esc_radix = RADIX_BY_CHANNEL[code]
            esc_digits = []
            if esc_len == 0:
                events.append(
                    {
                        "type": "escaped_literal",
                        "length": esc_len,
                        "radix": esc_radix,
                        "digits": [],
                        "charcode": 0,
                    }
                )
                state = "CONTROL"
            else:
                state = "ESC_DATA"
            continue

        if state == "ESC_DATA":
            if not (DIGIT_START <= code <= DIGIT_END):
                raise ValueError("SIGN_VALUE_DECODE_ERROR")
            esc_digits.append(code)
            if len(esc_digits) == esc_len:
                value = _decode_digits(esc_digits, esc_radix)
                events.append(
                    {
                        "type": "escaped_literal",
                        "length": esc_len,
                        "radix": esc_radix,
                        "digits": list(esc_digits),
                        "charcode": value,
                    }
                )
                state = "CONTROL"
            continue

    if state != "CONTROL":
        raise ValueError("INCOMPLETE_ESCAPE_SEQUENCE")
    return events


def canonicalize_stream(payload: str, hash_algo: str = DEFAULT_HASH_ALGO) -> StreamCanonicalResult:
    events = parse_inband_stream(payload)

    # Build per-frame accumulators from parsed events.
    frame_totals: List[int] = [0]
    frame_bel_counts: List[int] = [0]
    frame_values_raw: List[int] = []
    for ev in events:
        et = ev["type"]
        if et == "reserved":
            frame_values_raw.append(frame_totals[-1])
            frame_totals.append(0)
            frame_bel_counts.append(0)
            continue

        if et == "operator":
            code = int(ev["code"])
            if code == FS_CODE and frame_totals[-1] != 0:
                frame_values_raw.append(frame_totals[-1])
                frame_totals.append(0)
                frame_bel_counts.append(0)
            frame_totals[-1] += _sign_for_code(code) * code
            continue

        if et == "null":
            continue

        if et == "data_digit":
            code = int(ev["code"])
            if code == BEL_CODE:
                sign = 1 if (frame_bel_counts[-1] % 2 == 0) else -1
                frame_totals[-1] += sign * BEL_CODE
                frame_bel_counts[-1] += 1
            else:
                frame_totals[-1] += _sign_for_code(code) * code
            continue

        if et == "escaped_literal":
            # Charcode value (not controlpoint semantics) contributes deterministically.
            frame_totals[-1] += int(ev["charcode"])
            continue

    frame_values_raw.append(frame_totals[-1])
    vals = [v % ORBIT_BASE for v in frame_values_raw]
    number = pattern_number(vals, base=ORBIT_BASE)
    payload_obj = {
        "spec_version": _SPEC["spec_version"],
        "canonicalization": CANONICALIZATION,
        "orbit_weight": ORBIT_BASE,
        "parser_events": events,
        "frames": vals,
        "pattern_number": number,
    }
    digest = canonical_hash(payload_obj, hash_algo=hash_algo)
    return StreamCanonicalResult(
        canonicalization=CANONICALIZATION,
        frame_values=vals,
        pattern_number=number,
        stream_digest=digest,
        hash_algo=hash_algo,
        parser_events=events,
    )
