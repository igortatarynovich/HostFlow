#!/usr/bin/env python3
"""Fetch Figma UI icons via REST Images API (batch export, no MCP rate limits).

Requires FIGMA_ACCESS_TOKEN env var (Personal Access Token from Figma settings).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "shared" / "figma_icon_index.json"
ICONS_ROOT = REPO / "hostflow-frontend" / "public" / "assets" / "icons"
NORMALIZE = REPO / "scripts" / "assets" / "normalize_figma_icon_svg.py"
TMP = Path("/tmp/figma-icon-import")
FILE_KEY = "sWZuu7zlP6zn9pz4lVUxIE"
BATCH_SIZE = 40


def api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"https://api.figma.com/v1{path}",
        headers={"X-Figma-Token": token},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def curl_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fsSL", url, "-o", str(dest)], check=True)


def pending_icons() -> list[dict]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    icons = index["icons"]
    out = []
    for icon in icons:
        path = ICONS_ROOT / "light" / "ui" / icon["section_slug"] / f"{icon['id']}.svg"
        if not path.exists():
            out.append(icon)
    return out


def install_icon(icon: dict, light_url: str, dark_url: str | None = None) -> None:
    icon_id = icon["id"]
    section = icon["section_slug"]
    light = ICONS_ROOT / "light" / "ui" / section / f"{icon_id}.svg"
    dark = ICONS_ROOT / "dark" / "ui" / section / f"{icon_id}.svg"

    if dark_url and dark_url != light_url:
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

    raw = TMP / f"{icon_id}.raw.svg"
    curl_download(light_url, raw)
    subprocess.run([sys.executable, str(NORMALIZE), str(raw), str(light), str(dark)], check=True)


def fetch_batch(token: str, icons: list[dict], *, use_dark: bool) -> dict[str, str]:
    node_map: dict[str, dict] = {}
    ids: list[str] = []
    for icon in icons:
        light_id = icon["figma_node_id_light"].replace(":", "-")
        node_map[light_id] = icon
        ids.append(icon["figma_node_id_light"])
        if use_dark:
            dark_id = icon["figma_node_id_dark"].replace(":", "-")
            node_map[dark_id] = icon
            ids.append(icon["figma_node_id_dark"])

    query = urllib.parse.urlencode({"ids": ",".join(ids), "format": "svg"})
    data = api_get(f"/images/{FILE_KEY}?{query}", token)
    if data.get("err"):
        raise RuntimeError(data["err"])
    return data.get("images", {})


def main() -> int:
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("Set FIGMA_ACCESS_TOKEN (Figma → Settings → Personal access tokens)", file=sys.stderr)
        return 1

    pending = pending_icons()
    if not pending:
        print("All icons already installed.")
        return 0

    use_dark = "--with-dark" in sys.argv
    installed = 0
    failed: list[str] = []

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        print(f"Batch {start // BATCH_SIZE + 1}: {len(batch)} icons...")
        try:
            images = fetch_batch(token, batch, use_dark=use_dark)
        except urllib.error.HTTPError as exc:
            print(f"  API error: {exc}", file=sys.stderr)
            time.sleep(2)
            continue

        for icon in batch:
            light_key = icon["figma_node_id_light"]
            dark_key = icon["figma_node_id_dark"]
            light_url = images.get(light_key)
            dark_url = images.get(dark_key) if use_dark else None
            if not light_url:
                failed.append(icon["id"])
                print(f"  missing URL: {icon['section_slug']}/{icon['id']}", file=sys.stderr)
                continue
            try:
                install_icon(icon, light_url, dark_url)
                installed += 1
                print(f"  {icon['section_slug']}/{icon['id']}.svg")
            except subprocess.CalledProcessError:
                failed.append(icon["id"])
                print(f"  install failed: {icon['id']}", file=sys.stderr)

        time.sleep(0.5)

    remaining = len(pending_icons())
    print(f"\nInstalled: {installed} | Failed: {len(failed)} | Remaining: {remaining}")
    if failed:
        print("Failed ids:", ", ".join(failed[:20]), "..." if len(failed) > 20 else "")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
