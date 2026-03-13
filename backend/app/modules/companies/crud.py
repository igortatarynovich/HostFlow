from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.tenant import Tenant
from backend.app.models.tenant import TenantType
from backend.app.models.tenant import TenantLink
from backend.app.models.user import Role as UserRole, User
from .schemas import (
    BillingProfile,
    ComplianceProfile,
    CompanyReadiness,
    Contact,
    IntegrationsProfile,
    LegalProfile,
    OperationsProfile,
    PortalProfile,
    ContractRecord,
    OrderRecord,
)


# --- helpers ---------------------------------------------------------------

def _extract_session(db_like) -> AsyncSession:
    """
    В create_company в параметр 'db' может прилетать кортеж из зависимостей
    (например, (AsyncSession, current_user)). Аккуратно достаём AsyncSession.
    """
    if isinstance(db_like, AsyncSession):
        return db_like
    if isinstance(db_like, tuple):
        for item in db_like:
            if isinstance(item, AsyncSession):
                return item
    raise TypeError("AsyncSession not found in provided dependency")


def _tenant_id_from_session(db_like) -> str:
    """Берём tenant_id из AsyncSession.info и приводим к str (для SQLite VARCHAR(36))."""
    db = _extract_session(db_like)
    tenant_id = db.info.get("tenant_id")
    if isinstance(tenant_id, UUID):
        return str(tenant_id)
    return str(tenant_id) if tenant_id is not None else ""


async def _validate_company_user(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str | None,
    allowed_roles: set[str] | None = None,
) -> str | None:
    normalized = str(user_id or "").strip()
    if not normalized:
        return None
    user = (
        await session.execute(select(User).where(User.id == normalized).limit(1))
    ).scalar_one_or_none()
    if user is None:
        raise ValueError("Company owner/manager user not found")
    if user.tenant_id and str(user.tenant_id) != tenant_id:
        raise ValueError("Company owner/manager must belong to current tenant")
    if not bool(getattr(user, "is_active", True)) or getattr(user, "deleted_at", None):
        raise ValueError("Company owner/manager must be active")
    if allowed_roles:
        role_value = str(getattr(getattr(user, "role", None), "value", getattr(user, "role", ""))).strip().lower()
        if role_value not in allowed_roles:
            raise ValueError("Company owner must have elevated role")
    return normalized


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged


PROFILE_SECTIONS: Tuple[str, ...] = (
    "legal",
    "billing",
    "operations",
    "compliance",
    "client_portal",
    "integrations",
    "contracts",
    "company_orders",
)


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    if value is None:
        return []
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if value in (None, "", [], {}):
            continue
        cleaned[key] = value
    return cleaned


def _prune_nested(value: Any) -> Any:
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, inner in value.items():
            pruned = _prune_nested(inner)
            if pruned in (None, "", [], {}):
                continue
            result[key] = pruned
        return result
    if isinstance(value, list):
        items = [_prune_nested(item) for item in value]
        return [item for item in items if item not in (None, "", [], {})]
    return value


def _normalize_contacts_map(raw: Any, *, strict: bool = False) -> Dict[str, Dict[str, Any]]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        iterable: Iterable[Tuple[Any, Any]] = raw.items()
    elif isinstance(raw, list):
        iterable = ((None, item) for item in raw)
    else:
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    for key, value in iterable:
        data = _ensure_dict(value)
        full_name = data.get("full_name") or data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        if not full_name and not email and not phone:
            if strict:
                errors.append("Contact must include full_name, email, or phone")
            continue
        raw_id = data.get("id") or key
        try:
            contact_id = UUID(str(raw_id)) if raw_id else uuid4()
        except (TypeError, ValueError):
            contact_id = uuid4()
        try:
            contact = Contact(
                id=contact_id,
                role=data.get("role"),
                full_name=str(full_name or "").strip() or (email or phone or ""),
                email=email,
                phone=phone,
                is_primary=bool(data.get("is_primary")),
                is_portal_user=bool(data.get("is_portal_user")),
            )
        except ValidationError as exc:  # pragma: no cover - future edge cases
            if strict:
                errors.append(str(exc))
            continue
        normalized[str(contact.id)] = contact.model_dump(mode="json", exclude_none=True)

    if strict and errors:
        raise ValueError("; ".join(errors))

    # Ensure only one primary contact
    primary_ids = [cid for cid, payload in normalized.items() if payload.get("is_primary")]
    if strict and len(primary_ids) > 1:
        raise ValueError("Multiple contacts marked as primary")
    if len(primary_ids) == 0 and normalized and not strict:
        # default first contact as primary when not strict (legacy data)
        first_key = next(iter(normalized))
        normalized[first_key]["is_primary"] = True
    return normalized


