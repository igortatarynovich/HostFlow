"""Forms Publish — frozen write classification (FP-1).

Contract id: ``forms_publish.v1``.

One operator question. One write. Twelve answerers. A later FP slice may
retire a leftover; it must not add a thirteenth write of the same question.

FP-2 wires the authenticated product route to ``commit_publish``.
FP-3 public serve consumes the frozen snapshot through Form Runtime.
FP-4 is the operator projection over those closed writes / serve.
Not P4 Themes. Not P5 Analytics. Not FormTemplate SoT. Not a second
submit engine. Not Hiring E2E. Not leftover-store deletion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

CONTRACT_ID: Final[str] = "forms_publish.v1"

OPERATOR_QUESTION: Final[str] = (
    "for this HostFlow form, what is published — the frozen snapshot a "
    "stranger fills at the public URL — and which act created that snapshot?"
)

WRITE_AUTHORITY: Final[str] = "commit_publish_ledger"
WRITE_PRODUCER_REL: Final[str] = "backend/app/forms_platform/adapter.py"
WRITE_API: Final[str] = "commit_publish"
PRODUCT_ROUTE_REL: Final[str] = "backend/app/api/v1/platform/forms_publications.py"
PRODUCT_ROUTE_PATH: Final[str] = "/api/v1/platform/forms/{form_id}/publish"
LEDGER_REL: Final[str] = "backend/app/models/form_publication_version.py"
PUBLIC_CONTRACT_ID: Final[str] = "forms.public_contract.v1"
ADAPTER_ID: Final[str] = "forms.endpoint_adapter_v1"

SURVIVING_SERVE_DEFINITION: Final[str] = "frozen_publication_snapshot"
LEFTOVER_SERVE_DEFINITION: Final[str] = "form_presentation_runtime_v1"

OPERATOR_STATES: Final[tuple[str, ...]] = (
    "draft",
    "published",
    "live",
    "inactive",
    "never_published",
)

FpRole = Literal[
    "write_authority",
    "not_this_write",
    "leftover",
    "consume",
]

CLOSED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "write_authority",
        "not_this_write",
        "leftover",
        "consume",
    }
)


@dataclass(frozen=True)
class Answerer:
    code: str
    role: FpRole
    paths: tuple[str, ...]
    owner: str | None = None
    expiry: str | None = None


ANSWERERS: Final[tuple[Answerer, ...]] = (
    Answerer(
        code="commit_publish_ledger",
        role="write_authority",
        paths=(
            "backend/app/forms_platform/adapter.py",
            "backend/app/models/form_publication_version.py",
            "backend/app/api/v1/platform/forms_publications.py",
        ),
    ),
    Answerer(
        code="tenant_lead_form_published_pointer",
        role="consume",
        paths=("backend/app/models/tenant_lead_form.py",),
    ),
    Answerer(
        code="intake_form_write_service_version_bump",
        role="not_this_write",
        paths=("backend/app/services/intake_form_write_service.py",),
    ),
    Answerer(
        code="form_definition_published_version_write",
        role="not_this_write",
        paths=("backend/app/intake_platform/form_definition.py",),
    ),
    Answerer(
        code="builder_draft_save",
        role="not_this_write",
        paths=("backend/app/forms_platform/builder/draft_persistence.py",),
    ),
    Answerer(
        code="entity_profile_presentation_public_serve",
        role="not_this_write",
        paths=("backend/app/entity_profile/presentation_runtime.py",),
    ),
    Answerer(
        code="publication_bridge_resolve",
        role="consume",
        paths=(
            "backend/app/forms_platform/publication_bridge.py",
            "backend/app/forms_platform/operator_publication.py",
        ),
    ),
    Answerer(
        code="form_runtime_serve",
        role="consume",
        paths=(
            "backend/app/forms_platform/runtime/serve.py",
            "backend/app/forms_platform/public_serve_bridge.py",
        ),
    ),
    Answerer(
        code="public_submit_bridge",
        role="consume",
        paths=("backend/app/forms_platform/public_submit_bridge.py",),
    ),
    Answerer(
        code="activate_deactivate_lifecycle",
        role="consume",
        paths=("backend/app/forms_platform/adapter.py",),
    ),
    Answerer(
        code="communications_automation_published_version",
        role="not_this_write",
        paths=("backend/app/communications/automation/lifecycle.py",),
    ),
    Answerer(
        code="public_intake_unbound_no_ledger",
        role="not_this_write",
        paths=(
            "backend/app/api/public/intake.py",
            "backend/app/entity_profile/public_intake_presentation_bridge.py",
        ),
    ),
)


def write_authority_answerers() -> tuple[Answerer, ...]:
    return tuple(row for row in ANSWERERS if row.role == "write_authority")


def leftover_answerers() -> tuple[Answerer, ...]:
    return tuple(row for row in ANSWERERS if row.role == "leftover")


def classified_codes() -> tuple[str, ...]:
    return tuple(row.code for row in ANSWERERS)
