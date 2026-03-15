#!/usr/bin/env python3
"""Render README-ready Aztec PNGs from proof chunk JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from aztec_code_generator import AztecCode
from PIL import Image, ImageDraw


def _read_chunks(chunks_dir: Path) -> List[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(chunks_dir.glob("chunk-*.json"))
    ]


def _render_chunk_png(chunk_payload: dict, out_path: Path, module_size: int, border: int, ec_percent: int) -> None:
    data = json.dumps(chunk_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    code = AztecCode(data, ec_percent=ec_percent)
    code.save(str(out_path), module_size=module_size, border=border, format="PNG")


def _compose_labeled_grid(images: List[Path], labels: List[str], out_path: Path) -> None:
    loaded = [Image.open(p).convert("RGB") for p in images]
    w = max(im.width for im in loaded)
    h = max(im.height for im in loaded)
    pad = 24
    label_h = 28
    canvas_h = len(loaded) * (h + label_h + pad) + pad
    canvas = Image.new("RGB", (w + 2 * pad, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    y = pad
    for i, im in enumerate(loaded):
        x = pad + (w - im.width) // 2
        canvas.paste(im, (x, y))
        draw.text((pad, y + im.height + 6), labels[i], fill=(0, 0, 0))
        y += h + label_h + pad

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG")


def render_readme_assets(
    proof_dir: Path,
    outdir: Path,
    *,
    module_size: int = 4,
    border: int = 2,
    ec_percent: int = 23,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    mapping = {
        "control-codes": "aztec-control-codes.png",
        "algorithms": "aztec-algorithms.png",
    }

    for key, out_name in mapping.items():
        chunks = _read_chunks(proof_dir / key / "chunks")
        if not chunks:
            raise ValueError(f"no chunks found for {key}")
        _render_chunk_png(
            chunks[0],
            outdir / out_name,
            module_size=module_size,
            border=border,
            ec_percent=ec_percent,
        )

    full_chunks = _read_chunks(proof_dir / "full" / "chunks")
    if not full_chunks:
        raise ValueError("no chunks found for full")

    full_imgs: List[Path] = []
    labels: List[str] = []
    for c in full_chunks:
        idx = int(c["index"])
        png = outdir / f"aztec-full-{idx:02d}.png"
        _render_chunk_png(c, png, module_size=module_size, border=border, ec_percent=ec_percent)
        full_imgs.append(png)
        labels.append(f"full chunk {idx+1}/{len(full_chunks)}")

    _compose_labeled_grid(full_imgs, labels, outdir / "aztec-full.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Aztec proof PNG images for README")
    parser.add_argument("--proof-dir", default="aztec-proof")
    parser.add_argument("--outdir", default="docs/assets")
    parser.add_argument("--module-size", type=int, default=4)
    parser.add_argument("--border", type=int, default=2)
    parser.add_argument("--ec-percent", type=int, default=23)
    args = parser.parse_args()

    render_readme_assets(
        Path(args.proof_dir),
        Path(args.outdir),
        module_size=args.module_size,
        border=args.border,
        ec_percent=args.ec_percent,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
