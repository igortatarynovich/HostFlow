from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.calendar_integration import CalendarConnection, CalendarItem, CalendarItemLink
from backend.app.services.communications_oauth import OAuthProviderError, refresh_oauth_access_token


class CalendarPushError(RuntimeError):
    pass


def _provider_oauth_name(provider: str) -> str:
    p = str(provider or "").strip().lower()
    if p == "google":
        return "gmail"
    if p == "microsoft":
        return "microsoft_graph"
    raise CalendarPushError(f"Unsupported provider: {provider}")


def _provider_client_credentials(provider: str) -> tuple[str, str | None]:
    p = str(provider or "").strip().lower()
    if p == "google":
        return (
            str(settings.calendar_google_client_id or "").strip(),
            str(settings.calendar_google_client_secret or "").strip() or None,
        )
    if p == "microsoft":
        return (
            str(settings.calendar_microsoft_client_id or "").strip(),
            str(settings.calendar_microsoft_client_secret or "").strip() or None,
        )
    raise CalendarPushError(f"Unsupported provider: {provider}")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    value = dt
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _item_payload(item: CalendarItem) -> dict[str, Any]:
    return dict(item.payload or {}) if isinstance(item.payload, dict) else {}


def _payload_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_attendees(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    attendees: list[dict[str, str]] = []
    for entry in raw:
        if isinstance(entry, str):
            email = entry.strip()
            if email:
                attendees.append({"email": email, "name": ""})
            continue
        if isinstance(entry, dict):
            email = str(entry.get("email") or entry.get("address") or "").strip()
            if not email:
                continue
            name = str(entry.get("name") or entry.get("displayName") or "").strip()
            response_status = str(entry.get("response_status") or entry.get("responseStatus") or entry.get("status") or "").strip()
            attendees.append({"email": email, "name": name, "response_status": response_status})
    return attendees


def _apply_provider_overrides(base: dict[str, Any], payload: dict[str, Any], provider: str) -> dict[str, Any]:
    overrides = payload.get("provider_overrides")
    if not isinstance(overrides, dict):
        return base
    provider_overrides = overrides.get(provider)
    if not isinstance(provider_overrides, dict):
        return base
    merged = dict(base)
    merged.update(provider_overrides)
    return merged


async def _ensure_access_token(db: AsyncSession, conn: CalendarConnection) -> str:
    token_meta = dict(conn.token_meta_json or {})
    access_token = str(token_meta.get("access_token") or "").strip()
    refresh_token = str(token_meta.get("refresh_token") or "").strip()
    expires_at_raw = token_meta.get("expires_at")
    expires_at = 0
    try:
        expires_at = int(float(expires_at_raw)) if expires_at_raw is not None else 0
    except Exception:
        expires_at = 0
    now_ts = int(datetime.now(timezone.utc).timestamp())
    must_refresh = (not access_token) or (expires_at > 0 and expires_at <= (now_ts + 60))
    if not must_refresh:
        return access_token
    if not refresh_token:
        raise CalendarPushError("access_token is missing and refresh_token is not available")

    client_id, client_secret = _provider_client_credentials(conn.provider)
    if not client_id:
        raise CalendarPushError(f"OAuth client_id is not configured for provider: {conn.provider}")
    try:
        refreshed = await refresh_oauth_access_token(
            provider=_provider_oauth_name(conn.provider),
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scope=None,
        )
    except OAuthProviderError as exc:
        raise CalendarPushError(str(exc)) from exc

    token_meta["access_token"] = refreshed.access_token
    if refreshed.refresh_token:
        token_meta["refresh_token"] = refreshed.refresh_token
    token_meta["token_type"] = refreshed.token_type
    token_meta["scope"] = refreshed.scope
    token_meta["expires_in"] = refreshed.expires_in
    token_meta["expires_at"] = now_ts + int(refreshed.expires_in or 3600)
    conn.token_meta_json = token_meta
    conn.last_error = None
    await db.flush()
    return str(refreshed.access_token)


def _google_body(item: CalendarItem) -> dict[str, Any]:
    payload = _item_payload(item)
    body: dict[str, Any] = {
        "summary": item.title,
        "description": item.description or "",
        "start": {"dateTime": _iso(item.starts_at), "timeZone": item.timezone or "UTC"},
        "end": {"dateTime": _iso(item.ends_at or item.starts_at), "timeZone": item.timezone or "UTC"},
    }
    location = _payload_str(payload, "location", "meeting_location")
    if location:
        body["location"] = location
    attendees = _normalize_attendees(payload.get("attendees"))
    if attendees:
        body["attendees"] = [
            {
                "email": row["email"],
                **({"displayName": row["name"]} if row.get("name") else {}),
                **({"responseStatus": row.get("response_status")} if row.get("response_status") else {}),
            }
            for row in attendees
        ]
    reminder_minutes = payload.get("reminder_minutes")
    try:
        remind = int(reminder_minutes) if reminder_minutes is not None else None
    except Exception:
        remind = None
    if remind is not None and remind >= 0:
        body["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": remind}]}
    recurrence = payload.get("recurrence")
    if isinstance(recurrence, list) and recurrence:
        body["recurrence"] = [str(x) for x in recurrence if str(x).strip()]
    elif isinstance(recurrence, str) and recurrence.strip():
        rule = recurrence.strip()
        body["recurrence"] = [rule if rule.upper().startswith("RRULE:") else f"RRULE:{rule}"]
    visibility = _payload_str(payload, "visibility")
    if visibility in {"default", "public", "private", "confidential"}:
        body["visibility"] = visibility
    transparency = _payload_str(payload, "transparency")
    if transparency in {"opaque", "transparent"}:
        body["transparency"] = transparency
    meeting_link = _payload_str(payload, "meeting_link", "meetingLink")
    if meeting_link:
        desc = str(body.get("description") or "").strip()
        if meeting_link not in desc:
            body["description"] = f"{desc}\n\n{meeting_link}".strip()
    conference_data = payload.get("google_conference_data")
    if isinstance(conference_data, dict):
        body["conferenceData"] = conference_data
    return _apply_provider_overrides(body, payload, "google")


