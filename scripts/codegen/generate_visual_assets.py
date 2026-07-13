#!/usr/bin/env python3
"""
Generate TypeScript and Python visual asset catalogs from **shared/visual_assets.json**.

  python3 scripts/codegen/generate_visual_assets.py           # write outputs
  python3 scripts/codegen/generate_visual_assets.py --check   # fail if drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "shared" / "visual_assets.json"
TS_OUT = REPO_ROOT / "hostflow-frontend" / "src" / "platform" / "icons" / "visualAssets.generated.ts"
PY_OUT = REPO_ROOT / "backend" / "app" / "reference" / "visual_asset_catalog.py"

_TS_HEADER = """/**
 * GENERATED FILE — do not edit by hand.
 * Source: `shared/visual_assets.json`.
 * Regenerate: `python3 scripts/codegen/generate_visual_assets.py` or `npm run codegen:visual-assets`.
 */

"""

_PY_HEADER = '''# GENERATED FILE — do not edit by hand.
# Source: shared/visual_assets.json
# Regenerate: python3 scripts/codegen/generate_visual_assets.py

"""Platform Reference Layer — visual assets catalog (icons, logos, flags)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

VisualAssetCategory = Literal["brand", "contact", "source", "flag", "product", "ui"]
VisualAssetKind = Literal["brand", "glyph", "flag", "logo"]


@dataclass(frozen=True)
class VisualAssetItem:
    id: str
    label: str
    category: VisualAssetCategory
    kind: VisualAssetKind
    tabler: str | None = None
    tabler_filled: str | None = None
    svg: str | None = None
    svg_filled: str | None = None
    svg_light: str | None = None
    svg_dark: str | None = None
    svg_filled_light: str | None = None
    svg_filled_dark: str | None = None
    brand_color: str | None = None
    aliases: tuple[str, ...] = ()

