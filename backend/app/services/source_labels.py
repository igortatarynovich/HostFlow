from __future__ import annotations

from typing import Optional

_SOURCE_LABELS = {
    "meta": "FB",
    "facebook": "FB",
    "facebook_ads": "FB",
    "fb": "FB",
    "fb_ads": "FB",
    "facebookads": "FB",
    "facebook-ads": "FB",
    "public-intake": "Анкета",
    "public_intake": "Анкета",
    "public-intake-ui": "Анкета",
    "public_intake_ui": "Анкета",
    "public-form": "Анкета",
    "public_form": "Анкета",
    "website_form": "Анкета",
    "site_form": "Анкета",
    "form": "Анкета",
}


def normalize_candidate_source(value: Optional[str], default: Optional[str] = None) -> Optional[str]:
    """
    Normalize internal source codes (e.g. meta/web forms) to user-facing labels.
    """
    candidate = (value or "").strip()
    if not candidate and default:
        candidate = default.strip()
    if not candidate:
        return None
    label = _SOURCE_LABELS.get(candidate.lower())
    if label:
        return label
    if candidate and candidate.upper().startswith("FB"):
        return "FB"
    return label or candidate
