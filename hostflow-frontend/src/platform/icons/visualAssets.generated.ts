/**
 * GENERATED FILE — do not edit by hand.
 * Source: `shared/visual_assets.json`.
 * Regenerate: `python3 scripts/codegen/generate_visual_assets.py` or `npm run codegen:visual-assets`.
 */


export const VISUAL_ASSETS_CATALOG_VERSION = "visual-assets-v2" as const

export const VISUAL_ASSET_SIZE_TOKENS = {
  "xs": 12,
  "sm": 16,
  "md": 20,
  "lg": 24,
  "xl": 32,
  "2xl": 48,
} as const

export type VisualAssetSizeToken = keyof typeof VISUAL_ASSET_SIZE_TOKENS
export type VisualAssetCategory = "contact" | "flag" | "product" | "source"
export type VisualAssetKind = "brand" | "flag" | "glyph" | "logo"

export type VisualAssetRecord = {
  id: string
  label: string
  category: VisualAssetCategory
  kind: VisualAssetKind
  tabler?: string
  tabler_filled?: string
  svg?: string
  svg_filled?: string
  svg_light?: string
  svg_dark?: string
  svg_filled_light?: string
  svg_filled_dark?: string
  brand_color?: string
  aliases?: string[]
}

export const VISUAL_ASSETS = 
[
  {
    "id": "whatsapp",
    "label": "WhatsApp",
    "category": "contact",
    "kind": "brand",
    "tabler": "IconBrandWhatsapp",
    "tabler_filled": "IconBrandWhatsappFilled",
    "svg": "/assets/icons/light/brands/whatsapp.svg",
    "svg_filled": "/assets/icons/light/brands/whatsapp-filled.svg",
    "brand_color": "#25D366",
    "aliases": [
      "wa"
    ],
    "svg_light": "/assets/icons/light/brands/whatsapp.svg",
    "svg_dark": "/assets/icons/dark/brands/whatsapp.svg",
    "svg_filled_light": "/assets/icons/light/brands/whatsapp-filled.svg",
    "svg_filled_dark": "/assets/icons/dark/brands/whatsapp-filled.svg"
  },
  {
    "id": "telegram",
    "label": "Telegram",
    "category": "contact",
    "kind": "brand",
    "tabler": "IconBrandTelegram",
    "svg": "/assets/icons/light/brands/telegram.svg",
    "brand_color": "#26A5E4",
    "aliases": [
      "tg"
    ],
    "svg_light": "/assets/icons/light/brands/telegram.svg",
    "svg_dark": "/assets/icons/dark/brands/telegram.svg"
  },
  {
    "id": "viber",
    "label": "Viber",
    "category": "contact",
    "kind": "brand",
    "svg": "/assets/icons/light/brands/viber.svg",
    "brand_color": "#7360F2",
    "svg_light": "/assets/icons/light/brands/viber.svg",
    "svg_dark": "/assets/icons/dark/brands/viber.svg"
  },
  {
    "id": "phone",
    "label": "Phone",
    "category": "contact",
    "kind": "glyph",
    "tabler": "IconPhone",
    "svg": "/assets/icons/light/contact/phone.svg",
    "svg_light": "/assets/icons/light/contact/phone.svg",
    "svg_dark": "/assets/icons/dark/contact/phone.svg"
  },
  {
    "id": "email",
    "label": "Email",
    "category": "contact",
    "kind": "glyph",
    "tabler": "IconMail",
    "svg": "/assets/icons/light/contact/email.svg",
    "aliases": [
      "mail"
    ],
    "svg_light": "/assets/icons/light/contact/email.svg",
    "svg_dark": "/assets/icons/dark/contact/email.svg"
  },
  {
    "id": "sms",
    "label": "SMS",
    "category": "contact",
    "kind": "glyph",
    "tabler": "IconMessage",
    "svg": "/assets/icons/light/contact/sms.svg",
    "svg_light": "/assets/icons/light/contact/sms.svg",
    "svg_dark": "/assets/icons/dark/contact/sms.svg"
  },
  {
    "id": "meta",
    "label": "Meta",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandMeta",
    "svg": "/assets/icons/light/brands/meta.svg",
    "brand_color": "#0081FB",
    "svg_light": "/assets/icons/light/brands/meta.svg",
    "svg_dark": "/assets/icons/dark/brands/meta.svg"
  },
  {
    "id": "facebook",
    "label": "Facebook",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandFacebook",
    "tabler_filled": "IconBrandFacebookFilled",
    "svg": "/assets/icons/light/brands/facebook.svg",
    "svg_filled": "/assets/icons/light/brands/facebook-filled.svg",
    "brand_color": "#1877F2",
    "svg_light": "/assets/icons/light/brands/facebook.svg",
    "svg_dark": "/assets/icons/dark/brands/facebook.svg",
    "svg_filled_light": "/assets/icons/light/brands/facebook-filled.svg",
    "svg_filled_dark": "/assets/icons/dark/brands/facebook-filled.svg"
  },
  {
    "id": "google",
    "label": "Google",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandGoogle",
    "tabler_filled": "IconBrandGoogleFilled",
    "svg": "/assets/icons/light/brands/google.svg",
    "brand_color": "#4285F4",
    "svg_light": "/assets/icons/light/brands/google.svg",
    "svg_dark": "/assets/icons/dark/brands/google.svg"
  },
  {
    "id": "tiktok",
    "label": "TikTok",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandTiktok",
    "tabler_filled": "IconBrandTiktokFilled",
    "svg": "/assets/icons/light/brands/tiktok.svg",
    "brand_color": "#000000",
    "svg_light": "/assets/icons/light/brands/tiktok.svg",
    "svg_dark": "/assets/icons/dark/brands/tiktok.svg"
  },
  {
    "id": "linkedin",
    "label": "LinkedIn",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandLinkedin",
    "tabler_filled": "IconBrandLinkedinFilled",
    "svg": "/assets/icons/light/brands/linkedin.svg",
    "svg_filled": "/assets/icons/light/brands/linkedin-filled.svg",
    "brand_color": "#0A66C2",
    "svg_light": "/assets/icons/light/brands/linkedin.svg",
    "svg_dark": "/assets/icons/dark/brands/linkedin.svg",
    "svg_filled_light": "/assets/icons/light/brands/linkedin-filled.svg",
    "svg_filled_dark": "/assets/icons/dark/brands/linkedin-filled.svg"
  },
  {
    "id": "instagram",
    "label": "Instagram",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandInstagram",
    "tabler_filled": "IconBrandInstagramFilled",
    "svg": "/assets/icons/light/brands/instagram.svg",
    "brand_color": "#E4405F",
    "svg_light": "/assets/icons/light/brands/instagram.svg",
    "svg_dark": "/assets/icons/dark/brands/instagram.svg"
  },
  {
    "id": "x",
    "label": "X",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandX",
    "svg": "/assets/icons/light/brands/x.svg",
    "brand_color": "#000000",
    "aliases": [
      "twitter"
    ],
    "svg_light": "/assets/icons/light/brands/x.svg",
    "svg_dark": "/assets/icons/dark/brands/x.svg"
  },
  {
    "id": "vk",
    "label": "VK",
    "category": "source",
    "kind": "brand",
    "tabler": "IconBrandVk",
    "svg": "/assets/icons/light/brands/vk.svg",
    "brand_color": "#0077FF",
    "svg_light": "/assets/icons/light/brands/vk.svg",
    "svg_dark": "/assets/icons/dark/brands/vk.svg"
  },
  {
    "id": "referral",
    "label": "Referral",
    "category": "source",
    "kind": "glyph",
    "tabler": "IconUsers",
    "svg": "/assets/icons/light/source/referral.svg",
    "svg_light": "/assets/icons/light/source/referral.svg",
    "svg_dark": "/assets/icons/dark/source/referral.svg"
  },
  {
    "id": "website",
    "label": "Website",
    "category": "source",
    "kind": "glyph",
    "tabler": "IconWorld",
    "svg": "/assets/icons/light/source/website.svg",
    "aliases": [
      "web",
      "direct"
    ],
    "svg_light": "/assets/icons/light/source/website.svg",
    "svg_dark": "/assets/icons/dark/source/website.svg"
  },
  {
    "id": "webhook",
    "label": "Webhook",
    "category": "source",
    "kind": "glyph",
    "tabler": "IconWebhook",
    "svg": "/assets/icons/light/source/webhook.svg",
    "svg_light": "/assets/icons/light/source/webhook.svg",
    "svg_dark": "/assets/icons/dark/source/webhook.svg"
  },
  {
    "id": "flag-pl",
    "label": "Poland",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/pl.svg",
    "aliases": [
      "pl"
    ],
    "svg_light": "/assets/icons/light/flags/pl.svg",
    "svg_dark": "/assets/icons/dark/flags/pl.svg"
  },
  {
    "id": "flag-de",
    "label": "Germany",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/de.svg",
    "aliases": [
      "de"
    ],
    "svg_light": "/assets/icons/light/flags/de.svg",
    "svg_dark": "/assets/icons/dark/flags/de.svg"
  },
  {
    "id": "flag-ua",
    "label": "Ukraine",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/ua.svg",
    "aliases": [
      "ua"
    ],
    "svg_light": "/assets/icons/light/flags/ua.svg",
    "svg_dark": "/assets/icons/dark/flags/ua.svg"
  },
  {
    "id": "flag-by",
    "label": "Belarus",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/by.svg",
    "aliases": [
      "by"
    ],
    "svg_light": "/assets/icons/light/flags/by.svg",
    "svg_dark": "/assets/icons/dark/flags/by.svg"
  },
  {
    "id": "flag-cz",
    "label": "Czechia",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/cz.svg",
    "aliases": [
      "cz"
    ],
    "svg_light": "/assets/icons/light/flags/cz.svg",
    "svg_dark": "/assets/icons/dark/flags/cz.svg"
  },
  {
    "id": "flag-lt",
    "label": "Lithuania",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/lt.svg",
    "aliases": [
      "lt"
    ],
    "svg_light": "/assets/icons/light/flags/lt.svg",
    "svg_dark": "/assets/icons/dark/flags/lt.svg"
  },
  {
    "id": "flag-lv",
    "label": "Latvia",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/lv.svg",
    "aliases": [
      "lv"
    ],
    "svg_light": "/assets/icons/light/flags/lv.svg",
    "svg_dark": "/assets/icons/dark/flags/lv.svg"
  },
  {
    "id": "flag-ee",
    "label": "Estonia",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/ee.svg",
    "aliases": [
      "ee"
    ],
    "svg_light": "/assets/icons/light/flags/ee.svg",
    "svg_dark": "/assets/icons/dark/flags/ee.svg"
  },
  {
    "id": "flag-ro",
    "label": "Romania",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/ro.svg",
    "aliases": [
      "ro"
    ],
    "svg_light": "/assets/icons/light/flags/ro.svg",
    "svg_dark": "/assets/icons/dark/flags/ro.svg"
  },
  {
    "id": "flag-md",
    "label": "Moldova",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/md.svg",
    "aliases": [
      "md"
    ],
    "svg_light": "/assets/icons/light/flags/md.svg",
    "svg_dark": "/assets/icons/dark/flags/md.svg"
  },
  {
    "id": "flag-ge",
    "label": "Georgia",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/ge.svg",
    "aliases": [
      "ge"
    ],
    "svg_light": "/assets/icons/light/flags/ge.svg",
    "svg_dark": "/assets/icons/dark/flags/ge.svg"
  },
  {
    "id": "flag-uz",
    "label": "Uzbekistan",
    "category": "flag",
    "kind": "flag",
    "svg": "/assets/icons/light/flags/uz.svg",
    "aliases": [
      "uz"
    ],
    "svg_light": "/assets/icons/light/flags/uz.svg",
    "svg_dark": "/assets/icons/dark/flags/uz.svg"
  },
  {
    "id": "hostflow",
    "label": "HostFlow",
    "category": "product",
    "kind": "logo",
    "svg": "/logo_hf.svg",
    "svg_light": "/logo_hf.svg",
    "svg_dark": "/logo_hf_white.svg"
  },
  {
    "id": "hostflow-white",
    "label": "HostFlow",
    "category": "product",
    "kind": "logo",
    "svg": "/logo_hf_white.svg",
    "svg_light": "/logo_hf_white.svg",
    "svg_dark": "/logo_hf_white.svg"
  },
  {
    "id": "hostflow-text",
    "label": "HostFlow",
    "category": "product",
    "kind": "logo",
    "svg": "/logo_text.svg",
    "svg_light": "/logo_text.svg",
    "svg_dark": "/logo_text_white.svg"
  },
  {
    "id": "hostflow-favicon",
    "label": "HostFlow",
    "category": "product",
    "kind": "logo",
    "svg": "/favicon.svg",
    "svg_light": "/favicon.svg",
    "svg_dark": "/favicon.svg"
  }
] as const satisfies readonly VisualAssetRecord[]

