#!/usr/bin/env python3
"""Normalize Figma-exported SVG: strip backgrounds, emit light/dark stroke variants."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LIGHT_STROKE = "#0F172A"
DARK_STROKE = "#E2E8F0"


def normalize_svg(raw: str, *, theme: str = "light", preserve_colors: bool = False) -> str:
    text = raw
    text = re.sub(r"<rect[^>]*fill=\"#F5F5F5\"[^>]*/>\s*", "", text)
    text = re.sub(r"<rect[^>]*fill=\"#F7F7FA\"[^>]*/>\s*", "", text)
    text = re.sub(r"<rect[^>]*fill=\"#f5f5f5\"[^>]*/>\s*", "", text, flags=re.I)
    text = re.sub(r"<rect[^>]*fill=\"#f7f7fa\"[^>]*/>\s*", "", text, flags=re.I)
    text = re.sub(r"<rect[^>]*fill=\"white\"[^>]*/>\s*", "", text, flags=re.I)
    text = re.sub(r"<g id=\"[^\"]+\">\s*(?=<g id=\"icon\">)", "", text)
    text = re.sub(r"</g>\s*</svg>", "</svg>", text)

    if not preserve_colors:
        stroke = LIGHT_STROKE if theme == "light" else DARK_STROKE
        text = re.sub(r'stroke="#0[Ff]172[Aa]"', f'stroke="{stroke}"', text)
        text = re.sub(r'stroke="#334155"', f'stroke="{stroke}"', text)
        text = re.sub(r'stroke="#000000"', f'stroke="{stroke}"', text)
        text = re.sub(r'stroke="#000"', f'stroke="{stroke}"', text)
        text = re.sub(r'stroke="#[Ee]2[Ee]8[Ff]0"', f'stroke="{stroke}"', text)

    if 'role="img"' not in text:
        text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)

    if 'viewBox="0 0 24 24"' in text:
        text = re.sub(r'<svg([^>]*)width="[^"]*"', r"<svg\1width=\"24\"", text, count=1)
        text = re.sub(r'<svg([^>]*)height="[^"]*"', r'<svg\1height="24"', text, count=1)

    return text.strip() + "\n"


def write_variants(
    src: Path,
    light_dest: Path,
    dark_dest: Path,
    *,
    from_pair: bool = False,
    dark_src: Path | None = None,
) -> None:
    raw = src.read_text(encoding="utf-8")
    light_dest.parent.mkdir(parents=True, exist_ok=True)
    dark_dest.parent.mkdir(parents=True, exist_ok=True)
    if from_pair and dark_src:
        light_dest.write_text(normalize_svg(raw, theme="light", preserve_colors=True), encoding="utf-8")
        dark_raw = dark_src.read_text(encoding="utf-8")
        dark_dest.write_text(normalize_svg(dark_raw, theme="dark", preserve_colors=True), encoding="utf-8")
        return
    light_dest.write_text(normalize_svg(raw, theme="light"), encoding="utf-8")
    dark_dest.write_text(normalize_svg(raw, theme="dark"), encoding="utf-8")


def main() -> int:
    args = sys.argv[1:]
    from_pair = False
    if "--from-pair" in args:
        from_pair = True
        args.remove("--from-pair")
    if len(args) not in (3, 4):
        print(
            "Usage: normalize_figma_icon_svg.py <raw.svg> <light.out> <dark.out> "
            "[<dark.raw.svg>] [--from-pair]"
        )
        return 1
    dark_src = Path(args[3]) if len(args) == 4 else None
    write_variants(
        Path(args[0]),
        Path(args[1]),
        Path(args[2]),
        from_pair=from_pair,
        dark_src=dark_src,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