def _serialize_legal_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)
    try:
        legal = LegalProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid legal section: {exc}") from exc
    payload = legal.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    return payload or None


def _serialize_billing_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)
    accounts: List[Dict[str, Any]] = []
    for item in _ensure_list(data.get("bank_accounts")):
        account_raw = _ensure_dict(item)
        if not account_raw.get("iban"):
            continue
        raw_id = account_raw.get("id")
        try:
            account_id = UUID(str(raw_id)) if raw_id else uuid4()
        except (TypeError, ValueError):
            account_id = uuid4()
        account_raw["id"] = account_id
        accounts.append(account_raw)
    data["bank_accounts"] = accounts
    try:
        billing = BillingProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid billing section: {exc}") from exc
    payload = billing.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    return payload or None


def _serialize_operations_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)

    def _to_int(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    for key in ("fleet_tractors", "fleet_intl_perc", "fleet_local_perc", "drivers_total"):
        if key in data:
            converted = _to_int(data[key])
            if converted is not None:
                data[key] = converted
            else:
                data.pop(key, None)

    trailer_types = _ensure_dict(data.get("trailer_types") or data.get("trailers"))
    data["trailer_types"] = {
        str(name): _to_int(count)
        for name, count in trailer_types.items()
    }

    lanes_raw = _ensure_dict(data.get("lanes"))
    data["lanes"] = {
        "origins": [str(item).strip() for item in _ensure_list(lanes_raw.get("origins")) if str(item).strip()],
        "destinations": [str(item).strip() for item in _ensure_list(lanes_raw.get("destinations")) if str(item).strip()],
    }

    data["work_modes"] = [
        str(item).upper()
        for item in _ensure_list(data.get("work_modes"))
        if str(item).strip()
    ]
    data["cargo_types"] = [
        str(item).strip()
        for item in _ensure_list(data.get("cargo_types"))
        if str(item).strip()
    ]
    data["languages"] = [
        str(item).strip()
        for item in _ensure_list(data.get("languages"))
        if str(item).strip()
    ]
    data["preferred_nationalities"] = [
        str(item).strip()
        for item in _ensure_list(data.get("preferred_nationalities"))
        if str(item).strip()
    ]

    try:
        operations = OperationsProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid operations section: {exc}") from exc
    payload = operations.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    if payload.get("trailer_types"):
        payload["trailer_types"] = {
            key: value
            for key, value in payload["trailer_types"].items()
            if value is not None
        }
    return payload or None


def _serialize_compliance_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)
    try:
        compliance = ComplianceProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid compliance section: {exc}") from exc
    payload = compliance.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    return payload or None


def _serialize_portal_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)
    roles: List[Dict[str, Any]] = []
    for item in _ensure_list(data.get("portal_roles")):
        role_raw = _ensure_dict(item)
        if not role_raw.get("full_name") and not role_raw.get("email"):
            continue
        try:
            role_id = UUID(str(role_raw.get("id"))) if role_raw.get("id") else uuid4()
        except (TypeError, ValueError):
            role_id = uuid4()
        role_raw["id"] = role_id
        roles.append(role_raw)
    data["portal_roles"] = roles
    try:
        portal = PortalProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid client portal section: {exc}") from exc
    payload = portal.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    return payload or None


