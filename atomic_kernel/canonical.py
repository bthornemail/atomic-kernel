"""Core canonicalization API for message-level artifacts."""

from __future__ import annotations

from typing import Any, Dict

from canonical import DEFAULT_HASH_ALGO, MATH_ID_LAW_VERSION, canonical_math_id
from identity import ObjectChain
from replay_engine import replay_artifact

from .stream import canonicalize_digits, encode_to_control_stream


def canonicalize(
    message: str,
    *,
    tick: int = 8,
    hash_algo: str = DEFAULT_HASH_ALGO,
) -> Dict[str, Any]:
    """Generate a deterministic message artifact from text content."""
    digits = encode_to_control_stream(message)
    c = canonicalize_digits(digits, hash_algo=hash_algo)
    seed = (int(c["pattern_number"]) % 65535) + 1

    chain = ObjectChain(seed, hash_algo=hash_algo)
    rec = chain.step(tick)
    replay = replay_artifact("kernel", 16, seed, 8, hash_algo=hash_algo)

    return {
        "message": message,
        "control_digits": digits,
        "canonicalization": c["canonicalization"],
        "hash_algo": hash_algo,
        "stream_digest": c["stream_digest"],
        "pattern_number": c["pattern_number"],
        "frame_values": c["frame_values"],
        "seed_hex": f"0x{seed:04X}",
        "tick": tick,
        "sid": rec["sid"],
        "clock": rec["clock"],
        "oid": rec["oid"],
        "replay_hash": replay.replay_hash,
        "math_law_version": MATH_ID_LAW_VERSION,
        "math_id_v2": canonical_math_id(
            {
                "message": message,
                "control_digits": digits,
                "pattern_number": c["pattern_number"],
                "tick": tick,
                "seed_hex": f"0x{seed:04X}",
            }
        ),
    }
