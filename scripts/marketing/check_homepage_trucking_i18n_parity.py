#!/usr/bin/env python3
"""Parity check for homepage + trucking public i18n (EN / RU / PL).

Scopes:
  - public.crm_landing
  - public.marketing.use_case_trucking_recruitment
  - public.marketing.common (CTA / FAQ / related used on trucking)
  - app.seo.landing
  - app.seo.pricing

Fails when:
  1) key sets differ across locales
  2) RU/PL leaf strings still equal EN (except allowlisted technical/brand tokens)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "hostflow-frontend" / "src" / "i18n"

SCOPES = (
    ("public", "crm_landing"),
    ("public", "marketing", "use_case_trucking_recruitment"),
    ("public", "marketing", "common"),
    ("app", "seo", "landing"),
    ("app", "seo", "pricing"),
)

# Leaves that may stay identical across locales (paths, brands, prices, codes).
ALLOW_EQUAL = {
    "FAQ",
    "Solo",
    "Team",
    "Business",
    "Enterprise",
    "HostFlow",
    "Focus Personnel",
    "Code 95",
    "C / CE",
    "Meta",
    "Recruitment",
    "Recruitment CRM vs ATS",
    "€29",
    "€24",
    "€129",
    "€109",
    "€249",
    "€219",
    "WhatsApp",
    # Natural PL cognates (same spelling / loanword as EN marketing short labels)
    "Problem",
    "Transport",
    "Demo",
}

ALLOW_SUFFIXES = (
    "screenshot_src",
)

ALLOW_CONTAINS = (
    "/landing/",
)


def dig(data: dict, path: tuple[str, ...]):
    cur = data
    for part in path:
        cur = cur[part]
    return cur


def flatten(node, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(flatten(value, path))
    else:
        out[prefix] = "" if node is None else str(node)
    return out


def allowed_equal(key: str, value: str) -> bool:
    if value in ALLOW_EQUAL:
        return True
    if any(key.endswith(suf) for suf in ALLOW_SUFFIXES):
        return True
    if any(token in value for token in ALLOW_CONTAINS):
        return True
    # plan seats lines may keep "workspace" as product noun; still require translation of surrounding text
    return False


def main() -> int:
    locales = {
        "en": json.loads((I18N / "en.json").read_text()),
        "ru": json.loads((I18N / "ru.json").read_text()),
        "pl": json.loads((I18N / "pl.json").read_text()),
    }

    flat: dict[str, dict[str, str]] = {loc: {} for loc in locales}
    for scope in SCOPES:
        scope_label = ".".join(scope)
        for loc, data in locales.items():
            try:
                node = dig(data, scope)
            except KeyError:
                print(f"MISSING scope {scope_label} in {loc}", file=sys.stderr)
                return 1
            for key, value in flatten(node).items():
                flat[loc][f"{scope_label}.{key}"] = value

    errors: list[str] = []
    en_keys = set(flat["en"])
    for loc in ("ru", "pl"):
        keys = set(flat[loc])
        missing = sorted(en_keys - keys)
        extra = sorted(keys - en_keys)
        if missing:
            errors.append(f"{loc}: missing {len(missing)} keys (e.g. {missing[:5]})")
        if extra:
            errors.append(f"{loc}: extra {len(extra)} keys (e.g. {extra[:5]})")

    english_leftovers: list[str] = []
    for loc in ("ru", "pl"):
        for key, en_val in flat["en"].items():
            loc_val = flat[loc].get(key)
            if loc_val is None:
                continue
            if loc_val == en_val and en_val.strip() and not allowed_equal(key, en_val):
                english_leftovers.append(f"{loc}: {key} = {en_val!r}")

    print("Homepage + trucking i18n parity")
    print(f"EN keys: {len(en_keys)}")
    print(f"RU keys: {len(flat['ru'])}")
    print(f"PL keys: {len(flat['pl'])}")
    print(f"English leftovers (RU/PL == EN): {len(english_leftovers)}")

    if english_leftovers:
        print("\nLeftovers:")
        for line in english_leftovers[:80]:
            print(f"  {line}")
        if len(english_leftovers) > 80:
            print(f"  … +{len(english_leftovers) - 80} more")

    if errors or english_leftovers:
        for err in errors:
            print(err, file=sys.stderr)
        print("FAIL", file=sys.stderr)
        return 1

    print("OK: key parity and no unexpected English leftovers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
