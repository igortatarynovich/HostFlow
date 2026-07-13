#!/usr/bin/env python3
"""Install Figma icon exports into light/dark theme folders."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "shared" / "figma_icon_index.json"
ICONS_ROOT = REPO / "hostflow-frontend" / "public" / "assets" / "icons"
NORMALIZE = REPO / "scripts" / "assets" / "normalize_figma_icon_svg.py"
TMP = Path("/tmp/figma-icon-import")


def curl_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fsSL", url, "-o", str(dest)], check=True)


def install_pair(
    *,
    icon_id: str,
    section: str,
    light_url: str | None,
    dark_url: str | None,
    single_url: str | None = None,
) -> None:
    light = ICONS_ROOT / "light" / "ui" / section / f"{icon_id}.svg"
    dark = ICONS_ROOT / "dark" / "ui" / section / f"{icon_id}.svg"

    if light_url and dark_url and light_url != dark_url:
        raw_light = TMP / f"{icon_id}.light.raw.svg"
        raw_dark = TMP / f"{icon_id}.dark.raw.svg"
        curl_download(light_url, raw_light)
        curl_download(dark_url, raw_dark)
        subprocess.run(
            [
                sys.executable,
                str(NORMALIZE),
                str(raw_light),
                str(light),
                str(dark),
                str(raw_dark),
                "--from-pair",
            ],
            check=True,
        )
        return

    url = single_url or light_url or dark_url
    if not url:
        raise ValueError(f"No export URL for {icon_id}")
    raw = TMP / f"{icon_id}.raw.svg"
    curl_download(url, raw)
    subprocess.run([sys.executable, str(NORMALIZE), str(raw), str(light), str(dark)], check=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: install_figma_icon_exports.py <exports.json>")
        print(
            '  exports.json: [{"id":"home","section_slug":"navigation-main-menu",'
            '"light_url":"...","dark_url":"..."}]'
        )
        return 1

    exports = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    by_node = {item["figma_node_id"]: item for item in index["icons"]}
    by_id = {item["id"]: item for item in index["icons"]}

    installed = 0
    for entry in exports:
        node_id = entry.get("figma_node_id") or entry.get("nodeId")
        meta = by_node.get(node_id) or by_id.get(entry.get("id", "")) or entry
        icon_id = entry.get("id") or meta.get("id")
        section = entry.get("section_slug") or meta.get("section_slug", "ui")
        light_url = entry.get("light_url") or entry.get("url")
        dark_url = entry.get("dark_url")
        if node_id and not light_url and entry.get("url"):
            light_url = entry["url"]

        install_pair(
            icon_id=icon_id,
            section=section,
            light_url=light_url,
            dark_url=dark_url,
            single_url=entry.get("url") if not dark_url else None,
        )
        installed += 1
        print(f"  {section}/{icon_id}.svg")

    print(f"Installed {installed} icons (light + dark)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
