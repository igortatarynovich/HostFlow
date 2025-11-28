from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set
from uuid import UUID


VACANCY_PATTERN = re.compile(r"vacancy[_-]([0-9a-fA-F-]{6,})")

PHONE_ALIASES = (
    "phone_number",
    "phone",
    "phone number",
    "mobile",
    "телефон",
    "номер_телефона",
    "phonenumber",
    "phoneNumber",
)

NAME_ALIASES = (
    "full_name",
    "name",
    "имя",
    "fio",
)

FIRST_NAME_ALIASES = (
    "first_name",
    "имя",
)

LAST_NAME_ALIASES = (
    "last_name",
    "фамилия",
    "surname",
)

COUNTRY_ALIASES = (
    "country",
    "country_code",
    "страна",
)

CONTACT_ALIASES = (
    "preferred_contact",
    "preferredcontact",
    "preferred_channel",
    "preferred communication channel",
    "preferred contact",
    "preferred_contact_method",
    "preferred contact method",
    "preferred_contact_channel",
    "preferred contact channel",
    "preferred communication method",
    "preferred communication channel",
    "предпочтительный канал связи",
    "предпочтительный канал",
    "способ_связи",
    "канал_связи",
)

COMPANY_ALIASES = (
    "company",
    "company_name",
    "companyid",
    "company name",
    "employer_name",
    "компания",
    "компания название",
    "компания - название",
    "компания—название",
    "компания — название",
    "работодатель",
    "employer",
)

IN_POLAND_ALIASES = (
    "in_poland",
    "находится_в_польше",
    "находится в польше",
    "is_in_poland",
    "проживает_в_польше",
    "проживает в польше",
)

POLAND_STAY_BASIS_ALIASES = (
    "poland_stay_basis",
    "основание_пребывания",
    "stay_basis",
    "основание пребывания",
    "право_пребывания",
    "type_of_residence_in_poland",
    "type of residence in poland",
    "residence_basis",
    "residence basis",
)


def _normalize_field_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()

