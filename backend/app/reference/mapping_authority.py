"""Mapping Authority — frozen write classification (MA-1).

Contract id: ``mapping_authority.v1``.

One operator question. One write. Twelve answerers. A later MA slice may
retire a leftover; it must not add a thirteenth write of the same question.

Not the resolver (MA-2). Not the operator editor (MA-3). Not consumer
cutover (MA-4). Not a fourth store. Not Zapier. Not Sales convert. Not
OCR. Not CL6. Not Hiring E2E. Not External Intake publish.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

CONTRACT_ID: Final[str] = "mapping_authority.v1"

OPERATOR_QUESTION: Final[str] = (
    "for this source (Meta form, public form, import file, flight), "
    "which incoming answer writes which canonical entity field — "
    "including which source option writes which canonical option when "
    "the destination is choice-typed — and what happens when the binding "
    "is unset or the contract cannot compute a fact?"
)

WRITE_AUTHORITY: Final[str] = "intake_source_profile_mapping_rules"
WRITE_PRODUCER_REL: Final[str] = "backend/app/entity_profile/mapping_write.py"
WRITE_API: Final[str] = "validate_intake_mapping_rules_write"
DESTINATION_VOCABULARY: Final[str] = "qualified_code"

BINDING_STATES: Final[tuple[str, ...]] = ("mapped", "ignored", "unmapped")
HEALTH_STATES: Final[tuple[str, ...]] = ("valid", "needs_review", "invalid")
UNCERTAINTY_OUTCOMES: Final[tuple[str, ...]] = ("needs_info", "review_required")
FORBIDDEN_ON_UNCERTAINTY: Final[str] = "no_fit"

MaRole = Literal[
    "write_authority",
    "not_this_write",
    "leftover",
    "consume",
    "consume_or_fold",
    "consume_or_retire",
]

CLOSED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "write_authority",
        "not_this_write",
        "leftover",
        "consume",
        "consume_or_fold",
        "consume_or_retire",
    }
)


@dataclass(frozen=True)
class Answerer:
    code: str
    role: MaRole
    paths: tuple[str, ...]


ANSWERERS: Final[tuple[Answerer, ...]] = (
    Answerer(
        code="intake_source_profile_mapping_rules",
        role="write_authority",
        paths=(
            "backend/app/models/intake_routing.py",
            "backend/app/entity_profile/mapping_write.py",
        ),
    ),
    Answerer(
        code="meta_lead_form_mappings",
        role="leftover",
        paths=(
            "backend/app/models/lead.py",
            "backend/app/modules/leads/field_mapping_resolve.py",
        ),
    ),
    Answerer(
        code="meta_lead_settings_field_mapping",
        role="leftover",
        paths=("backend/app/models/lead.py",),
    ),
    Answerer(
        code="silent_precedence_chain",
        role="leftover",
        paths=(
            "backend/app/entity_profile/ingest_runtime.py",
            "backend/app/modules/leads/field_mapping_resolve.py",
        ),
    ),
    Answerer(
        code="meta_leads_admin_ui",
        role="leftover",
        paths=("hostflow-frontend/src/pages/admin/MetaLeadsAdminPage.tsx",),
    ),
    Answerer(
        code="c5_and_intake_form_editors",
        role="consume_or_fold",
        paths=(
            "hostflow-frontend/src/pages/marketing/MarketingSourceMappingPage.tsx",
            "hostflow-frontend/src/components/admin/IntakeFormMappingEditor.tsx",
        ),
    ),
    Answerer(
        code="mapping_applied_v1_diagnostics",
        role="consume",
        paths=("backend/app/acquisition/mapping_applied_stamp.py",),
    ),
    Answerer(
        code="cl6_flight_map",
        role="not_this_write",
        paths=("backend/app/entity_profile/flight_map_runtime.py",),
    ),
    Answerer(
        code="sales_convert_mapping_v1",
        role="not_this_write",
        paths=("backend/app/modules/sales/services/convert_mapping.py",),
    ),
    Answerer(
        code="ocr_and_telegram_bootstrap",
        role="leftover",
        paths=(
            "backend/app/modules/documents/mapping_candidate.py",
            "backend/app/api/v1/communications/_helpers/telegram_intake/candidate_link.py",
        ),
    ),
    Answerer(
        code="dual_vocabulary_and_hardcoded_extractors",
        role="leftover",
        paths=(
            "backend/app/field_registry/intake_mapping.py",
            "backend/app/entity_profile/ingest_runtime.py",
            "backend/app/entity_profile/public_intake_draft_session.py",
            "backend/app/entity_profile/facade.py",
        ),
    ),
    Answerer(
        code="lead_criteria_and_forms_answers",
        role="not_this_write",
        paths=(
            "backend/app/modules/leads/lead_criteria_eval.py",
            "backend/app/forms_platform/answers.py",
        ),
    ),
)


def write_authority_answerers() -> tuple[Answerer, ...]:
    return tuple(row for row in ANSWERERS if row.role == "write_authority")


def classified_codes() -> tuple[str, ...]:
    return tuple(row.code for row in ANSWERERS)