def _serialize_integrations_section(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    data = _ensure_dict(raw)
    data["provider_ids"] = [str(item).strip() for item in _ensure_list(data.get("provider_ids")) if str(item).strip()]
    data["webhooks"] = [_ensure_dict(item) for item in _ensure_list(data.get("webhooks"))]
    try:
        integrations = IntegrationsProfile.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid integrations section: {exc}") from exc
    payload = integrations.model_dump(mode="json", exclude_none=True)
    payload = _prune_nested(payload)
    return payload or None


def _serialize_contracts_section(raw: Any) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in _ensure_list(raw):
        data = _ensure_dict(item)
        if not data.get("title"):
            continue
        try:
            contract_id = UUID(str(data.get("id"))) if data.get("id") else uuid4()
        except (TypeError, ValueError):
            contract_id = uuid4()
        data["id"] = contract_id
        try:
            contract = ContractRecord.model_validate(data)
        except ValidationError:
            continue
        payload = contract.model_dump(mode="json", exclude_none=True)
        result.append(_prune_nested(payload))
    return result


def _serialize_orders_section(raw: Any) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for item in _ensure_list(raw):
        data = _ensure_dict(item)
        if not data.get("title"):
            continue
        try:
            order_id = UUID(str(data.get("id"))) if data.get("id") else uuid4()
        except (TypeError, ValueError):
            order_id = uuid4()
        data["id"] = order_id
        try:
            order = OrderRecord.model_validate(data)
        except ValidationError:
            continue
        payload = order.model_dump(mode="json", exclude_none=True)
        result.append(_prune_nested(payload))
    return result


def _apply_extra_patch(current: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    extra = deepcopy(current)

    if "legal" in patch:
        legal_payload = _serialize_legal_section(patch.get("legal"))
        if legal_payload:
            extra["legal"] = legal_payload
        else:
            extra.pop("legal", None)

    if "billing" in patch:
        billing_payload = _serialize_billing_section(patch.get("billing"))
        if billing_payload:
            extra["billing"] = billing_payload
        else:
            extra.pop("billing", None)

    if "operations" in patch:
        operations_payload = _serialize_operations_section(patch.get("operations"))
        if operations_payload:
            extra["operations"] = operations_payload
        else:
            extra.pop("operations", None)

    if "compliance" in patch:
        compliance_payload = _serialize_compliance_section(patch.get("compliance"))
        if compliance_payload:
            extra["compliance"] = compliance_payload
        else:
            extra.pop("compliance", None)

    if "client_portal" in patch:
        portal_payload = _serialize_portal_section(patch.get("client_portal"))
        if portal_payload:
            extra["client_portal"] = portal_payload
        else:
            extra.pop("client_portal", None)

    if "integrations" in patch:
        integrations_payload = _serialize_integrations_section(patch.get("integrations"))
        if integrations_payload:
            extra["integrations"] = integrations_payload
        else:
            extra.pop("integrations", None)

    if "contracts" in patch:
        contracts_payload = _serialize_contracts_section(patch.get("contracts"))
        if contracts_payload:
            extra["contracts"] = contracts_payload
        else:
            extra.pop("contracts", None)

    if "company_orders" in patch:
        orders_payload = _serialize_orders_section(patch.get("company_orders"))
        if orders_payload:
            extra["company_orders"] = orders_payload
        else:
            extra.pop("company_orders", None)

    return extra


def _parse_date(value: Any) -> Optional[datetime.date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def calculate_company_readiness(company: Company) -> CompanyReadiness:
    extra = _ensure_dict(getattr(company, "extra", {}))
    legal = _ensure_dict(extra.get("legal"))
    billing = _ensure_dict(extra.get("billing"))
    compliance = _ensure_dict(extra.get("compliance"))
    portal = _ensure_dict(extra.get("client_portal"))

    contacts_map = _normalize_contacts_map(getattr(company, "contacts", {}), strict=False)
    has_legal = bool(
        legal.get("reg_no")
        or legal.get("vat_eu")
        or _ensure_dict(legal.get("registered_address"))
        or _ensure_dict(legal.get("operational_address"))
    )
    has_primary_contact = any(payload.get("is_primary") for payload in contacts_map.values())
    bank_accounts = _ensure_list(billing.get("bank_accounts"))
    has_primary_bank = any(_ensure_dict(item).get("is_primary") for item in bank_accounts)
    payment_terms = billing.get("payment_terms_days")
    invoice_email = billing.get("invoice_email")
    billing_ready = bool(payment_terms and invoice_email)

    fin_status = compliance.get("fin_check_status") or "pending"
    doc_valid_until = _parse_date(compliance.get("doc_valid_until"))
    compliance_valid = True
    if doc_valid_until:
        compliance_valid = doc_valid_until >= datetime.utcnow().date()

    client_portal_enabled = bool(portal.get("enabled"))

    components = [
        has_legal,
        has_primary_contact,
        has_primary_bank,
        billing_ready,
        compliance_valid,
        client_portal_enabled,
    ]
    readiness_score = (sum(1 for flag in components if flag) / len(components)) * 100 if components else None

    readiness_state = "ready"
    if not has_legal:
        readiness_state = "legal_missing"
    elif not has_primary_contact:
        readiness_state = "contact_missing"
    elif not has_primary_bank:
        readiness_state = "bank_missing"
    elif not billing_ready:
        readiness_state = "billing_invalid"
    elif not compliance_valid:
        readiness_state = "compliance_expired"

    return CompanyReadiness(
        company_id=UUID(str(company.id)),
        has_legal=has_legal,
        has_primary_contact=has_primary_contact,
        has_primary_bank=has_primary_bank,
        fin_check_status=fin_status,
        billing_ready=billing_ready,
        compliance_valid=compliance_valid,
        client_portal_enabled=client_portal_enabled,
        readiness_score=readiness_score,
        readiness_state=readiness_state,
    )


def _sync_contacts_extra(company: Company) -> None:
    contacts_map = _normalize_contacts_map(getattr(company, "contacts", {}), strict=False)
    extra = _ensure_dict(getattr(company, "extra", {}))
    if contacts_map:
        extra = _deep_merge(extra, {"contacts": contacts_map})
    else:
        extra.pop("contacts", None)
    company.contacts = contacts_map
    company.extra = extra


def _onboarding_module_profile(company_type: str | None) -> Dict[str, bool]:
    normalized = str(company_type or "").strip().lower()
    # Keep defaults permissive for agency; tailor focused presets for employer/services.
    profiles: Dict[str, Dict[str, bool]] = {
        "agency": {
            "candidates": True,
            "companies": True,
            "vacancies": True,
            "documents": True,
            "leads": True,
            "services": True,
            "client_portal": True,
        },
        "employer": {
            "candidates": True,
            "companies": True,
            "vacancies": True,
            "documents": True,
            "leads": False,
            "services": False,
            "client_portal": False,
        },
        "services": {
            "candidates": False,
            "companies": True,
            "vacancies": False,
            "documents": True,
            "leads": True,
            "services": True,
            "client_portal": False,
        },
    }
    return dict(profiles.get(normalized) or profiles["agency"])


def _bootstrap_tenant_settings_for_company_type(
    tenant_settings: Any,
    *,
    company_type: str | None,
) -> Dict[str, Any]:
    settings_payload = _ensure_dict(tenant_settings)
    settings_payload["business_type"] = str(company_type or "agency").strip().lower() or "agency"
    modules_payload = _ensure_dict(settings_payload.get("modules"))
    modules_payload.update(_onboarding_module_profile(company_type))
    settings_payload["modules"] = modules_payload
    return settings_payload


def _business_funnel_presets(company_type: str | None) -> Dict[str, Dict[str, Any]]:
    normalized = str(company_type or "").strip().lower() or "agency"
    candidate_presets = {
        "agency": {
            "name": "Candidate Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "In progress", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Declined / Rejected", "declined_rejected", True),
            ],
        },
        "employer": {
            "name": "Hiring Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Screening", "in_progress", False),
                ("interview", "Interview", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Declined / Rejected", "declined_rejected", True),
            ],
        },
    }
    lead_presets = {
        "agency": {
            "name": "Lead Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("contacted", "Contact made", "in_progress", False),
                ("qualified", "Qualified", "in_progress", False),
                ("converted", "Converted", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        },
        "services": {
            "name": "Service Sales Pipeline",
            "stages": [
                ("new", "New request", "new", False),
                ("contacted", "In progress", "in_progress", False),
                ("qualified", "Proposal sent", "in_progress", False),
                ("converted", "Won", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        },
    }
    return {
        "candidate": candidate_presets.get(normalized, candidate_presets["agency"]),
        "lead": lead_presets.get(normalized, lead_presets["agency"]),
    }


async def _ensure_default_funnel_if_missing(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel_type: str,
    name: str,
    stages: list[tuple[str, str, str, bool]],
) -> None:
    existing_funnels = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.type == funnel_type,
            )
        )
    ).scalars().all()
    target: Funnel | None = None
    for funnel in existing_funnels:
        if funnel.is_default:
            target = funnel
            break
    if target is None:
        for funnel in existing_funnels:
            if (funnel.name or "").strip() == name:
                target = funnel
                break
    created = False
    if target is None:
        target = Funnel(
            tenant_id=tenant_id,
            type=funnel_type,
            name=name,
            is_default=True,
        )
        db.add(target)
        await db.flush()
        created = True
    for funnel in existing_funnels:
        funnel.is_default = funnel.id == target.id
    target.is_default = True
    if created:
        target.name = name

    existing_stages = (
        await db.execute(
            select(FunnelStage).where(FunnelStage.funnel_id == target.id)
        )
    ).scalars().all()
    if existing_stages:
        return

    for order, (code, label, system_stage, is_terminal) in enumerate(stages):
        db.add(
            FunnelStage(
                funnel_id=target.id,
                code=code,
                label=label,
                system_stage=system_stage,
                order=order,
                is_terminal=bool(is_terminal),
            )
        )
    await db.flush()


