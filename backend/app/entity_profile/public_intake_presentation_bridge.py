"""Public intake ↔ Form Presentation Runtime bridge (P7)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    DRIVER_CE_INTAKE_PRESENTATION_CODE,
    DRIVER_CE_PROFILE_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id
from backend.app.entity_profile.presentation_runtime import (
    FORM_PRESENTATION_RUNTIME_V1,
    FormPresentationNotFoundError,
    resolve_form_presentation_for_intake_source,
)
from backend.app.entity_profile.presentation_rules import (
    apply_presentation_rules_evaluation,
    missing_required_presentation_fields,
)
from backend.app.services.questionnaire_form_binding import is_repaired_b2b_questionnaire_form

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


_SERVICE_SALES_PREFIX = "service_sales."
_CONTACT_SUFFIX_TO_BUCKET = {
    "contact_full_name": ("personal", "full_name"),
    "contact_company_name": ("client_company", "name"),
    "contact_phone": ("contacts", "phone"),
    "contact_email": ("contacts", "email"),
    "contact_website": ("client_company", "website"),
}


def _sync_service_sales_contacts(state: dict[str, Any], block: dict[str, Any]) -> None:
    contacts = _record(state.get("contacts"))
    personal = _record(state.get("personal"))
    client_company = _record(state.get("client_company"))
    buckets = {"contacts": contacts, "personal": personal, "client_company": client_company}
    for code, raw in block.items():
        if not str(code).startswith(_SERVICE_SALES_PREFIX) or _is_empty(raw):
            continue
        suffix = str(code).rsplit(".", 1)[-1]
        mapping = _CONTACT_SUFFIX_TO_BUCKET.get(suffix)
        if mapping is None:
            continue
        bucket_name, key = mapping
        value = str(raw).strip() if isinstance(raw, str) else raw
        buckets[bucket_name][key] = value
    state["contacts"] = contacts
    state["personal"] = personal
    state["client_company"] = client_company


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

    if code.startswith(_SERVICE_SALES_PREFIX):
        block = _record(state.get(PRESENTATION_VALUES_V1))
        if code in block and not _is_empty(block.get(code)):
            return block.get(code)
        client_company = _record(state.get("client_company"))
        contacts = _record(state.get("contacts"))
        personal = _record(state.get("personal"))
        suffix = code.split(".")[-1]
        if suffix == "contact_full_name":
            return personal.get("full_name")
        if suffix == "contact_company_name":
            return client_company.get("name")
        if suffix == "contact_phone":
            return contacts.get("phone")
        if suffix == "contact_email":
            return contacts.get("email")
        if suffix == "contact_website":
            return client_company.get("website")
        return block.get(code)

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
    _sync_service_sales_contacts(state, block)
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
    """Return list of missing required qualified_codes (static + P10A required_if)."""
    field_codes = [
        str(f.get("qualified_code") or "")
        for f in (presentation.get("fields") or [])
        if isinstance(f, dict)
    ]
    values = presentation_values_dict_from_state(state, field_codes)
    return missing_required_presentation_fields(presentation, values)


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
    presentation_code = ""

    entity_profile_hint = str(intake_state.get("entity_profile_code") or "").strip()
    if entity_profile_hint:
        entity_profile_code = entity_profile_hint

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
            presentation_code = str(getattr(profile, "presentation_code", None) or "").strip()

        lead_form_row = None
        if lead_form_id:
            from backend.app.models.tenant_lead_form import TenantLeadForm

            lead_form_row = await db.get(TenantLeadForm, str(lead_form_id))

        codes_to_try: list[str] = []
        if presentation_code:
            codes_to_try.append(presentation_code)

        is_repaired_b2b = (
            entity_profile_code == TARGETED_ADVERTISING_PROFILE_CODE
            and lead_form_row is not None
            and is_repaired_b2b_questionnaire_form(lead_form_row)
        )
        if entity_profile_code == TARGETED_ADVERTISING_PROFILE_CODE and not is_repaired_b2b:
            from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PRESENTATION_CODE

            if TARGETED_ADVERTISING_PRESENTATION_CODE not in codes_to_try:
                codes_to_try.append(TARGETED_ADVERTISING_PRESENTATION_CODE)
        elif entity_profile_code != TARGETED_ADVERTISING_PROFILE_CODE:
            if DRIVER_CE_INTAKE_PRESENTATION_CODE not in codes_to_try:
                codes_to_try.append(DRIVER_CE_INTAKE_PRESENTATION_CODE)

        for code in codes_to_try:
            try:
                presentation = await resolve_form_presentation_for_intake_source(
                    db,
                    tenant_id=str(tenant_id),
                    intake_source_profile_id=str(intake_source_profile_id),
                    presentation_code=code,
                )
                if presentation.get("contract_version") != FORM_PRESENTATION_RUNTIME_V1:
                    continue
                field_codes = [
                    str(f.get("qualified_code") or "")
                    for f in (presentation.get("fields") or [])
                    if isinstance(f, dict)
                ]
                values = presentation_values_dict_from_state(intake_state, field_codes)
                return apply_presentation_rules_evaluation(presentation, values)
            except FormPresentationNotFoundError:
                continue

    return None
