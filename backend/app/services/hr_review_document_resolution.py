"""Resolve HR approval document rows from candidate document hub (SoT for files)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver

# document_key (HR verification card) -> candidate Document.doc_type aliases
DOC_KEY_CANDIDATE_TYPES: dict[str, frozenset[str]] = {
    "Passport / ID": frozenset(
        {
            "passport",
            "passport_scan",
            "national_id",
            "id_card",
            "identity_card",
            "identity_document",
        }
    ),
    "Legal stay": frozenset(
        {
            "legal_stay",
            "residence_permit",
            "residence_card",
            "karta_pobytu",
            "visa",
            "visa_d",
        }
    ),
    "Work permit": frozenset({"work_permit", "work_permit_application", "work_permit_card"}),
    "Red paper": frozenset({"red_paper", "red_paper_certificate"}),
    "Medical": frozenset({"medical", "medical_certificate", "medical_exam"}),
    "Psychological": frozenset({"psychological", "psychological_certificate", "psychotest", "psychological_exam"}),
    "Driver license": frozenset({"driver_license", "driver_license_code95", "eu_driver_license"}),
    "Code95": frozenset({"code95", "qualification_code95", "code_95", "driver_license_code95"}),
    "Tacho card": frozenset({"tacho_card", "tachograph_card", "tachograph"}),
    "Work experience": frozenset(
        {
            "employment_record",
            "swiadectwo_pracy",
            "work_certificate",
            "employment_history",
        }
    ),
}

_UPLOADED_STATUSES = frozenset(
    {
        "uploaded",
        "approved",
        "verified",
        "pending",
        "in_review",
        "submitted",
    }
)


def _norm_doc_type(raw: str) -> str:
    return str(raw or "").strip().lower().replace("-", "_")


def _doc_has_files(doc: Document) -> bool:
    files = getattr(doc, "files", None)
    if isinstance(files, list):
        return len(files) > 0
    if isinstance(files, dict):
        return bool(files)
    return False


def _doc_score(doc: Document) -> int:
    st = _norm_doc_type(str(getattr(doc, "status", "") or ""))
    score = 0
    if st in ("approved", "verified"):
        score += 8
    elif st in _UPLOADED_STATUSES:
        score += 5
    if _doc_has_files(doc):
        score += 6
    exp = getattr(doc, "expire_date", None) or getattr(doc, "expires_at", None)
    if exp:
        score += 1
    return score


async def load_candidate_documents_index(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> dict[str, list[Document]]:
    cid = str(candidate_id or "").strip()
    if not cid:
        return {}
    rows = (
        await db.execute(
            select(Document)
            .where(
                Document.tenant_id == str(tenant_id).strip(),
                Document.candidate_id == cid,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.updated_at.desc())
        )
    ).scalars().all()
    by_type: dict[str, list[Document]] = {}
    for doc in rows:
        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(db, doc)
        key = _norm_doc_type(str(resolved.canonical_code or ""))
        if not key:
            continue
        by_type.setdefault(key, []).append(doc)
    return by_type


def pick_candidate_document_for_key(
    by_type: dict[str, list[Document]],
    document_key: str,
) -> Optional[Document]:
    aliases = DOC_KEY_CANDIDATE_TYPES.get(document_key) or frozenset()
    candidates: list[Document] = []
    for alias in aliases:
        candidates.extend(by_type.get(_norm_doc_type(alias), []))
    if not candidates:
        return None
    candidates.sort(key=_doc_score, reverse=True)
    return candidates[0]


async def merge_candidate_documents_into_approval_rows(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: Optional[str],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fill document_id / status / expires from recruitment documents when HR context row is empty."""
    cid = str(candidate_id or "").strip()
    if not cid:
        return rows
    by_type = await load_candidate_documents_index(db, tenant_id, cid)
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        if r.get("document_id"):
            out.append(r)
            continue
        key = str(r.get("document_key") or "").strip()
        doc = pick_candidate_document_for_key(by_type, key)
        if not doc:
            out.append(r)
            continue
        r["document_id"] = str(doc.id)
        r["document_version"] = int(getattr(doc, "version", 1) or 1)
        st = _norm_doc_type(str(getattr(doc, "status", "") or ""))
        if st in ("approved", "verified"):
            r["status"] = "verified"
            r["verified"] = True
        elif _doc_has_files(doc) or st in _UPLOADED_STATUSES:
            r["status"] = "uploaded"
        exp = getattr(doc, "expire_date", None) or getattr(doc, "expires_at", None)
        if exp:
            r["expires_at"] = exp.isoformat() if hasattr(exp, "isoformat") else str(exp)
        r["context_type"] = r.get("context_type") or str(doc.doc_type or "")
        out.append(r)
    return out