async def _bootstrap_default_funnels_for_business_type(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_type: str | None,
    modules: Dict[str, bool] | None,
) -> None:
    presets = _business_funnel_presets(company_type)
    enabled_modules = modules or {}
    if bool(enabled_modules.get("candidates", True)):
        candidate = presets["candidate"]
        await _ensure_default_funnel_if_missing(
            db,
            tenant_id=tenant_id,
            funnel_type="candidate",
            name=str(candidate["name"]),
            stages=list(candidate["stages"]),
        )
    if bool(enabled_modules.get("leads", True)):
        lead = presets["lead"]
        await _ensure_default_funnel_if_missing(
            db,
            tenant_id=tenant_id,
            funnel_type="lead",
            name=str(lead["name"]),
            stages=list(lead["stages"]),
        )


async def update_company_extra_section(
    db: AsyncSession,
    company_id: UUID,
    section: str,
    payload: Any,
) -> Optional[Company]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    patch = {section: payload}
    try:
        updated_extra = _apply_extra_patch(_ensure_dict(company.extra), patch)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    company.extra = updated_extra
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


def _get_billing_details(company: Company) -> Dict[str, Any]:
    extra = _ensure_dict(getattr(company, "extra", {}))
    return _ensure_dict(extra.get("billing"))


def _get_bank_accounts_list(billing: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [_ensure_dict(item) for item in _ensure_list(billing.get("bank_accounts"))]


async def add_company_bank_account(
    db: AsyncSession,
    company_id: UUID,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    billing = _get_billing_details(company)
    accounts = _get_bank_accounts_list(billing)
    if payload.get("is_primary"):
        for item in accounts:
            item["is_primary"] = False
    accounts.append(payload)

    try:
        serialized_billing = _serialize_billing_section({**billing, "bank_accounts": accounts})
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    updated_extra = _apply_extra_patch(_ensure_dict(company.extra), {"billing": serialized_billing})
    company.extra = updated_extra
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)

    bank_accounts = _get_bank_accounts_list(_ensure_dict(company.extra.get("billing")))
    return bank_accounts[-1] if bank_accounts else None


async def update_company_bank_account(
    db: AsyncSession,
    company_id: UUID,
    account_id: UUID,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    account_key = str(account_id)
    billing = _get_billing_details(company)
    accounts = _get_bank_accounts_list(billing)
    updated_accounts: List[Dict[str, Any]] = []
    target_found = False
    new_primary = False
    for item in accounts:
        if str(item.get("id")) == account_key:
            merged = _deep_merge(item, payload)
            merged["id"] = account_id
            updated_accounts.append(merged)
            target_found = True
            new_primary = bool(merged.get("is_primary"))
        else:
            updated_accounts.append(item)

    if not target_found:
        return None

    if new_primary:
        for item in updated_accounts:
            if str(item.get("id")) != account_key:
                item["is_primary"] = False

    try:
        serialized_billing = _serialize_billing_section({**billing, "bank_accounts": updated_accounts})
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    company.extra = _apply_extra_patch(_ensure_dict(company.extra), {"billing": serialized_billing})
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)

    bank_accounts = _get_bank_accounts_list(_ensure_dict(company.extra.get("billing")))
    for item in bank_accounts:
        if str(item.get("id")) == account_key:
            return item
    return None


async def delete_company_bank_account(
    db: AsyncSession,
    company_id: UUID,
    account_id: UUID,
) -> bool:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return False

    account_key = str(account_id)
    billing = _get_billing_details(company)
    accounts = _get_bank_accounts_list(billing)
    removed_primary = any(str(item.get("id")) == account_key and item.get("is_primary") for item in accounts)
    remaining = [item for item in accounts if str(item.get("id")) != account_key]

    if len(remaining) == len(accounts):
        return False

    if removed_primary and remaining:
        remaining[0]["is_primary"] = True
        for item in remaining[1:]:
            item["is_primary"] = False

    serialized_billing = _serialize_billing_section({**billing, "bank_accounts": remaining})
    company.extra = _apply_extra_patch(_ensure_dict(company.extra), {"billing": serialized_billing})
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return True


async def add_company_contact(
    db: AsyncSession,
    company_id: UUID,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    existing_contacts = _normalize_contacts_map(company.contacts, strict=False)
    try:
        new_contact_map = _normalize_contacts_map([payload], strict=True)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if not new_contact_map:
        raise ValueError("Contact payload is empty")
    new_id, new_contact = next(iter(new_contact_map.items()))

    if new_contact.get("is_primary"):
        for item in existing_contacts.values():
            item["is_primary"] = False

    existing_contacts[new_id] = new_contact
    company.contacts = existing_contacts
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company.contacts.get(new_id)


async def update_company_contact(
    db: AsyncSession,
    company_id: UUID,
    contact_id: UUID,
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    contacts_map = _normalize_contacts_map(company.contacts, strict=False)
    contact_key = str(contact_id)
    if contact_key not in contacts_map:
        return None

    updated_contact = _deep_merge(contacts_map[contact_key], payload)
    try:
        normalized = _normalize_contacts_map({contact_key: updated_contact}, strict=True)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    new_contact = next(iter(normalized.values()))

    if new_contact.get("is_primary"):
        for cid, item in contacts_map.items():
            item["is_primary"] = cid == contact_key
    else:
        contacts_map[contact_key]["is_primary"] = False

    contacts_map[contact_key] = new_contact
    company.contacts = contacts_map
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company.contacts.get(contact_key)


async def delete_company_contact(
    db: AsyncSession,
    company_id: UUID,
    contact_id: UUID,
) -> bool:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return False

    contacts_map = _normalize_contacts_map(company.contacts, strict=False)
    contact_key = str(contact_id)
    if contact_key not in contacts_map:
        return False

    removed_primary = contacts_map[contact_key].get("is_primary")
    contacts_map.pop(contact_key, None)

    # ensure at least one primary remains
    if removed_primary:
        for item in contacts_map.values():
            item["is_primary"] = False
        if contacts_map:
            first_key = next(iter(contacts_map))
            contacts_map[first_key]["is_primary"] = True

    company.contacts = contacts_map
    _sync_contacts_extra(company)
    company.updated_at = _now_utc()
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return True


async def get_company_readiness_info(
    db: AsyncSession,
    company_id: UUID,
) -> Optional[CompanyReadiness]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None
    return calculate_company_readiness(company)


# --- CRUD ------------------------------------------------------------------

async def list_companies(
    db: AsyncSession,
    q: Optional[str] = None,
    include_archived: bool = False,
    allowed_company_ids: set[str] | None = None,
) -> List[Company]:
    tenant_id = _tenant_id_from_session(db)

    # For client tenant: include companies linked via TenantLink (handoff_include_company_id)
    # For agency tenant: include companies from all linked client tenants
    # Same logic as in candidates scope
    from backend.app.services.handoff import is_client_tenant_for_list
    is_client = await is_client_tenant_for_list(db, tenant_id)
    
    if is_client:
        # Companies linked via TenantLink.handoff_include_company_id when client_tenant_id = tenant
        include_company_subq = select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == tenant_id,
            TenantLink.handoff_include_company_id.isnot(None),
        )
        # Companies owned by client tenant (company.tenant_id = tenant)
        client_owned_companies = select(Company.id).where(Company.tenant_id == tenant_id)
        # Combine: linked companies OR owned companies
        stmt = select(Company).where(
            or_(
                Company.id.in_(include_company_subq),
                Company.id.in_(client_owned_companies),
            )
        )
    else:
        # For agency: include own companies + companies from linked client tenants + linked companies directly
        # Get companies from linked client tenants via TenantLink
        linked_client_tenants_subq = select(TenantLink.client_tenant_id).where(
            TenantLink.agency_tenant_id == tenant_id,
            TenantLink.client_tenant_id.isnot(None),
        )
        linked_companies_subq = select(TenantLink.client_company_id).where(
            TenantLink.agency_tenant_id == tenant_id,
            TenantLink.client_company_id.isnot(None),
        )
        companies_from_linked_tenants = select(Company.id).where(
            Company.tenant_id.in_(linked_client_tenants_subq)
        )
        # Own companies OR companies from linked client tenants OR directly linked companies
        stmt = select(Company).where(
            or_(
                Company.tenant_id == tenant_id,
                Company.id.in_(companies_from_linked_tenants),
                Company.id.in_(linked_companies_subq),
            )
        )

    if not include_archived:
        stmt = stmt.where(Company.is_archived.is_(False))

    if allowed_company_ids is not None:
        allowed = [str(cid) for cid in allowed_company_ids if cid]
        if not allowed:
            return []
        stmt = stmt.where(Company.id.in_(allowed))

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Company.name.ilike(like),
                Company.legal_name.ilike(like),
            )
        )

    result = await _extract_session(db).execute(stmt)
    companies = cast(List[Company], result.scalars().all())
    for company in companies:
        _sync_contacts_extra(company)
    return companies


