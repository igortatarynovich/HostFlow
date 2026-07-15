"""ADR-022 P1 — entity profile gate validation tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.intake_platform.constants import FormPurpose, SubmissionPolicyMode
from backend.app.intake_platform.entity_profile_gate import validate_form_definition_triple


def test_entity_profile_gate_rejects_invalid_purpose_for_sales_profile() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_form_definition_triple(
            purpose=FormPurpose.application.value,
            target_entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
            submission_policy={
                "mode": SubmissionPolicyMode.create.value,
            },
        )
    assert exc.value.status_code == 422
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "purpose_not_allowed"


def test_entity_profile_gate_requires_match_policy_for_match_or_create() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_form_definition_triple(
            purpose=FormPurpose.inquiry.value,
            target_entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
            submission_policy={"mode": SubmissionPolicyMode.match_or_create.value},
        )
    assert exc.value.status_code == 422
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "match_policy_required"
