#!/usr/bin/env python3
"""Install a batch of Figma MCP export URLs into ui icon folders."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "shared" / "figma_icon_index.json"
INSTALL = REPO / "scripts" / "assets" / "install_figma_icon_exports.py"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: figma_import_batch.py <batch-exports.json>")
        print("  [{\"nodeId\":\"19:2\",\"url\":\"https://...\"}]")
        return 1

    batch = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    by_light = {item["figma_node_id_light"]: item for item in index["icons"]}
    by_dark = {item["figma_node_id_dark"]: item for item in index["icons"]}
    by_any = {item["figma_node_id"]: item for item in index["icons"]}

    exports: list[dict] = []
    for entry in batch:
        node_id = entry.get("nodeId") or entry.get("figma_node_id")
        url = entry.get("url") or entry.get("export", {}).get("url")
        if not node_id or not url:
            continue
        meta = by_light.get(node_id) or by_dark.get(node_id) or by_any.get(node_id)
        if not meta:
            print(f"  skip unknown node {node_id}", file=sys.stderr)
            continue
        item = {
            "id": meta["id"],
            "section_slug": meta["section_slug"],
            "figma_node_id": node_id,
        }
        if node_id == meta.get("figma_node_id_light"):
            item["light_url"] = url
        elif node_id == meta.get("figma_node_id_dark"):
            item["dark_url"] = url
        else:
            item["url"] = url
        exports.append(item)

    if not exports:
        print("No exports to install", file=sys.stderr)
        return 1

    tmp = Path("/tmp/figma-batch-install.json")
    tmp.write_text(json.dumps(exports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(INSTALL), str(tmp)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