export type VisualAssetId =
  | "by"
  | "cz"
  | "de"
  | "direct"
  | "ee"
  | "email"
  | "facebook"
  | "flag-by"
  | "flag-cz"
  | "flag-de"
  | "flag-ee"
  | "flag-ge"
  | "flag-lt"
  | "flag-lv"
  | "flag-md"
  | "flag-pl"
  | "flag-ro"
  | "flag-ua"
  | "flag-uz"
  | "ge"
  | "google"
  | "hostflow"
  | "hostflow-favicon"
  | "hostflow-text"
  | "hostflow-white"
  | "instagram"
  | "linkedin"
  | "lt"
  | "lv"
  | "mail"
  | "md"
  | "meta"
  | "phone"
  | "pl"
  | "referral"
  | "ro"
  | "sms"
  | "telegram"
  | "tg"
  | "tiktok"
  | "twitter"
  | "ua"
  | "uz"
  | "viber"
  | "vk"
  | "wa"
  | "web"
  | "webhook"
  | "website"
  | "whatsapp"
  | "x"

const ASSET_BY_ID = new Map<string, VisualAssetRecord>(
  VISUAL_ASSETS.map((asset) => [asset.id, asset]),
)

const ASSET_BY_ALIAS = new Map<string, VisualAssetRecord>()
for (const asset of VISUAL_ASSETS) {
  for (const alias of asset.aliases ?? []) {
    ASSET_BY_ALIAS.set(alias, asset)
  }
}

