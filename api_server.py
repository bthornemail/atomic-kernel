import json
import subprocess
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

from authority import authorize
from aztec_bundle import build_bundle
from canonical import DEFAULT_HASH_ALGO, canonical_hash
from control_plane import CANONICALIZATION, validate_control_plane
from identity import GENESIS, ObjectChain, sid
from oracle_parity import check_parity
from replay_engine import replay_artifact
from stream_sign_value import canonicalize_stream

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "bin" / "python"
RENDERER = ROOT / "render_aztec_payload.py"


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _seed_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0)
    raise ValueError("invalid seed")


def _render_aztec_png_data_url(
    payload_text: str,
    *,
    ec_percent: int = 23,
    module_size: int = 4,
    border: int = 2,
) -> str:
    if not VENV_PY.exists() or not RENDERER.exists():
        raise ValueError("RENDERER_UNAVAILABLE")
    proc = subprocess.run(
        [
            str(VENV_PY),
            str(RENDERER),
            "--ec-percent",
            str(ec_percent),
            "--module-size",
            str(module_size),
            "--border",
            str(border),
        ],
        input=payload_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise ValueError("RENDER_FAILED")
    b64 = base64.b64encode(proc.stdout).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _identity_verify(
    mode: str,
    seed: int,
    ticks: List[int],
    hash_algo: str,
    allow_legacy_untagged: bool,
) -> Dict[str, Any]:
    if mode not in {"kernel", "16d"}:
        payload = {"ok": False, "reason_code": "INVALID_MODE", "records": []}
        payload["result_hash"] = canonical_hash(payload, hash_algo=hash_algo)
        return payload

    chain = ObjectChain(seed, hash_algo=hash_algo)
    records = [chain.step(int(t)) for t in ticks]
    verified = all(chain.verify(r, allow_legacy_untagged=allow_legacy_untagged) for r in records)

    payload = {
        "ok": verified,
        "reason_code": "OK" if verified else "UNTAGGED_DIGEST",
        "mode": mode,
        "hash_algo": hash_algo,
        "sid": sid("world.object", f"0x{seed & 0xFFFF:04X}", hash_algo=hash_algo),
        "records": [
            {
                "n": r["n"],
                "clock": r["clock"],
                "hash_algo": r["hash_algo"],
                "sid": r["sid"],
                "oid": r["oid"],
                "prev_oid": r["prev_oid"],
                "state_hex": r["hex"],
            }
            for r in records
        ],
    }
    payload["result_hash"] = canonical_hash(payload, hash_algo=hash_algo)
    return payload


class AtomicKernelHandler(BaseHTTPRequestHandler):
    server_version = "AtomicKernelHTTP/1.1"

    def do_GET(self) -> None:
        if self.path in {"/", "/dashboard"}:
            html = (ROOT / "dashboard.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path in {"/message-demo"}:
            html = (ROOT / "message-demo.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path in {"/message-demo-static"}:
            html = (ROOT / "message-demo-static.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/js/atomic-kernel.js":
            js = (ROOT / "js" / "atomic-kernel.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(js)))
            self.end_headers()
            self.wfile.write(js)
            return
        _json_response(self, 404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        try:
            data = _read_json(self)
        except Exception:
            _json_response(self, 400, {"error": "INVALID_JSON"})
            return

        hash_algo = str(data.get("hash_algo", DEFAULT_HASH_ALGO))

        if self.path == "/replay":
            mode = str(data.get("mode", "kernel"))
            width = int(data.get("width", 16))
            steps = int(data.get("steps", 16))
            try:
                seed = _seed_int(data.get("seed", 1))
            except Exception:
                _json_response(self, 400, {"error": "INVALID_SEED"})
                return

            artifact = replay_artifact(mode=mode, width=width, seed=seed, steps=steps, hash_algo=hash_algo)
            _json_response(self, 200, artifact.as_dict())
            return

        if self.path == "/replay/hash":
            mode = str(data.get("mode", "kernel"))
            width = int(data.get("width", 16))
            steps = int(data.get("steps", 16))
            try:
                seed = _seed_int(data.get("seed", 1))
            except Exception:
                _json_response(self, 400, {"error": "INVALID_SEED"})
                return

            artifact = replay_artifact(mode=mode, width=width, seed=seed, steps=steps, hash_algo=hash_algo)
            _json_response(
                self,
                200,
                {
                    "mode": artifact.mode,
                    "law_version": artifact.law_version,
                    "hash_algo": artifact.hash_algo,
                    "digest": artifact.digest,
                    "width": artifact.width,
                    "seed_hex": artifact.seed_hex,
                    "steps": artifact.steps,
                    "replay_hash": artifact.replay_hash,
                    "canonical_json": artifact.canonical_json,
                },
            )
            return

        if self.path == "/control-plane/validate":
            mode = str(data.get("mode", "kernel"))
            payload = str(data.get("payload", ""))
            canonicalization = str(data.get("canonicalization", CANONICALIZATION))
            result = validate_control_plane(
                payload,
                mode=mode,
                hash_algo=hash_algo,
                canonicalization=canonicalization,
            )
            _json_response(self, 200, result.as_dict())
            return

        if self.path == "/stream/canonicalize":
            payload = str(data.get("payload", ""))
            try:
                out = canonicalize_stream(payload, hash_algo=hash_algo).as_dict()
                _json_response(self, 200, out)
            except ValueError as exc:
                _json_response(self, 200, {"ok": False, "reason_code": str(exc)})
            return

        if self.path == "/identity/verify":
            mode = str(data.get("mode", "kernel"))
            ticks = data.get("ticks", [0, 8, 16])
            allow_legacy_untagged = bool(data.get("allow_legacy_untagged", False))
            try:
                seed = _seed_int(data.get("seed", 1))
                tick_list = [int(v) for v in ticks]
            except Exception:
                _json_response(self, 400, {"error": "INVALID_IDENTITY_INPUT"})
                return
            result = _identity_verify(
                mode=mode,
                seed=seed,
                ticks=tick_list,
                hash_algo=hash_algo,
                allow_legacy_untagged=allow_legacy_untagged,
            )
            _json_response(self, 200, result)
            return

        if self.path == "/authority/check":
            mode = str(data.get("mode", "kernel"))
            operation = str(data.get("operation", "verify"))
            layer = int(data.get("layer", 1))
            artifact_hash = str(data.get("artifact_hash", GENESIS))
            decision = authorize(
                mode=mode,
                operation=operation,
                layer=layer,
                artifact_hash=artifact_hash,
                hash_algo=hash_algo,
            )
            _json_response(self, 200, decision.as_dict())
            return

        if self.path == "/oracle/parity":
            try:
                width = int(data.get("width", 16))
                seed_hex = str(data.get("seed", "0x06AC"))
                steps = int(data.get("steps", 16))
                out = check_parity(width=width, seed_hex=seed_hex, steps=steps, hash_algo=hash_algo)
                _json_response(self, 200, out)
            except Exception:
                _json_response(self, 200, {"ok": False, "reason_code": "ORACLE_ERROR"})
            return

        if self.path == "/aztec/render":
            try:
                artifact = data.get("artifact")
                if not isinstance(artifact, dict):
                    _json_response(self, 200, {"ok": False, "reason_code": "INVALID_ARTIFACT"})
                    return
                hash_algo = str(data.get("hash_algo", DEFAULT_HASH_ALGO))
                chunk_bytes = int(data.get("chunk_bytes", 900))
                ec_percent = int(data.get("ec_percent", 23))
                module_size = int(data.get("module_size", 4))
                border = int(data.get("border", 2))

                manifest, chunks = build_bundle(
                    artifact,
                    hash_algo=hash_algo,
                    chunk_bytes=chunk_bytes,
                )

                images = []
                for c in chunks:
                    chunk_text = json.dumps(
                        c,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                    data_url = _render_aztec_png_data_url(
                        chunk_text,
                        ec_percent=ec_percent,
                        module_size=module_size,
                        border=border,
                    )
                    images.append(
                        {
                            "index": c["index"],
                            "order_index": c.get("order_index", c["index"]),
                            "chunk_digest": c["chunk_digest"],
                            "data_url": data_url,
                        }
                    )

                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "bundle_id": manifest["bundle_id"],
                        "manifest_digest": manifest["manifest_digest"],
                        "payload_digest": manifest["payload_digest"],
                        "total_chunks": manifest["total_chunks"],
                        "images": images,
                    },
                )
            except ValueError as exc:
                _json_response(self, 200, {"ok": False, "reason_code": str(exc)})
            except Exception:
                _json_response(self, 200, {"ok": False, "reason_code": "AZTEC_RENDER_ERROR"})
            return

        _json_response(self, 404, {"error": "NOT_FOUND"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), AtomicKernelHandler)
    print(f"Atomic Kernel API listening at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
