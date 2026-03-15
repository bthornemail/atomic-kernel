#!/usr/bin/env python3
"""Deterministic Aztec payload bundle builder for Atomic Kernel artifacts.

This module does not render barcode images directly. It emits compact JSON
records that can be encoded into Aztec symbols by external tools.
"""

from __future__ import annotations

import argparse
import base64
import json
import zlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

from canonical import DEFAULT_HASH_ALGO, SUPPORTED_HASH_ALGOS, digest_bytes
from replay_engine import replay_artifact

SPEC_VERSION = "ak.spec.v1"
BUNDLE_TYPE = "ak.aztec.bundle.v1"
CHUNK_TYPE = "ak.aztec.chunk.v1"
DEFAULT_CHUNK_BYTES = 1200

ALGORITHM_IDS = {
    "extract": "extract_control_stream.v1",
    "parse": "parse_orbit_channels.v1",
    "reduce": "reduce_orbit36.v1",
    "emit": "emit_propagation_artifact.v1",
}


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64u_decode(text: str) -> bytes:
    padding = "=" * ((4 - (len(text) % 4)) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _split_chunks(text: str, chunk_bytes: int) -> List[str]:
    raw = text.encode("utf-8")
    parts = []
    for start in range(0, len(raw), chunk_bytes):
        parts.append(raw[start : start + chunk_bytes].decode("utf-8"))
    return parts


def build_bundle(
    payload: Dict[str, Any],
    *,
    hash_algo: str = DEFAULT_HASH_ALGO,
    chunk_bytes: int = DEFAULT_CHUNK_BYTES,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if hash_algo not in SUPPORTED_HASH_ALGOS:
        raise ValueError("UNKNOWN_HASH_ALGO")
    if chunk_bytes < 256:
        raise ValueError("INVALID_CHUNK_BYTES")

    canonical = _canonical_json_bytes(payload)
    compressed = zlib.compress(canonical, level=9)
    encoded = _b64u_encode(compressed)
    payload_digest = digest_bytes(canonical, hash_algo=hash_algo)
    compressed_digest = digest_bytes(compressed, hash_algo=hash_algo)

    data_parts = _split_chunks(encoded, chunk_bytes)
    if not data_parts:
        data_parts = [""]

    bundle_seed = _canonical_json_bytes(
        {
            "payload_digest": payload_digest,
            "compressed_digest": compressed_digest,
            "parts": len(data_parts),
            "chunk_bytes": chunk_bytes,
            "hash_algo": hash_algo,
        }
    )
    bundle_id = digest_bytes(bundle_seed, hash_algo=hash_algo)

    chunks: List[Dict[str, Any]] = []
    for idx, part in enumerate(data_parts):
        chunk_payload = {
            "type": CHUNK_TYPE,
            "bundle_id": bundle_id,
            "index": idx,
            "total": len(data_parts),
            "hash_algo": hash_algo,
            "data": part,
        }
        chunk_payload["chunk_digest"] = digest_bytes(
            _canonical_json_bytes(chunk_payload), hash_algo=hash_algo
        )
        chunks.append(chunk_payload)

    manifest = {
        "type": BUNDLE_TYPE,
        "spec_version": SPEC_VERSION,
        "hash_algo": hash_algo,
        "canonicalization": "stream-sign-value-v1",
        "algorithms": ALGORITHM_IDS,
        "payload_encoding": "zlib+base64url+canonical-json",
        "bundle_id": bundle_id,
        "chunk_bytes": chunk_bytes,
        "total_chunks": len(chunks),
        "payload_digest": payload_digest,
        "compressed_digest": compressed_digest,
        "original_bytes": len(canonical),
        "compressed_bytes": len(compressed),
    }
    manifest["manifest_digest"] = digest_bytes(
        _canonical_json_bytes(manifest), hash_algo=hash_algo
    )
    return manifest, chunks


def recover_bundle(
    manifest: Dict[str, Any],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    hash_algo = str(manifest.get("hash_algo", DEFAULT_HASH_ALGO))
    bundle_id = str(manifest.get("bundle_id", ""))
    total_chunks = int(manifest.get("total_chunks", -1))
    expected_payload_digest = str(manifest.get("payload_digest", ""))
    expected_compressed_digest = str(manifest.get("compressed_digest", ""))

    if hash_algo not in SUPPORTED_HASH_ALGOS:
        raise ValueError("UNKNOWN_HASH_ALGO")
    if total_chunks < 1:
        raise ValueError("INVALID_CHUNK_COUNT")

    by_index = {int(c.get("index", -1)): c for c in chunks}
    if len(by_index) != total_chunks:
        raise ValueError("MISSING_CHUNKS")

    encoded_parts: List[str] = []
    for idx in range(total_chunks):
        if idx not in by_index:
            raise ValueError("MISSING_CHUNKS")
        c = by_index[idx]
        if str(c.get("bundle_id")) != bundle_id:
            raise ValueError("BUNDLE_ID_MISMATCH")
        if int(c.get("total", -1)) != total_chunks:
            raise ValueError("CHUNK_TOTAL_MISMATCH")

        chk = dict(c)
        chunk_digest = str(chk.pop("chunk_digest", ""))
        if digest_bytes(_canonical_json_bytes(chk), hash_algo=hash_algo) != chunk_digest:
            raise ValueError("CHUNK_DIGEST_MISMATCH")

        encoded_parts.append(str(c.get("data", "")))

    encoded = "".join(encoded_parts)
    compressed = _b64u_decode(encoded)
    if digest_bytes(compressed, hash_algo=hash_algo) != expected_compressed_digest:
        raise ValueError("COMPRESSED_DIGEST_MISMATCH")

    canonical = zlib.decompress(compressed)
    if digest_bytes(canonical, hash_algo=hash_algo) != expected_payload_digest:
        raise ValueError("PAYLOAD_DIGEST_MISMATCH")

    return json.loads(canonical.decode("utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def cmd_pack_replay(args: argparse.Namespace) -> int:
    artifact = replay_artifact(
        mode=args.mode,
        width=args.width,
        seed=int(args.seed, 0),
        steps=args.steps,
        hash_algo=args.hash_algo,
    ).as_dict()

    manifest, chunks = build_bundle(
        artifact,
        hash_algo=args.hash_algo,
        chunk_bytes=args.chunk_bytes,
    )
    out = Path(args.outdir)
    (out / "chunks").mkdir(parents=True, exist_ok=True)
    _write_json(out / "manifest.json", manifest)
    for c in chunks:
        _write_json(out / "chunks" / f"chunk-{c['index']:04d}.json", c)

    lines = "\n".join(
        json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for c in chunks
    )
    (out / "chunks.ndjson").write_text(lines + ("\n" if lines else ""), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "outdir": str(out),
                "bundle_id": manifest["bundle_id"],
                "total_chunks": manifest["total_chunks"],
                "hash_algo": manifest["hash_algo"],
                "note": "Encode each chunk-*.json (or each NDJSON line) into one Aztec symbol.",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def cmd_unpack(args: argparse.Namespace) -> int:
    indir = Path(args.indir)
    manifest = json.loads((indir / "manifest.json").read_text(encoding="utf-8"))
    chunks_dir = indir / "chunks"
    chunks = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(chunks_dir.glob("chunk-*.json"))
    ]
    payload = recover_bundle(manifest, chunks)
    out = Path(args.output)
    out.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(out),
                "payload_digest": manifest["payload_digest"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomic Kernel Aztec bundle tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pack = sub.add_parser("pack-replay", help="Create Aztec chunk bundle from replay artifact")
    pack.add_argument("--mode", default="16d", choices=["kernel", "16d"])
    pack.add_argument("--width", type=int, default=32)
    pack.add_argument("--seed", default="0x0B7406AC")
    pack.add_argument("--steps", type=int, default=64)
    pack.add_argument("--hash-algo", default=DEFAULT_HASH_ALGO, choices=sorted(SUPPORTED_HASH_ALGOS))
    pack.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES)
    pack.add_argument("--outdir", default="aztec-bundle")
    pack.set_defaults(func=cmd_pack_replay)

    unpack = sub.add_parser("unpack", help="Recover canonical payload from chunk bundle")
    unpack.add_argument("--indir", default="aztec-bundle")
    unpack.add_argument("--output", default="aztec-bundle/recovered.json")
    unpack.set_defaults(func=cmd_unpack)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
