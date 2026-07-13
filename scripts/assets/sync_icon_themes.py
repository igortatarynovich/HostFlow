#!/usr/bin/env python3
"""Organize icon SVGs into light/dark theme folders and generate dark variants."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ICONS_ROOT = REPO / "hostflow-frontend" / "public" / "assets" / "icons"
LIGHT = ICONS_ROOT / "light"
DARK = ICONS_ROOT / "dark"

# Monochrome brand icons: invert fill/stroke for dark theme.
MONOCHROME_BRANDS = {"x", "tiktok"}

# Colored brands keep the same asset in both themes.
COLORED_BRANDS = {
    "whatsapp",
    "whatsapp-filled",
    "telegram",
    "facebook",
    "facebook-filled",
    "meta",
    "google",
    "linkedin",
    "linkedin-filled",
    "instagram",
    "viber",
    "vk",
}

CATEGORIES = ("brands", "contact", "source", "flags")


def ensure_theme_dirs() -> None:
    for theme in (LIGHT, DARK):
        for category in CATEGORIES:
            (theme / category).mkdir(parents=True, exist_ok=True)


def migrate_flat_to_light() -> None:
    """Move legacy flat folders (brands/, contact/, …) into light/."""
    for category in CATEGORIES:
        legacy = ICONS_ROOT / category
        if not legacy.is_dir():
            continue
        target = LIGHT / category
        target.mkdir(parents=True, exist_ok=True)
        for svg in legacy.glob("*.svg"):
            dest = target / svg.name
            if not dest.exists():
                shutil.copy2(svg, dest)


def to_dark_monochrome(svg_text: str) -> str:
    """Replace dark fills/strokes with light ones for dark backgrounds."""
    text = svg_text
    text = re.sub(r'fill="#000000"', 'fill="#FFFFFF"', text, flags=re.IGNORECASE)
    text = re.sub(r'fill="#000"', 'fill="#FFFFFF"', text, flags=re.IGNORECASE)
    text = re.sub(r'fill="black"', 'fill="#FFFFFF"', text, flags=re.IGNORECASE)
    text = re.sub(r'stroke="#000000"', 'stroke="#FFFFFF"', text, flags=re.IGNORECASE)
    text = re.sub(r'stroke="#000"', 'stroke="#FFFFFF"', text, flags=re.IGNORECASE)
    text = re.sub(r'stroke="black"', 'stroke="#FFFFFF"', text, flags=re.IGNORECASE)
    # Tabler-style glyphs: prefer currentColor for theme via CSS when possible.
    text = re.sub(r'stroke="#334155"', 'stroke="#E2E8F0"', text)
    text = re.sub(r'stroke="currentColor"', 'stroke="#E2E8F0"', text)
    return text


def normalize_glyph_for_light(svg_text: str) -> str:
    text = svg_text
    if 'stroke="' not in text and "stroke='" not in text:
        text = text.replace("<svg ", '<svg stroke="#334155" ', 1)
    text = text.replace('stroke="currentColor"', 'stroke="#334155"')
    return text


def normalize_glyph_for_dark(svg_text: str) -> str:
    text = svg_text
    if 'stroke="' not in text and "stroke='" not in text:
        text = text.replace("<svg ", '<svg stroke="#E2E8F0" ', 1)
    text = text.replace('stroke="currentColor"', 'stroke="#E2E8F0"')
    text = text.replace('stroke="#334155"', 'stroke="#E2E8F0"')
    return text


def sync_category(category: str) -> list[str]:
    actions: list[str] = []
    light_dir = LIGHT / category
    dark_dir = DARK / category
    if not light_dir.exists():
        return actions

    for src in sorted(light_dir.glob("*.svg")):
        name = src.stem
        light_text = src.read_text(encoding="utf-8")
        dark_dest = dark_dir / src.name

        if category == "flags":
            shutil.copy2(src, dark_dest)
            actions.append(f"{category}/{src.name}: identical light/dark")
            continue

        if category == "brands":
            if name in MONOCHROME_BRANDS:
                dark_text = to_dark_monochrome(light_text)
                dark_dest.write_text(dark_text.strip() + "\n", encoding="utf-8")
                actions.append(f"brands/{src.name}: monochrome dark variant")
            else:
                shutil.copy2(src, dark_dest)
                actions.append(f"brands/{src.name}: colored, same in both themes")
            continue

        # contact + source glyphs
        light_text = normalize_glyph_for_light(light_text)
        src.write_text(light_text.strip() + "\n", encoding="utf-8")
        dark_text = normalize_glyph_for_dark(light_text)
        dark_dest.write_text(dark_text.strip() + "\n", encoding="utf-8")
        actions.append(f"{category}/{src.name}: glyph light/dark stroke variants")

    return actions


def main() -> int:
    ensure_theme_dirs()
    migrate_flat_to_light()

    all_actions: list[str] = []
    for category in CATEGORIES:
        all_actions.extend(sync_category(category))

    print(f"Synced {len(all_actions)} icon theme files:")
    for line in all_actions:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
