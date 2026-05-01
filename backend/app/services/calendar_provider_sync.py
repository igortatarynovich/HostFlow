from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


class CalendarProviderSyncError(RuntimeError):
    pass


@dataclass
class CalendarProviderSyncResult:
    events: list[dict[str, Any]]
    next_cursor: Optional[str] = None
    cursor_meta: dict[str, Any] | None = None


def _auth_headers(access_token: str) -> dict[str, str]:
    token = str(access_token or "").strip()
    if not token:
        raise CalendarProviderSyncError("access_token is required")
    return {"Authorization": f"Bearer {token}"}


async def fetch_google_events(
    *,
    access_token: str,
    calendar_ref: str | None,
    cursor: str | None,
    cursor_meta: dict[str, Any] | None = None,
) -> CalendarProviderSyncResult:
    calendar_id = str(calendar_ref or "primary").strip() or "primary"
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    max_pages = int((cursor_meta or {}).get("max_pages") or 30)
    if max_pages < 1:
        max_pages = 1
    params: Dict[str, Any] = {"singleEvents": "true", "maxResults": "250"}
    if cursor:
        params["syncToken"] = cursor
    else:
        updated_min = (cursor_meta or {}).get("updatedMin")
        if isinstance(updated_min, str) and updated_min.strip():
            params["updatedMin"] = updated_min
    events: list[dict[str, Any]] = []
    next_page: Optional[str] = None
    next_sync: Optional[str] = None
    retried_without_sync_token = False
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(max_pages):
                page_params = dict(params)
                if next_page:
                    page_params["pageToken"] = next_page
                resp = await client.get(url, params=page_params, headers=_auth_headers(access_token))
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code >= 400:
                    # Google incremental cursor may expire. In this case provider returns
                    # 410/fullSyncRequired and requires a fresh full sync without syncToken.
                    if (
                        resp.status_code == 410
                        and "syncToken" in page_params
                        and not retried_without_sync_token
                    ):
                        params.pop("syncToken", None)
                        next_page = None
                        retried_without_sync_token = True
                        continue
                    raise CalendarProviderSyncError(
                        f"Google Calendar sync failed: {resp.status_code} {data if isinstance(data, dict) else resp.text}"
                    )
                items = data.get("items") if isinstance(data, dict) else []
                events.extend([x for x in (items or []) if isinstance(x, dict)])
                next_page = data.get("nextPageToken") if isinstance(data, dict) else None
                next_sync = data.get("nextSyncToken") if isinstance(data, dict) else None
                if not next_page:
                    break
    except httpx.HTTPError as exc:
        raise CalendarProviderSyncError(f"Google Calendar request failed: {exc}") from exc
    return CalendarProviderSyncResult(
        events=events,
        next_cursor=next_sync,
        cursor_meta={
            "nextPageToken": next_page,
            "calendar_ref": calendar_id,
            "max_pages": max_pages,
        },
    )


async def fetch_microsoft_events(
    *,
    access_token: str,
    calendar_ref: str | None,
    cursor: str | None,
    cursor_meta: dict[str, Any] | None = None,
) -> CalendarProviderSyncResult:
    # For v1 increment use /me/events/delta with stored deltaLink cursor.
    base = "https://graph.microsoft.com/v1.0"
    max_pages = int((cursor_meta or {}).get("max_pages") or 30)
    if max_pages < 1:
        max_pages = 1
    start_url = cursor or f"{base}/me/events/delta"
    start_params = None if cursor else {"$top": "100"}
    if start_params is not None and calendar_ref:
        start_params["calendarId"] = calendar_ref
    events: list[dict[str, Any]] = []
    next_cursor = None
    next_url: Optional[str] = start_url
    params: Optional[dict[str, str]] = start_params
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(max_pages):
                if not next_url:
                    break
                resp = await client.get(next_url, params=params, headers=_auth_headers(access_token))
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code >= 400:
                    raise CalendarProviderSyncError(
                        f"Microsoft Graph sync failed: {resp.status_code} {data if isinstance(data, dict) else resp.text}"
                    )
                value = data.get("value") if isinstance(data, dict) else []
                events.extend([x for x in (value or []) if isinstance(x, dict)])
                delta_link = data.get("@odata.deltaLink") if isinstance(data, dict) else None
                next_link = data.get("@odata.nextLink") if isinstance(data, dict) else None
                if delta_link:
                    next_cursor = delta_link
                    break
                next_cursor = next_link
                next_url = next_link
                params = None
                if not next_link:
                    break
    except httpx.HTTPError as exc:
        raise CalendarProviderSyncError(f"Microsoft Graph request failed: {exc}") from exc
    return CalendarProviderSyncResult(
        events=events,
        next_cursor=next_cursor,
        cursor_meta={"calendar_ref": calendar_ref or "default", "max_pages": max_pages},
    )