async def get_company(db: AsyncSession, company_id: UUID) -> Optional[Company]:
    tenant_id = _tenant_id_from_session(db)

    # For agency: also allow access to companies from linked client tenants
    from backend.app.services.handoff import is_client_tenant_for_list
    is_client = await is_client_tenant_for_list(db, tenant_id)
    
    if is_client:
        # Client tenant: only own companies
        stmt = select(Company).where(
            Company.tenant_id == tenant_id,
            Company.id == str(company_id),
        )
    else:
        # Agency: own companies OR companies from linked client tenants OR directly linked companies
        linked_client_tenants_subq = select(TenantLink.client_tenant_id).where(
            TenantLink.agency_tenant_id == tenant_id,
            TenantLink.client_tenant_id.isnot(None),
        )
        linked_companies_subq = select(TenantLink.client_company_id).where(
            TenantLink.agency_tenant_id == tenant_id,
            TenantLink.client_company_id.isnot(None),
        )
        companies_from_linked_tenants = select(Company.id).where(
            Company.tenant_id.in_(linked_client_tenants_subq)
        )
        stmt = select(Company).where(
            Company.id == str(company_id),
        ).where(
            or_(
                Company.tenant_id == tenant_id,
                Company.id.in_(companies_from_linked_tenants),
                Company.id.in_(linked_companies_subq),
            )
        )

    result = await _extract_session(db).execute(stmt)
    company = result.scalars().first()
    if company:
        _sync_contacts_extra(company)
    return company


