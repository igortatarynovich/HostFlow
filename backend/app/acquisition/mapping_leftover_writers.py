"""MA-3 leftover mapping HTTP writers — fail-closed.

Leftover Meta / Intake stores stay read-through (MA-2). HTTP PUTs that used to
write those stores return 410. This is not leftover-writer retirement as a
product claim, does not delete leftover tables, does not open MA-4, and does
not declare Mapping Operator Gate PASS.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from backend.app.constants.spa_paths import MARKETING_SOURCES

INTAKE_FORM_MAPPING_WRITES_RETIRED = "intake_form_mapping_writes_retired"
INTAKE_FORM_MAPPING_EVALUATOR_RETIRED = "intake_form_mapping_evaluator_retired"
META_MAPPING_WRITES_RETIRED = "meta_lead_mapping_writes_retired"


def mapping_workspace_path(source_id: str | None = None) -> str:
    sid = str(source_id or "").strip()
    if sid:
        return f"{MARKETING_SOURCES}/{sid}/mapping"
    return MARKETING_SOURCES


def raise_intake_form_mapping_writes_retired(*, mapping_path: str) -> NoReturn:
    raise HTTPException(
        status_code=410,
        detail={
            "code": INTAKE_FORM_MAPPING_WRITES_RETIRED,
            "message": (
                "Intake form mapping is edited in the Mapping workspace. "
                "This leftover PUT is no longer a writer."
            ),
            "mapping_path": mapping_path,
        },
    )


def raise_intake_form_mapping_evaluator_retired(*, mapping_path: str) -> NoReturn:
    raise HTTPException(
        status_code=410,
        detail={
            "code": INTAKE_FORM_MAPPING_EVALUATOR_RETIRED,
            "message": (
                "Intake mapping test-ingest is a leftover competing create path. "
                "A real submission or Test lead is the operator proof; this endpoint "
                "does not write the Mapping contract."
            ),
            "mapping_path": mapping_path,
        },
    )


def raise_meta_mapping_writes_retired(*, mapping_path: str | None = None) -> NoReturn:
    path = mapping_path or mapping_workspace_path()
    raise HTTPException(
        status_code=410,
        detail={
            "code": META_MAPPING_WRITES_RETIRED,
            "message": (
                "Meta field mapping is edited in the Mapping workspace. "
                "This leftover writer is retired."
            ),
            "mapping_path": path,
        },
    )


__all__ = [
    "INTAKE_FORM_MAPPING_EVALUATOR_RETIRED",
    "INTAKE_FORM_MAPPING_WRITES_RETIRED",
    "META_MAPPING_WRITES_RETIRED",
    "mapping_workspace_path",
    "raise_intake_form_mapping_evaluator_retired",
    "raise_intake_form_mapping_writes_retired",
    "raise_meta_mapping_writes_retired",
]
