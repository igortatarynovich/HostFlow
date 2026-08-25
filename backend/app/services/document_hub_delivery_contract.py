"""Document Hub delivery façade — `documents.hub_adapter_v1`.

E2 bound public-contract / adapter ids onto this façade. E3 adds
entity-link resolve for HR employee. E4 adds Candidate primary-link
resolve on the same adapter. E5 drops `documents.candidate_id`; Candidate
relationship SoT is Hub `document_entity_links` only. E6 seals expiry /
validity as Hub `expires_at` + engine evaluation on the same adapter.
E7 seals outstanding ask (required type + entity via Document Link) as
additive `outstanding_asks` on resolve / owner_summary. DR1-runtime may
persist Engine-projected asks on this same adapter, keyed by entity-link
identity. E8-bind: display / select / persist canonical registry codes;
R4 aliases are resolve-only, not stored identity. E8-eval: required /
optional / blocked applicability from R5 ``merge(pack, tenant_delta)``
(+ Overlay as already-defined CL7 input). Not a second Adapter. Not a
Hub request / reminder / packages table. Not OCR. Not CL8. Not mass
D3–D9 bind. Does not rewrite CL7 evaluate / Overlay / DR1-runtime /
E8-bind identity.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_types.registry import (
    canonical_codes,
    is_canonical_code,
    normalize_input_doc_type,
)
from backend.app.models.document import Document
from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.modules.documents.crud import ensure_ruleset_seed, list_candidate_documents
from backend.app.modules.documents.crud import list_document_types as list_document_types_crud
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.modules.documents.owner_summary import EQUIVALENT_SATISFACTION
from backend.app.modules.documents.pack_projection import project_document_packs_from_expected
from backend.app.modules.documents.reminder_candidate_projection import project_reminder_candidates_from_packs
from backend.app.modules.documents.reminder_work_queue_projection import project_reminder_work_queue
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.modules.documents.router import _build_synthetic_documents
from backend.app.modules.documents.storage import get_uploads_root, sanitize_filename
from backend.app.reference.document_policy_merge import merge_resolved_policy
from backend.app.services.document_expiry_engine import evaluate_expiry
from backend.app.services.document_ruleset import load_default_ruleset

PUBLIC_CONTRACT_ID = "documents.public_contract.v1"
ADAPTER_ID = "documents.hub_adapter_v1"
PUBLIC_OPERATIONS = (
    "list",
    "resolve",
    "set_resolution",
    "owner_summary",
    "verification_status",
    "list_types",
)

# E3 first consumer — Document Link SoT.
E3_LINKED_ENTITY_TYPE = "workforce_employee"
E3_RELATION_TYPE = "reused_for_hr"
# E4 Candidate Document Link — persist Hub rows; column dropped in E5.
E4_LINKED_ENTITY_TYPE = "candidate"
E4_RELATION_TYPE = "primary"

ALLOWED_ENTITY_LINK_RESOLVE = frozenset(
    {
        (E3_LINKED_ENTITY_TYPE, E3_RELATION_TYPE),
        (E4_LINKED_ENTITY_TYPE, E4_RELATION_TYPE),
    }
)

# Hub-owned outstanding-ask persist. Keyed by Document Link identity
# (required type + entity). Not a request table. Not Catalog
# ``document.requested``. Engine is the sole writer (DR1-runtime).
_OUTSTANDING_ASK_STORE: dict[tuple[str, str], list[dict[str, str]]] = {}

APPLICABILITY_REQUIRED = "required"
APPLICABILITY_OPTIONAL = "optional"
APPLICABILITY_BLOCKED = "blocked"
ERROR_SCREENING_AS_REQUIRED = "screening_as_required"
ERROR_OCR_PRODUCT = "ocr_product"
ERROR_PACKAGES_TABLE = "packages_table"
ERROR_CL8 = "cl8"
ERROR_HUB_REQUEST_TABLE = "hub_request_table"
ERROR_CATALOG_DOCUMENT_REQUESTED = "catalog_document_requested"

_SCREENING_REQUIRED_KEYS = frozenset({"screening_as_required", "required_true"})
_OCR_KEYS = frozenset({"ocr", "ocr_product"})
_PACKAGES_KEYS = frozenset(
    {"packages_table", "hub_packages_table", "mint_packages", "packages_product"}
)
_CL8_KEYS = frozenset({"cl8", "mint_cl8", "as_cl8"})
_HUB_REQUEST_TABLE_KEYS = frozenset(
    {
        "hub_request_table",
        "document_request_table",
        "mint_hub_request",
        "reminder_table",
    }
)
_CATALOG_REQUESTED_KEYS = frozenset(
    {
        "document.requested",
        "catalog_document_requested",
        "mint_document_requested",
    }
)


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def persist_canonical_type_identity_via_contract(raw: Any) -> str:
    """Stored Hub type identity is a registry code. Aliases resolve via R4 only."""
    text = str(raw or "").strip()
    if not text:
        return ""
    code = normalize_input_doc_type(text)
    return code if is_canonical_code(code) else ""


def list_canonical_types_for_select_via_contract() -> list[str]:
    """Canonical registry codes offered for D4 display / select. Not aliases."""
    return sorted(canonical_codes())


def _truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _policy_error_from_mapping(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    for key in _SCREENING_REQUIRED_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_SCREENING_AS_REQUIRED
    screening = payload.get("screening")
    if isinstance(screening, Mapping) and _truthy_flag(screening.get("required")):
        return ERROR_SCREENING_AS_REQUIRED
    for key in _OCR_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_OCR_PRODUCT
    for key in _PACKAGES_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_PACKAGES_TABLE
    for key in _CL8_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_CL8
    for key in _HUB_REQUEST_TABLE_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_HUB_REQUEST_TABLE
    for key in _CATALOG_REQUESTED_KEYS:
        if _truthy_flag(payload.get(key)):
            return ERROR_CATALOG_DOCUMENT_REQUESTED
    return None


def _when_matches(when: Any, ctx: Mapping[str, Any]) -> bool:
    if not isinstance(when, Mapping) or not when:
        return True
    for key, expected in when.items():
        val = ctx.get(key)
        if isinstance(expected, list):
            if val not in expected:
                return False
        elif val != expected:
            return False
    return True


def _canonical_type_set(values: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(values, (list, tuple, set, frozenset)):
        return out
    for raw in values:
        code = persist_canonical_type_identity_via_contract(raw)
        if code:
            out.add(code)
    return out


def evaluate_required_doc_applicability_via_contract(
    owner_context: Mapping[str, Any] | None = None,
    *,
    tenant_delta: Mapping[str, Any] | None = None,
    overlay: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Required / optional / blocked from R5 merge + Overlay CL7 input.

    Overlay is a typed input (``document_types``) — this façade does not
    import Overlay / CL7 runtimes and does not rewrite E8-bind identity.
    Existing R5 packs are policy input. Not OCR. Not a packages table.
    """
    ctx = dict(owner_context or {})
    delta: Mapping[str, Any] | None = tenant_delta
    if delta is None:
        nested = ctx.pop("tenant_delta", None)
        delta = nested if isinstance(nested, Mapping) else None
    else:
        ctx.pop("tenant_delta", None)

    policy_error = _policy_error_from_mapping(ctx)
    if policy_error is None:
        policy_error = _policy_error_from_mapping(delta)
    if policy_error is None:
        policy_error = _policy_error_from_mapping(overlay)
    if policy_error is not None:
        return {"ok": False, "error": policy_error, "applicability": []}

    resolved = merge_resolved_policy(delta)
    checklist = compute_candidate_checklist(ctx, resolved)
    debug = checklist.get("debug") if isinstance(checklist.get("debug"), dict) else {}

    required = _canonical_type_set(checklist.get("requiredTypes"))
    optional = _canonical_type_set(checklist.get("optionalTypes"))
    blocked = _canonical_type_set(debug.get("removed_by_overrides"))
    for rule in (resolved.get("candidate") or {}).get("overrides") or []:
        if not isinstance(rule, Mapping):
            continue
        if not _when_matches(rule.get("when"), ctx):
            continue
        blocked.update(_canonical_type_set(rule.get("remove")))

    if isinstance(overlay, Mapping) and overlay.get("ok") is not False:
        extra = _canonical_type_set(overlay.get("document_types"))
        required.update(extra)
        optional.difference_update(extra)
        blocked.difference_update(extra)

    optional.difference_update(required)
    blocked.difference_update(required)
    blocked.difference_update(optional)

    rows: list[dict[str, str]] = []
    for code in sorted(required):
        rows.append({"doc_type": code, "applicability": APPLICABILITY_REQUIRED})
    for code in sorted(optional):
        rows.append({"doc_type": code, "applicability": APPLICABILITY_OPTIONAL})
    for code in sorted(blocked):
        rows.append({"doc_type": code, "applicability": APPLICABILITY_BLOCKED})
    return {"ok": True, "applicability": rows}


