"""Tenant-scoped Form Presentation write path (P8).

UI may select fields from an Entity Profile subset only — never create canonical fields.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import REQUIREMENT_OPTIONAL, REQUIREMENT_REQUIRED
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import resolve_entity_profile_facade
from backend.app.entity_profile.mapping_validation import allowed_qualified_codes_from_profile_view
from backend.app.entity_profile.presentation_rules import drop_invalid_presentation_rules
from backend.app.models.entity_profile import EpIntakePresentation


VALID_INTAKE_LEVELS = frozenset({"required", "optional", "hidden"})


class PresentationWriteError(ValueError):
    def __init__(self, code: str, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def build_tenant_form_presentation_code(*, entity_profile_code: str, public_slug: str) -> str:
    profile = str(entity_profile_code or "").strip()
    slug = str(public_slug or "").strip().lower()
    if not profile or not slug:
        raise PresentationWriteError(
            code="presentation_code_inputs_missing",
            message="entity_profile_code and public_slug are required to derive presentation_code",
        )
    return f"{profile}.form.{slug}"


def _normalize_field_rows(fields: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Build ordered field_subset and presentation_overrides from write payload."""
    if not fields:
        raise PresentationWriteError(
            code="presentation_fields_empty",
            message="At least one presentation field is required",
        )

    seen: set[str] = set()
    ordered: list[tuple[int, str, dict[str, Any]]] = []
    for index, raw in enumerate(fields):
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("qualified_code") or "").strip()
        if not code:
            continue
        if code in seen:
            raise PresentationWriteError(
                code="presentation_duplicate_field",
                message=f"Duplicate qualified_code in presentation: {code}",
                details={"qualified_code": code},
            )
        seen.add(code)
        level = str(raw.get("intake_level") or REQUIREMENT_OPTIONAL).strip().lower()
        if level not in VALID_INTAKE_LEVELS:
            raise PresentationWriteError(
                code="presentation_invalid_intake_level",
                message=f"Invalid intake_level for {code}: {level}",
                details={"qualified_code": code, "intake_level": level},
            )
        sort_order = raw.get("sort_order")
        try:
            order = int(sort_order) if sort_order is not None else (index + 1) * 10
        except (TypeError, ValueError):
            order = (index + 1) * 10
        override: dict[str, Any] = {"intake_level": level}
        label = str(raw.get("label_override") or raw.get("label") or "").strip()
        if label:
            override["label_override"] = label
        widget = str(raw.get("widget_hint") or "").strip()
        if widget:
            override["widget_hint"] = widget
        rules = raw.get("presentation_rules")
        if isinstance(rules, dict) and rules:
            override["presentation_rules"] = dict(rules)
        ordered.append((order, code, override))

    if not ordered:
        raise PresentationWriteError(
            code="presentation_fields_empty",
            message="At least one valid qualified_code is required",
        )

    ordered.sort(key=lambda item: (item[0], item[1]))
    field_subset = [code for _, code, _ in ordered]
    presentation_overrides = {code: override for _, code, override in ordered}
    return field_subset, presentation_overrides


