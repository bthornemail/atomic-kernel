from dataclasses import dataclass
from typing import Dict

from canonical import DEFAULT_HASH_ALGO, canonical_hash

NORMATIVE_LAYERS = set(range(1, 9))
ADVISORY_LAYERS = set(range(9, 33))


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    reason_code: str
    mode: str
    layer: int
    operation: str
    hash_algo: str
    reason_hash: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "mode": self.mode,
            "layer": self.layer,
            "operation": self.operation,
            "hash_algo": self.hash_algo,
            "reason_hash": self.reason_hash,
        }


def authorize(
    mode: str,
    operation: str,
    layer: int,
    artifact_hash: str,
    hash_algo: str = DEFAULT_HASH_ALGO,
) -> AuthorityDecision:
    op = operation.strip().lower()
    if mode not in {"kernel", "16d"}:
        code = "INVALID_MODE"
        allowed = False
    elif layer < 1 or layer > 32:
        code = "INVALID_LAYER"
        allowed = False
    elif layer in ADVISORY_LAYERS and op in {"mutate", "write", "override"}:
        code = "AUTHORITY_ESCALATION_BLOCKED"
        allowed = False
    elif op not in {"read", "project", "mutate", "write", "override", "verify"}:
        code = "UNKNOWN_OPERATION"
        allowed = False
    else:
        code = "ALLOW"
        allowed = True

    payload = {
        "mode": mode,
        "layer": layer,
        "operation": op,
        "artifact_hash": artifact_hash,
        "reason_code": code,
        "allowed": allowed,
    }
    try:
        reason_hash = canonical_hash(payload, hash_algo=hash_algo)
    except ValueError:
        code = "UNKNOWN_HASH_ALGO"
        allowed = False
        payload["reason_code"] = code
        payload["allowed"] = allowed
        hash_algo = DEFAULT_HASH_ALGO
        reason_hash = canonical_hash(payload, hash_algo=hash_algo)

    return AuthorityDecision(
        allowed=allowed,
        reason_code=code,
        mode=mode,
        layer=layer,
        operation=op,
        hash_algo=hash_algo,
        reason_hash=reason_hash,
    )
