"""Which Meta forms may appear on the Intake route picker.

Sources / Connect Source still lists Graph Lead Forms on connected Pages so an
operator can claim a Source. The Intake route dropdown is routing, not discovery:
it must not replay leftover mappings or Graph catalogs from a Page this tenant
no longer owns, and it must not list every Lead Form on a shared Page.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set


def keep_intake_route_form(
    *,
    form_id: str,
    page_id: Optional[str],
    claimed_form_ids: Iterable[str],
    connected_page_ids: Iterable[str],
    graph_form_ids: Iterable[str],
) -> bool:
    """Return True when this form belongs on the tenant's Intake route picker.

    Keep only if the form is an active Meta intake source (claimed) **and** it
    still belongs to this tenant's connected Pages: either ``page_id`` is a
    stored credential Page, or Graph listed the form on a connected Page.
    """
    fid = str(form_id or "").strip()
    if not fid:
        return False
    claimed: Set[str] = {str(x).strip() for x in claimed_form_ids if str(x).strip()}
    if fid not in claimed:
        return False
    pid = str(page_id or "").strip()
    connected: Set[str] = {str(x).strip() for x in connected_page_ids if str(x).strip()}
    graph: Set[str] = {str(x).strip() for x in graph_form_ids if str(x).strip()}
    if pid and pid in connected:
        return True
    return fid in graph


def drop_empty_page_duplicates(form_id: str, page_id: Optional[str], form_ids_with_page: Iterable[str]) -> bool:
    """Hide nameless discovered rows when the same form already has a Page id."""
    fid = str(form_id or "").strip()
    if str(page_id or "").strip():
        return False
    return fid in {str(x).strip() for x in form_ids_with_page if str(x).strip()}
