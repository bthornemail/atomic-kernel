import hashlib
import json
from typing import Any

DEFAULT_HASH_ALGO = "sha3_256"
SUPPORTED_HASH_ALGOS = {"sha256", "sha3_256"}


def canonical_json_bytes(payload: Any) -> bytes:
    """Canonical JSON bytes for deterministic hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_json_text(payload: Any) -> str:
    return canonical_json_bytes(payload).decode("utf-8")


def digest_bytes(data: bytes, hash_algo: str = DEFAULT_HASH_ALGO) -> str:
    if hash_algo == "sha256":
        h = hashlib.sha256(data).hexdigest()
    elif hash_algo == "sha3_256":
        h = hashlib.sha3_256(data).hexdigest()
    else:
        raise ValueError("UNKNOWN_HASH_ALGO")
    return f"{hash_algo}:{h}"


def digest_text(text: str, hash_algo: str = DEFAULT_HASH_ALGO) -> str:
    return digest_bytes(text.encode("utf-8"), hash_algo=hash_algo)


def canonical_hash(payload: Any, hash_algo: str = DEFAULT_HASH_ALGO) -> str:
    return digest_bytes(canonical_json_bytes(payload), hash_algo=hash_algo)


def parse_tagged_digest(tagged: str) -> tuple[str, str]:
    if not isinstance(tagged, str) or ":" not in tagged:
        raise ValueError("UNTAGGED_DIGEST")
    algo, hexd = tagged.split(":", 1)
    if algo not in SUPPORTED_HASH_ALGOS:
        raise ValueError("UNKNOWN_HASH_ALGO")
    if len(hexd) == 0:
        raise ValueError("UNTAGGED_DIGEST")
    return algo, hexd


def verify_digest(data: bytes, tagged_digest: str, allow_legacy_untagged: bool = False) -> bool:
    if allow_legacy_untagged and isinstance(tagged_digest, str) and ":" not in tagged_digest:
        # Legacy support: treat bare hex as sha256.
        return hashlib.sha256(data).hexdigest() == tagged_digest

    algo, _ = parse_tagged_digest(tagged_digest)
    return digest_bytes(data, hash_algo=algo) == tagged_digest
