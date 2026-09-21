"""Entity Profile ingest runtime bridge — Meta / public intake (P3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.facade import resolve_entity_profile_for_intake_source
from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.entity_profile.mapping_validation import (
    MappingValidationResult,
    allowed_qualified_codes_from_profile_view,
    validate_mapping_rules_for_profile,
)
from backend.app.entity_profile.mapping_resolve import resolve_mapping_authority
from backend.app.field_registry.canonical_facts import (
    apply_authority_rules_to_sources,
    merge_canonical_facts,
)
from backend.app.modules.leads.intake_route import IntakeRouteContext, resolve_intake_route_for_ingest
from backend.app.modules.leads.normalizer import extract_meta_lead_form_context


@dataclass
class IngestEnvelope:
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any] = field(default_factory=dict)
    entity_profile_code: Optional[str] = None
    route_intent: str = "unknown"
    mapping_result: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    resolution_source: str = "not_specified"
    bridge_source: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    mapping_rules_source: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_payload_stored": True,
            "entity_profile_code": self.entity_profile_code,
            "route_intent": self.route_intent,
            "mapping_result": self.mapping_result,
            "warnings": self.warnings,
            "resolution_source": self.resolution_source,
            "bridge_source": self.bridge_source,
            "intake_source_profile_id": self.intake_source_profile_id,
            "mapping_rules_source": self.mapping_rules_source,
        }


def stamp_ingest_envelope_v1(normalized: dict[str, Any], envelope: IngestEnvelope) -> None:
    normalized["ingest_envelope_v1"] = envelope.to_dict()


def stamp_mapping_applied_from_envelope(
    normalized: dict[str, Any],
    *,
    rules: list[dict[str, Any]],
    envelope: IngestEnvelope,
    profile_updated_at: str | None = None,
) -> None:
    """Diagnostics PR5 — persist mapping revision fingerprint used at ingest."""
    from backend.app.acquisition.mapping_applied_stamp import stamp_mapping_applied_v1

    stamp_mapping_applied_v1(
        normalized,
        rules=rules,
        source_id=envelope.intake_source_profile_id,
        rules_source=envelope.mapping_rules_source,
        profile_updated_at=profile_updated_at,
    )

def _minimal_normalized_for_routing(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    ctx = extract_meta_lead_form_context(payload, source=source)
    return {
        "form_id": ctx.get("form_id"),
        "page_id": ctx.get("page_id"),
    }


async def resolve_entity_profile_for_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_route: IntakeRouteContext,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
    vacancy_id: Optional[str] = None,
) -> dict[str, Any]:
    vac_entity_code, vac_profile_id, vac_profile_code = await resolve_entity_profile_hints_from_vacancy(
        db,
        tenant_id=str(tenant_id),
        vacancy_id=vacancy_id,
    )
    explicit_code = str(getattr(intake_route, "entity_profile_code", None) or "").strip() or None
    if not explicit_code and vac_entity_code:
        explicit_code = vac_entity_code
    return await resolve_entity_profile_for_intake_source(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=intake_route.intake_source_profile_id,
        entity_profile_code=explicit_code,
        candidate_profile_id=candidate_profile_id or vac_profile_id,
        candidate_profile_code=candidate_profile_code or vac_profile_code,
        include_presentations=True,
    )


async def prepare_meta_ingest_runtime(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str,
    raw_payload: dict[str, Any],
    own_company_id: Optional[str] = None,
    settings_row: Optional[Any] = None,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
    vacancy_id: Optional[str] = None,
) -> tuple[list[dict[str, Any]], IngestEnvelope, IntakeRouteContext, dict[str, Any]]:
    """
    Resolve intake route + Entity Profile + validate field mapping for Meta-style ingest.

    Returns: (validated_mapping_rules, envelope_shell, intake_route, profile_view)
    """
    src = (source or "meta").strip().lower() or "meta"
    minimal = _minimal_normalized_for_routing(raw_payload, source=src)
    intake_route = await resolve_intake_route_for_ingest(
        db,
        tenant_id=str(tenant_id),
        source=src,
        normalized=minimal,
        payload=raw_payload,
        own_company_id_hint=str(own_company_id or "").strip() or None,
    )

    profile_view = await resolve_entity_profile_for_ingest(
        db,
        tenant_id=str(tenant_id),
        intake_route=intake_route,
        candidate_profile_id=candidate_profile_id,
        candidate_profile_code=candidate_profile_code,
        vacancy_id=vacancy_id,
    )

    resolved = await resolve_mapping_authority(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=intake_route.intake_source_profile_id,
        payload=raw_payload,
        source=src,
        settings_row=settings_row,
    )
    raw_rules = list(resolved.rules)
    rules_source = resolved.rules_source
    profile_updated_at: Optional[str] = resolved.profile_updated_at

    allowed = allowed_qualified_codes_from_profile_view(profile_view)
    validation = validate_mapping_rules_for_profile(
        raw_rules,
        allowed_qualified_codes=allowed,
        entity_profile_code=str(profile_view.get("entity_profile_code") or "").strip() or None,
        resolution_source=str(profile_view.get("resolution_source") or "not_specified"),
    )

    warnings = list(profile_view.get("warnings") or []) + list(validation.warnings)
    envelope = IngestEnvelope(
        raw_payload=raw_payload,
        entity_profile_code=str(profile_view.get("entity_profile_code") or "").strip() or None,
        route_intent=intake_route.route_intent,
        mapping_result=validation.to_dict(),
        warnings=warnings,
        resolution_source=str(profile_view.get("resolution_source") or "not_specified"),
        bridge_source=profile_view.get("bridge_source"),
        intake_source_profile_id=intake_route.intake_source_profile_id,
        mapping_rules_source=rules_source,
    )
    # Stash for callers that stamp after normalize (avoids extra profile fetch).
    envelope.mapping_result = {
        **envelope.mapping_result,
        "profile_updated_at": profile_updated_at,
    }
    return validation.accepted_rules, envelope, intake_route, profile_view


def _flatten_public_intake_state(intake_state: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for section in ("contacts", "personal", "experience", "agreements"):
        bucket = intake_state.get(section)
        if isinstance(bucket, dict):
            for key, value in bucket.items():
                flat[f"{section}.{key}"] = value
    presentation = intake_state.get("presentation_values_v1")
    if isinstance(presentation, dict):
        for key, value in presentation.items():
            code = str(key or "").strip()
            if code:
                flat[code] = value
    return flat


def _presentation_canonical_facts(intake_state: dict[str, Any]) -> dict[str, Any]:
    presentation = intake_state.get("presentation_values_v1")
    if not isinstance(presentation, dict):
        return {}
    return {
        str(code).strip(): value
        for code, value in presentation.items()
        if str(code or "").strip() and value not in (None, "")
    }


def _contact_identity_canonical_facts(intake_state: dict[str, Any]) -> dict[str, Any]:
    """Session start identity (email/phone) uses existing candidate write destinations.

    Public intake collects contact on the start page, not as a published field.
    Mapping Operator Surface is not this path — destinations already exist on
    ``CANDIDATE_WRITE_BY_QUALIFIED``.
    """
    contacts = intake_state.get("contacts")
    if not isinstance(contacts, dict):
        return {}
    out: dict[str, Any] = {}
    email = str(contacts.get("email") or "").strip()
    if email:
        out["recruitment.candidate.contacts.email"] = email
    phone = str(contacts.get("phone") or "").strip()
    if phone:
        out["recruitment.candidate.contacts.phone"] = phone
    phone_cc = str(contacts.get("phone_country_code") or "").strip()
    if phone_cc:
        out["recruitment.candidate.contacts.phone_country_code"] = phone_cc
    return out


async def prepare_public_intake_runtime(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any],
    intake_source_profile_id: Optional[str] = None,
    entity_profile_code: Optional[str] = None,
    candidate_profile_id: Optional[str] = None,
    candidate_profile_code: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    route_intent_override: Optional[str] = None,
) -> tuple[IngestEnvelope, dict[str, Any], MappingValidationResult]:
    """Build ingest envelope for public candidate intake submit."""
    raw_payload = dict(intake_state or {})
    flat = _flatten_public_intake_state(intake_state)

    vac_entity_code, vac_profile_id, vac_profile_code = await resolve_entity_profile_hints_from_vacancy(
        db,
        tenant_id=str(tenant_id),
        vacancy_id=vacancy_id,
    )
    explicit_code = str(entity_profile_code or "").strip() or vac_entity_code or None

    profile_view = await resolve_entity_profile_for_intake_source(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=intake_source_profile_id,
        entity_profile_code=explicit_code,
        candidate_profile_id=candidate_profile_id or vac_profile_id,
        candidate_profile_code=candidate_profile_code or vac_profile_code,
        include_presentations=True,
    )

    resolved = await resolve_mapping_authority(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=intake_source_profile_id,
        payload=raw_payload,
        source="public_intake",
    )
    allowed = allowed_qualified_codes_from_profile_view(profile_view)
    validation = validate_mapping_rules_for_profile(
        list(resolved.rules),
        allowed_qualified_codes=allowed,
        entity_profile_code=str(profile_view.get("entity_profile_code") or "").strip() or None,
        resolution_source=str(profile_view.get("resolution_source") or "not_specified"),
    )

    mapped_facts = apply_authority_rules_to_sources(flat, validation.accepted_rules)
    normalized_payload: dict[str, Any] = {}
    merge_canonical_facts(normalized_payload, _contact_identity_canonical_facts(intake_state), overwrite=False)
    merge_canonical_facts(normalized_payload, _presentation_canonical_facts(intake_state), overwrite=False)
    merge_canonical_facts(normalized_payload, mapped_facts, overwrite=True)

    warnings = list(profile_view.get("warnings") or []) + list(validation.warnings)
    override = str(route_intent_override or "").strip() or None
    if override:
        route_intent = override
    else:
        route_intent = "candidate_application"
        ak = str((intake_state or {}).get("application_kind") or "").strip().lower()
        if ak == "client":
            route_intent = "sales_inquiry"
        elif intake_source_profile_id:
            from backend.app.models.intake_routing import IntakeSourceProfile

            isp = await db.scalar(
                select(IntakeSourceProfile)
                .where(
                    IntakeSourceProfile.id == str(intake_source_profile_id),
                    IntakeSourceProfile.tenant_id == str(tenant_id),
                )
                .limit(1)
            )
            if isp is not None and str(getattr(isp, "route_intent", "") or "").strip():
                route_intent = str(isp.route_intent).strip()
        entity_code_preview = str(profile_view.get("entity_profile_code") or "").strip()
        if route_intent == "candidate_application" and entity_code_preview.startswith("service_sales."):
            route_intent = "sales_inquiry"
    entity_code = str(profile_view.get("entity_profile_code") or "").strip()
    envelope = IngestEnvelope(
        raw_payload=raw_payload,
        normalized_payload=normalized_payload,
        entity_profile_code=entity_code or None,
        route_intent=route_intent,
        mapping_result=validation.to_dict(),
        warnings=warnings,
        resolution_source=str(profile_view.get("resolution_source") or "not_specified"),
        bridge_source=profile_view.get("bridge_source"),
        intake_source_profile_id=resolved.intake_source_profile_id or intake_source_profile_id,
        mapping_rules_source=resolved.rules_source,
    )
    envelope.mapping_result = {
        **envelope.mapping_result,
        "profile_updated_at": resolved.profile_updated_at,
    }
    stamp_mapping_applied_from_envelope(
        normalized_payload,
        rules=validation.accepted_rules,
        envelope=envelope,
        profile_updated_at=resolved.profile_updated_at,
    )
    return envelope, profile_view, validation


async def resolve_public_intake_source_profile_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form_id: Optional[str] = None,
    public_slug: Optional[str] = None,
) -> Optional[str]:
    """Resolve IntakeSourceProfile.id for a public lead form binding."""
    from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile

    binding_probes: list[str] = []
    if lead_form_id:
        binding_probes.extend([f"lead_form_id:{lead_form_id}", lead_form_id, f"form_id:{lead_form_id}"])
    if public_slug:
        binding_probes.extend([f"public_slug:{public_slug}", public_slug, f"slug:{public_slug}"])
    if binding_probes:
        row = await db.scalar(
            select(IntakeSourceProfile.id)
            .join(IntakeSourceBinding, IntakeSourceBinding.intake_source_profile_id == IntakeSourceProfile.id)
            .where(
                IntakeSourceProfile.tenant_id == str(tenant_id),
                IntakeSourceProfile.is_active.is_(True),
                IntakeSourceBinding.tenant_id == str(tenant_id),
                IntakeSourceBinding.provider == "public_intake",
                IntakeSourceBinding.is_active.is_(True),
                IntakeSourceBinding.external_key.in_(binding_probes),
            )
            .order_by(IntakeSourceBinding.priority.desc(), IntakeSourceProfile.created_at.asc())
            .limit(1)
        )
        if row:
            return str(row)

    profile_codes: list[str] = []
    if lead_form_id:
        profile_codes.append(f"public-form-{lead_form_id}")
    if public_slug:
        profile_codes.append(f"public-form-{public_slug}")
    if profile_codes:
        row = await db.scalar(
            select(IntakeSourceProfile.id).where(
                IntakeSourceProfile.tenant_id == str(tenant_id),
                IntakeSourceProfile.is_active.is_(True),
                IntakeSourceProfile.provider == "public_intake",
                IntakeSourceProfile.code.in_(profile_codes),
            ).limit(1)
        )
        if row:
            return str(row)
    return None
