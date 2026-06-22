"""Form Presentation Runtime — read-only field schema for public/Meta forms (P5A).

Form Runtime displays fields from Entity Profile + ``ep_intake_presentations`` subset.
It does **not** decide routing, outcomes, or entity creation.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import DEFAULT_REGISTRY_VERSION
from backend.app.entity_profile.resolver import resolve_effective_entity_profile
from backend.app.models.entity_profile import PLATFORM_TENANT_SCOPE, EpIntakePresentation
from backend.app.modules.intake_routing import crud as intake_crud


FORM_PRESENTATION_RUNTIME_V1 = "form_presentation_runtime_v1"


class FormPresentationNotFoundError(LookupError):
    """Raised when presentation_code does not resolve for the given Entity Profile."""

    def __init__(self, *, entity_profile_code: str, presentation_code: str) -> None:
        self.entity_profile_code = str(entity_profile_code or "").strip()
        self.presentation_code = str(presentation_code or "").strip()
        super().__init__(
            f"Form presentation not found: {self.presentation_code} "
            f"(entity_profile={self.entity_profile_code})"
        )


def _effective_label(
    *,
    qualified_code: str,
    field_row: dict[str, Any],
    presentation_overrides: dict[str, Any],
) -> str:
    override = presentation_overrides.get(qualified_code)
    if isinstance(override, dict):
        label = str(override.get("label_override") or "").strip()
        if label:
            return label
    embedded = field_row.get("field") if isinstance(field_row.get("field"), dict) else {}
    for key in ("label_key", "name"):
        value = str(embedded.get(key) or "").strip()
        if value:
            return value
    return qualified_code.split(".")[-1].replace("_", " ").title()


def _presentation_field_row(
    *,
    qualified_code: str,
    field_row: dict[str, Any],
    presentation_overrides: dict[str, Any],
    sort_order: int,
) -> dict[str, Any]:
    override = presentation_overrides.get(qualified_code)
    override_dict = dict(override) if isinstance(override, dict) else {}
    embedded = field_row.get("field") if isinstance(field_row.get("field"), dict) else {}
    return {
        "qualified_code": qualified_code,
        "sort_order": sort_order,
        "intake_level": field_row.get("intake_level") or "optional",
        "label": _effective_label(
            qualified_code=qualified_code,
            field_row=field_row,
            presentation_overrides=presentation_overrides,
        ),
        "field_type": embedded.get("field_type"),
        "field": embedded or None,
        "presentation_overrides": override_dict,
        "widget_hint": override_dict.get("widget_hint") or embedded.get("field_type"),
    }


async def _load_intake_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    presentation_code: str,
) -> EpIntakePresentation | None:
    code = str(presentation_code or "").strip()
    if not code:
        return None
    tenant_scope = str(tenant_id).strip()
    rows = (
        await db.execute(
            select(EpIntakePresentation).where(
                EpIntakePresentation.entity_profile_id == entity_profile_id,
                EpIntakePresentation.presentation_code == code,
                EpIntakePresentation.is_active.is_(True),
                EpIntakePresentation.tenant_id.in_([tenant_scope, PLATFORM_TENANT_SCOPE]),
            )
        )
    ).scalars().all()
    if not rows:
        return None
    for row in rows:
        if row.tenant_id == tenant_scope:
            return row
    return rows[0]


async def resolve_form_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    presentation_code: str,
    intake_source_profile_id: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve Form Presentation schema for public/Meta runtime consumers.

    Returns ``form_presentation_runtime_v1`` contract — display-only; no decisions.
    """
    profile_code = str(entity_profile_code or "").strip()
    pres_code = str(presentation_code or "").strip()
    if not profile_code or not pres_code:
        raise FormPresentationNotFoundError(
            entity_profile_code=profile_code or "?",
            presentation_code=pres_code or "?",
        )

    if intake_source_profile_id:
        intake_profile = await intake_crud.get_profile_by_id(
            db,
            tenant_id=str(tenant_id),
            profile_id=str(intake_source_profile_id),
        )
        if intake_profile is not None:
            bound_code = str(getattr(intake_profile, "entity_profile_code", None) or "").strip()
            if bound_code and bound_code != profile_code:
                raise FormPresentationNotFoundError(
                    entity_profile_code=profile_code,
                    presentation_code=pres_code,
                )

    profile_view = await resolve_effective_entity_profile(
        db,
        tenant_id=str(tenant_id),
        profile_code=profile_code,
    )
    if profile_view.get("resolution_source") == "not_found" or not profile_view.get("profile"):
        raise FormPresentationNotFoundError(
            entity_profile_code=profile_code,
            presentation_code=pres_code,
        )

    profile_meta = profile_view["profile"]
    presentation = await _load_intake_presentation(
        db,
        tenant_id=str(tenant_id),
        entity_profile_id=str(profile_meta["id"]),
        presentation_code=pres_code,
    )
    if presentation is None:
        raise FormPresentationNotFoundError(
            entity_profile_code=profile_code,
            presentation_code=pres_code,
        )

    field_subset = [str(code).strip() for code in (presentation.field_subset or []) if str(code).strip()]
    presentation_overrides = dict(presentation.presentation_overrides or {})
    profile_fields_by_code = {
        str(row.get("qualified_code") or "").strip(): row
        for row in (profile_view.get("fields") or [])
        if str(row.get("qualified_code") or "").strip()
    }

    warnings: list[str] = []
    fields_out: list[dict[str, Any]] = []
    for index, qualified_code in enumerate(field_subset):
        field_row = profile_fields_by_code.get(qualified_code)
        if field_row is None:
            warnings.append(f"presentation_field_not_in_profile:{qualified_code}")
            continue
        fields_out.append(
            _presentation_field_row(
                qualified_code=qualified_code,
                field_row=field_row,
                presentation_overrides=presentation_overrides,
                sort_order=(index + 1) * 10,
            )
        )

    return {
        "contract_version": FORM_PRESENTATION_RUNTIME_V1,
        "entity_profile_code": profile_code,
        "presentation_code": pres_code,
        "resolution_source": profile_view.get("resolution_source"),
        "registry_version": profile_meta.get("registry_version") or DEFAULT_REGISTRY_VERSION,
        "entity_type": profile_meta.get("entity_type"),
        "profile_name": profile_meta.get("name"),
        "field_subset": field_subset,
        "fields": fields_out,
        "warnings": warnings,
        "intake_source_profile_id": str(intake_source_profile_id).strip() if intake_source_profile_id else None,
        "ownership": "display_only",
    }


async def resolve_form_presentation_for_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: str,
    presentation_code: str,
) -> dict[str, Any]:
    """Resolve presentation using ``entity_profile_code`` from an intake source profile."""
    intake_profile = await intake_crud.get_profile_by_id(
        db,
        tenant_id=str(tenant_id),
        profile_id=str(intake_source_profile_id),
    )
    if intake_profile is None:
        raise FormPresentationNotFoundError(
            entity_profile_code="?",
            presentation_code=presentation_code,
        )
    entity_code = str(getattr(intake_profile, "entity_profile_code", None) or "").strip()
    if not entity_code:
        raise FormPresentationNotFoundError(
            entity_profile_code="?",
            presentation_code=presentation_code,
        )
    return await resolve_form_presentation(
        db,
        tenant_id=str(tenant_id),
        entity_profile_code=entity_code,
        presentation_code=presentation_code,
        intake_source_profile_id=str(intake_source_profile_id),
    )
