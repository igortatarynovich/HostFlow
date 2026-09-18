"""Read-only normalized evidence views for employment_start_allowed.v1.

Projections over existing Hub/document-like mappings. No new evidence tables.
Documents remain the write authority; this module only normalizes for evaluate.
"""

from __future__ import annotations

from typing import Any, Mapping


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _meta(doc: Mapping[str, Any] | None) -> dict[str, Any]:
    d = _record(doc)
    meta = d.get("meta") or d.get("meta_json") or {}
    return _record(meta)


def project_contract_evidence_view(document: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Documents-owned mapping into written_instrument_confirmed view.

    Does not treat draft_preview or ESO-4 basis ack as proof.
    """
    if not document:
        return None
    d = _record(document)
    status = _norm(d.get("status"))
    if status in {"rejected", "deleted", "soft_deleted", "draft_preview"}:
        return {
            "written_instrument_confirmed": False,
            "instrument_kind": None,
            "evidence_document_id": d.get("id"),
            "rejected": True,
        }
    # Explicit generation kind / source ban
    if _norm(d.get("generation_kind")) == "contract_draft_preview":
        return {
            "written_instrument_confirmed": False,
            "instrument_kind": None,
            "evidence_document_id": d.get("id"),
            "draft_only": True,
        }

    meta = _meta(d)
    doc_type = _norm(d.get("type") or d.get("document_type") or d.get("code") or meta.get("type"))

    confirmed = meta.get("written_instrument_confirmed")
    if confirmed is True:
        kind = _norm(meta.get("instrument_kind")) or (
            "written_confirmation_of_terms"
            if meta.get("confirmation_of_terms") is True
            else "signed_employment_contract"
        )
        return {
            "written_instrument_confirmed": True,
            "instrument_kind": kind,
            "employer_ref": meta.get("employer_name") or meta.get("employer_id") or d.get("employer_id"),
            "start_at": meta.get("start_at"),
            "evidence_document_id": d.get("id"),
        }

    if meta.get("confirmation_of_terms") is True and (
        meta.get("confirmed_at") or meta.get("signed_at")
    ):
        return {
            "written_instrument_confirmed": True,
            "instrument_kind": "written_confirmation_of_terms",
            "employer_ref": meta.get("employer_name") or meta.get("employer_id"),
            "start_at": meta.get("start_at"),
            "evidence_document_id": d.get("id"),
        }

    if doc_type in {"employment_contract", "umowa_o_prace"} and meta.get("signed_at"):
        return {
            "written_instrument_confirmed": True,
            "instrument_kind": "signed_employment_contract",
            "employer_ref": meta.get("employer_name") or meta.get("employer_id"),
            "start_at": meta.get("start_at"),
            "evidence_document_id": d.get("id"),
        }

    # Document exists alone is not confirmation
    return {
        "written_instrument_confirmed": False,
        "instrument_kind": None,
        "employer_ref": meta.get("employer_name"),
        "start_at": meta.get("start_at"),
        "evidence_document_id": d.get("id"),
    }


def project_medical_evidence_view(
    document: Mapping[str, Any] | None,
    *,
    verified_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not document:
        return None
    d = _record(document)
    meta = _meta(d)
    verified = _record(verified_fields)
    valid_until = (
        meta.get("expires_at")
        or meta.get("medical_valid_until")
        or verified.get("exam_valid_until")
        or verified.get("verified_value")
    )
    return {
        "medical_valid_until": valid_until,
        "fit_for_work": meta.get("fit_for_work"),
        "applies_to_post": meta.get("applies_to_post") or meta.get("post_key"),
        "working_conditions_ref": meta.get("working_conditions_ref"),
        "conditions_match": meta.get("conditions_match"),
        "evidence_document_id": d.get("id"),
    }


def project_bhp_evidence_view(document: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None
    d = _record(document)
    meta = _meta(d)
    return {
        "training_date": meta.get("training_date"),
        "training_kind": meta.get("training_kind") or meta.get("bhp_stage"),
        "employer_id": meta.get("employer_id") or d.get("employer_id"),
        "applies_to_post": meta.get("applies_to_post") or meta.get("post_key"),
        "post_key": meta.get("post_key") or meta.get("applies_to_post"),
        "expires_at": meta.get("expires_at"),
        "evidence_document_id": d.get("id"),
    }


__all__ = [
    "project_contract_evidence_view",
    "project_medical_evidence_view",
    "project_bhp_evidence_view",
]
