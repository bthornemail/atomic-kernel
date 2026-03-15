import json
import subprocess
import sys
from pathlib import Path

from canonical import canonical_hash
from replay_engine import replay_artifact

ROOT = Path(__file__).resolve().parent
HASKELL_DIR = ROOT / "dev-docs" / "haskell"
DIFF_PATH = HASKELL_DIR / "conformance_diff.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_steps(rows):
    out = []
    for row in rows:
        out.append(
            {
                "step": int(row["step"]),
                "state_hex": str(row["state_hex"]).upper(),
                "band": {
                    "width": int(row["band"]["width"]),
                    "density": int(row["band"]["density"]),
                    "texture": int(row["band"]["texture"]),
                },
            }
        )
    return out


def rows_digest(rows, hash_algo: str):
    return canonical_hash({"rows": rows}, hash_algo=hash_algo)


def from_fixture(width):
    fixture = load_json(HASKELL_DIR / f"replay-{width}.json")
    rows = normalize_steps(fixture["steps"])
    return rows


def from_python(width, seed, steps, hash_algo: str):
    art = replay_artifact(mode="16d", width=width, seed=seed, steps=steps, hash_algo=hash_algo)
    rows = []
    for row in art.states:
        rows.append(
            {
                "step": row["step"],
                "state_hex": row["state_hex"].upper(),
                "band": row["band"],
            }
        )
    rows = normalize_steps(rows)
    return rows, rows_digest(rows, hash_algo=hash_algo), art.replay_hash


def from_haskell(width, seed, steps, hash_algo: str):
    proc = subprocess.run(
        ["runhaskell", str(HASKELL_DIR / "oracle.hs"), str(width), seed, str(steps)],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(proc.stdout)
    rows = normalize_steps(parsed["steps"])
    return rows, rows_digest(rows, hash_algo=hash_algo)


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i, a[i], b[i]
    if len(a) != len(b):
        return n, a[n:] if n < len(a) else [], b[n:] if n < len(b) else []
    return None


def main():
    cfg = load_json(HASKELL_DIR / "conformance_cases.json")
    case = cfg["cases"][0]
    hash_algo = cfg.get("hash_algo", "sha3_256")
    canonicalization = cfg.get("canonicalization", "stream-sign-value-v1")
    failures = []

    for width in case["widths"]:
        seed = case["seeds"][str(width)]
        steps = case["steps"]
        fixture_rows = from_fixture(width)
        fixture_digest = rows_digest(fixture_rows, hash_algo=hash_algo)
        py_rows, py_rows_digest, py_hash = from_python(width, int(seed, 0), steps, hash_algo=hash_algo)
        hs_rows, hs_rows_digest = from_haskell(width, seed, steps, hash_algo=hash_algo)

        d1 = first_diff(fixture_rows, py_rows)
        d2 = first_diff(fixture_rows, hs_rows)

        if d1 is not None or fixture_digest != py_rows_digest:
            failures.append(
                {
                    "width": width,
                    "kind": "PYTHON_VS_FIXTURE",
                    "diff": d1,
                    "fixture_digest": fixture_digest,
                    "python_rows_digest": py_rows_digest,
                    "python_replay_hash": py_hash,
                }
            )
        if d2 is not None or fixture_digest != hs_rows_digest:
            failures.append(
                {
                    "width": width,
                    "kind": "HASKELL_VS_FIXTURE",
                    "diff": d2,
                    "fixture_digest": fixture_digest,
                    "haskell_rows_digest": hs_rows_digest,
                }
            )

    artifact = {
        "conformance_version": cfg["conformance_version"],
        "mode": cfg["mode"],
        "hash_algo": hash_algo,
        "canonicalization": canonicalization,
        "ok": len(failures) == 0,
        "failures": failures,
    }
    artifact["result_hash"] = canonical_hash(artifact, hash_algo=hash_algo)

    if failures:
        DIFF_PATH.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Conformance failed. Diff written to {DIFF_PATH}")
        print(json.dumps(artifact, indent=2, sort_keys=True))
        sys.exit(1)

    if DIFF_PATH.exists():
        DIFF_PATH.unlink()
    print("Conformance passed")
    print(json.dumps(artifact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
