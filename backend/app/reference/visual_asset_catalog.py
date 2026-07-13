# GENERATED FILE — do not edit by hand.
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


CATALOG_VERSION: Final[str] = 'visual-assets-v2'

SIZE_TOKENS: Final[dict[str, int]] = {
    'xs': 12,
    'sm': 16,
    'md': 20,
    'lg': 24,
    'xl': 32,
    '2xl': 48,
}

VISUAL_ASSETS: Final[tuple[VisualAssetItem, ...]] = (
    VisualAssetItem(id='whatsapp', label='WhatsApp', category='contact', kind='brand', tabler='IconBrandWhatsapp', tabler_filled='IconBrandWhatsappFilled', svg='/assets/icons/light/brands/whatsapp.svg', svg_filled='/assets/icons/light/brands/whatsapp-filled.svg', svg_light='/assets/icons/light/brands/whatsapp.svg', svg_dark='/assets/icons/dark/brands/whatsapp.svg', svg_filled_light='/assets/icons/light/brands/whatsapp-filled.svg', svg_filled_dark='/assets/icons/dark/brands/whatsapp-filled.svg', brand_color='#25D366', aliases=('wa',),),
    VisualAssetItem(id='telegram', label='Telegram', category='contact', kind='brand', tabler='IconBrandTelegram', tabler_filled=None, svg='/assets/icons/light/brands/telegram.svg', svg_filled=None, svg_light='/assets/icons/light/brands/telegram.svg', svg_dark='/assets/icons/dark/brands/telegram.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#26A5E4', aliases=('tg',),),
    VisualAssetItem(id='viber', label='Viber', category='contact', kind='brand', tabler=None, tabler_filled=None, svg='/assets/icons/light/brands/viber.svg', svg_filled=None, svg_light='/assets/icons/light/brands/viber.svg', svg_dark='/assets/icons/dark/brands/viber.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#7360F2', aliases=(),),
    VisualAssetItem(id='phone', label='Phone', category='contact', kind='glyph', tabler='IconPhone', tabler_filled=None, svg='/assets/icons/light/contact/phone.svg', svg_filled=None, svg_light='/assets/icons/light/contact/phone.svg', svg_dark='/assets/icons/dark/contact/phone.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='email', label='Email', category='contact', kind='glyph', tabler='IconMail', tabler_filled=None, svg='/assets/icons/light/contact/email.svg', svg_filled=None, svg_light='/assets/icons/light/contact/email.svg', svg_dark='/assets/icons/dark/contact/email.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('mail',),),
    VisualAssetItem(id='sms', label='SMS', category='contact', kind='glyph', tabler='IconMessage', tabler_filled=None, svg='/assets/icons/light/contact/sms.svg', svg_filled=None, svg_light='/assets/icons/light/contact/sms.svg', svg_dark='/assets/icons/dark/contact/sms.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='meta', label='Meta', category='source', kind='brand', tabler='IconBrandMeta', tabler_filled=None, svg='/assets/icons/light/brands/meta.svg', svg_filled=None, svg_light='/assets/icons/light/brands/meta.svg', svg_dark='/assets/icons/dark/brands/meta.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#0081FB', aliases=(),),
    VisualAssetItem(id='facebook', label='Facebook', category='source', kind='brand', tabler='IconBrandFacebook', tabler_filled='IconBrandFacebookFilled', svg='/assets/icons/light/brands/facebook.svg', svg_filled='/assets/icons/light/brands/facebook-filled.svg', svg_light='/assets/icons/light/brands/facebook.svg', svg_dark='/assets/icons/dark/brands/facebook.svg', svg_filled_light='/assets/icons/light/brands/facebook-filled.svg', svg_filled_dark='/assets/icons/dark/brands/facebook-filled.svg', brand_color='#1877F2', aliases=(),),
    VisualAssetItem(id='google', label='Google', category='source', kind='brand', tabler='IconBrandGoogle', tabler_filled='IconBrandGoogleFilled', svg='/assets/icons/light/brands/google.svg', svg_filled=None, svg_light='/assets/icons/light/brands/google.svg', svg_dark='/assets/icons/dark/brands/google.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#4285F4', aliases=(),),
    VisualAssetItem(id='tiktok', label='TikTok', category='source', kind='brand', tabler='IconBrandTiktok', tabler_filled='IconBrandTiktokFilled', svg='/assets/icons/light/brands/tiktok.svg', svg_filled=None, svg_light='/assets/icons/light/brands/tiktok.svg', svg_dark='/assets/icons/dark/brands/tiktok.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#000000', aliases=(),),
    VisualAssetItem(id='linkedin', label='LinkedIn', category='source', kind='brand', tabler='IconBrandLinkedin', tabler_filled='IconBrandLinkedinFilled', svg='/assets/icons/light/brands/linkedin.svg', svg_filled='/assets/icons/light/brands/linkedin-filled.svg', svg_light='/assets/icons/light/brands/linkedin.svg', svg_dark='/assets/icons/dark/brands/linkedin.svg', svg_filled_light='/assets/icons/light/brands/linkedin-filled.svg', svg_filled_dark='/assets/icons/dark/brands/linkedin-filled.svg', brand_color='#0A66C2', aliases=(),),
    VisualAssetItem(id='instagram', label='Instagram', category='source', kind='brand', tabler='IconBrandInstagram', tabler_filled='IconBrandInstagramFilled', svg='/assets/icons/light/brands/instagram.svg', svg_filled=None, svg_light='/assets/icons/light/brands/instagram.svg', svg_dark='/assets/icons/dark/brands/instagram.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#E4405F', aliases=(),),
    VisualAssetItem(id='x', label='X', category='source', kind='brand', tabler='IconBrandX', tabler_filled=None, svg='/assets/icons/light/brands/x.svg', svg_filled=None, svg_light='/assets/icons/light/brands/x.svg', svg_dark='/assets/icons/dark/brands/x.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#000000', aliases=('twitter',),),
    VisualAssetItem(id='vk', label='VK', category='source', kind='brand', tabler='IconBrandVk', tabler_filled=None, svg='/assets/icons/light/brands/vk.svg', svg_filled=None, svg_light='/assets/icons/light/brands/vk.svg', svg_dark='/assets/icons/dark/brands/vk.svg', svg_filled_light=None, svg_filled_dark=None, brand_color='#0077FF', aliases=(),),
    VisualAssetItem(id='referral', label='Referral', category='source', kind='glyph', tabler='IconUsers', tabler_filled=None, svg='/assets/icons/light/source/referral.svg', svg_filled=None, svg_light='/assets/icons/light/source/referral.svg', svg_dark='/assets/icons/dark/source/referral.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='website', label='Website', category='source', kind='glyph', tabler='IconWorld', tabler_filled=None, svg='/assets/icons/light/source/website.svg', svg_filled=None, svg_light='/assets/icons/light/source/website.svg', svg_dark='/assets/icons/dark/source/website.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('web', 'direct',),),
    VisualAssetItem(id='webhook', label='Webhook', category='source', kind='glyph', tabler='IconWebhook', tabler_filled=None, svg='/assets/icons/light/source/webhook.svg', svg_filled=None, svg_light='/assets/icons/light/source/webhook.svg', svg_dark='/assets/icons/dark/source/webhook.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='flag-pl', label='Poland', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/pl.svg', svg_filled=None, svg_light='/assets/icons/light/flags/pl.svg', svg_dark='/assets/icons/dark/flags/pl.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('pl',),),
    VisualAssetItem(id='flag-de', label='Germany', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/de.svg', svg_filled=None, svg_light='/assets/icons/light/flags/de.svg', svg_dark='/assets/icons/dark/flags/de.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('de',),),
    VisualAssetItem(id='flag-ua', label='Ukraine', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/ua.svg', svg_filled=None, svg_light='/assets/icons/light/flags/ua.svg', svg_dark='/assets/icons/dark/flags/ua.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('ua',),),
    VisualAssetItem(id='flag-by', label='Belarus', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/by.svg', svg_filled=None, svg_light='/assets/icons/light/flags/by.svg', svg_dark='/assets/icons/dark/flags/by.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('by',),),
    VisualAssetItem(id='flag-cz', label='Czechia', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/cz.svg', svg_filled=None, svg_light='/assets/icons/light/flags/cz.svg', svg_dark='/assets/icons/dark/flags/cz.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('cz',),),
    VisualAssetItem(id='flag-lt', label='Lithuania', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/lt.svg', svg_filled=None, svg_light='/assets/icons/light/flags/lt.svg', svg_dark='/assets/icons/dark/flags/lt.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('lt',),),
    VisualAssetItem(id='flag-lv', label='Latvia', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/lv.svg', svg_filled=None, svg_light='/assets/icons/light/flags/lv.svg', svg_dark='/assets/icons/dark/flags/lv.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('lv',),),
    VisualAssetItem(id='flag-ee', label='Estonia', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/ee.svg', svg_filled=None, svg_light='/assets/icons/light/flags/ee.svg', svg_dark='/assets/icons/dark/flags/ee.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('ee',),),
    VisualAssetItem(id='flag-ro', label='Romania', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/ro.svg', svg_filled=None, svg_light='/assets/icons/light/flags/ro.svg', svg_dark='/assets/icons/dark/flags/ro.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('ro',),),
    VisualAssetItem(id='flag-md', label='Moldova', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/md.svg', svg_filled=None, svg_light='/assets/icons/light/flags/md.svg', svg_dark='/assets/icons/dark/flags/md.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('md',),),
    VisualAssetItem(id='flag-ge', label='Georgia', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/ge.svg', svg_filled=None, svg_light='/assets/icons/light/flags/ge.svg', svg_dark='/assets/icons/dark/flags/ge.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('ge',),),
    VisualAssetItem(id='flag-uz', label='Uzbekistan', category='flag', kind='flag', tabler=None, tabler_filled=None, svg='/assets/icons/light/flags/uz.svg', svg_filled=None, svg_light='/assets/icons/light/flags/uz.svg', svg_dark='/assets/icons/dark/flags/uz.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=('uz',),),
    VisualAssetItem(id='hostflow', label='HostFlow', category='product', kind='logo', tabler=None, tabler_filled=None, svg='/logo_hf.svg', svg_filled=None, svg_light='/logo_hf.svg', svg_dark='/logo_hf_white.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='hostflow-white', label='HostFlow', category='product', kind='logo', tabler=None, tabler_filled=None, svg='/logo_hf_white.svg', svg_filled=None, svg_light='/logo_hf_white.svg', svg_dark='/logo_hf_white.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='hostflow-text', label='HostFlow', category='product', kind='logo', tabler=None, tabler_filled=None, svg='/logo_text.svg', svg_filled=None, svg_light='/logo_text.svg', svg_dark='/logo_text_white.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
    VisualAssetItem(id='hostflow-favicon', label='HostFlow', category='product', kind='logo', tabler=None, tabler_filled=None, svg='/favicon.svg', svg_filled=None, svg_light='/favicon.svg', svg_dark='/favicon.svg', svg_filled_light=None, svg_filled_dark=None, brand_color=None, aliases=(),),
)

VISUAL_ASSETS_BY_ID: Final[dict[str, VisualAssetItem]] = {
    item.id: item for item in VISUAL_ASSETS
}

def _build_alias_index() -> dict[str, VisualAssetItem]:
    index: dict[str, VisualAssetItem] = {}
    for item in VISUAL_ASSETS:
        for alias in item.aliases:
            index[alias] = item
    return index


_ALIAS_INDEX: Final[dict[str, VisualAssetItem]] = _build_alias_index()

def list_visual_assets() -> tuple[VisualAssetItem, ...]:
    return VISUAL_ASSETS


def get_visual_asset(asset_id: str | None) -> VisualAssetItem | None:
    if not asset_id:
        return None
    key = str(asset_id).strip().lower()
    if not key:
        return None
    if key in VISUAL_ASSETS_BY_ID:
        return VISUAL_ASSETS_BY_ID[key]
    return _ALIAS_INDEX.get(key)


def resolve_icon_size(token: str | int, *, default: int = 16) -> int:
    if isinstance(token, int):
        return token
    key = str(token).strip().lower()
    return SIZE_TOKENS.get(key, default)


def list_assets_by_category(category: VisualAssetCategory) -> tuple[VisualAssetItem, ...]:
    return tuple(item for item in VISUAL_ASSETS if item.category == category)


VisualAssetTheme = Literal["light", "dark"]


def resolve_visual_asset_svg(
    asset: VisualAssetItem,
    variant: Literal["default", "filled"] = "default",
    theme: VisualAssetTheme = "light",
) -> str | None:
    if variant == "filled":
        if theme == "dark" and asset.svg_filled_dark:
            return asset.svg_filled_dark
        if theme == "light" and asset.svg_filled_light:
            return asset.svg_filled_light
        return asset.svg_filled
    if theme == "dark" and asset.svg_dark:
        return asset.svg_dark
    if theme == "light" and asset.svg_light:
        return asset.svg_light
    return asset.svg

