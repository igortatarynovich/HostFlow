HostFlow visual assets dataset
===========================

Canonical source: `shared/visual_assets.json`

## Canonical sources

Brand and flag SVGs are fetched from official/canonical open datasets:

| Source | Assets | URL |
|--------|--------|-----|
| [Simple Icons](https://simpleicons.org/) | WhatsApp, Telegram, Facebook, Meta, TikTok, X, VK, Viber | Brand guideline paths |
| [Wikimedia Commons](https://commons.wikimedia.org/) | Google G, LinkedIn, Instagram (gradient) | Official logo files |
| [flag-icons](https://github.com/lipis/flag-icons) | Country flags (PL, DE, UA, …) | ISO 3166-1 alpha-2 |

Re-fetch originals:

```bash
python3 scripts/assets/fetch_canonical_icons.py
```

Contact/source glyphs (`contact/`, `source/`) use Tabler-compatible paths — no single canonical brand owner.

## Contents

| Category | Examples | Use case |
|----------|----------|----------|
| `brand` / `contact` | WhatsApp, Telegram, phone, email | Contact quick actions, messenger chips |
| `source` | Meta, Google, TikTok, LinkedIn, referral | Intake source facets and badges |
| `flag` | PL, DE, UA, BY, CZ, LT, LV, EE, RO, MD, GE, UZ | Citizenship / country display |
| `product` | hostflow, hostflow-white, favicon | Product branding |

## Size tokens

| Token | px |
|-------|----|
| `xs`  | 12 |
| `sm`  | 16 |
| `md`  | 20 |
| `lg`  | 24 |
| `xl`  | 32 |
| `2xl` | 48 |

SVG assets scale to any size. Pass a token or pixel value to `PlatformIcon`.

## File layout

```
shared/visual_assets.json          # SSOT manifest
hostflow-frontend/public/assets/icons/
  light/                           # Light-theme SVGs
    brands/
    contact/
    source/
    flags/
  dark/                            # Dark-theme SVGs (auto-generated where needed)
    brands/
    contact/
    source/
    flags/
hostflow-frontend/src/platform/icons/
  PlatformIcon.tsx                 # React resolver component
  visualAssets.generated.ts        # Generated catalog (do not edit)
backend/app/reference/
  visual_asset_catalog.py          # Generated Python catalog (do not edit)
```

## Light / dark themes

Each asset has `svg_light` and `svg_dark` paths in the manifest:

| Kind | Light | Dark |
|------|-------|------|
| Colored brands | brand color SVG | same file |
| Monochrome brands (X, TikTok) | black fill | white fill |
| Glyphs (phone, email, …) | slate-700 stroke | slate-200 stroke |
| Flags | identical | identical |
| Product logos | `/logo_hf.svg` | `/logo_hf_white.svg` |

Generate dark variants after fetching:

```bash
python3 scripts/assets/sync_icon_themes.py
```

## Regenerate catalogs

```bash
python3 scripts/codegen/generate_visual_assets.py
# or
npm run codegen:visual-assets
```

## Usage (frontend)

```tsx
import { PlatformIcon } from '@/platform/icons'

// Monochrome Tabler icon (default)
<PlatformIcon id="whatsapp" size="sm" />

// Colored brand logo
<PlatformIcon id="whatsapp" size="md" variant="brand" />

// Country flag
<PlatformIcon id="flag-pl" size={20} variant="brand" />

// Auto theme (switches with Tailwind `dark:` on parent/html)
<PlatformIcon id="x" size="md" variant="brand" theme="auto" />

// Explicit theme
<PlatformIcon id="phone" size="sm" theme="dark" />
```

## Usage (backend)

```python
from backend.app.reference.visual_asset_catalog import get_visual_asset, resolve_icon_size, resolve_visual_asset_svg

asset = get_visual_asset("meta")
px = resolve_icon_size("sm")  # 16
dark_svg = resolve_visual_asset_svg(asset, theme="dark")
```

## Adding a new asset

1. Add SVG to `public/assets/icons/<category>/` if needed.
2. Add entry to `shared/visual_assets.json`.
3. If Tabler icon exists, set `tabler` field; add to `tablerIconMap.ts` if not already mapped.
4. Run codegen script.
