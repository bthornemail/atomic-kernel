import json
import os
import sys
import threading
import time
import unittest
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import run_server
from authority import authorize
from aztec_bundle import build_bundle, recover_bundle
from canonical import canonical_hash, digest_bytes, parse_tagged_digest
from control_plane import validate_control_plane
from replay_engine import replay_artifact
from stream_sign_value import (
    ORBIT_BASE,
    canonicalize_stream,
    decode_pattern,
    frame_value,
    parse_inband_stream,
    pattern_number,
)


class V1Tests(unittest.TestCase):
    def test_replay_deterministic(self):
        a = replay_artifact("kernel", 16, 0x0001, 8)
        b = replay_artifact("kernel", 16, 0x0001, 8)
        self.assertEqual(a.replay_hash, b.replay_hash)
        self.assertEqual(a.canonical_json, b.canonical_json)
        self.assertTrue(a.replay_hash.startswith("sha3_256:"))

    def test_mode_bound_hashes(self):
        a = replay_artifact("kernel", 16, 0x0001, 8)
        b = replay_artifact("16d", 16, 0x0001, 8)
        self.assertNotEqual(a.replay_hash, b.replay_hash)

    def test_hash_agility(self):
        payload = {"x": 1}
        h1 = canonical_hash(payload, hash_algo="sha256")
        h2 = canonical_hash(payload, hash_algo="sha3_256")
        self.assertTrue(h1.startswith("sha256:"))
        self.assertTrue(h2.startswith("sha3_256:"))
        self.assertNotEqual(h1, h2)
        with self.assertRaises(ValueError):
            canonical_hash(payload, hash_algo="blake3")

    def test_16d_rejects_forbidden_4bit(self):
        a = replay_artifact("16d", 16, 0x0001, 1)
        four = a.states[0]["four_bit"]
        self.assertFalse(four["valid"])
        self.assertEqual(four["name"], "FORBIDDEN")

    def test_sign_value_roundtrip(self):
        fv = [frame_value([0x1C, 0x1D]), frame_value([0x1E]), frame_value([0x1F, 0x07, 0x07])]
        p = pattern_number(fv)
        self.assertEqual(decode_pattern(p, len(fv)), fv)
        self.assertEqual(ORBIT_BASE, 36)

    def test_inband_escape_literal(self):
        # ESC len=2 radix=US(60) digits [1,0] => charcode 60
        events = parse_inband_stream("\x27\x02\x1f\x01\x00")
        lit = [e for e in events if e["type"] == "escaped_literal"][0]
        self.assertEqual(lit["charcode"], 60)
        out = canonicalize_stream("\x27\x02\x1f\x01\x00")
        self.assertTrue(out.stream_digest.startswith("sha3_256:"))

    def test_incomplete_escape_rejected(self):
        with self.assertRaises(ValueError):
            parse_inband_stream("\x27\x02")

    def test_reserved_control_code_rejected(self):
        with self.assertRaises(ValueError):
            frame_value([0x3C])

    def test_control_plane_fail_closed(self):
        out = validate_control_plane("A\x01B", mode="kernel")
        self.assertFalse(out.ok)
        self.assertEqual(out.reason_code, "UNKNOWN_TOKEN")

    def test_control_plane_ordering(self):
        out = validate_control_plane("alpha\x1eone\x1dtwo", mode="kernel")
        self.assertFalse(out.ok)
        self.assertEqual(out.reason_code, "OUT_OF_ORDER_SEPARATOR")

    def test_authority_block(self):
        d = authorize(mode="kernel", operation="override", layer=20, artifact_hash="sha256:abc")
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason_code, "AUTHORITY_ESCALATION_BLOCKED")

    def test_tagged_digest_parser(self):
        algo, hx = parse_tagged_digest("sha3_256:" + "a" * 64)
        self.assertEqual(algo, "sha3_256")
        self.assertEqual(len(hx), 64)
        with self.assertRaises(ValueError):
            parse_tagged_digest("" + "a" * 64)

    def test_aztec_bundle_roundtrip(self):
        artifact = replay_artifact("16d", 32, 0x0B7406AC, 16).as_dict()
        manifest, chunks = build_bundle(artifact, chunk_bytes=400)
        out = recover_bundle(manifest, chunks)
        self.assertEqual(out, artifact)
        self.assertEqual(manifest["canonicalization"], "stream-sign-value-v1")


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.thread = threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": 8090}, daemon=True)
        cls.thread.start()
        time.sleep(0.4)

    def _post(self, path, payload):
        req = Request(
            f"http://127.0.0.1:8090{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_replay_hash_endpoint_deterministic(self):
        body = {"mode": "16d", "width": 32, "seed": "0x0B7406AC", "steps": 16}
        a = self._post("/replay/hash", body)
        b = self._post("/replay/hash", body)
        self.assertEqual(a["replay_hash"], b["replay_hash"])
        self.assertEqual(a["canonical_json"], b["canonical_json"])
        self.assertEqual(a["hash_algo"], "sha3_256")
        self.assertIn("digest", a)

    def test_hash_algo_unknown_fail_closed(self):
        out = self._post("/control-plane/validate", {"mode": "kernel", "hash_algo": "bad", "payload": "a"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason_code"], "UNKNOWN_HASH_ALGO")

    def test_invalid_mode_fail_closed(self):
        out = self._post("/control-plane/validate", {"mode": "bad", "payload": "a"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason_code"], "INVALID_MODE")

    def test_oracle_parity_endpoint(self):
        out = self._post("/oracle/parity", {"width": 16, "seed": "0x06AC", "steps": 8})
        self.assertTrue(out["ok"])
        self.assertEqual(out["reason_code"], "OK")
        self.assertEqual(out["hash_algo"], "sha3_256")

    def test_stream_canonicalize_endpoint(self):
        out = self._post("/stream/canonicalize", {"payload": "a\u001cb\u001dc\u001ed\u001f"})
        self.assertEqual(out["canonicalization"], "stream-sign-value-v1")
        self.assertTrue(out["stream_digest"].startswith("sha3_256:"))
        self.assertIn("parser_events", out)

    def test_stream_canonicalize_reserved_event(self):
        out = self._post("/stream/canonicalize", {"payload": "\u003c"})
        self.assertEqual(out["canonicalization"], "stream-sign-value-v1")
        self.assertTrue(any(ev.get("type") == "reserved" for ev in out["parser_events"]))

    def test_stream_canonicalize_incomplete_escape(self):
        out = self._post("/stream/canonicalize", {"payload": "\u0027\u0002"})
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason_code"], "INCOMPLETE_ESCAPE_SEQUENCE")


if __name__ == "__main__":
    unittest.main()
