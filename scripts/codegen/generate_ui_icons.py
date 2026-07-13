#!/usr/bin/env python3
"""Generate TypeScript UI icon catalog from shared/figma_icon_index.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "shared" / "figma_icon_index.json"
OUT = REPO / "hostflow-frontend" / "src" / "platform" / "icons" / "uiIconPaths.generated.ts"

_HEADER = """/**
 * GENERATED FILE — do not edit by hand.
 * Source: `shared/figma_icon_index.json`.
 * Regenerate: `python3 scripts/codegen/generate_ui_icons.py`
 */

"""

# When the same bare id appears in multiple sections, pick the canonical section.
_SECTION_PRIORITY = [
    "navigation-main-menu",
    "communication",
    "actions",
    "workflow",
    "filters",
    "documents",
    "source-icons",
    "sales",
    "candidate-hr",
    "fleet",
    "status",
    "time",
    "notifications",
    "analytics",
    "attachments",
    "automation",
    "system",
    "priority",
]


def _ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _composite(section: str, icon_id: str) -> str:
    return f"{section}/{icon_id}"


def _pick_alias_section(bare_id: str, sections: set[str]) -> str:
    for section in _SECTION_PRIORITY:
        if section in sections:
            return section
    return sorted(sections)[0]


def generate(data: dict) -> str:
    icons = data["icons"]
    sections = sorted({icon["section_slug"] for icon in icons})

    records: dict[str, dict] = {}
    bare_to_sections: dict[str, set[str]] = {}

    for icon in icons:
        key = _composite(icon["section_slug"], icon["id"])
        records[key] = {
            "key": key,
            "id": icon["id"],
            "section": icon["section_slug"],
            "label": icon["label"],
        }
        bare_to_sections.setdefault(icon["id"], set()).add(icon["section_slug"])

    composite_ids = sorted(records.keys())
    aliases: dict[str, str] = {}
    for bare_id, icon_sections in bare_to_sections.items():
        preferred = _pick_alias_section(bare_id, icon_sections)
        aliases[bare_id] = _composite(preferred, bare_id)

    section_union = " | ".join(_ts_string(s) for s in sections)
    id_union = " | ".join(_ts_string(k) for k in composite_ids)
    alias_keys = sorted(aliases.keys())
    alias_union = " | ".join(_ts_string(k) for k in alias_keys)

    lines = [
        _HEADER,
        f"export type UiIconSection = {section_union}\n",
        f"export type UiIconKey = {id_union}\n",
        f"export type UiIconAliasId = {alias_union}\n",
        "export type UiIconId = UiIconKey | UiIconAliasId\n",
        "export type UiIconRecord = {",
        "  key: UiIconKey",
        "  id: string",
        "  section: UiIconSection",
        "  label: string",
        "}\n",
        "export const UI_ICONS = {",
    ]
    for key in composite_ids:
        rec = records[key]
        lines.append(
            f"  {_ts_string(key)}: {{ key: {_ts_string(rec['key'])}, id: {_ts_string(rec['id'])}, "
            f"section: {_ts_string(rec['section'])}, label: {_ts_string(rec['label'])} }},"
        )
    lines.append("} as const satisfies Record<UiIconKey, UiIconRecord>\n")

    lines.append("export const UI_ICON_ALIASES = {")
    for bare_id in alias_keys:
        lines.append(f"  {_ts_string(bare_id)}: {_ts_string(aliases[bare_id])},")
    lines.append("} as const satisfies Record<UiIconAliasId, UiIconKey>\n")

    lines.append("export const UI_ICON_KEYS = Object.keys(UI_ICONS) as UiIconKey[]\n")
    lines.append(
        "export function resolveUiIconKey(id: UiIconId): UiIconKey {\n"
        "  if (Object.prototype.hasOwnProperty.call(UI_ICONS, id)) return id as UiIconKey\n"
        "  if (Object.prototype.hasOwnProperty.call(UI_ICON_ALIASES, id)) {\n"
        "    return UI_ICON_ALIASES[id as UiIconAliasId]\n"
        "  }\n"
        "  throw new Error(`Unknown UI icon id: ${id}`)\n"
        "}\n"
    )
    lines.append(
        "export function isUiIconId(value: string): value is UiIconId {\n"
        "  return Object.prototype.hasOwnProperty.call(UI_ICONS, value)\n"
        "    || Object.prototype.hasOwnProperty.call(UI_ICON_ALIASES, value)\n"
        "}\n"
    )
    lines.append("export type UiIconTheme = 'light' | 'dark'\n")
    lines.append(
        "export function resolveUiIconUrl(id: UiIconId, theme: UiIconTheme = 'light'): string {\n"
        "  const record = UI_ICONS[resolveUiIconKey(id)]\n"
        "  return `/assets/icons/${theme}/ui/${record.section}/${record.id}.svg`\n"
        "}\n"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data = json.loads(INDEX.read_text(encoding="utf-8"))
    content = generate(data)

    if args.check:
        if not OUT.exists():
            print(f"Missing {OUT}", file=sys.stderr)
            return 1
        if OUT.read_text(encoding="utf-8") != content:
            print(f"Drift detected in {OUT}", file=sys.stderr)
            return 1
        print("uiIconPaths.generated.ts is up to date")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT} ({len(data['icons'])} icons, {len(content.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
