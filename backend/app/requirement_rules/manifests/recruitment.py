"""Recruitment document pack requirement manifests (P1)."""

from __future__ import annotations

from typing import Any


def recruitment_driver_ce_document_pack() -> dict[str, Any]:
    """Deterministic driver C+E document requirements — aligned with public intake checklist."""
    return {
        "pack_code": "recruitment.driver_ce_documents",
        "entity_type": "candidate",
        "module_owner": "recruitment",
        "name": "Driver C+E documents",
        "required_documents": [
            {
                "document_type_code": "passport",
                "level": "blocking",
                "verification": "optional",
                "reason_code": "driver_ce_pack_passport",
            },
            {
                "document_type_code": "driver_license",
                "level": "blocking",
                "verification": "optional",
                "reason_code": "driver_ce_pack_driver_license",
            },
            {
                "document_type_code": "code95",
                "level": "blocking",
                "verification": "optional",
                "reason_code": "driver_ce_pack_code95",
            },
            {
                "document_type_code": "tacho_card",
                "level": "blocking",
                "verification": "optional",
                "reason_code": "driver_ce_pack_tacho_card",
            },
        ],
    }


DOCUMENT_PACK_MANIFESTS: dict[str, dict[str, Any]] = {
    "recruitment.driver_ce_documents": recruitment_driver_ce_document_pack(),
}
