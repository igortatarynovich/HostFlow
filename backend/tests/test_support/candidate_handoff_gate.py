"""Seed minimal candidate documents so PATCH stage=ready_for_handoff passes the docs gate."""

from __future__ import annotations

from typing import Dict, Sequence

from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS

# Aligns with default checklist used by hiring / handoff gate (see test_documents._ensure_required_documents).
DEFAULT_HANDOFF_GATE_DOC_TYPES: tuple[str, ...] = (
    "driver_license",
    "code95",
    "tacho_card",
    "national_id",
    "passport",
)


async def seed_documents_for_ready_for_handoff(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    candidate_id: str,
    *,
    doc_types: Sequence[str] | None = None,
) -> None:
    types = tuple(doc_types) if doc_types is not None else DEFAULT_HANDOFF_GATE_DOC_TYPES
    detail = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
    )
    assert detail.status_code == 200, detail.text
    cand = detail.json()
    contacts = cand.get("contacts") if isinstance(cand.get("contacts"), dict) else {}
    personal = cand.get("personal_data") if isinstance(cand.get("personal_data"), dict) else {}

    patch_payload: dict[str, object] = {}
    if not str(cand.get("phone") or contacts.get("phone") or "").strip():
        patch_payload["phone"] = "+48123456789"
    if not str(cand.get("email") or contacts.get("email") or "").strip():
        patch_payload["email"] = "handoff-gate@example.com"
    address_raw = personal.get("address") or cand.get("address")
    has_address = False
    if isinstance(address_raw, str):
        has_address = bool(address_raw.strip())
    elif isinstance(address_raw, dict):
        has_address = bool(str(address_raw.get("line1") or address_raw.get("address") or "").strip())
    if not has_address:
        extra = cand.get("extra") if isinstance(cand.get("extra"), dict) else {}
        patch_payload["extra"] = {**extra, "address": "Handoff Gate Street 1, Warsaw"}

    if patch_payload:
        contact_patch = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=manager_headers,
            json=patch_payload,
        )
        assert contact_patch.status_code == 200, contact_patch.text
    for doc_type in types:
        payload = {
            "candidate_id": candidate_id,
            "type": doc_type,
            "status": "approved",
            "extra": {"title": doc_type},
        }
        resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
        assert resp.status_code == 200, resp.text

    confirm = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"extra": {"recruitment_dossier_confirmed_blocks": list(RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS)}},
    )
    assert confirm.status_code == 200, confirm.text
