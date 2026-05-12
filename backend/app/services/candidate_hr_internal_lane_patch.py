"""HR internal-lane: narrow candidate PATCH surface (recruitment vs HR ownership).

See ``docs/specs/architecture/candidate-field-zones-hr-internal-lane.md``.
"""

from __future__ import annotations

from typing import AbstractSet

from fastapi import HTTPException

# v1: HR may touch only operational / document-pipeline fields on the candidate row.
# Identity and recruitment domain stay out of HR PATCH — use dedicated flows.
HR_INTERNAL_LANE_PATCH_ALLOWLIST = frozenset({"note", "extra", "docs_progress"})


def assert_hr_internal_lane_patch_keys_allowed(patch_keys: AbstractSet[str]) -> None:
    """Reject PATCH keys outside the HR lane allowlist (422 hr_field_not_allowed)."""
    keys = {str(k) for k in patch_keys if k is not None and str(k).strip()}
    disallowed = sorted(keys - HR_INTERNAL_LANE_PATCH_ALLOWLIST)
    if disallowed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "hr_field_not_allowed",
                "fields": disallowed,
                "message": "These candidate fields are outside the HR internal-lane patch allowlist.",
            },
        )


__all__ = ["HR_INTERNAL_LANE_PATCH_ALLOWLIST", "assert_hr_internal_lane_patch_keys_allowed"]
