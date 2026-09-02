"""Requirement Policy Authority — frozen write classification (RPM-1).

Contract id: ``requirement_policy_authority.v1``.

One operator question. One write. Nine answerers. A later RPM slice may
retire a leftover; it must not add a tenth write of the same question.

Not the operator UI (RPM-2). Not consumer cutover (RPM-3). Not Overlay.
Not Mapping. Not Hiring E2E. Not a Hub packages table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

CONTRACT_ID: Final[str] = "requirement_policy_authority.v1"

OPERATOR_QUESTION: Final[str] = (
    "for this tenant / client / vacancy / profile / country, "
    "must this candidate provide document type X?"
)

WRITE_AUTHORITY: Final[str] = "r5_merge_pack_tenant_delta"
WRITE_PRODUCER_REL: Final[str] = "backend/app/reference/document_policy_merge.py"
WRITE_MERGE_API: Final[str] = "merge_resolved_policy"

RpmRole = Literal[
    "write_authority",
    "not_this_write",
    "leftover",
    "consume",
    "consume_or_retire",
    "consume_or_explicit_contract",
    "consume_or_fold",
]

CLOSED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "write_authority",
        "not_this_write",
        "leftover",
        "consume",
        "consume_or_retire",
        "consume_or_explicit_contract",
        "consume_or_fold",
    }
)


@dataclass(frozen=True)
class Answerer:
    code: str
    role: RpmRole
    paths: tuple[str, ...]


ANSWERERS: Final[tuple[Answerer, ...]] = (
    Answerer(
        code="r5_pack_tenant_delta",
        role="write_authority",
        paths=(
            "backend/app/reference/document_policy_merge.py",
            "docs/specs/platform/document-policy-platform-pack-v1.json",
        ),
    ),
    Answerer(
        code="vacancy_overlay_screening",
        role="not_this_write",
        paths=("backend/app/entity_profile/vacancy_overlay_runtime.py",),
    ),
    Answerer(
        code="leftover_sample_ruleset",
        role="leftover",
        paths=("backend/app/modules/documents/data/sample_ruleset.json",),
    ),
    Answerer(
        code="hub_document_pack_definitions",
        role="consume_or_retire",
        paths=("backend/app/modules/documents/pack_definitions.py",),
    ),
    Answerer(
        code="db_ref_packs_transfer",
        role="consume",
        paths=(
            "backend/app/services/transfer_policy_resolver.py",
            "backend/app/models/ref_document_type.py",
        ),
    ),
    Answerer(
        code="adr018_engine_packs",
        role="consume_or_explicit_contract",
        paths=(
            "backend/app/requirement_rules/requirement_rule_graph.py",
            "backend/app/requirement_rules/data/requirement_policy.recruitment.driver_ce.pl.v1.json",
        ),
    ),
    Answerer(
        code="document_applicability_policy",
        role="consume",
        paths=("backend/app/services/document_applicability_policy.py",),
    ),
    Answerer(
        code="hiring_pipeline_gates",
        role="consume",
        paths=(
            "hostflow-frontend/src/utils/candidateStageDocPolicy.ts",
            "backend/app/services/candidate_doc_pipeline_guard.py",
        ),
    ),
    Answerer(
        code="document_policies_table",
        role="consume_or_fold",
        paths=(
            "backend/app/models/document_policy.py",
            "backend/app/api/v1/document_policies.py",
        ),
    ),
)


def write_authority_answerers() -> tuple[Answerer, ...]:
    return tuple(row for row in ANSWERERS if row.role == "write_authority")


def classified_codes() -> tuple[str, ...]:
    return tuple(row.code for row in ANSWERERS)
