"""Identity API wrappers for package consumers."""

from __future__ import annotations

from canonical import DEFAULT_HASH_ALGO
from identity import oid, sid_for_object

__all__ = ["sid_for_object", "oid", "DEFAULT_HASH_ALGO"]
