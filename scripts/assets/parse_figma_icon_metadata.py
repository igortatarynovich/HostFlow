#!/usr/bin/env python3
"""Parse Figma get_metadata XML into icon index JSON."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_IN = Path("/tmp/figma-icon-metadata.xml")
OUT = REPO / "shared" / "figma_icon_index.json"

# Legacy flat icon frames (pre-componentization)
LEGACY_ICON_FRAME_RE = re.compile(
    r'<frame id="([^"]+)" name="([^"]+)" x="[^"]+" y="[^"]+" width="80" height="60">\s*'
    r'\n\s*<frame id="([^"]+)" name="icon"',
    re.MULTILINE,
)

# Component sets: Icon / Category / Label with Size+Theme variants
COMPONENT_SET_RE = re.compile(
    r'<frame id="([^"]+)" name="Icon / ([^/]+) / ([^"]+)"[^>]*>\s*'
    r'((?:\s*<symbol id="([^"]+)" name="([^"]+)"[^>]*/>\s*)+)',
    re.MULTILINE,
)
SYMBOL_RE = re.compile(r'<symbol id="([^"]+)" name="([^"]+)"')
SECTION_RE = re.compile(r'name="(\d+ · [^"]+)"')

SECTION_SLUG_MAP = {
    "navigation": "navigation-main-menu",
    "source icons": "source-icons",
    "communication": "communication",
    "actions": "actions",
    "workflow": "workflow",
    "documents": "documents",
    "candidate & hr": "candidate-hr",
    "sales": "sales",
    "fleet": "fleet",
    "status": "status",
    "priority": "priority",
    "time": "time",
    "filters": "filters",
    "attachments": "attachments",
    "notifications": "notifications",
    "analytics": "analytics",
    "automation": "automation",
    "system": "system",
}


def slugify(label: str) -> str:
    mapping = {
        "Meta Ads": "meta",
        "Google Ads": "google-ads",
        "Google Search": "google-search",
        "Google Maps": "google-maps",
        "Landing Page": "landing-page",
        "QR Code": "qr-code",
        "Import File": "import-file",
        "API Source": "api-source",
        "WhatsApp": "whatsapp",
        "Telegram": "telegram",
        "Facebook": "facebook",
        "Instagram": "instagram",
        "LinkedIn": "linkedin",
        "TikTok": "tiktok",
        "YouTube": "youtube",
        "Email": "email",
        "Phone": "phone",
        "SMS": "sms",
        "Website": "website",
        "Referral": "referral",
        "Webhook": "webhook",
        "Messenger": "messenger",
        "Viber": "viber",
        "CSV": "csv",
        "Manual": "manual",
        "CRM": "crm",
        "Internal": "internal",
        "Recommendation": "recommendation",
        "Главная": "home",
        "Настройки": "settings",
        "Кандидаты": "candidates",
        "Документы": "documents",
        "Календарь": "calendar",
        "Уведомления": "notifications",
        "Поиск": "search",
        "Фильтр": "filter",
    }
    if label in mapping:
        return mapping[label]
    slug = label.lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug or "icon"


def section_slug(section: str) -> str:
    # "2 · Source Icons" -> "source-icons"
    name = section.split("·", 1)[-1].strip().lower()
    name = html.unescape(name)
    if name in SECTION_SLUG_MAP:
        return SECTION_SLUG_MAP[name]
    name = re.sub(r"[^\w\s/-]", "", name)
    name = name.split("/")[0].strip()
    return re.sub(r"[\s_]+", "-", name)


def category_slug(category: str) -> str:
    key = html.unescape(category.strip()).lower()
    return SECTION_SLUG_MAP.get(key, re.sub(r"[\s_]+", "-", key))


def parse_legacy_icons(text: str) -> list[dict]:
    sections: list[tuple[int, str]] = []
    for m in SECTION_RE.finditer(text):
        sections.append((m.start(), m.group(1)))

    icons: list[dict] = []
    for parent_id, label, icon_id in LEGACY_ICON_FRAME_RE.findall(text):
        pos = text.find(f'id="{parent_id}"')
        section = "uncategorized"
        for sec_pos, sec_name in reversed(sections):
            if sec_pos < pos:
                section = sec_name
                break
        icons.append(
            {
                "id": slugify(label),
                "label": label,
                "section": section,
                "section_slug": section_slug(section),
                "figma_node_id": icon_id,
                "figma_parent_id": parent_id,
                "figma_node_id_light": icon_id,
                "figma_node_id_dark": icon_id,
                "export_size": 24,
            }
        )
    return icons


def parse_component_icons(text: str) -> list[dict]:
    icons: list[dict] = []
    for parent_id, category, label, _symbols_block, _first_id, _first_name in COMPONENT_SET_RE.findall(
        text
    ):
        # Re-find symbols for this component set (regex groups collapse repeats)
        set_match = re.search(
            rf'<frame id="{re.escape(parent_id)}" name="Icon / {re.escape(category)} / {re.escape(label)}"[^>]*>(.*?)</frame>',
            text,
            re.DOTALL,
        )
        if not set_match:
            continue
        symbols = SYMBOL_RE.findall(set_match.group(1))
        light_24 = dark_24 = None
        for node_id, variant_name in symbols:
            if "Size=24" not in variant_name:
                continue
            if "Theme=Light" in variant_name:
                light_24 = node_id
            elif "Theme=Dark" in variant_name:
                dark_24 = node_id
        if not light_24:
            continue
        cat = html.unescape(category.strip())
        lbl = html.unescape(label.strip())
        icons.append(
            {
                "id": slugify(lbl),
                "label": lbl,
                "section": cat,
                "section_slug": category_slug(cat),
                "figma_node_id": light_24,
                "figma_parent_id": parent_id,
                "figma_node_id_light": light_24,
                "figma_node_id_dark": dark_24 or light_24,
                "export_size": 24,
            }
        )
    return icons


def parse_metadata(text: str) -> list[dict]:
    component_icons = parse_component_icons(text)
    if component_icons:
        return component_icons
    return parse_legacy_icons(text)


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    if not src.exists():
        alt = Path("/root/.cursor/projects/opt/agent-tools/d291dcd3-9baa-4830-83b1-c6836512acf3.txt")
        src = alt if alt.exists() else src
    text = src.read_text(encoding="utf-8")
    icons = parse_metadata(text)
    payload = {
        "schema_version": 2,
        "figma_file_key": "sWZuu7zlP6zn9pz4lVUxIE",
        "figma_canvas_node_id": "5:2",
        "icon_count": len(icons),
        "icons": icons,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(icons)} icons to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
