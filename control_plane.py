from dataclasses import dataclass
from typing import Dict, List

from canonical import DEFAULT_HASH_ALGO, canonical_hash
from stream_sign_value import CANONICALIZATION, canonicalize_stream

FS = "\x1c"
GS = "\x1d"
RS = "\x1e"
US = "\x1f"
ALLOWED = {FS, GS, RS, US}
ORDER = {FS: 0, GS: 1, RS: 2, US: 3}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason_code: str
    mode: str
    hash_algo: str
    canonicalization: str
    parsed: Dict[str, object]
    result_hash: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "ok": self.ok,
            "reason_code": self.reason_code,
            "mode": self.mode,
            "hash_algo": self.hash_algo,
            "canonicalization": self.canonicalization,
            "parsed": self.parsed,
            "result_hash": self.result_hash,
        }


def _contains_disallowed_controls(payload: str) -> bool:
    for ch in payload:
        if ord(ch) < 32 and ch not in {"\n", "\r", "\t"} and ch not in ALLOWED and ord(ch) != 0x07:
            return True
    return False


def parse_control_plane(payload: str) -> Dict[str, object]:
    if not isinstance(payload, str):
        return {"ok": False, "reason_code": "INVALID_TYPE", "parsed": {}}
    if payload == "":
        return {"ok": False, "reason_code": "EMPTY_REQUIRED_SEGMENT", "parsed": {}}
    if _contains_disallowed_controls(payload):
        return {"ok": False, "reason_code": "UNKNOWN_TOKEN", "parsed": {}}

    level = 0
    for ch in payload:
        if ch not in ALLOWED:
            continue
        if ch == FS:
            level = 0
            continue
        rank = ORDER[ch]
        if rank < level:
            return {"ok": False, "reason_code": "OUT_OF_ORDER_SEPARATOR", "parsed": {}}
        level = rank

    fs_groups = payload.split(FS)
    if any(group == "" for group in fs_groups):
        return {"ok": False, "reason_code": "EMPTY_REQUIRED_SEGMENT", "parsed": {}}

    out: List[Dict[str, object]] = []
    for fs_idx, fs_group in enumerate(fs_groups):
        gs_groups = fs_group.split(GS)
        if any(group == "" for group in gs_groups):
            return {"ok": False, "reason_code": "EMPTY_REQUIRED_SEGMENT", "parsed": {}}

        gs_out: List[Dict[str, object]] = []
        for gs_idx, gs_group in enumerate(gs_groups):
            rs_groups = gs_group.split(RS)
            if any(group == "" for group in rs_groups):
                return {"ok": False, "reason_code": "EMPTY_REQUIRED_SEGMENT", "parsed": {}}

            rs_out: List[Dict[str, object]] = []
            for rs_idx, rs_group in enumerate(rs_groups):
                units = rs_group.split(US)
                if any(unit == "" for unit in units):
                    return {"ok": False, "reason_code": "EMPTY_REQUIRED_SEGMENT", "parsed": {}}

                rs_out.append({"rs_index": rs_idx, "units": units})

            gs_out.append({"gs_index": gs_idx, "records": rs_out})

        out.append({"fs_index": fs_idx, "groups": gs_out})

    return {"ok": True, "reason_code": "OK", "parsed": {"segments": out}}


def validate_control_plane(
    payload: str,
    mode: str = "kernel",
    hash_algo: str = DEFAULT_HASH_ALGO,
    canonicalization: str = CANONICALIZATION,
) -> ValidationResult:
    parsed_result = parse_control_plane(payload)
    ok = bool(parsed_result["ok"])
    reason_code = str(parsed_result["reason_code"])

    if mode not in {"kernel", "16d"}:
        ok = False
        reason_code = "INVALID_MODE"

    if canonicalization != CANONICALIZATION:
        ok = False
        reason_code = "UNSUPPORTED_CANONICALIZATION"

    parsed = parsed_result["parsed"] if ok else {}

    stream_obj = {}
    if ok:
        try:
            stream = canonicalize_stream(payload, hash_algo=hash_algo)
            stream_obj = stream.as_dict()
        except ValueError as exc:
            ok = False
            reason_code = str(exc)
            stream_obj = {}

    payload_obj = {
        "mode": mode,
        "hash_algo": hash_algo,
        "canonicalization": canonicalization,
        "payload": payload,
        "ok": ok,
        "reason_code": reason_code,
        "parsed": parsed,
        "stream": stream_obj,
    }

    try:
        result_hash = canonical_hash(payload_obj, hash_algo=hash_algo)
    except ValueError:
        ok = False
        reason_code = "UNKNOWN_HASH_ALGO"
        payload_obj["ok"] = ok
        payload_obj["reason_code"] = reason_code
        payload_obj["stream"] = {}
        result_hash = canonical_hash(payload_obj, hash_algo=DEFAULT_HASH_ALGO)
        hash_algo = DEFAULT_HASH_ALGO

    if stream_obj:
        parsed = {**parsed, "stream": stream_obj}

    return ValidationResult(
        ok=ok,
        reason_code=reason_code,
        mode=mode,
        hash_algo=hash_algo,
        canonicalization=canonicalization,
        parsed=parsed,
        result_hash=result_hash,
    )