def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    result: List[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _iter_values(mapping: Dict[str, List[str]], *keys: str) -> Iterator[str]:
    for key in keys:
        normalized_key = key.lower()
        values = mapping.get(normalized_key)
        if not values:
            continue
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                yield text


def _first(mapping: Dict[str, List[str]], *keys: str) -> Optional[str]:
    return next(_iter_values(mapping, *keys), None)


def _first_valid(mapping: Dict[str, List[str]], transform, *keys: str) -> Optional[str]:
    for raw in _iter_values(mapping, *keys):
        value = transform(raw)
        if value:
            return value
    return None


def _split_full_name(full_name: str) -> Dict[str, str]:
    name = full_name.strip()
    if not name:
        return {"first_name": "", "last_name": ""}
    parts = name.split()
    if len(parts) == 1:
        return {"first_name": parts[0], "last_name": ""}
    return {"first_name": parts[0], "last_name": " ".join(parts[1:])}


def _extract_vacancy_hint(values: Iterable[str]) -> Optional[str]:
    for item in values:
        match = VACANCY_PATTERN.search(item)
        if match:
            return match.group(1)
    return None


def _clean_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    text = str(phone).strip()
    if not text:
        return None
    normalized = re.sub(r"[\s\-\(\)]", "", text)
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    if normalized.startswith("+"):
        digits = re.sub(r"\D", "", normalized)
        normalized = "+" + digits if digits else ""
    else:
        digits = re.sub(r"\D", "", normalized)
        normalized = "+" + digits if digits else ""
    if not normalized or not normalized.startswith("+"):
        return None
    digit_count = len(re.sub(r"\D", "", normalized))
    if digit_count < 11 or digit_count > 15:
        return None
    return normalized


def _infer_country_code(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    if phone.startswith("+") and len(phone) >= 3:
        return phone[:3]
    return None


def _normalize_preferred_contact(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    mapping = {
        "телефон": "phone",
        "phone": "phone",
        "call": "phone",
        "звонок": "phone",
        "viber": "viber",
        "вайбер": "viber",
        "whatsapp": "whatsapp",
        "ватсап": "whatsapp",
        "ватсапп": "whatsapp",
        "telegram": "telegram",
        "телеграм": "telegram",
        "tg": "telegram",
    }
    normalized = mapping.get(raw)
    if normalized:
        return normalized
    # handle raw values like "WhatsApp", "Телефон"
    for key, val in mapping.items():
        if raw == key:
            return val
    # fall back to trimmed original if it's already one of supported options
    if raw in {"phone", "viber", "whatsapp", "telegram"}:
        return raw
    return None


def _normalize_bool_hint(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    truthy = {"true", "yes", "1", "да", "y", "ok", "on"}
    falsy = {"false", "no", "0", "нет", "n", "off"}
    if raw in truthy:
        return True
    if raw in falsy:
        return False
    return None


def _normalize_poland_basis(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    lowered = raw.lower()
    for ch in "()":
        lowered = lowered.replace(ch, " ")
    lowered = lowered.replace("-", " ").replace("_", " ")
    collapsed = " ".join(part for part in lowered.split() if part)

    if not collapsed:
        return None

    text = collapsed
    if "visa" in text:
        if "d" in text or "type d" in text or "d type" in text:
            return "visa_d"
        if "c" in text or "type c" in text or "c type" in text:
            return "visa_c"
        return "other"
    if "karta" in text or "pobytu" in text or "residence" in text or "card" in text:
        return "karta_pobytu"
    if "eu" in text and "citizen" in text:
        return "eu_citizen"
    return "other"


def _is_poland_value(value: Optional[str]) -> bool:
    if not value:
        return False
    raw = value.strip().lower()
    if not raw:
        return False
    aliases = {"poland", "pl", "polska", "польша", "pl.", "pl (poland)"}
    return raw in aliases


def normalize_meta_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw Meta webhook payload into a flattened dict."""

    entry = (payload.get("entry") or [{}])[0] or {}
    changes = (entry.get("changes") or [{}])[0] or {}
    value = changes.get("value") or payload

    field_data = value.get("field_data") or []
    mapping: Dict[str, List[str]] = {}
    original_field_names: Set[str] = set()
    for item in field_data:
        normalized_name = _normalize_field_name(item.get("name"))
        if not normalized_name:
            continue
        mapping[normalized_name] = _as_list(item.get("values"))
        original_field_names.add(str(item.get("name") or "").strip())

    full_name = _first(mapping, *NAME_ALIASES) or ""
    first_name = _first(mapping, *FIRST_NAME_ALIASES)
    last_name = _first(mapping, *LAST_NAME_ALIASES)

    if not first_name or not last_name:
        parts = _split_full_name(full_name)
        first_name = first_name or parts["first_name"]
        last_name = last_name or parts["last_name"]

    email = (_first(mapping, "email", "work_email") or "").strip().lower() or None
    phone = _first_valid(mapping, _clean_phone, *PHONE_ALIASES)
    phone_country_code = _infer_country_code(phone)
    country_hint = _first(mapping, *COUNTRY_ALIASES)
    preferred_contact = _normalize_preferred_contact(_first(mapping, *CONTACT_ALIASES))

    vacancy_field = _first(mapping, "vacancy_id", "vacancy", "position_id")
    vacancy_hint_fields = [v for key, values in mapping.items() if key.startswith("utm") for v in values]
    if vacancy_field and not vacancy_hint_fields:
        vacancy_hint_fields.append(vacancy_field)
    vacancy_hint = _extract_vacancy_hint(vacancy_hint_fields)

    utm_fields = {key: values for key, values in mapping.items() if key.startswith("utm_")}

    company_values = list(_iter_values(mapping, *COMPANY_ALIASES))
    company_id_hint = None
    company_name_hint = None
    for candidate in company_values:
        try:
            company_id_hint = str(UUID(candidate))
            break
        except (TypeError, ValueError):
            if not company_name_hint:
                company_name_hint = candidate.strip()
    if not company_name_hint:
        company_name_hint = _first(mapping, "company_name")

    graph_error = value.get("graph_error")

    ad_id = value.get("ad_id") or value.get("adgroup_id") or value.get("adset_id")
    try:
        ad_id_int = int(ad_id) if ad_id is not None else None
    except (TypeError, ValueError):  # pragma: no cover - defensive
        ad_id_int = None

    normalized: Dict[str, Any] = {
        "raw_lead_id": value.get("leadgen_id") or value.get("id"),
        "form_id": value.get("form_id"),
        "created_time": value.get("created_time"),
        "full_name": full_name,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "email": email,
        "phone": phone,
        "phone_country_code": phone_country_code,
        "vacancy_id_hint": vacancy_field,
        "vacancy_hint": vacancy_hint,
        "company_id_hint": company_id_hint,
        "utm": {k: v[0] for k, v in utm_fields.items() if v},
        "ad_id": ad_id_int,
        "raw_field_names": sorted(original_field_names),
    }
    if company_name_hint:
        normalized["company_name_hint"] = company_name_hint
    company_hints: List[str] = []
    for item in company_values:
        item = item.strip()
        if item and item not in company_hints:
            company_hints.append(item)
    for utm_value in normalized["utm"].values():
        if isinstance(utm_value, str):
            candidate = utm_value.strip()
            if candidate and candidate not in company_hints:
                company_hints.append(candidate)
    if company_hints:
        normalized["company_hints"] = company_hints
    if country_hint:
        normalized["country_raw"] = country_hint
        normalized["country"] = country_hint.upper()
        if not normalized.get("in_poland") and _is_poland_value(country_hint):
            normalized["in_poland"] = True
    if preferred_contact:
        normalized["preferred_contact"] = preferred_contact
    in_poland_hint = _first(mapping, *IN_POLAND_ALIASES)
    in_poland_value = _normalize_bool_hint(in_poland_hint)
    if in_poland_value is not None:
        normalized["in_poland"] = in_poland_value
    poland_basis = _first(mapping, *POLAND_STAY_BASIS_ALIASES)
    if poland_basis:
        poland_basis_clean = poland_basis.strip()
        canonical_basis = _normalize_poland_basis(poland_basis_clean)
        if canonical_basis:
            normalized["poland_stay_basis"] = canonical_basis
            normalized["poland_stay_basis_raw"] = poland_basis_clean
        else:
            normalized["poland_stay_basis"] = poland_basis_clean
    if normalized.get("poland_stay_basis") and normalized.get("in_poland") is None:
        normalized["in_poland"] = True
    if graph_error:
        normalized["graph_error"] = graph_error

    # Attempt to parse canonical vacancy UUID from hint
    for key in (vacancy_field, vacancy_hint):
        if not key:
            continue
        try:
            normalized["vacancy_id"] = str(UUID(key))
            break
        except (TypeError, ValueError):
            continue
    else:
        normalized["vacancy_id"] = None

    # Normalize company UUID if provided
    if company_id_hint:
        try:
            normalized["company_id"] = str(UUID(company_id_hint))
        except ValueError:
            normalized["company_id"] = None
    else:
        normalized["company_id"] = None

    return normalized
