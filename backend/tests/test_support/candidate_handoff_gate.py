"""Seed minimal candidate documents so PATCH stage=ready_for_handoff passes the docs gate."""

from __future__ import annotations

from typing import Dict, Sequence

from httpx import AsyncClient

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
    for doc_type in types:
        payload = {
            "candidate_id": candidate_id,
            "type": doc_type,
            "status": "approved",
            "extra": {"title": doc_type},
        }
        resp = await client.post("/api/v1/documents/", headers=manager_headers, json=payload)
        assert resp.status_code == 200, resp.text
