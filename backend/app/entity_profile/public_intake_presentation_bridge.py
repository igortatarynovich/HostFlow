"""Public intake ↔ Form Presentation Runtime bridge (P7)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    DRIVER_CE_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_PROFILE_CODE,
)
from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.entity_profile.presentation_runtime import (
    FormPresentationNotFoundError,
    resolve_form_presentation_for_intake_source,
)

PRESENTATION_VALUES_V1 = "presentation_values_v1"


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _split_full_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in str(full_name or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def presentation_value_from_state(state: dict[str, Any], qualified_code: str) -> Any:
    """Read a presentation field value from intake_state (canonical store + legacy fallback)."""
    code = str(qualified_code or "").strip()
    if not code:
        return None
    block = _record(state.get(PRESENTATION_VALUES_V1))
    if code in block and not _is_empty(block.get(code)):
        return block.get(code)

    contacts = _record(state.get("contacts"))
    personal = _record(state.get("personal"))
    experience = _record(state.get("experience"))

    if code == "recruitment.candidate.first_name":
        first, _ = _split_full_name(str(personal.get("full_name") or ""))
        return first or None
    if code == "recruitment.candidate.last_name":
        _, last = _split_full_name(str(personal.get("full_name") or ""))
        return last or None
    if code == "recruitment.candidate.contacts.phone":
        return contacts.get("phone")
    if code == "recruitment.candidate.contacts.email":
        return contacts.get("email")
    if code == "platform.identity.citizenship":
        return personal.get("citizenship")
    if code == "platform.identity.birth_date":
        return personal.get("birth_date")
    if code == "recruitment.candidate.experience.years_ce":
        return experience.get("years_ce")
    if code == "recruitment.candidate.personal.in_poland":
        return personal.get("in_poland")
    return block.get(code)


def apply_presentation_values_to_state(
    state: dict[str, Any],
    values: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Merge qualified_code values into intake_state and sync legacy contacts/personal/experience."""
    if not values:
        return state
    block = _record(state.get(PRESENTATION_VALUES_V1))
    for key, raw in values.items():
        code = str(key or "").strip()
        if not code:
            continue
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            block.pop(code, None)
        else:
            block[code] = raw
    state[PRESENTATION_VALUES_V1] = block

    contacts = _record(state.get("contacts"))
    personal = _record(state.get("personal"))
    experience = _record(state.get("experience"))

    first = block.get("recruitment.candidate.first_name")
    last = block.get("recruitment.candidate.last_name")
    if not _is_empty(first) or not _is_empty(last):
        fn = str(first or "").strip()
        ln = str(last or "").strip()
        personal["full_name"] = " ".join(p for p in [fn, ln] if p).strip()

    phone = block.get("recruitment.candidate.contacts.phone")
    if not _is_empty(phone):
        contacts["phone"] = str(phone).strip()

    email = block.get("recruitment.candidate.contacts.email")
    if not _is_empty(email):
        contacts["email"] = str(email).strip()

    citizenship = block.get("platform.identity.citizenship")
    if not _is_empty(citizenship):
        personal["citizenship"] = citizenship

    birth_date = block.get("platform.identity.birth_date")
    if not _is_empty(birth_date):
        personal["birth_date"] = birth_date

    years_ce = block.get("recruitment.candidate.experience.years_ce")
    if years_ce is not None and years_ce != "":
        experience["years_ce"] = years_ce

    in_poland = block.get("recruitment.candidate.personal.in_poland")
    if in_poland is not None and in_poland != "":
        personal["in_poland"] = in_poland

    state["contacts"] = contacts
    state["personal"] = personal
    state["experience"] = experience
    return state


def presentation_values_dict_from_state(state: dict[str, Any], field_codes: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for code in field_codes:
        c = str(code or "").strip()
        if not c:
            continue
        val = presentation_value_from_state(state, c)
        if not _is_empty(val):
            out[c] = val
    stored = _record(state.get(PRESENTATION_VALUES_V1))
    for code, val in stored.items():
        if code not in out and not _is_empty(val):
            out[code] = val
    return out


def validate_presentation_required_fields(
    presentation: dict[str, Any],
    state: dict[str, Any],
) -> list[str]:
    """Return list of missing required qualified_codes."""
    missing: list[str] = []
    for field in presentation.get("fields") or []:
        if not isinstance(field, dict):
            continue
        level = str(field.get("intake_level") or "optional").strip().lower()
        if level != "required":
            continue
        code = str(field.get("qualified_code") or "").strip()
        if not code:
            continue
        if _is_empty(presentation_value_from_state(state, code)):
            missing.append(code)
    return missing


async def resolve_public_session_form_presentation(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Resolve form_presentation_runtime_v1 for a public intake session, or None for legacy UI."""
    lf = intake_state.get("lead_form") if isinstance(intake_state.get("lead_form"), dict) else {}
    lead_form_id = str(lf.get("id") or "").strip() or None
    public_slug = str(lf.get("public_slug") or "").strip() or None

    intake_source_profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=lead_form_id,
        public_slug=public_slug,
    )
    entity_profile_code = DRIVER_CE_PROFILE_CODE
    presentation_code = DRIVER_CE_INTAKE_PRESENTATION_CODE

    if intake_source_profile_id:
        from backend.app.modules.intake_routing import crud as intake_crud

        profile = await intake_crud.get_profile_by_id(
            db,
            tenant_id=str(tenant_id),
            profile_id=str(intake_source_profile_id),
        )
        if profile is not None:
            bound = str(getattr(profile, "entity_profile_code", None) or "").strip()
            if bound:
                entity_profile_code = bound
        try:
            return await resolve_form_presentation_for_intake_source(
                db,
                tenant_id=str(tenant_id),
                intake_source_profile_id=str(intake_source_profile_id),
                presentation_code=presentation_code,
            )
        except FormPresentationNotFoundError:
            return None

    return None
