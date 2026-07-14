"""Tests for RequirementEvaluation result contract (PR 2B-1)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from backend.app.requirement_rules.evaluation.fingerprint import (
    EvaluationDocumentFact,
    EvaluationFingerprintInput,
    compute_evaluation_input_fingerprint,
)
from backend.app.requirement_rules.evaluation.process_state import (
    ProcessCompletionSufficient,
    ProcessState,
    map_process_state_to_requirement_status,
)
from backend.app.requirement_rules.evaluation.result_contract import (
    EvaluationReason,
    EvaluationReasonCode,
    EvaluationReasonSeverity,
    EvaluationReasonSourceType,
    MatchRole,
    MatchedDocumentReference,
    NextActionCode,
    OverallEvaluationStatus,
    RequirementApplicability,
    RequirementEvaluationResult,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
    RequirementOwnership,
    compute_can_transition,
    compute_is_blocking,
    compute_overall_status,
    recompute_blocking_for_target_stage,
)
from backend.app.requirement_rules.evaluation.tie_break import (
    TieBreakCandidate,
    select_best_document_candidate,
)


def _passport_ref(
    *,
    document_id: str = "doc-passport-1",
    match_role: MatchRole = MatchRole.identity_evidence,
    valid_to: date | None = date(2030, 1, 1),
    review_status: str = "approved",
) -> MatchedDocumentReference:
    return MatchedDocumentReference(
        document_id=document_id,
        document_type_code="passport",
        document_type_version_id="passport.v1",
        review_status=review_status,
        valid_to=valid_to,
        match_role=match_role,
    )


def _sample_row(**overrides) -> RequirementEvaluationRow:
    base = RequirementEvaluationRow(
        requirement_code="legal_stay_confirmation",
        applicability=RequirementApplicability.applicable,
        status=RequirementEvaluationStatus.missing,
        is_blocking=True,
        required_by_stage="docs_received",
        blocks_stage="permit_ordered",
        matched_alternative=None,
        matched_documents=(),
        matched_person_facts=(),
        matched_process=None,
        excluded_alternatives=(),
        missing_fields=(),
        reasons=(
            EvaluationReason(
                code=EvaluationReasonCode.document_missing,
                message_key="requirement.legal_stay.document_missing",
                severity=EvaluationReasonSeverity.blocker,
                source_type=EvaluationReasonSourceType.policy,
                source_ref="legal_stay_confirmation",
                details={"requirement_code": "legal_stay_confirmation"},
            ),
        ),
        ownership=RequirementOwnership(
            source_responsibility="candidate",
            operational_owner="candidate",
            verification_role="recruiter",
            acquisition_mode="upload",
        ),
        next_action=NextActionCode.upload_document,
    )
    if overrides:
        return RequirementEvaluationRow(**{**base.__dict__, **overrides})
    return base


def _sample_result(**overrides) -> RequirementEvaluationResult:
    row = _sample_row()
    base = RequirementEvaluationResult(
        entity_type="candidate",
        entity_id="cand-1",
        policy_ref="recruitment.driver_ce.pl/v1",
        policy_version="1.1.0",
        target_stage="permit_ordered",
        evaluated_at=datetime(2026, 7, 13, 12, 0, 0),
        input_fingerprint="abc123",
        overall_status=OverallEvaluationStatus.blocked,
        can_transition=False,
        blocking_requirements=("legal_stay_confirmation",),
        requirements=(row,),
    )
    if overrides:
        return RequirementEvaluationResult(**{**base.__dict__, **overrides})
    return base


class TestResultContractSerialization:
    def test_round_trip_result_dto(self) -> None:
        original = _sample_result()
        restored = RequirementEvaluationResult.from_dict(original.to_dict())
        assert restored == original

    def test_unknown_status_rejected(self) -> None:
        payload = _sample_row().to_dict()
        payload["status"] = "totally_unknown"
        with pytest.raises(ValueError, match="Unknown status"):
            RequirementEvaluationRow.from_dict(payload)


class TestBlockingVsTargetStage:
    def test_same_status_different_is_blocking_by_target_stage(self) -> None:
        row = _sample_row(
            status=RequirementEvaluationStatus.missing,
            applicability=RequirementApplicability.applicable,
            blocks_stage="permit_ordered",
        )
        at_docs_received = recompute_blocking_for_target_stage(row, target_stage="docs_received")
        at_permit_ordered = recompute_blocking_for_target_stage(row, target_stage="permit_ordered")

        assert at_docs_received.status == at_permit_ordered.status == RequirementEvaluationStatus.missing
        assert at_docs_received.is_blocking is False
        assert at_permit_ordered.is_blocking is True

    def test_compute_is_blocking_matches_helper(self) -> None:
        assert compute_is_blocking(
            applicability=RequirementApplicability.applicable,
            status=RequirementEvaluationStatus.missing,
            blocks_stage="permit_ordered",
            target_stage="permit_ordered",
        )
        assert not compute_is_blocking(
            applicability=RequirementApplicability.applicable,
            status=RequirementEvaluationStatus.fulfilled,
            blocks_stage="permit_ordered",
            target_stage="permit_ordered",
        )


class TestTieBreak:
    def _candidate(self, **kwargs) -> TieBreakCandidate:
        defaults = {
            "document_id": "doc-a",
            "document_type_code": "passport",
            "document_type_version_id": "passport.v1",
            "review_status": "approved",
            "schema_valid": True,
            "valid_to": date(2030, 1, 1),
            "allows_perpetual_validity": False,
            "review_approved_at": datetime(2026, 1, 1),
            "alternative_fully_satisfied": True,
            "is_expired": False,
        }
        defaults.update(kwargs)
        return TieBreakCandidate(**defaults)

    def test_deterministic_regardless_of_input_order(self) -> None:
        a = self._candidate(document_id="doc-a", valid_to=date(2030, 6, 1))
        b = self._candidate(document_id="doc-b", valid_to=date(2031, 1, 1))
        c = self._candidate(document_id="doc-c", valid_to=date(2029, 1, 1))

        winner_1 = select_best_document_candidate([a, b, c])
        winner_2 = select_best_document_candidate([c, a, b])
        assert winner_1 == winner_2 == b

    def test_prefers_valid_over_expired(self) -> None:
        valid = self._candidate(document_id="doc-valid", is_expired=False)
        expired = self._candidate(document_id="doc-expired", is_expired=True, valid_to=date(2020, 1, 1))
        assert select_best_document_candidate([expired, valid]) == valid

    def test_prefers_approved_over_pending_review(self) -> None:
        approved = self._candidate(document_id="doc-approved", review_status="approved")
        pending = self._candidate(
            document_id="doc-pending",
            review_status="pending_review",
            review_approved_at=None,
        )
        assert select_best_document_candidate([pending, approved]) == approved

    def test_perpetual_allowed_when_schema_flag_set(self) -> None:
        perpetual = self._candidate(
            document_id="doc-perpetual",
            valid_to=None,
            allows_perpetual_validity=True,
        )
        limited = self._candidate(
            document_id="doc-limited",
            valid_to=date(2035, 1, 1),
            allows_perpetual_validity=False,
        )
        assert select_best_document_candidate([limited, perpetual]) == perpetual

    def test_null_valid_to_not_perpetual_without_schema_flag(self) -> None:
        incomplete = self._candidate(
            document_id="doc-incomplete",
            valid_to=None,
            allows_perpetual_validity=False,
        )
        complete = self._candidate(
            document_id="doc-complete",
            valid_to=date(2028, 1, 1),
            allows_perpetual_validity=False,
        )
        assert select_best_document_candidate([incomplete, complete]) == complete


class TestMatchedReferences:
    def test_same_document_two_requirements_different_roles(self) -> None:
        doc_id = "doc-licence-1"
        entitlement_ref = MatchedDocumentReference(
            document_id=doc_id,
            document_type_code="driver_license",
            document_type_version_id="driver_license.v1",
            review_status="approved",
            valid_to=date(2030, 1, 1),
            match_role=MatchRole.entitlement_evidence,
        )
        qualification_ref = MatchedDocumentReference(
            document_id=doc_id,
            document_type_code="driver_license",
            document_type_version_id="driver_license.v1",
            review_status="approved",
            valid_to=date(2030, 1, 1),
            match_role=MatchRole.qualification_evidence,
        )
        assert entitlement_ref.document_id == qualification_ref.document_id
        assert entitlement_ref.match_role != qualification_ref.match_role

    def test_legacy_alias_rejected(self) -> None:
        with pytest.raises(ValueError, match="legacy alias"):
            MatchedDocumentReference(
                document_id="doc-1",
                document_type_code="decision",
                document_type_version_id=None,
                review_status="approved",
                valid_to=None,
                match_role=MatchRole.general_evidence,
            )

    def test_unclassified_rejected(self) -> None:
        with pytest.raises(ValueError, match="forbidden evidence type"):
            MatchedDocumentReference(
                document_id="doc-1",
                document_type_code="unclassified",
                document_type_version_id=None,
                review_status="approved",
                valid_to=None,
                match_role=MatchRole.general_evidence,
            )


class TestProcessStateMapping:
    @pytest.mark.parametrize(
        ("state", "completion", "expected"),
        [
            (ProcessState.not_started, ProcessCompletionSufficient.document, RequirementEvaluationStatus.missing),
            (ProcessState.submitted, ProcessCompletionSufficient.document, RequirementEvaluationStatus.process_pending),
            (
                ProcessState.decision_issued,
                ProcessCompletionSufficient.decision,
                RequirementEvaluationStatus.fulfilled,
            ),
            (
                ProcessState.decision_issued,
                ProcessCompletionSufficient.document,
                RequirementEvaluationStatus.process_pending,
            ),
            (ProcessState.document_issued, ProcessCompletionSufficient.document, RequirementEvaluationStatus.fulfilled),
            (ProcessState.rejected, ProcessCompletionSufficient.document, RequirementEvaluationStatus.invalid),
        ],
    )
    def test_contextual_mapping(
        self,
        state: ProcessState,
        completion: ProcessCompletionSufficient,
        expected: RequirementEvaluationStatus,
    ) -> None:
        assert map_process_state_to_requirement_status(state, completion_sufficient=completion) == expected


class TestFingerprint:
    def _doc_fact(self, **kwargs) -> EvaluationDocumentFact:
        defaults = {
            "document_id": "doc-1",
            "document_type_code": "passport",
            "document_type_version_id": "passport.v1",
            "review_status": "approved",
            "valid_to": date(2030, 1, 1),
            "schema_valid": True,
            "lifecycle_status": "active",
            "document_data": {"document_number": "AB123"},
        }
        defaults.update(kwargs)
        return EvaluationDocumentFact(**defaults)

    def _input(self, **kwargs) -> EvaluationFingerprintInput:
        defaults = {
            "policy_ref": "recruitment.driver_ce.pl/v1",
            "policy_version": "1.1.0",
            "target_stage": "permit_ordered",
            "person_facts": {"citizenship": "UA"},
            "documents": (self._doc_fact(),),
            "process_states": {"work_authorization_process": "submitted"},
            "overrides": {},
        }
        defaults.update(kwargs)
        return EvaluationFingerprintInput(**defaults)

    def test_order_independent_documents(self) -> None:
        a = self._doc_fact(document_id="doc-a")
        b = self._doc_fact(document_id="doc-b", document_type_code="driver_license")
        fp1 = compute_evaluation_input_fingerprint(self._input(documents=(a, b)))
        fp2 = compute_evaluation_input_fingerprint(self._input(documents=(b, a)))
        assert fp1 == fp2

    def test_changes_on_review_validity_person_policy(self) -> None:
        base = compute_evaluation_input_fingerprint(self._input())
        review_changed = compute_evaluation_input_fingerprint(
            self._input(documents=(self._doc_fact(review_status="pending_review"),))
        )
        validity_changed = compute_evaluation_input_fingerprint(
            self._input(documents=(self._doc_fact(valid_to=date(2029, 1, 1)),))
        )
        person_changed = compute_evaluation_input_fingerprint(
            self._input(person_facts={"citizenship": "PL"})
        )
        policy_changed = compute_evaluation_input_fingerprint(
            self._input(policy_version="1.2.0")
        )
        assert len({base, review_changed, validity_changed, person_changed, policy_changed}) == 5

    def test_legacy_alias_rejected_in_fingerprint(self) -> None:
        with pytest.raises(ValueError, match="legacy alias"):
            self._doc_fact(document_type_code="voivodeship_decision")


class TestReasonsStable:
    def test_reason_codes_are_enum_not_free_text(self) -> None:
        reason = EvaluationReason(
            code=EvaluationReasonCode.citizenship_unknown,
            message_key="requirement.person.citizenship_unknown",
            severity=EvaluationReasonSeverity.blocker,
            source_type=EvaluationReasonSourceType.person,
            source_ref="platform.identity.citizenship",
        )
        payload = reason.to_dict()
        assert payload["code"] == "citizenship_unknown"
        assert payload["message_key"] == "requirement.person.citizenship_unknown"
        restored = EvaluationReason.from_dict(payload)
        assert restored.code == EvaluationReasonCode.citizenship_unknown


class TestOverallStatus:
    def test_blocked_when_any_blocking_requirement(self) -> None:
        row = _sample_row(is_blocking=True)
        assert compute_can_transition((row,)) is False
        assert compute_overall_status((row,), can_transition=False) == OverallEvaluationStatus.blocked

    def test_next_action_is_enum(self) -> None:
        row = _sample_row(next_action=NextActionCode.resolve_person_context)
        restored = RequirementEvaluationRow.from_dict(row.to_dict())
        assert restored.next_action == NextActionCode.resolve_person_context
