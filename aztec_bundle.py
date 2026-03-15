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
DEFAULT_ORDERING = "spiral_ccw_outer_to_core"
ORDERING_MODES = {"spiral_ccw_outer_to_core", "index_asc"}
CODEWORD_BITS = {6, 8, 10, 12}

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


def _bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def _bits_to_bytes(bits: str) -> bytes:
    if not bits:
        return b""
    if len(bits) % 8:
        bits = bits + ("0" * (8 - (len(bits) % 8)))
    return bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))


def _guard_reserved_codewords(data: bytes, word_bits: int) -> Tuple[bytes, Dict[str, Any]]:
    bits = _bytes_to_bits(data)
    original_bit_length = len(bits)
    if original_bit_length == 0:
        return data, {"enabled": False, "word_bits": word_bits}

    if word_bits not in CODEWORD_BITS:
        raise ValueError("INVALID_CODEWORD_BITS")

    pad = (word_bits - (len(bits) % word_bits)) % word_bits
    bits_padded = bits + ("0" * pad)
    words = [bits_padded[i : i + word_bits] for i in range(0, len(bits_padded), word_bits)]

    stuffed_zero: List[int] = []
    stuffed_one: List[int] = []
    for i, w in enumerate(words):
        if set(w) == {"0"}:
            words[i] = w[:-1] + "1"
            stuffed_zero.append(i)
        elif set(w) == {"1"}:
            words[i] = w[:-1] + "0"
            stuffed_one.append(i)

    stuffed_bits = "".join(words)
    stuffed_bytes = _bits_to_bytes(stuffed_bits)
    meta = {
        "enabled": True,
        "method": "word-guard-v1",
        "word_bits": word_bits,
        "original_bit_length": original_bit_length,
        "pad_bits": pad,
        "stuffed_zero_indices": stuffed_zero,
        "stuffed_one_indices": stuffed_one,
    }
    return stuffed_bytes, meta


def _unguard_reserved_codewords(data: bytes, meta: Dict[str, Any]) -> bytes:
    if not meta.get("enabled"):
        return data
    word_bits = int(meta.get("word_bits", 0))
    if word_bits not in CODEWORD_BITS:
        raise ValueError("INVALID_CODEWORD_BITS")

    bits = _bytes_to_bits(data)
    words = [bits[i : i + word_bits] for i in range(0, len(bits), word_bits)]
    for idx in meta.get("stuffed_zero_indices", []):
        i = int(idx)
        if i >= len(words):
            raise ValueError("STUFFING_INDEX_OUT_OF_RANGE")
        words[i] = "0" * word_bits
    for idx in meta.get("stuffed_one_indices", []):
        i = int(idx)
        if i >= len(words):
            raise ValueError("STUFFING_INDEX_OUT_OF_RANGE")
        words[i] = "1" * word_bits

    restored_bits = "".join(words)[: int(meta.get("original_bit_length", 0))]
    return _bits_to_bytes(restored_bits)