'''


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(data: dict) -> None:
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if not data.get("catalog_version"):
        raise ValueError("catalog_version is required")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("assets must be a non-empty list")
    seen_ids: set[str] = set()
    for item in assets:
        asset_id = item["id"]
        if asset_id in seen_ids:
            raise ValueError(f"duplicate asset id: {asset_id}")
        seen_ids.add(asset_id)
        for alias in item.get("aliases") or []:
            if alias in seen_ids:
                raise ValueError(f"duplicate alias/id: {alias}")
            seen_ids.add(alias)


def _py_str(value: str | None) -> str:
    if value is None:
        return "None"
    return repr(value)


def _py_tuple(values: list[str] | None) -> str:
    if not values:
        return "()"
    inner = ", ".join(repr(v) for v in values)
    return f"({inner},)"


def _generate_python(data: dict) -> str:
    catalog_version = data["catalog_version"]
    size_tokens = data["size_tokens"]
    assets = data["assets"]

    lines = [
        _PY_HEADER,
        f'CATALOG_VERSION: Final[str] = {catalog_version!r}',
        "",
        "SIZE_TOKENS: Final[dict[str, int]] = {",
    ]
    for key, value in size_tokens.items():
        lines.append(f'    {key!r}: {value},')
    lines.append("}")
    lines.append("")
    lines.append("VISUAL_ASSETS: Final[tuple[VisualAssetItem, ...]] = (")

    for item in assets:
        lines.append(
            "    VisualAssetItem("
            f'id={item["id"]!r}, '
            f'label={item["label"]!r}, '
            f'category={item["category"]!r}, '
            f'kind={item["kind"]!r}, '
            f'tabler={_py_str(item.get("tabler"))}, '
            f'tabler_filled={_py_str(item.get("tabler_filled"))}, '
            f'svg={_py_str(item.get("svg"))}, '
            f'svg_filled={_py_str(item.get("svg_filled"))}, '
            f'svg_light={_py_str(item.get("svg_light"))}, '
            f'svg_dark={_py_str(item.get("svg_dark"))}, '
            f'svg_filled_light={_py_str(item.get("svg_filled_light"))}, '
            f'svg_filled_dark={_py_str(item.get("svg_filled_dark"))}, '
            f'brand_color={_py_str(item.get("brand_color"))}, '
            f'aliases={_py_tuple(item.get("aliases"))},'
            "),"
        )

    lines.extend(
        [
            ")",
            "",
            "VISUAL_ASSETS_BY_ID: Final[dict[str, VisualAssetItem]] = {",
            "    item.id: item for item in VISUAL_ASSETS",
            "}",
            "",
            "def _build_alias_index() -> dict[str, VisualAssetItem]:",
            "    index: dict[str, VisualAssetItem] = {}",
            "    for item in VISUAL_ASSETS:",
            "        for alias in item.aliases:",
            "            index[alias] = item",
            "    return index",
            "",
            "",
            "_ALIAS_INDEX: Final[dict[str, VisualAssetItem]] = _build_alias_index()",
        ]
    )

    lines.extend(
        [
            "",
            "def list_visual_assets() -> tuple[VisualAssetItem, ...]:",
            "    return VISUAL_ASSETS",
            "",
            "",
            "def get_visual_asset(asset_id: str | None) -> VisualAssetItem | None:",
            '    if not asset_id:',
            "        return None",
            "    key = str(asset_id).strip().lower()",
            "    if not key:",
            "        return None",
            "    if key in VISUAL_ASSETS_BY_ID:",
            "        return VISUAL_ASSETS_BY_ID[key]",
            "    return _ALIAS_INDEX.get(key)",
            "",
            "",
            "def resolve_icon_size(token: str | int, *, default: int = 16) -> int:",
            '    if isinstance(token, int):',
            "        return token",
            "    key = str(token).strip().lower()",
            "    return SIZE_TOKENS.get(key, default)",
            "",
            "",
            "def list_assets_by_category(category: VisualAssetCategory) -> tuple[VisualAssetItem, ...]:",
            "    return tuple(item for item in VISUAL_ASSETS if item.category == category)",
            "",
            "",
            'VisualAssetTheme = Literal["light", "dark"]',
            "",
            "",
            "def resolve_visual_asset_svg(",
            "    asset: VisualAssetItem,",
            '    variant: Literal["default", "filled"] = "default",',
            '    theme: VisualAssetTheme = "light",',
            ") -> str | None:",
            '    if variant == "filled":',
            '        if theme == "dark" and asset.svg_filled_dark:',
            "            return asset.svg_filled_dark",
            '        if theme == "light" and asset.svg_filled_light:',
            "            return asset.svg_filled_light",
            "        return asset.svg_filled",
            '    if theme == "dark" and asset.svg_dark:',
            "        return asset.svg_dark",
            '    if theme == "light" and asset.svg_light:',
            "        return asset.svg_light",
            "    return asset.svg",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def _generate_typescript(data: dict) -> str:
    catalog_version = data["catalog_version"]
    size_tokens = data["size_tokens"]
    assets = data["assets"]

    asset_ids = [item["id"] for item in assets]
    for item in assets:
        asset_ids.extend(item.get("aliases") or [])

    categories = sorted({item["category"] for item in assets})
    kinds = sorted({item["kind"] for item in assets})

    lines = [
        _TS_HEADER,
        f"export const VISUAL_ASSETS_CATALOG_VERSION = {json.dumps(catalog_version)} as const",
        "",
        "export const VISUAL_ASSET_SIZE_TOKENS = {",
    ]
    for key, value in size_tokens.items():
        lines.append(f"  {json.dumps(key)}: {value},")
    lines.extend(
        [
            "} as const",
            "",
            "export type VisualAssetSizeToken = keyof typeof VISUAL_ASSET_SIZE_TOKENS",
            f"export type VisualAssetCategory = {' | '.join(json.dumps(c) for c in categories)}",
            f"export type VisualAssetKind = {' | '.join(json.dumps(k) for k in kinds)}",
            "",
            "export type VisualAssetRecord = {",
            "  id: string",
            "  label: string",
            "  category: VisualAssetCategory",
            "  kind: VisualAssetKind",
            "  tabler?: string",
            "  tabler_filled?: string",
            "  svg?: string",
            "  svg_filled?: string",
            "  svg_light?: string",
            "  svg_dark?: string",
            "  svg_filled_light?: string",
            "  svg_filled_dark?: string",
            "  brand_color?: string",
            "  aliases?: string[]",
            "}",
            "",
            "export const VISUAL_ASSETS: readonly VisualAssetRecord[] = ",
            json.dumps(assets, ensure_ascii=True, indent=2),
            " as const",
            "",
            "export type VisualAssetId =",
        ]
    )

    unique_ids = sorted(set(asset_ids))
    if unique_ids:
        lines.append("  | " + "\n  | ".join(json.dumps(i) for i in unique_ids))
    else:
        lines.append("  never")

    lines.extend(
        [
            "",
            "const ASSET_BY_ID = new Map<string, VisualAssetRecord>(",
            "  VISUAL_ASSETS.map((asset) => [asset.id, asset]),",
            ")",
            "",
            "const ASSET_BY_ALIAS = new Map<string, VisualAssetRecord>()",
            "for (const asset of VISUAL_ASSETS) {",
            "  for (const alias of asset.aliases ?? []) {",
            "    ASSET_BY_ALIAS.set(alias, asset)",
            "  }",
            "}",
            "",
            "export function getVisualAsset(id: string | null | undefined): VisualAssetRecord | undefined {",
            "  if (!id) return undefined",
            "  const key = id.trim().toLowerCase()",
            "  if (!key) return undefined",
            "  return ASSET_BY_ID.get(key) ?? ASSET_BY_ALIAS.get(key)",
            "}",
            "",
            "export function resolveIconSize(",
            "  size: VisualAssetSizeToken | number | undefined,",
            "  fallback = 16,",
            "): number {",
            "  if (typeof size === 'number') return size",
            "  if (!size) return fallback",
            "  return VISUAL_ASSET_SIZE_TOKENS[size] ?? fallback",
            "}",
            "",
            "export function listAssetsByCategory(category: VisualAssetCategory): VisualAssetRecord[] {",
            "  return VISUAL_ASSETS.filter((asset) => asset.category === category)",
            "}",
            "",
            "export type VisualAssetTheme = 'light' | 'dark'",
            "",
            "export function resolveVisualAssetSvg(",
            "  asset: VisualAssetRecord,",
            "  variant: 'default' | 'filled' = 'default',",
            "  theme: VisualAssetTheme = 'light',",
            "): string | undefined {",
            "  if (variant === 'filled') {",
            "    if (theme === 'dark' && asset.svg_filled_dark) return asset.svg_filled_dark",
            "    if (theme === 'light' && asset.svg_filled_light) return asset.svg_filled_light",
            "    return asset.svg_filled",
            "  }",
            "  if (theme === 'dark' && asset.svg_dark) return asset.svg_dark",
            "  if (theme === 'light' && asset.svg_light) return asset.svg_light",
            "  return asset.svg",
            "}",
            "",
            "export function hasThemedVisualAssetSvg(asset: VisualAssetRecord): boolean {",
            "  return Boolean(asset.svg_light && asset.svg_dark && asset.svg_light !== asset.svg_dark)",
            "}",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate visual asset catalogs")
    parser.add_argument("--check", action="store_true", help="Fail if generated files drift")
    args = parser.parse_args()

    data = _load_json(MANIFEST)
    _validate(data)

    py_content = _generate_python(data)
    ts_content = _generate_typescript(data)

    if args.check:
        drift = False
        for path, expected in ((PY_OUT, py_content), (TS_OUT, ts_content)):
            if not path.exists():
                print(f"MISSING: {path}", file=sys.stderr)
                drift = True
            elif path.read_text(encoding="utf-8") != expected:
                print(f"DRIFT: {path}", file=sys.stderr)
                drift = True
        return 1 if drift else 0

    PY_OUT.parent.mkdir(parents=True, exist_ok=True)
    TS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.write_text(py_content, encoding="utf-8")
    TS_OUT.write_text(ts_content, encoding="utf-8")
    print(f"Wrote {PY_OUT}")
    print(f"Wrote {TS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
