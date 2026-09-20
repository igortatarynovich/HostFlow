"""FP-4 — operator projection over existing publish / serve authority.

Does not write a publication. Does not decide serve. Maps ledger + lifecycle
fields already owned by Adapter ``commit_publish`` / ``deactivate`` / resolve
onto the frozen operator states. Public URL is the FP-3 serve path.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from backend.app.forms_platform.constants import LIFECYCLE_ARCHIVED
from backend.app.reference.forms_publish_contract import OPERATOR_STATES

PUBLIC_FORM_PATH = "/public/intake"

NEVER_PUBLISHED = "never_published"
LIVE = "live"
INACTIVE = "inactive"

assert NEVER_PUBLISHED in OPERATOR_STATES
assert LIVE in OPERATOR_STATES
assert INACTIVE in OPERATOR_STATES


def has_publication_ledger(lead_form: Any) -> bool:
    """Ledger evidence already owned by FP-2: version pointer + frozen snapshot."""
    raw_version = int(getattr(lead_form, "published_version", 0) or 0)
    snap = getattr(lead_form, "published_snapshot_v1", None)
    return raw_version > 0 and isinstance(snap, dict) and bool(snap)


def operator_state_from_lead_form(lead_form: Any) -> str:
    """Current operator-visible publication state. Not a second live calculator."""
    if not has_publication_ledger(lead_form):
        return NEVER_PUBLISHED
    lifecycle = str(getattr(lead_form, "lifecycle_status", "") or "")
    if lifecycle == LIFECYCLE_ARCHIVED or not bool(getattr(lead_form, "is_active", False)):
        return INACTIVE
    return LIVE


def public_form_url_from_publication(
    *,
    public_slug: str | None,
    operator_state: str,
) -> str | None:
    """FP-3 serve path. Absent unless the publication is live."""
    if operator_state != LIVE:
        return None
    slug = str(public_slug or "").strip()
    if not slug:
        return None
    return f"{PUBLIC_FORM_PATH}?lead_form_slug={quote(slug, safe='-_.')}"
