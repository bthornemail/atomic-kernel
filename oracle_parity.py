import json
import subprocess
from pathlib import Path
from typing import Dict, List

from canonical import DEFAULT_HASH_ALGO, canonical_hash
from replay_engine import replay_artifact
from stream_sign_value import CANONICALIZATION

ROOT = Path(__file__).resolve().parent
HASKELL_DIR = ROOT / "dev-docs" / "haskell"


def _load(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        {
            "step": int(r["step"]),
            "state_hex": str(r["state_hex"]).upper(),
            "band": {
                "width": int(r["band"]["width"]),
                "density": int(r["band"]["density"]),
                "texture": int(r["band"]["texture"]),
            },
        }
        for r in rows
    ]


def check_parity(width: int, seed_hex: str, steps: int, hash_algo: str = DEFAULT_HASH_ALGO) -> Dict[str, object]:
    fixture = _load(HASKELL_DIR / f"replay-{width}.json")
    fixture_rows = _normalize(fixture["steps"][:steps])

    py = replay_artifact("16d", width, int(seed_hex, 0), steps, hash_algo=hash_algo)
    py_rows = _normalize(
        [{"step": r["step"], "state_hex": r["state_hex"], "band": r["band"]} for r in py.states]
    )

    proc = subprocess.run(
        ["runhaskell", str(HASKELL_DIR / "oracle.hs"), str(width), seed_hex, str(steps)],
        capture_output=True,
        text=True,
        check=True,
    )
    hs = json.loads(proc.stdout)
    hs_rows = _normalize(hs["steps"])

    ok = fixture_rows == py_rows == hs_rows
    payload = {
        "ok": ok,
        "reason_code": "OK" if ok else "PARITY_MISMATCH",
        "width": width,
        "seed_hex": seed_hex.upper(),
        "steps": steps,
        "hash_algo": hash_algo,
        "canonicalization": CANONICALIZATION,
        "python_hash": py.replay_hash,
    }
    payload["result_hash"] = canonical_hash(payload, hash_algo=hash_algo)
    return payload