export function getVisualAsset(id: string | null | undefined): VisualAssetRecord | undefined {
  if (!id) return undefined
  const key = id.trim().toLowerCase()
  if (!key) return undefined
  return ASSET_BY_ID.get(key) ?? ASSET_BY_ALIAS.get(key)
}

export function resolveIconSize(
  size: VisualAssetSizeToken | number | undefined,
  fallback = 16,
): number {
  if (typeof size === 'number') return size
  if (!size) return fallback
  return VISUAL_ASSET_SIZE_TOKENS[size] ?? fallback
}

export function listAssetsByCategory(category: VisualAssetCategory): VisualAssetRecord[] {
  return VISUAL_ASSETS.filter((asset) => asset.category === category)
}

export type VisualAssetTheme = 'light' | 'dark'

export function resolveVisualAssetSvg(
  asset: VisualAssetRecord,
  variant: 'default' | 'filled' = 'default',
  theme: VisualAssetTheme = 'light',
): string | undefined {
  if (variant === 'filled') {
    if (theme === 'dark' && asset.svg_filled_dark) return asset.svg_filled_dark
    if (theme === 'light' && asset.svg_filled_light) return asset.svg_filled_light
    return asset.svg_filled
  }
  if (theme === 'dark' && asset.svg_dark) return asset.svg_dark
  if (theme === 'light' && asset.svg_light) return asset.svg_light
  return asset.svg
}

export function hasThemedVisualAssetSvg(asset: VisualAssetRecord): boolean {
  return Boolean(asset.svg_light && asset.svg_dark && asset.svg_light !== asset.svg_dark)
}

