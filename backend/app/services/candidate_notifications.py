"""Candidate notification services: document requested, etc."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.services.document_catalog import get_doc_type_defaults
from backend.app.services.tenant_email import send_email_for_tenant


def get_document_display_name(doc_type: str) -> str:
    defaults = get_doc_type_defaults(doc_type)
    title = defaults.title or {}
    return (
        title.get("en")
        or title.get("pl")
        or title.get("ru")
        or next(iter(title.values()), doc_type)
    )


async def send_document_requested_email_to_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
    doc_type: str,
    status_url: Optional[str] = None,
) -> bool:
    """
    Send email to candidate when a document is requested.
    Returns True if sent successfully.
    """
    to_email = (getattr(candidate, "email", None) or "").strip()
    if not to_email:
        return False

    first_name = (getattr(candidate, "first_name", None) or "").strip() or "Candidate"
    document_name = get_document_display_name(doc_type)

    subject = f"HostFlow — Proszę przesłać dokument: {document_name}"
    body_parts = [
        f"Witaj {first_name},",
        "",
        f"Zwracamy się z prośbą o przesłanie dokumentu: {document_name}.",
    ]
    if status_url:
        body_parts.extend(
            [
                "",
                "Możesz go przesłać tutaj:",
                status_url,
                "",
                "Link jest ważny przez ograniczony czas.",
            ]
        )
    body_parts.extend(
        [
            "",
            "W razie pytań skontaktuj się z rekruterem.",
            "",
            "Pozdrawiamy,",
            "HostFlow",
        ]
    )
    body = "\n".join(body_parts)

    try:
        return await send_email_for_tenant(
            db,
            tenant_id=tenant_id,
            to=to_email,
            subject=subject,
            body=body,
        )
    except Exception:
        return False


async def send_documents_reminder_email_to_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
    requested_doc_names: list[str],
    status_url: Optional[str] = None,
) -> bool:
    """
    Send reminder email to candidate listing requested documents.
    Returns True if sent successfully.
    """
    to_email = (getattr(candidate, "email", None) or "").strip()
    if not to_email:
        return False

    first_name = (getattr(candidate, "first_name", None) or "").strip() or "Candidate"

    if requested_doc_names:
        doc_list = "\n".join(f"  • {name}" for name in requested_doc_names)
        subject = "HostFlow — Proszę przesłać dokumenty"
        body_parts = [
            f"Witaj {first_name},",
            "",
            "Zwracamy się z prośbą o przesłanie następujących dokumentów:",
            "",
            doc_list,
        ]
    else:
        subject = "HostFlow — Proszę sprawdzić status dokumentów"
        body_parts = [
            f"Witaj {first_name},",
            "",
            "Prosimy o sprawdzenie statusu Twoich dokumentów i uzupełnienie brakujących.",
        ]

    if status_url:
        body_parts.extend(
            [
                "",
                "Możesz je przesłać tutaj:",
                status_url,
                "",
                "Link jest ważny przez ograniczony czas.",
            ]
        )
    body_parts.extend(
        [
            "",
            "W razie pytań skontaktuj się z rekruterem.",
            "",
            "Pozdrawiamy,",
            "HostFlow",
        ]
    )
    body = "\n".join(body_parts)

    try:
        return await send_email_for_tenant(
            db,
            tenant_id=tenant_id,
            to=to_email,
            subject=subject,
            body=body,
        )
    except Exception:
        return False
