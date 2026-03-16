"""Message to control-stream helpers for package consumers."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from canonical import DEFAULT_HASH_ALGO
from stream_sign_value import canonicalize_stream


def _cp_to_digits(cp: int) -> List[int]:
    if cp == 0:
        return [0]
    out: List[int] = []
    n = cp
    while n > 0:
        n, d = divmod(n, 60)
        out.append(d)
    return list(reversed(out))


def encode_to_control_stream(message: str) -> List[int]:
    """Encode text into base-60 control digits, separated by FS (0x1C)."""
    digits: List[int] = []
    for ch in message:
        cp = ord(ch)
        digits.extend(_cp_to_digits(cp))
        digits.append(0x1C)
    if digits and digits[-1] == 0x1C:
        digits.pop()
    return digits


def canonicalize_digits(
    digits: Sequence[int],
    *,
    hash_algo: str = DEFAULT_HASH_ALGO,
) -> Dict[str, Any]:
    """Canonicalize already-encoded control digits."""
    payload = "".join(chr(int(d)) for d in digits)
    out = canonicalize_stream(payload, hash_algo=hash_algo)
    return {
        "canonicalization": out.canonicalization,
        "frame_values": out.frame_values,
        "pattern_number": out.pattern_number,
        "stream_digest": out.stream_digest,
        "hash_algo": out.hash_algo,
    }