async def create_company(db: AsyncSession, data, *, actor_user_id: str | None = None) -> Company:
    """
    Создать компанию в пределах текущего tenant.
    Генерируем id сами (uuid4), т.к. в модели/БД нет дефолта.
    Если это первая компания и передан company_type (agency|employer|services),
    выставляем Tenant.type + bootstrap settings/modules.
    """
    session = _extract_session(db)
    tenant_id = _tenant_id_from_session(session)

    payload = data.model_dump(exclude_unset=True)
    company_type = payload.pop("company_type", None)  # not a Company field
    owner_user_id_raw = payload.pop("owner_user_id", None)
    manager_user_id_raw = payload.pop("manager_user_id", None)

    # Count companies before create to know if this is the first
    count_result = await session.execute(
        select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id)
    )
    company_count_before = int(count_result.scalar_one() or 0)

    payload.setdefault("id", str(uuid4()))
    payload["tenant_id"] = tenant_id
    owner_user_id = await _validate_company_user(
        session,
        tenant_id=tenant_id,
        user_id=str(owner_user_id_raw) if owner_user_id_raw else actor_user_id,
        allowed_roles={UserRole.superadmin.value, UserRole.administrator.value, UserRole.supervisor.value},
    )
    manager_user_id = await _validate_company_user(
        session,
        tenant_id=tenant_id,
        user_id=str(manager_user_id_raw) if manager_user_id_raw else owner_user_id,
    )
    payload["owner_user_id"] = owner_user_id
    payload["manager_user_id"] = manager_user_id

    contacts_raw = payload.pop("contacts", None)
    normalized_contacts = (
        _normalize_contacts_map(contacts_raw, strict=True)
        if contacts_raw is not None
        else {}
    )

    extra_payload = _ensure_dict(payload.pop("extra", None))
    extra_normalized = _apply_extra_patch({}, extra_payload)
    if normalized_contacts:
        extra_normalized = _deep_merge(extra_normalized, {"contacts": normalized_contacts})

    payload["contacts"] = normalized_contacts
    payload["extra"] = extra_normalized

    obj = Company(**payload)
    _sync_contacts_extra(obj)
    session.add(obj)
    await session.flush()

    if company_count_before == 0 and company_type in ("agency", "employer", "services"):
        tenant = (
            await session.execute(
                select(Tenant).where(Tenant.id == tenant_id).limit(1)
            )
        ).scalar_one_or_none()
        if tenant is not None:
            if company_type == "employer":
                tenant_type = TenantType.company
            else:
                # "services" keeps full workspace behavior (same as agency tenant type).
                tenant_type = TenantType.agency
            tenant.type = tenant_type
            tenant.settings = _bootstrap_tenant_settings_for_company_type(
                tenant.settings,
                company_type=company_type,
            )
            session.add(tenant)
            tenant_modules = _ensure_dict(tenant.settings.get("modules")) if isinstance(tenant.settings, dict) else {}
            await _bootstrap_default_funnels_for_business_type(
                session,
                tenant_id=tenant_id,
                company_type=company_type,
                modules=tenant_modules,
            )

    await session.commit()
    await session.refresh(obj)
    return obj


