from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal, Optional

ReminderReason = Literal["expiring_soon", "expired", "missing_expiry", "missing"]
ReminderSeverity = Literal["low", "medium", "high", "critical"]
OwnerType = Literal["candidate", "employee"]

_PACK_RECIPIENT_ROLE: dict[str, str] = {
    "driver_pack": "hr",
    "legal_stay_pack": "hr",
    "employment_pack": "hr",
    "client_pack": "hr",
}


def _severity_for_expiring(days_left: Optional[int]) -> ReminderSeverity:
    if days_left is None:
        return "medium"
    if days_left < 0:
        return "critical"
    if days_left <= 7:
        return "high"
    if days_left <= 14:
        return "medium"
    return "low"


def _why_for_reason(reason: ReminderReason) -> str:
    return {
        "expiring_soon": "document_expiring_soon",
        "expired": "document_expired",
        "missing_expiry": "expiry_date_missing",
        "missing": "required_document_missing",
    }[reason]


def project_reminder_candidates_from_packs(
    packs: list[dict[str, Any]],
    *,
    owner_type: OwnerType = "candidate",
    reference_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    """
    Projection-only reminder candidates derived from document pack gaps/warnings.

    Does not create reminders or notifications — surfaces what *would* need follow-up.
    """
    today = reference_date or date.today()
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_candidate(
        *,
        document_code: str,
        reason: ReminderReason,
        source_pack: str,
        severity: ReminderSeverity,
        due_date: Optional[date],
        days_left: Optional[int] = None,
    ) -> None:
        key = (document_code, reason, source_pack)
        if key in seen:
            return
        seen.add(key)
        out.append(
            {
                "document_code": document_code,
                "reason": reason,
                "why": _why_for_reason(reason),
                "severity": severity,
                "due_date": due_date.isoformat() if due_date else None,
                "days_left": days_left,
                "source_pack": source_pack,
                "owner_type": owner_type,
                "recipient_role": _PACK_RECIPIENT_ROLE.get(source_pack, "hr"),
            }
        )

    for pack in packs:
        if not isinstance(pack, dict):
            continue
        if pack.get("skeleton"):
            continue
        pack_code = str(pack.get("code") or "").strip()
        if not pack_code:
            continue

        for code in pack.get("missing") or []:
            add_candidate(
                document_code=str(code),
                reason="missing",
                source_pack=pack_code,
                severity="high",
                due_date=today,
            )

        for code in pack.get("expired") or []:
            add_candidate(
                document_code=str(code),
                reason="expired",
                source_pack=pack_code,
                severity="critical",
                due_date=today,
            )

        for code in pack.get("missing_expiry") or []:
            add_candidate(
                document_code=str(code),
                reason="missing_expiry",
                source_pack=pack_code,
                severity="medium",
                due_date=today + timedelta(days=7),
            )

        for row in pack.get("expiring_soon") or []:
            if not isinstance(row, dict):
                continue
            document_code = str(row.get("document_code") or "").strip()
            if not document_code:
                continue
            days_left = row.get("days_left")
            parsed_days = int(days_left) if isinstance(days_left, int) else None
            expires_raw = row.get("expires_on")
            due: Optional[date] = None
            if expires_raw:
                try:
                    due = date.fromisoformat(str(expires_raw)[:10])
                except Exception:
                    due = None
            add_candidate(
                document_code=document_code,
                reason="expiring_soon",
                source_pack=pack_code,
                severity=_severity_for_expiring(parsed_days),
                due_date=due,
                days_left=parsed_days,
            )

    out.sort(
        key=lambda row: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(str(row.get("severity")), 9),
            str(row.get("due_date") or ""),
            str(row.get("document_code") or ""),
        )
    )
    return out
