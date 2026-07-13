from __future__ import annotations

from backend.app.reference.visual_asset_catalog import (
    CATALOG_VERSION,
    SIZE_TOKENS,
    VISUAL_ASSETS,
    get_visual_asset,
    list_assets_by_category,
    list_visual_assets,
    resolve_icon_size,
    resolve_visual_asset_svg,
)


def test_visual_asset_catalog_basic_shape() -> None:
    assert CATALOG_VERSION.startswith("visual-assets-")
    assert len(VISUAL_ASSETS) >= 10
    assert SIZE_TOKENS["sm"] == 16
    assert SIZE_TOKENS["2xl"] == 48


def test_visual_asset_lookup_and_aliases() -> None:
    assert get_visual_asset("whatsapp") is not None
    assert get_visual_asset("wa") is not None
    assert get_visual_asset(" WA ") is not None
    assert get_visual_asset(None) is None

    assert get_visual_asset("pl") is not None
    assert get_visual_asset("flag-pl") is not None


def test_visual_asset_category_filter() -> None:
    flags = list_assets_by_category("flag")
    assert len(flags) >= 5
    assert all(item.category == "flag" for item in flags)


def test_visual_asset_iterable() -> None:
    assets = list_visual_assets()
    assert isinstance(assets, tuple)
    assert assets == VISUAL_ASSETS


def test_resolve_icon_size() -> None:
    assert resolve_icon_size("md") == 20
    assert resolve_icon_size(24) == 24
    assert resolve_icon_size("unknown", default=18) == 18


def test_resolve_visual_asset_svg_themes() -> None:
    x_asset = get_visual_asset("x")
    assert x_asset is not None
    light = resolve_visual_asset_svg(x_asset, theme="light")
    dark = resolve_visual_asset_svg(x_asset, theme="dark")
    assert light is not None
    assert dark is not None
    assert light != dark
    assert "/light/" in light
    assert "/dark/" in dark

    hostflow = get_visual_asset("hostflow")
    assert hostflow is not None
    assert resolve_visual_asset_svg(hostflow, theme="light") == "/logo_hf.svg"
    assert resolve_visual_asset_svg(hostflow, theme="dark") == "/logo_hf_white.svg"