def _microsoft_body(item: CalendarItem) -> dict[str, Any]:
    payload = _item_payload(item)
    body: dict[str, Any] = {
        "subject": item.title,
        "body": {"contentType": "text", "content": item.description or ""},
        "start": {"dateTime": (_iso(item.starts_at) or "").replace("Z", ""), "timeZone": item.timezone or "UTC"},
        "end": {"dateTime": (_iso(item.ends_at or item.starts_at) or "").replace("Z", ""), "timeZone": item.timezone or "UTC"},
    }
    location = _payload_str(payload, "location", "meeting_location")
    if location:
        body["location"] = {"displayName": location}
    attendees = _normalize_attendees(payload.get("attendees"))
    if attendees:
        body["attendees"] = [
            {
                "emailAddress": {"address": row["email"], **({"name": row["name"]} if row["name"] else {})},
                "type": "required",
            }
            for row in attendees
        ]
    reminder_minutes = payload.get("reminder_minutes")
    try:
        remind = int(reminder_minutes) if reminder_minutes is not None else None
    except Exception:
        remind = None
    if remind is not None and remind >= 0:
        body["isReminderOn"] = True
        body["reminderMinutesBeforeStart"] = remind
    recurrence = payload.get("microsoft_recurrence")
    if isinstance(recurrence, dict):
        body["recurrence"] = recurrence
    visibility = _payload_str(payload, "visibility")
    if visibility in {"normal", "personal", "private", "confidential"}:
        body["sensitivity"] = visibility
    is_online_meeting = bool(payload.get("is_online_meeting") or payload.get("online_meeting"))
    if is_online_meeting:
        body["isOnlineMeeting"] = True
        provider = _payload_str(payload, "online_meeting_provider")
        if provider:
            body["onlineMeetingProvider"] = provider
    meeting_link = _payload_str(payload, "meeting_link", "meetingLink")
    if meeting_link:
        content = str((body.get("body") or {}).get("content") or "").strip()
        if meeting_link not in content:
            body["body"] = {"contentType": "text", "content": f"{content}\n\n{meeting_link}".strip()}
    return _apply_provider_overrides(body, payload, "microsoft")


