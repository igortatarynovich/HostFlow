"""Hiring Eligibility Composition — one decision (HE-3).

Contract id: ``hiring_eligibility_composition.v1``.

Consumes ``hiring_acceptance.v1`` eligibility step. The ten classified
answerers are inputs. The requirement-shaped conjunct is the RPM result
(``r5_required_set``). The composer emits one operator-readable refusal.

Not HE-4 / RS-7. Not min HR. Not LI-2+. Not a Hiring-owned policy write.
Not a change to HE-2 stage authority. Not a reopening of
``candidate_evidence`` ↔ Document Link.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Mapping

from backend.app.reference.hiring_acceptance import (
    CONTRACT_ID as HIRING_ACCEPTANCE_CONTRACT_ID,
    ELIGIBILITY_ANSWERERS,
)
from backend.app.reference.requirement_policy_consumer_parity import (
    CONTRACT_ID as RPM_PARITY_CONTRACT_ID,
)

CONTRACT_ID: Final[str] = "hiring_eligibility_composition.v1"
PARENT_CONTRACT_ID: Final[str] = HIRING_ACCEPTANCE_CONTRACT_ID
REQUIREMENT_CONJUNCT_SOURCE: Final[str] = "rpm_result"
REQUIREMENT_CONJUNCT_API: Final[str] = "r5_required_set"
REQUIREMENT_CONJUNCT_PARENT: Final[str] = RPM_PARITY_CONTRACT_ID
ENGINE_SPLIT: Final[str] = "v1_and_v2_not_eligibility_authorities"

CLASSIFIED_ANSWERER_CODES: Final[tuple[str, ...]] = tuple(
    row.code for row in ELIGIBILITY_ANSWERERS
)

# These classified rows must not answer “may this candidate transfer?”.
# v1/v2 stay on their existing paths. The transfer-policy aggregator is
# replaced by this composer. Pipeline gates and legacy doc-type lists do
# not mint a required-document set.
NOT_ELIGIBILITY_AUTHORITIES: Final[frozenset[str]] = frozenset(
    {
        "transfer_policy_composer",
        "requirement_rules_v1",
        "requirement_rules_v2",
        "pipeline_gates",
        "legacy_doc_type_blockers",
    }
)

REFUSAL_ORDER: Final[tuple[str, ...]] = (
    "workforce_packs",
    "package_readiness",
    "field_requirements",
    "operational_requirements",
    "handoff_routing",
)

_DEFAULT_REFUSAL: Final[dict[str, str]] = {
    "workforce_packs": "Workforce eligibility blocks transfer",
    "package_readiness": "Recruitment dossier is not ready for transfer",
    "field_requirements": "Required candidate data is missing",
    "operational_requirements": "An operational requirement is still open",
    "handoff_routing": "No handoff destination enabled (handoff rules + tenant link)",
}

FORBIDDEN_IMPLEMENTATION: Final[tuple[str, ...]] = (
    "new_hiring_product",
    "new_hiring_policy_authority",
    "new_stage_machine",
    "he2_stage_authority_change",
    "evidence_disposition_reopen",
    "rs7_execution",
    "he4_acceptance_walk",
    "min_hr_handoff",
    "li2_lifecycle_cutover",
    "inherited_dr1_mapping_red_fix",
    "tenth_rpm_write",
)


@dataclass(frozen=True)
class EligibilityDecision:
    allowed: bool
    refusal_reason: str | None
    requirement_source: str
    requirement_unmet: tuple[str, ...]
    ignored_authorities: tuple[str, ...]


def neutral_conjuncts() -> dict[str, tuple[bool, str]]:
    return {code: (True, "") for code in CLASSIFIED_ANSWERER_CODES}


def _norm_codes(codes: frozenset[str] | set[str]) -> frozenset[str]:
    out: set[str] = set()
    for raw in codes:
        text = str(raw or "").strip().lower()
        if text:
            out.add(text)
    return frozenset(out)


def requirement_refusal(unmet: tuple[str, ...]) -> str:
    if len(unmet) == 1:
        return f"Required document is missing: {unmet[0]}"
    listed = ", ".join(unmet)
    return f"Required documents are missing: {listed}"


def compose_hiring_eligibility(
    *,
    rpm_required: frozenset[str] | set[str],
    rpm_unmet: frozenset[str] | set[str],
    conjuncts: Mapping[str, tuple[bool, str]],
) -> EligibilityDecision:
    """One eligibility decision.

    ``rpm_required`` is the RPM result. ``rpm_unmet`` may only name members
    of that set. A code outside it is a Hiring-owned policy write and is
    rejected. Classified non-authorities cannot flip the decision.
    """
    required = _norm_codes(set(rpm_required))
    unmet = _norm_codes(set(rpm_unmet))
    outside = unmet - required
    if outside:
        raise ValueError(
            "requirement conjunct refused codes outside RPM result: "
            + ", ".join(sorted(outside))
        )

    missing_codes = [code for code in CLASSIFIED_ANSWERER_CODES if code not in conjuncts]
    if missing_codes:
        raise ValueError(
            "eligibility composer missing classified answerers: "
            + ", ".join(missing_codes)
        )

    reason: str | None = None
    if unmet:
        reason = requirement_refusal(tuple(sorted(unmet)))
    else:
        for code in REFUSAL_ORDER:
            ok, message = conjuncts[code]
            if ok:
                continue
            text = str(message or "").strip() or _DEFAULT_REFUSAL[code]
            reason = text
            break

    return EligibilityDecision(
        allowed=reason is None,
        refusal_reason=reason,
        requirement_source=REQUIREMENT_CONJUNCT_SOURCE,
        requirement_unmet=tuple(sorted(unmet)),
        ignored_authorities=tuple(
            code for code in CLASSIFIED_ANSWERER_CODES if code in NOT_ELIGIBILITY_AUTHORITIES
        ),
    )
