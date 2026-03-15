#!/usr/bin/env python3
"""Fail docs checks when Verified claims are missing explicit Evidence lines."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
SKIP = {ROOT / "docs" / "publication-claims.md"}


def needs_evidence(line: str) -> bool:
    s = line.strip()
    if "Verified" not in s:
        return False
    if s.startswith("Claim label:"):
        return True
    if s.startswith("Status:"):
        return True
    if s.startswith("- `Verified`:"):
        return True
    return False


def has_evidence(lines: list[str], start: int) -> bool:
    end = min(len(lines), start + 12)
    for j in range(start + 1, end):
        s = lines[j].strip()
        if s.startswith("#"):
            break
        if s == "":
            break
        if s.startswith("Evidence:"):
            return True
    return False


def main() -> int:
    failures: list[str] = []
    for path in TARGETS:
        if path in SKIP:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if needs_evidence(line) and not has_evidence(lines, i):
                failures.append(f"{path.relative_to(ROOT)}:{i+1}: Verified claim missing Evidence line")

    if failures:
        print("docs-claims check failed:")
        for f in failures:
            print(f"- {f}")
        return 1
    print("docs-claims check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
