#!/usr/bin/env python3
"""Report Figma UI icon import progress."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "shared" / "figma_icon_index.json"
ROOT = REPO / "hostflow-frontend" / "public" / "assets" / "icons"


def main() -> int:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    icons = index["icons"]
    pending = []
    installed = []
    for icon in icons:
        path = ROOT / "light" / "ui" / icon["section_slug"] / f"{icon['id']}.svg"
        if path.exists():
            installed.append(icon)
        else:
            pending.append(icon)

    print(f"Total: {len(icons)} | Installed: {len(installed)} | Pending: {len(pending)}")
    if pending:
        by_section = Counter(i["section_slug"] for i in pending)
        print("\nPending by section:")
        for section, count in sorted(by_section.items()):
            print(f"  {section}: {count}")
        print("\nNext batch node IDs (light):")
        for icon in pending[:30]:
            print(f"  {icon['figma_node_id_light']}\t{icon['section_slug']}/{icon['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
