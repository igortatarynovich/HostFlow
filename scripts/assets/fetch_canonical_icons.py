#!/usr/bin/env python3
"""Install canonical brand/flag SVGs from Simple Icons, Wikimedia, and flag-icons."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BRANDS = REPO / "hostflow-frontend" / "public" / "assets" / "icons" / "light" / "brands"
FLAGS = REPO / "hostflow-frontend" / "public" / "assets" / "icons" / "light" / "flags"
SYNC_THEMES = REPO / "scripts" / "assets" / "sync_icon_themes.py"
TMP = Path("/tmp/hostflow-icon-fetch")

BRAND_COLORS: dict[str, str] = {
    "whatsapp": "#25D366",
    "telegram": "#26A5E4",
    "facebook": "#1877F2",
    "meta": "#0081FB",
    "tiktok": "#000000",
    "instagram": "#E4405F",
    "x": "#000000",
    "vk": "#0077FF",
    "viber": "#7360F2",
}

SIMPLE_ICONS = [
    "whatsapp",
    "telegram",
    "facebook",
    "meta",
    "tiktok",
    "x",
    "vk",
    "viber",
]

WIKIMEDIA: dict[str, str] = {
    "google": "https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg",
    "linkedin": "https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg",
    "linkedin-filled": "https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg",
    "instagram-gradient": "https://upload.wikimedia.org/wikipedia/commons/e/e7/Instagram_logo_2016.svg",
}

FLAG_CODES = ["pl", "de", "ua", "by", "cz", "lt", "lv", "ee", "ro", "md", "ge", "uz"]


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fsSL", url, "-o", str(dest)], check=True)


def normalize_simple_icon(src: Path, dest: Path, fill: str) -> None:
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"<title>[^<]*</title>", "", text)
    if 'fill="' not in text and "fill='" not in text:
        text = text.replace("<path ", f'<path fill="{fill}" ', 1)
        text = re.sub(r"<path (?!fill)", f'<path fill="{fill}" ', text)
    text = text.replace('role="img"', 'role="img" aria-hidden="true"')
    if "aria-hidden" not in text:
        text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def normalize_wikimedia_google(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    text = re.sub(r'<path d="M1 1h22v22H1z" fill="none"/>', "", text)
    text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def normalize_wikimedia_linkedin(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"<\?xml[^>]*\?>", "", text)
    text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def normalize_instagram_gradient(src: Path, dest: Path) -> None:
    shutil.copy2(src, dest)
    text = dest.read_text(encoding="utf-8")
    if "aria-hidden" not in text:
        text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def normalize_flag(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    text = re.sub(r'\s+id="flag-icons-[^"]+"', "", text)
    if "aria-hidden" not in text:
        text = text.replace("<svg ", '<svg role="img" aria-hidden="true" ', 1)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    BRANDS.mkdir(parents=True, exist_ok=True)
    FLAGS.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []

    for slug in SIMPLE_ICONS:
        url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{slug}.svg"
        src = TMP / f"{slug}.svg"
        fetch(url, src)
        color = BRAND_COLORS[slug]
        dest = BRANDS / f"{slug}.svg"
        normalize_simple_icon(src, dest, color)
        installed.append(f"brands/{slug}.svg (Simple Icons)")

        if slug in {"whatsapp", "facebook"}:
            filled = BRANDS / f"{slug}-filled.svg"
            shutil.copy2(dest, filled)
            installed.append(f"brands/{slug}-filled.svg (Simple Icons)")

    for name, url in WIKIMEDIA.items():
        src = TMP / f"{name}.svg"
        fetch(url, src)
        if name == "google":
            normalize_wikimedia_google(src, BRANDS / "google.svg")
            installed.append("brands/google.svg (Wikimedia)")
        elif name.startswith("linkedin"):
            normalize_wikimedia_linkedin(src, BRANDS / f"{name.replace('-filled', '')}.svg" if name == "linkedin" else BRANDS / "linkedin-filled.svg")
            if name == "linkedin":
                installed.append("brands/linkedin.svg (Wikimedia)")
            else:
                installed.append("brands/linkedin-filled.svg (Wikimedia)")
        elif name == "instagram-gradient":
            normalize_instagram_gradient(src, BRANDS / "instagram.svg")
            installed.append("brands/instagram.svg (Wikimedia gradient)")

    for code in FLAG_CODES:
        url = f"https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/{code}.svg"
        src = TMP / f"flag-{code}.svg"
        fetch(url, src)
        normalize_flag(src, FLAGS / f"{code}.svg")
        installed.append(f"flags/{code}.svg (flag-icons)")

    print(f"Installed {len(installed)} assets:")
    for line in installed:
        print(f"  - {line}")

    if SYNC_THEMES.exists():
        subprocess.run([sys.executable, str(SYNC_THEMES)], check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
