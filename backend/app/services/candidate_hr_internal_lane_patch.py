"""HR internal-lane: narrow candidate PATCH surface (recruitment vs HR ownership).

See ``docs/specs/architecture/candidate-field-zones-hr-internal-lane.md``.
"""

from __future__ import annotations

from typing import AbstractSet, Mapping, Any

from fastapi import HTTPException

from backend.app.constants.stages import INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES

# v1: HR may touch operational / document-pipeline fields and post-handoff funnel stages only.
HR_INTERNAL_LANE_PATCH_ALLOWLIST = frozenset({"note", "extra", "docs_progress", "stage"})


def _hr_field_not_allowed(fields: list[str], message: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "hr_field_not_allowed",
            "fields": fields,
            "message": message
            or "These candidate fields are outside the HR internal-lane patch allowlist.",
        },
    )


def assert_hr_internal_lane_patch_keys_allowed(
    patch_keys: AbstractSet[str],
    payload: Mapping[str, Any] | None = None,
) -> None:
    """Reject PATCH keys outside the HR lane allowlist (422 hr_field_not_allowed)."""
    keys = {str(k) for k in patch_keys if k is not None and str(k).strip()}
    disallowed = sorted(keys - HR_INTERNAL_LANE_PATCH_ALLOWLIST)
    if disallowed:
        raise _hr_field_not_allowed(disallowed)

    if payload and "stage" in keys:
        stage_code = str(payload.get("stage") or "").strip()
        if stage_code and stage_code not in INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES:
            raise _hr_field_not_allowed(
                ["stage"],
                "Stage is outside the HR post-handoff lane for this candidate.",
            )


__all__ = ["HR_INTERNAL_LANE_PATCH_ALLOWLIST", "assert_hr_internal_lane_patch_keys_allowed"]
