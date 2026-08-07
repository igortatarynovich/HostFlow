"""Canonical outgoing message signature from the logged-in user profile.

HostFlow rule: communication templates must not embed a personal signature.
The engine appends the signature after the rendered body (plain + HTML).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.user import User

CLOSING_BY_LOCALE = {
    "pl": "Z poważaniem,",
    "en": "Kind regards,",
    "ru": "С уважением,",
}

DEFAULT_SIGNATURE_TOGGLES = {
    "show_phone": True,
    "show_email": True,
    "show_website": True,
}

# HostFlow brand teal (matches logo_hf.svg).
BRAND_COLOR = "#2e7070"
TEXT_COLOR = "#1f2937"
MUTED_COLOR = "#4b5563"
# Logo SVG is ~560×104; constrain to roughly the signature text column width.
LOGO_WIDTH_PX = 180

_URL_RE = re.compile(r"(https?://[^\s<]+)")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_signature_block(raw: Any) -> dict[str, Any]:
    """Normalize ``extra.profile.signature`` for API read/write."""
    data = _record(raw)
    toggles = {**DEFAULT_SIGNATURE_TOGGLES}
    for key in ("show_phone", "show_email", "show_website"):
        if key in data:
            toggles[key] = bool(data.get(key))
    return {
        "first_name": _trim(data.get("first_name")) or None,
        "last_name": _trim(data.get("last_name")) or None,
        "position": _trim(data.get("position")) or None,
        "phone": _trim(data.get("phone")) or None,
        "email": _trim(data.get("email")) or None,
        "company": _trim(data.get("company")) or None,
        "website": _trim(data.get("website")) or None,
        "logo_url": _trim(data.get("logo_url")) or None,
        **toggles,
    }


def merge_signature_block(existing: Any, patch: Any) -> dict[str, Any]:
    current = normalize_signature_block(existing)
    if not isinstance(patch, dict):
        return current
    for key in (
        "first_name",
        "last_name",
        "position",
        "phone",
        "email",
        "company",
        "website",
        "logo_url",
    ):
        if key in patch:
            current[key] = _trim(patch.get(key)) or None
    for key in ("show_phone", "show_email", "show_website"):
        if key in patch:
            current[key] = bool(patch.get(key))
    return normalize_signature_block(current)


def _profile_of(user: User) -> dict[str, Any]:
    return _record(_record(getattr(user, "extra", None)).get("profile"))


def _display_name(user: User, signature: dict[str, Any], profile: dict[str, Any]) -> str:
    first = _trim(signature.get("first_name")) or _trim(profile.get("first_name"))
    last = _trim(signature.get("last_name")) or _trim(profile.get("last_name"))
    combined = " ".join(part for part in (first, last) if part).strip()
    if combined:
        return combined
    # Legacy latin / signature name overrides before Cyrillic full_name.
    prefs = _record(getattr(user, "preferences", None))
    extra = _record(getattr(user, "extra", None))
    for candidate in (
        prefs.get("email_signature_name"),
        prefs.get("display_name_latin"),
        extra.get("email_signature_name"),
        extra.get("display_name_latin"),
        profile.get("email_signature_name"),
        profile.get("display_name_latin"),
    ):
        if _trim(candidate):
            return _trim(candidate)
    return _trim(user.full_name) or _trim(user.email)


def _normalize_website(value: str) -> str:
    raw = _trim(value)
    if not raw:
        return ""
    if re_match_scheme(raw):
        return raw
    return f"https://{raw}"


def absolute_public_url(value: str | None) -> str:
    """Turn app-relative asset paths into absolute URLs for outbound email."""
    raw = _trim(value)
    if not raw:
        return ""
    if re_match_scheme(raw):
        return raw
    base = _trim(getattr(settings, "frontend_url", None) or "") or "https://hostflow.cc"
    base = base.rstrip("/")
    if raw.startswith("/"):
        return f"{base}{raw}"
    return f"{base}/{raw}"


def default_brand_logo_url() -> str:
    return absolute_public_url("/logo_hf.svg")


def _resolve_logo_url(
    *,
    signature: dict[str, Any],
    profile: dict[str, Any],
    own_extra: dict[str, Any] | None = None,
) -> str:
    for candidate in (
        signature.get("logo_url"),
        _record(own_extra).get("logo_url"),
        _record(own_extra).get("logo_path"),
    ):
        resolved = absolute_public_url(_trim(candidate))
        if resolved:
            return resolved
    # Canonical HostFlow emails always end with a brand mark when none is configured.
    return default_brand_logo_url()


def _website_display(value: str) -> str:
    raw = _trim(value)
    if not raw:
        return ""
    parsed = urlparse(raw if re_match_scheme(raw) else f"https://{raw}")
    host = (parsed.netloc or parsed.path or raw).strip().rstrip("/")
    if host.lower().startswith("www."):
        host = host[4:]
    return host or raw


@dataclass(frozen=True)
class OutgoingSignature:
    closing: str
    full_name: str
    position: str
    company: str
    phone: str
    email: str
    website: str
    website_display: str
    logo_url: str
    show_phone: bool
    show_email: bool
    show_website: bool

    def plain_text(self) -> str:
        lines: list[str] = [self.closing, "", self.full_name]
        if self.position:
            lines.append(self.position)
        if self.company:
            lines.append("")
            lines.append(self.company)
        contact_lines: list[str] = []
        if self.show_phone and self.phone:
            contact_lines.append(f"☎ {self.phone}")
        if self.show_email and self.email:
            contact_lines.append(f"✉ {self.email}")
        if self.show_website and self.website_display:
            contact_lines.append(f"↗ {self.website_display}")
        if contact_lines:
            lines.append("")
            lines.extend(contact_lines)
        # Logo is HTML-only (<img>); never dump the URL into plain text.
        return "\n".join(lines).strip()

    def html(self) -> str:
        """Styled HTML signature for multipart emails (logo constrained to text width)."""
        name = html.escape(self.full_name)
        closing = html.escape(self.closing)
        position = html.escape(self.position) if self.position else ""
        company = html.escape(self.company) if self.company else ""

        blocks: list[str] = [
            f'<div style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:14px;line-height:1.45;color:{TEXT_COLOR};">',
            f'<p style="margin:0 0 12px 0;">{closing}</p>',
            f'<p style="margin:0;"><strong style="color:{BRAND_COLOR};font-size:15px;">{name}</strong></p>',
        ]
        if position:
            blocks.append(
                f'<p style="margin:2px 0 0 0;color:{MUTED_COLOR};">{position}</p>'
            )
        if company:
            blocks.append(
                f'<p style="margin:10px 0 0 0;"><strong style="color:{BRAND_COLOR};">{company}</strong></p>'
            )

        contact_rows: list[str] = []
        if self.show_phone and self.phone:
            phone_href = "".join(ch for ch in self.phone if ch.isdigit() or ch == "+")
            contact_rows.append(
                _contact_row(
                    "☎",
                    f'<a href="tel:{html.escape(phone_href)}" style="color:{TEXT_COLOR};text-decoration:none;">'
                    f"{html.escape(self.phone)}</a>",
                )
            )
        if self.show_email and self.email:
            contact_rows.append(
                _contact_row(
                    "✉",
                    f'<a href="mailto:{html.escape(self.email)}" style="color:{TEXT_COLOR};text-decoration:none;">'
                    f"{html.escape(self.email)}</a>",
                )
            )
        if self.show_website and self.website_display:
            href = html.escape(self.website or f"https://{self.website_display}")
            contact_rows.append(
                _contact_row(
                    "↗",
                    f'<a href="{href}" style="color:{BRAND_COLOR};text-decoration:none;">'
                    f"{html.escape(self.website_display)}</a>",
                )
            )
        if contact_rows:
            blocks.append(
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
                'style="margin:10px 0 0 0;border-collapse:collapse;">'
                + "".join(contact_rows)
                + "</table>"
            )

        if self.logo_url:
            logo = html.escape(self.logo_url)
            blocks.append(
                f'<p style="margin:14px 0 0 0;">'
                f'<img src="{logo}" width="{LOGO_WIDTH_PX}" alt="{company or "HostFlow"}" '
                f'style="width:{LOGO_WIDTH_PX}px;max-width:{LOGO_WIDTH_PX}px;height:auto;'
                f'display:block;border:0;outline:none;text-decoration:none;" />'
                f"</p>"
            )
        blocks.append("</div>")
        return "".join(blocks)


def _contact_row(icon: str, value_html: str) -> str:
    return (
        "<tr>"
        f'<td style="padding:2px 8px 2px 0;vertical-align:middle;width:18px;'
        f'color:{BRAND_COLOR};font-size:13px;line-height:18px;font-family:Arial,Helvetica,sans-serif;">'
        f"{html.escape(icon)}</td>"
        f'<td style="padding:2px 0;vertical-align:middle;font-size:13px;line-height:18px;'
        f'font-family:Arial,Helvetica,sans-serif;">{value_html}</td>'
        "</tr>"
    )


def re_match_scheme(value: str) -> bool:
    return bool(value.lower().startswith(("http://", "https://")))


def plain_body_to_html(body: str) -> str:
    """Escape plain template body and turn newlines / URLs into simple HTML."""
    text = (body or "").rstrip()
    if not text:
        return ""
    escaped = html.escape(text)

    def _link(match: re.Match[str]) -> str:
        url = match.group(1)
        return (
            f'<a href="{url}" style="color:{BRAND_COLOR};text-decoration:underline;">{url}</a>'
        )

    linked = _URL_RE.sub(_link, escaped)
    return linked.replace("\n", "<br>\n")


def wrap_email_html(body_html: str) -> str:
    return (
        '<!DOCTYPE html><html><body style="margin:0;padding:0;">'
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
        f'line-height:1.5;color:{TEXT_COLOR};">'
        f"{body_html}"
        "</div></body></html>"
    )


def closing_for_locale(locale: str | None) -> str:
    code = _trim(locale).lower()[:2] or "pl"
    return CLOSING_BY_LOCALE.get(code) or CLOSING_BY_LOCALE["pl"]


async def resolve_outgoing_signature(
    db: AsyncSession,
    *,
    user_id: str | None,
    tenant_id: str | None = None,
    own_company_id: str | None = None,
    locale: str | None = None,
) -> Optional[OutgoingSignature]:
    """Build signature strictly from the user profile signature block.

    Soft fallbacks stay inside the same profile (name / position / phone / email).
    Company, website and logo are never taken from own company, tenant or SMTP.
    """
    del tenant_id, own_company_id  # reserved for callers; signature is profile-only
    uid = _trim(user_id)
    if not uid:
        return None
    user = await db.scalar(select(User).where(User.id == uid).limit(1))
    if user is None:
        return None

    profile = _profile_of(user)
    signature = normalize_signature_block(profile.get("signature"))

    company = _trim(signature.get("company"))
    website = _trim(signature.get("website"))
    phone = _trim(signature.get("phone")) or _trim(profile.get("phone"))
    email = _trim(signature.get("email")) or _trim(user.email)
    position = _trim(signature.get("position")) or _trim(profile.get("position"))
    logo_url = _resolve_logo_url(signature=signature, profile=profile, own_extra=None)
    website_norm = _normalize_website(website) if website else ""

    return OutgoingSignature(
        closing=closing_for_locale(locale),
        full_name=_display_name(user, signature, profile),
        position=position,
        company=company,
        phone=phone,
        email=email,
        website=website_norm,
        website_display=_website_display(website_norm or website),
        logo_url=logo_url,
        show_phone=bool(signature.get("show_phone", True)),
        show_email=bool(signature.get("show_email", True)),
        show_website=bool(signature.get("show_website", True)),
    )


def append_outgoing_signature(body: str, signature_plain: str | None) -> str:
    """Append signature after template body. Idempotent if body already ends with it."""
    body_text = (body or "").rstrip()
    sig = (signature_plain or "").strip()
    if not sig:
        return body_text
    if body_text.endswith(sig):
        return body_text
    if not body_text:
        return sig
    return f"{body_text}\n\n{sig}"


def append_outgoing_signature_html(body_html: str, signature_html: str | None) -> str:
    """Append HTML signature after HTML body. Idempotent when signature already present."""
    body = (body_html or "").rstrip()
    sig = (signature_html or "").strip()
    if not sig:
        return wrap_email_html(body) if body else ""
    if sig in body:
        return wrap_email_html(body) if "<html" not in body.lower() else body
    combined = f"{body}<br><br>{sig}" if body else sig
    return wrap_email_html(combined)


__all__ = [
    "BRAND_COLOR",
    "LOGO_WIDTH_PX",
    "OutgoingSignature",
    "absolute_public_url",
    "append_outgoing_signature",
    "append_outgoing_signature_html",
    "closing_for_locale",
    "default_brand_logo_url",
    "merge_signature_block",
    "normalize_signature_block",
    "plain_body_to_html",
    "resolve_outgoing_signature",
    "wrap_email_html",
]