async def update_company(db: AsyncSession, company_id: UUID, data) -> Optional[Company]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    payload = data.model_dump(exclude_unset=True)
    payload.pop("tenant_id", None)
    payload.pop("id", None)
    owner_user_id_present = "owner_user_id" in payload
    manager_user_id_present = "manager_user_id" in payload
    owner_user_id_raw = payload.pop("owner_user_id", None)
    manager_user_id_raw = payload.pop("manager_user_id", None)

    contacts_patch = payload.pop("contacts", None)
    extra_patch = payload.pop("extra", None)
    try:
        if contacts_patch is not None:
            normalized_contacts = _normalize_contacts_map(contacts_patch, strict=True)
            company.contacts = normalized_contacts
        else:
            normalized_contacts = _normalize_contacts_map(company.contacts, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid contacts payload: {exc}") from exc

    updated_extra = _ensure_dict(company.extra)
    if extra_patch is not None:
        try:
            updated_extra = _apply_extra_patch(updated_extra, _ensure_dict(extra_patch))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    company.extra = updated_extra
    company.contacts = normalized_contacts
    _sync_contacts_extra(company)

    for field, value in payload.items():
        setattr(company, field, value)
    if owner_user_id_present:
        company.owner_user_id = await _validate_company_user(
            session,
            tenant_id=_tenant_id_from_session(session),
            user_id=str(owner_user_id_raw) if owner_user_id_raw else None,
            allowed_roles={UserRole.superadmin.value, UserRole.administrator.value, UserRole.supervisor.value},
        )
    if manager_user_id_present:
        company.manager_user_id = await _validate_company_user(
            session,
            tenant_id=_tenant_id_from_session(session),
            user_id=str(manager_user_id_raw) if manager_user_id_raw else (company.owner_user_id if owner_user_id_present else None),
        )

    company.updated_at = _now_utc()

    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def archive_company(db: AsyncSession, company_id: UUID) -> Optional[Company]:
    session = _extract_session(db)
    company = await get_company(session, company_id)
    if not company:
        return None

    company.is_archived = True
    company.updated_at = _now_utc()

    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company