async def push_create_event(
    db: AsyncSession,
    *,
    connection: CalendarConnection,
    item: CalendarItem,
) -> dict[str, Any]:
    token = await _ensure_access_token(db, connection)
    provider = str(connection.provider or "").strip().lower()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if provider == "google":
                url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1"
                resp = await client.post(
                    url,
                    json=_google_body(item),
                    headers={"Authorization": f"Bearer {token}"},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code >= 400:
                    raise CalendarPushError(f"google create failed: {resp.status_code} {payload if payload else resp.text}")
                return {
                    "provider_event_id": str(payload.get("id") or ""),
                    "provider_calendar_id": str(payload.get("organizer", {}).get("email") or "primary"),
                    "provider_version": str(payload.get("etag") or ""),
                    "raw": payload,
                }
            if provider == "microsoft":
                url = "https://graph.microsoft.com/v1.0/me/events"
                resp = await client.post(
                    url,
                    json=_microsoft_body(item),
                    headers={"Authorization": f"Bearer {token}"},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code >= 400:
                    raise CalendarPushError(f"microsoft create failed: {resp.status_code} {payload if payload else resp.text}")
                return {
                    "provider_event_id": str(payload.get("id") or ""),
                    "provider_calendar_id": "default",
                    "provider_version": str(payload.get("@odata.etag") or ""),
                    "raw": payload,
                }
    except httpx.HTTPError as exc:
        raise CalendarPushError(f"{provider} create request failed: {exc}") from exc
    raise CalendarPushError(f"Unsupported provider: {provider}")


async def push_update_event(
    db: AsyncSession,
    *,
    connection: CalendarConnection,
    link: CalendarItemLink,
    item: CalendarItem,
) -> dict[str, Any]:
    token = await _ensure_access_token(db, connection)
    provider = str(connection.provider or "").strip().lower()
    event_id = str(link.provider_event_id or "").strip()
    if not event_id:
        raise CalendarPushError("provider_event_id is missing")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if provider == "google":
                url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
                resp = await client.patch(
                    url,
                    json=_google_body(item),
                    headers={"Authorization": f"Bearer {token}"},
                )
                payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if resp.status_code >= 400:
                    raise CalendarPushError(f"google update failed: {resp.status_code} {payload if payload else resp.text}")
                return {"provider_version": str(payload.get("etag") or ""), "raw": payload}
            if provider == "microsoft":
                url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
                resp = await client.patch(
                    url,
                    json=_microsoft_body(item),
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code >= 400:
                    payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    raise CalendarPushError(f"microsoft update failed: {resp.status_code} {payload if payload else resp.text}")
                return {"provider_version": str(resp.headers.get("etag") or ""), "raw": {}}
    except httpx.HTTPError as exc:
        raise CalendarPushError(f"{provider} update request failed: {exc}") from exc
    raise CalendarPushError(f"Unsupported provider: {provider}")


async def push_delete_event(
    db: AsyncSession,
    *,
    connection: CalendarConnection,
    link: CalendarItemLink,
) -> None:
    token = await _ensure_access_token(db, connection)
    provider = str(connection.provider or "").strip().lower()
    event_id = str(link.provider_event_id or "").strip()
    if not event_id:
        raise CalendarPushError("provider_event_id is missing")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if provider == "google":
                url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
                resp = await client.delete(url, headers={"Authorization": f"Bearer {token}"})
                if resp.status_code >= 400 and resp.status_code != 404:
                    payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    raise CalendarPushError(f"google delete failed: {resp.status_code} {payload if payload else resp.text}")
                return
            if provider == "microsoft":
                url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
                resp = await client.delete(url, headers={"Authorization": f"Bearer {token}"})
                if resp.status_code >= 400 and resp.status_code != 404:
                    payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    raise CalendarPushError(f"microsoft delete failed: {resp.status_code} {payload if payload else resp.text}")
                return
    except httpx.HTTPError as exc:
        raise CalendarPushError(f"{provider} delete request failed: {exc}") from exc
    raise CalendarPushError(f"Unsupported provider: {provider}")