def build_bundle(
    payload: Dict[str, Any],
    *,
    hash_algo: str = DEFAULT_HASH_ALGO,
    chunk_bytes: int = DEFAULT_CHUNK_BYTES,
    ordering: str = DEFAULT_ORDERING,
    layers_mode: str = "auto",
    ecc_ratio: float = 0.23,
    min_check_words: int = 3,
    codeword_bits: int = 8,
    stuffing: bool = True,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if hash_algo not in SUPPORTED_HASH_ALGOS:
        raise ValueError("UNKNOWN_HASH_ALGO")
    if chunk_bytes < 256:
        raise ValueError("INVALID_CHUNK_BYTES")
    if ordering not in ORDERING_MODES:
        raise ValueError("UNKNOWN_ORDERING")
    if layers_mode not in {"compact", "full", "auto"}:
        raise ValueError("INVALID_LAYERS_MODE")
    if codeword_bits not in CODEWORD_BITS:
        raise ValueError("INVALID_CODEWORD_BITS")
    if ecc_ratio < 0.0 or ecc_ratio > 1.0:
        raise ValueError("INVALID_ECC_RATIO")
    if min_check_words < 1:
        raise ValueError("INVALID_MIN_CHECK_WORDS")

    canonical = _canonical_json_bytes(payload)
    compressed_raw = zlib.compress(canonical, level=9)
    compressed, stuffing_meta = (
        _guard_reserved_codewords(compressed_raw, codeword_bits) if stuffing else (compressed_raw, {"enabled": False, "word_bits": codeword_bits})
    )
    encoded = _b64u_encode(compressed)
    payload_digest = digest_bytes(canonical, hash_algo=hash_algo)
    compressed_raw_digest = digest_bytes(compressed_raw, hash_algo=hash_algo)
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
        if ordering == "spiral_ccw_outer_to_core":
            order_index = len(data_parts) - 1 - idx
        else:
            order_index = idx
        chunk_payload = {
            "type": CHUNK_TYPE,
            "bundle_id": bundle_id,
            "index": idx,
            "order_index": order_index,
            "total": len(data_parts),
            "hash_algo": hash_algo,
            "ordering": ordering,
            "data": part,
        }
        chunk_payload["chunk_digest"] = digest_bytes(
            _canonical_json_bytes(chunk_payload), hash_algo=hash_algo
        )
        chunks.append(chunk_payload)

    data_words = len(chunks)
    target_check_words = max(min_check_words, int(round(data_words * ecc_ratio + 3)))
    descriptor = {
        "bundle_id": bundle_id,
        "chunk_count": len(chunks),
        "data_words": data_words,
        "check_words": target_check_words,
        "ordering": ordering,
        "hash_algo": hash_algo,
    }
    descriptor_digest = digest_bytes(_canonical_json_bytes(descriptor), hash_algo=hash_algo)

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
        "compressed_raw_digest": compressed_raw_digest,
        "compressed_digest": compressed_digest,
        "original_bytes": len(canonical),
        "compressed_raw_bytes": len(compressed_raw),
        "compressed_bytes": len(compressed),
        "ordering": ordering,
        "aztec_profile": {
            "layers_mode": layers_mode,
            "ecc_policy": {
                "ratio": ecc_ratio,
                "min_check_words": min_check_words,
                "target_check_words": target_check_words,
            },
            "codeword_bits": codeword_bits,
            "bit_order": "msb-first",
        },
        "stuffing": stuffing_meta,
        "descriptor_parity": {
            "chunk_count": len(chunks),
            "data_words": data_words,
            "check_words": target_check_words,
            "descriptor_digest": descriptor_digest,
        },
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
    expected_compressed_raw_digest = str(manifest.get("compressed_raw_digest", ""))
    expected_compressed_digest = str(manifest.get("compressed_digest", ""))
    ordering = str(manifest.get("ordering", DEFAULT_ORDERING))
    stuffing_meta = manifest.get("stuffing", {"enabled": False})

    if hash_algo not in SUPPORTED_HASH_ALGOS:
        raise ValueError("UNKNOWN_HASH_ALGO")
    if total_chunks < 1:
        raise ValueError("INVALID_CHUNK_COUNT")
    if ordering not in ORDERING_MODES:
        raise ValueError("UNKNOWN_ORDERING")

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
        if str(c.get("ordering", "")) != ordering:
            raise ValueError("CHUNK_ORDERING_MISMATCH")

        chk = dict(c)
        chunk_digest = str(chk.pop("chunk_digest", ""))
        if digest_bytes(_canonical_json_bytes(chk), hash_algo=hash_algo) != chunk_digest:
            raise ValueError("CHUNK_DIGEST_MISMATCH")

        encoded_parts.append(str(c.get("data", "")))

    encoded = "".join(encoded_parts)
    compressed = _b64u_decode(encoded)
    if digest_bytes(compressed, hash_algo=hash_algo) != expected_compressed_digest:
        raise ValueError("COMPRESSED_DIGEST_MISMATCH")

    compressed_raw = _unguard_reserved_codewords(compressed, stuffing_meta)
    if expected_compressed_raw_digest and digest_bytes(
        compressed_raw, hash_algo=hash_algo
    ) != expected_compressed_raw_digest:
        raise ValueError("COMPRESSED_RAW_DIGEST_MISMATCH")

    canonical = zlib.decompress(compressed_raw)
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
        ordering=args.ordering,
        layers_mode=args.layers_mode,
        ecc_ratio=args.ecc_ratio,
        min_check_words=args.min_check_words,
        codeword_bits=args.codeword_bits,
        stuffing=not args.no_stuffing,
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


def cmd_pack_proof(args: argparse.Namespace) -> int:
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    payloads = {
        "control-codes": {
            "type": "ak.control.codes.v1",
            "range": "0x00..0x3B",
            "reserved": "0x3C..0x3F",
            "channels": {"FS": "0x1C", "GS": "0x1D", "RS": "0x1E", "US": "0x1F"},
            "canonicalization": "stream-sign-value-v1",
            "orbit_base": 36,
        },
        "algorithms": {
            "type": "ak.algorithms.v1",
            "spec_version": SPEC_VERSION,
            "algorithms": ALGORITHM_IDS,
            "canonicalization": "stream-sign-value-v1",
            "hash_algo_default": args.hash_algo,
        },
        "full": replay_artifact(
            mode=args.mode,
            width=args.width,
            seed=int(args.seed, 0),
            steps=args.steps,
            hash_algo=args.hash_algo,
        ).as_dict(),
    }

    index: Dict[str, Any] = {}
    for name, payload in payloads.items():
        manifest, chunks = build_bundle(
            payload,
            hash_algo=args.hash_algo,
            chunk_bytes=args.chunk_bytes,
            ordering=args.ordering,
            layers_mode=args.layers_mode,
            ecc_ratio=args.ecc_ratio,
            min_check_words=args.min_check_words,
            codeword_bits=args.codeword_bits,
            stuffing=not args.no_stuffing,
        )
        pdir = out / name
        (pdir / "chunks").mkdir(parents=True, exist_ok=True)
        _write_json(pdir / "manifest.json", manifest)
        for c in chunks:
            _write_json(pdir / "chunks" / f"chunk-{c['index']:04d}.json", c)
        lines = "\n".join(
            json.dumps(c, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            for c in chunks
        )
        (pdir / "chunks.ndjson").write_text(lines + ("\n" if lines else ""), encoding="utf-8")
        index[name] = {
            "manifest": str((pdir / "manifest.json").as_posix()),
            "chunks_ndjson": str((pdir / "chunks.ndjson").as_posix()),
            "total_chunks": manifest["total_chunks"],
            "payload_digest": manifest["payload_digest"],
        }

    _write_json(out / "index.json", index)
    print(json.dumps({"ok": True, "outdir": str(out), "artifacts": index}, sort_keys=True, separators=(",", ":")))
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
    pack.add_argument("--ordering", default=DEFAULT_ORDERING, choices=sorted(ORDERING_MODES))
    pack.add_argument("--layers-mode", default="auto", choices=["compact", "full", "auto"])
    pack.add_argument("--ecc-ratio", type=float, default=0.23)
    pack.add_argument("--min-check-words", type=int, default=3)
    pack.add_argument("--codeword-bits", type=int, default=8, choices=sorted(CODEWORD_BITS))
    pack.add_argument("--no-stuffing", action="store_true")
    pack.add_argument("--outdir", default="aztec-bundle")
    pack.set_defaults(func=cmd_pack_replay)

    proof = sub.add_parser("pack-proof", help="Create proof-layer bundles (control, algorithms, full)")
    proof.add_argument("--mode", default="16d", choices=["kernel", "16d"])
    proof.add_argument("--width", type=int, default=32)
    proof.add_argument("--seed", default="0x0B7406AC")
    proof.add_argument("--steps", type=int, default=64)
    proof.add_argument("--hash-algo", default=DEFAULT_HASH_ALGO, choices=sorted(SUPPORTED_HASH_ALGOS))
    proof.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES)
    proof.add_argument("--ordering", default=DEFAULT_ORDERING, choices=sorted(ORDERING_MODES))
    proof.add_argument("--layers-mode", default="auto", choices=["compact", "full", "auto"])
    proof.add_argument("--ecc-ratio", type=float, default=0.23)
    proof.add_argument("--min-check-words", type=int, default=3)
    proof.add_argument("--codeword-bits", type=int, default=8, choices=sorted(CODEWORD_BITS))
    proof.add_argument("--no-stuffing", action="store_true")
    proof.add_argument("--outdir", default="aztec-proof")
    proof.set_defaults(func=cmd_pack_proof)

    unpack = sub.add_parser("unpack", help="Recover canonical payload from chunk bundle")
    unpack.add_argument("--indir", default="aztec-bundle")
    unpack.add_argument("--output", default="aztec-bundle/recovered.json")
    unpack.set_defaults(func=cmd_unpack)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