def project_required_doc_applicability_via_contract(
    owner_context: Mapping[str, Any] | None = None,
    *,
    tenant_delta: Mapping[str, Any] | None = None,
    overlay: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Hub applicability projection for public resolve. Additive; no id bump."""
    result = evaluate_required_doc_applicability_via_contract(
        owner_context,
        tenant_delta=tenant_delta,
        overlay=overlay,
    )
    rows = result.get("applicability") if isinstance(result, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _hub_document_view(doc: Document, link: DocumentEntityLink) -> dict[str, Any]:
    expires = getattr(doc, "expires_at", None) or getattr(doc, "expire_date", None)
    evaluation = evaluate_expiry(expires_on=expires)
    stored = str(getattr(doc, "doc_type", "") or "")
    canonical = persist_canonical_type_identity_via_contract(stored)
    return {
        "id": str(doc.id),
        "title": str(getattr(doc, "custom_name", None) or canonical or stored),
        "doc_type": canonical,
        "status": _enum_value(getattr(doc, "status", None)),
        "expires_at": expires.isoformat() if expires is not None else None,
        "expiry_state": None if evaluation is None else evaluation.state,
        "days_left": None if evaluation is None else evaluation.days_left,
        "link": {
            "id": str(link.id),
            "linked_entity_type": str(link.linked_entity_type),
            "linked_entity_id": str(link.linked_entity_id),
            "relation_type": str(link.relation_type),
        },
    }


async def list_candidate_documents_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    status: str | None = None,
    type_filter: str | None = None,
    include_deleted: bool = False,
    limit: int | None = None,
    offset: int | None = None,
    active_own_company_id: str | None = None,
) -> list[Any]:
    """Internal façade for Candidate-origin rows via Hub primary links.

    Not the D2 consume path (that is ``list_entity_link_documents_via_contract``).
    """
    return await list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        status=status,
        type_filter=type_filter,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
        active_own_company_id=active_own_company_id,
    )


async def list_entity_link_documents_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    linked_entity_type: str,
    linked_entity_id: str,
    relation_type: str = E3_RELATION_TYPE,
) -> list[dict[str, Any]]:
    """Same `documents.hub_adapter_v1` — entity-link resolve (E3 + E4).

    Document Link SoT is Hub table `document_entity_links`.
    This is not a second Adapter. E5 dropped `documents.candidate_id`.
    """
    etype = str(linked_entity_type or "").strip()
    eid = str(linked_entity_id or "").strip()
    rel = str(relation_type or "").strip() or E3_RELATION_TYPE
    tid = str(tenant_id or "").strip()
    if not (tid and etype and eid):
        return []
    if (etype, rel) not in ALLOWED_ENTITY_LINK_RESOLVE:
        raise ValueError(
            "entity-link resolve allows workforce_employee / reused_for_hr "
            "or candidate / primary only"
        )

    links = list(
        (
            await db.execute(
                select(DocumentEntityLink)
                .where(
                    DocumentEntityLink.tenant_id == tid,
                    DocumentEntityLink.linked_entity_type == etype,
                    DocumentEntityLink.linked_entity_id == eid,
                    DocumentEntityLink.relation_type == rel,
                )
                .order_by(DocumentEntityLink.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    if not links:
        return []

    doc_ids = [str(link.document_id) for link in links]
    docs = list(
        (
            await db.execute(
                select(Document).where(
                    Document.tenant_id == tid,
                    Document.id.in_(doc_ids),
                    Document.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    by_id = {str(doc.id): doc for doc in docs}
    views: list[dict[str, Any]] = []
    for link in links:
        doc = by_id.get(str(link.document_id))
        if doc is None:
            continue
        views.append(_hub_document_view(doc, link))
    return views


async def ensure_ruleset_seed_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    ruleset_payload: dict[str, Any],
    own_company_id: str | None = None,
) -> Any:
    """Document Hub delivery contract adapter for ruleset seed resolution."""
    return await ensure_ruleset_seed(
        db,
        tenant_id,
        ruleset_payload,
        own_company_id=own_company_id,
    )


def _ask_store_key(linked_entity_type: str, linked_entity_id: str) -> tuple[str, str] | None:
    etype = str(linked_entity_type or "").strip()
    eid = str(linked_entity_id or "").strip()
    if not etype or not eid:
        return None
    return (etype, eid)


def persist_outstanding_asks_via_contract(
    asks: list[dict[str, Any]] | None,
    *,
    linked_entity_type: str,
    linked_entity_id: str,
) -> list[dict[str, str]]:
    """Persist Engine outstanding asks on ``documents.hub_adapter_v1``.

    SoT remains Hub required type + entity via Document Link — not a Hub
    request table, not Catalog ``document.requested``.
    """
    key = _ask_store_key(linked_entity_type, linked_entity_id)
    if key is None:
        return []
    rows: list[dict[str, str]] = []
    for raw in asks or []:
        if not isinstance(raw, dict):
            continue
        doc_type = persist_canonical_type_identity_via_contract(raw.get("doc_type"))
        state = str(raw.get("state") or "").strip()
        if not doc_type or not state:
            continue
        rows.append({"doc_type": doc_type, "state": state})
    _OUTSTANDING_ASK_STORE[key] = rows
    return list(rows)


def load_outstanding_asks_via_contract(
    *,
    linked_entity_type: str,
    linked_entity_id: str,
) -> list[dict[str, str]] | None:
    """Return Engine-persisted asks, or ``None`` when Engine has not written."""
    key = _ask_store_key(linked_entity_type, linked_entity_id)
    if key is None or key not in _OUTSTANDING_ASK_STORE:
        return None
    return list(_OUTSTANDING_ASK_STORE[key])


def _outstanding_asks_from_required(required: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = required or {}
    asks: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    buckets = (
        ("missing", "missing"),
        ("in_progress_types", "requested"),
        ("problematic", "problem"),
    )
    for key, state in buckets:
        for code in payload.get(key) or []:
            canonical = persist_canonical_type_identity_via_contract(code)
            if not canonical:
                continue
            item = (canonical, state)
            if item in seen:
                continue
            seen.add(item)
            asks.append({"doc_type": canonical, "state": state})
    return asks


def project_outstanding_asks_via_contract(
    items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Hub outstanding-ask projection for public resolve / owner_summary.

    SoT is Hub required type vs Document Link rows — not Candidate stage,
    not HR ``hr_document_requests`` JSON, not Activity ``document_request``,
    and not a Hub request table.
    """
    docs = [
        {
            "doc_type": persist_canonical_type_identity_via_contract(
                row.get("doc_type") or row.get("type")
            ),
            "status": row.get("status"),
            "expires_at": row.get("expires_at"),
        }
        for row in (items or [])
    ]
    docs = [row for row in docs if row["doc_type"]]
    summary = compute_owner_summary({}, load_default_ruleset(), docs)
    return _outstanding_asks_from_required(summary.get("required") if isinstance(summary, dict) else None)


def compute_owner_summary_via_contract(
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
    docs_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for owner-summary projection."""
    summary = compute_owner_summary(owner_context, ruleset_payload, docs_payload)
    if isinstance(summary, dict):
        summary["outstanding_asks"] = _outstanding_asks_from_required(summary.get("required"))
    return summary


def project_document_packs_via_contract(
    *,
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
    docs_payload: list[dict[str, Any]],
    expected_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for pack gap projection."""
    return project_document_packs_from_expected(
        ctx=owner_context,
        ruleset=ruleset_payload,
        docs=docs_payload,
        expected_documents=expected_documents,
    )


def project_reminder_candidates_via_contract(
    packs_payload: list[dict[str, Any]],
    *,
    owner_type: str = "candidate",
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for reminder candidate projection."""
    normalized_owner = owner_type if owner_type in {"candidate", "employee"} else "candidate"
    return project_reminder_candidates_from_packs(packs_payload, owner_type=normalized_owner)  # type: ignore[arg-type]


def project_reminder_work_queue_via_contract(
    reminder_candidates: list[dict[str, Any]],
    *,
    owner_type: str,
    owner_id: str,
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for reminder work queue projection."""
    return project_reminder_work_queue(
        reminder_candidates,
        owner_type=owner_type,
        owner_id=owner_id,
    )


def list_canonical_document_type_codes_via_contract() -> set[str]:
    """Canonical document type codes exposed via delivery contract.

    Existence SoT is ``document-type-registry-v1.json`` (R3). Aliases are
    R4 resolve-only and are not select / persist identity.
    """
    return set(canonical_codes())


async def list_document_types_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> Any:
    """Document Hub delivery contract adapter for document type catalog reads."""
    return await list_document_types_crud(db, tenant_id)


def compute_candidate_checklist_via_contract(
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for checklist computation."""
    return compute_candidate_checklist(owner_context, ruleset_payload)


def list_equivalent_satisfaction_map_via_contract() -> dict[str, list[str]]:
    """Document Hub delivery contract adapter for equivalent document-type map."""
    return dict(EQUIVALENT_SATISFACTION or {})


def build_synthetic_documents_via_contract(
    tenant_id: str,
    candidate_id: Any,
    checklist: dict[str, Any],
    existing_docs: list[dict[str, Any]],
) -> list[Any]:
    """Document Hub delivery contract adapter for synthetic checklist rows."""
    return _build_synthetic_documents(tenant_id, candidate_id, checklist, existing_docs)


def get_uploads_root_via_contract() -> str:
    """Document Hub delivery contract adapter for uploads root resolution."""
    return str(get_uploads_root())


def sanitize_filename_via_contract(filename: str) -> str:
    """Document Hub delivery contract adapter for filename sanitization."""
    return sanitize_filename(filename)


async def evaluate_document_hub_requirements_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
) -> dict[str, Any] | None:
    """Document Hub delivery contract adapter for Requirement Engine document requirements."""
    from backend.app.requirement_rules.document_hub_bridge import (
        evaluate_candidate_document_hub_requirements,
    )

    return await evaluate_candidate_document_hub_requirements(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=candidate,
    )


def merge_document_hub_requirements_into_summary_via_contract(
    summary: dict[str, Any],
    hub_section: dict[str, Any] | None,
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for Requirement Engine summary overlay."""
    if not hub_section:
        return summary
    from backend.app.requirement_rules.document_hub_bridge import (
        merge_requirement_engine_into_owner_summary,
    )

    return merge_requirement_engine_into_owner_summary(summary, hub_section)