def merge_client_fields_with_platform_preset(
    client_fields: list[dict[str, Any]],
    preset_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Overlay operator choices onto the platform questionnaire (widgets, rules, labels)."""
    preset_by_code: dict[str, dict[str, Any]] = {}
    for raw in preset_fields:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("qualified_code") or "").strip()
        if code:
            preset_by_code[code] = dict(raw)

    merged: list[dict[str, Any]] = []
    for raw in client_fields:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("qualified_code") or "").strip()
        if not code:
            continue
        base = dict(preset_by_code.get(code) or {})
        row: dict[str, Any] = {
            "qualified_code": code,
            "intake_level": raw.get("intake_level") or base.get("intake_level") or "optional",
            "sort_order": raw.get("sort_order") if raw.get("sort_order") is not None else base.get("sort_order"),
        }
        label = str(raw.get("label_override") or raw.get("label") or "").strip()
        if not label:
            label = str(base.get("label_override") or base.get("label") or "").strip()
        if label:
            row["label_override"] = label[:255]
        widget = str(raw.get("widget_hint") or base.get("widget_hint") or "").strip()
        if widget:
            row["widget_hint"] = widget[:64]
        rules = raw.get("presentation_rules")
        if not isinstance(rules, dict) or not rules:
            rules = base.get("presentation_rules")
        if isinstance(rules, dict) and rules:
            row["presentation_rules"] = dict(rules)
        merged.append(row)
    return merged


async def validate_presentation_fields_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    fields: list[dict[str, Any]],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """Validate field subset against Entity Profile; return subset, overrides, profile view."""
    profile_code = str(entity_profile_code or "").strip()
    if not profile_code:
        raise PresentationWriteError(
            code="entity_profile_code_required",
            message="entity_profile_code is required",
        )

    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=profile_code,
            include_presentations=False,
        )
    except EntityProfileNotFoundError as exc:
        raise PresentationWriteError(
            code="entity_profile_not_found",
            message=str(exc),
            details={"entity_profile_code": profile_code},
        ) from exc

    if profile_view.get("resolution_source") == "not_found" or not profile_view.get("profile"):
        raise PresentationWriteError(
            code="entity_profile_not_found",
            message=f"Entity profile not found: {profile_code}",
            details={"entity_profile_code": profile_code},
        )

    allowed = allowed_qualified_codes_from_profile_view(profile_view)
    field_subset, presentation_overrides = _normalize_field_rows(fields)
    unknown = [code for code in field_subset if code not in allowed]
    field_subset = [code for code in field_subset if code in allowed]
    presentation_overrides = {code: override for code, override in presentation_overrides.items() if code in allowed}
    if not field_subset:
        raise PresentationWriteError(
            code="presentation_field_not_in_profile",
            message="Presentation fields must belong to the selected Entity Profile",
            details={"unknown_fields": unknown, "entity_profile_code": profile_code},
        )

    for code, override in presentation_overrides.items():
        if str(override.get("intake_level") or "") == REQUIREMENT_REQUIRED and code not in field_subset:
            raise PresentationWriteError(
                code="presentation_required_outside_subset",
                message=f"Required field must be included in presentation subset: {code}",
                details={"qualified_code": code},
            )

    presentation_overrides = drop_invalid_presentation_rules(presentation_overrides, field_subset)

    return field_subset, presentation_overrides, profile_view


async def upsert_tenant_intake_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    presentation_code: str,
    field_subset: list[str],
    presentation_overrides: dict[str, Any],
) -> EpIntakePresentation:
    """Create or update tenant-scoped ep_intake_presentations row."""
    code = str(presentation_code or "").strip()
    if not code:
        raise PresentationWriteError(code="presentation_code_required", message="presentation_code is required")

    tenant_scope = str(tenant_id).strip()
    existing = await db.scalar(
        select(EpIntakePresentation).where(
            EpIntakePresentation.tenant_id == tenant_scope,
            EpIntakePresentation.presentation_code == code,
        )
    )
    if existing is not None:
        existing.entity_profile_id = str(entity_profile_id)
        existing.field_subset = list(field_subset)
        existing.presentation_overrides = dict(presentation_overrides)
        existing.is_active = True
        await db.flush()
        return existing

    row = EpIntakePresentation(
        id=str(uuid4()),
        tenant_id=tenant_scope,
        entity_profile_id=str(entity_profile_id),
        presentation_code=code,
        field_subset=list(field_subset),
        presentation_overrides=dict(presentation_overrides),
        is_active=True,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError as exc:
        raise PresentationWriteError(
            code="presentation_code_taken",
            message=f"Presentation code already exists: {code}",
            details={"presentation_code": code},
        ) from exc
    return row


async def create_tenant_intake_presentation_if_absent(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    presentation_code: str,
    field_subset: list[str],
    presentation_overrides: dict[str, Any],
) -> tuple[EpIntakePresentation | None, bool]:
    """Create tenant presentation only when missing — never overwrite user edits."""
    code = str(presentation_code or "").strip()
    if not code:
        raise PresentationWriteError(code="presentation_code_required", message="presentation_code is required")

    tenant_scope = str(tenant_id).strip()
    existing = await db.scalar(
        select(EpIntakePresentation).where(
            EpIntakePresentation.tenant_id == tenant_scope,
            EpIntakePresentation.presentation_code == code,
        )
    )
    if existing is not None:
        return existing, False

    row = EpIntakePresentation(
        id=str(uuid4()),
        tenant_id=tenant_scope,
        entity_profile_id=str(entity_profile_id),
        presentation_code=code,
        field_subset=list(field_subset),
        presentation_overrides=dict(presentation_overrides),
        is_active=True,
    )
    try:
        # Nested savepoint: concurrent create must not roll back the whole request
        # transaction (avoids expired ORM / MissingGreenlet on callers).
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        existing = await db.scalar(
            select(EpIntakePresentation).where(
                EpIntakePresentation.tenant_id == tenant_scope,
                EpIntakePresentation.presentation_code == code,
            )
        )
        return existing, False
    return row, True
