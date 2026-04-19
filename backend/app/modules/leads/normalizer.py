from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple
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

# §2.5: location / current jurisdiction vs citizenship (`country` above).
GEO_COUNTRY_ALIASES = (
    "geo_country",
    "location_country",
    "current_country",
    "work_location_country",
    "current_location_country",
    "where_do_you_live_country",
    "country_of_residence",
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
    "preferred_way_of_contact",
    "preferred way of contact",
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
    "what_is_the_legal_basis_of_your_stay_in_poland",
    "what_is_the_legal_basis_of_your_stay_in_poland?",
    "what is the legal basis of your stay in poland",
    "what is the legal basis of your stay in poland?",
    "legal_basis_of_stay_in_poland",
    "legal basis of stay in poland",
)

DRIVING_EXPERIENCE_ALIASES = (
    "ce_driving_experience_in_europe",
    "driving_experience_in_europe",
    "driving experience in europe",
    "ce_driving_experience",
    "ce driving experience",
    "driving_experience",
    "driving experience",
    "опыт_вождения_в_европе",
    "опыт вождения в европе",
    "опыт_вождения",
    "опыт вождения",
)


def _normalize_field_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _set_nested_value(target: Dict[str, Any], path: str, value: Any) -> None:
    parts = [part.strip() for part in str(path or "").split(".") if part.strip()]
    if not parts:
        return
    node: Dict[str, Any] = target
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _has_nested_value(target: Dict[str, Any], path: str) -> bool:
    parts = [part.strip() for part in str(path or "").split(".") if part.strip()]
    if not parts:
        return False
    node: Any = target
    for index, part in enumerate(parts):
        if not isinstance(node, dict) or part not in node:
            return False
        if index == len(parts) - 1:
            return True
        node = node.get(part)
    return False


def _coerce_mapping_rules(field_mapping: Any) -> List[Dict[str, Any]]:
    if not field_mapping:
        return []
    if isinstance(field_mapping, dict):
        rules = field_mapping.get("rules")
        if isinstance(rules, list):
            return [item for item in rules if isinstance(item, dict)]
        normalized_rules: List[Dict[str, Any]] = []
        for target, source in field_mapping.items():
            if not isinstance(target, str):
                continue
            if isinstance(source, dict):
                rule = dict(source)
                rule.setdefault("target", target)
                normalized_rules.append(rule)
                continue
            normalized_rules.append({"target": target, "source": source})
        return normalized_rules
    if isinstance(field_mapping, list):
        return [item for item in field_mapping if isinstance(item, dict)]
    return []


def _extract_source_values(
    mapping: Dict[str, List[str]],
    source: Any,
) -> Tuple[List[str], bool]:
    if isinstance(source, str):
        keys = [source]
    elif isinstance(source, (list, tuple, set)):
        keys = [str(item) for item in source]
    else:
        keys = []
    values: List[str] = []
    for key in keys:
        normalized_key = _normalize_field_name(key)
        if not normalized_key:
            continue
        values.extend(mapping.get(normalized_key) or [])
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return cleaned, bool(cleaned)


def _convert_mapped_value(raw_values: List[str], format_name: str) -> Any:
    if not raw_values:
        return None
    first = raw_values[0]
    fmt = str(format_name or "string").strip().lower()
    if fmt in {"string", "text"}:
        return first
    if fmt == "email":
        return first.lower()
    if fmt == "phone":
        return _clean_phone(first)
    if fmt == "bool":
        return _normalize_bool_hint(first)
    if fmt == "int":
        try:
            return int(first)
        except (TypeError, ValueError):
            return None
    if fmt == "float":
        try:
            return float(first)
        except (TypeError, ValueError):
            return None
    if fmt == "uuid":
        try:
            return str(UUID(first))
        except (TypeError, ValueError):
            return None
    if fmt == "country":
        return first.upper()
    if fmt == "geo_country":
        return first.upper()
    if fmt == "contact_channel":
        return _normalize_preferred_contact(first)
    if fmt == "list":
        return raw_values
    if fmt == "csv":
        return ", ".join(raw_values)
    if fmt == "lower":
        return first.lower()
    if fmt == "upper":
        return first.upper()
    return first


def _apply_custom_field_mapping(
    *,
    normalized: Dict[str, Any],
    source_mapping: Dict[str, List[str]],
    field_mapping: Any,
) -> None:
    rules = _coerce_mapping_rules(field_mapping)
    if not rules:
        return
    for rule in rules:
        target = str(rule.get("target") or "").strip()
        if not target:
            continue
        overwrite = bool(rule.get("overwrite", True))
        if not overwrite and _has_nested_value(normalized, target):
            continue
        raw_values, has_values = _extract_source_values(source_mapping, rule.get("source"))
        if not has_values:
            continue
        converted = _convert_mapped_value(raw_values, str(rule.get("format") or "string"))
        if converted is None:
            continue
        _set_nested_value(normalized, target, converted)

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


def parse_meta_export_ad_id(raw: Any) -> Optional[int]:
    """
    Meta Lead Center CSV / export rows use ``ag:120245658843840547``; webhooks may send ints.
    Used for ``meta_ads_map`` routing (numeric Graph ad id).
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    s = str(raw).strip()
    if not s:
        return None
    if ":" in s:
        prefix, rest = s.split(":", 1)
        if prefix.lower() == "ag" and rest.strip():
            s = rest.strip()
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def _clean_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    text = str(phone).strip()
    if not text:
        return None
    # Meta Lead Center CSV: ``p:+48501234567``
    if len(text) >= 2 and text[0].lower() == "p" and text[1] == ":":
        text = text[2:].strip()
    normalized = re.sub(r"[\s\-\(\)]", "", text)
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    if normalized.startswith("+"):
        digits = re.sub(r"\D", "", normalized)
        normalized = "+" + digits if digits else ""
    else:
        digits = re.sub(r"\D", "", normalized)
        # Polish mobile without country (common in exports): 9 digits starting 4–9 → +48
        if len(digits) == 9 and digits[0] in "456789":
            digits = "48" + digits
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
    # Check for waiting_for_trc first (before other TRC checks)
    if "waiting" in text and ("trc" in text or "karta" in text or "pobytu" in text or "residence" in text):
        return "waiting_for_trc"
    if "visa" in text:
        if "d" in text or "type d" in text or "d type" in text:
            return "visa_d"
        if "c" in text or "type c" in text or "c type" in text:
            return "visa_c"
        return "other"
    if "karta" in text or "pobytu" in text or "residence" in text or "card" in text:
        # Check if it's trc_(karta_pobytu) - already has karta pobytu
        if "trc" in text:
            return "karta_pobytu"
        return "karta_pobytu"
    if "eu" in text and "citizen" in text:
        return "eu_citizen"
    return "other"


def _normalize_driving_experience(value: Optional[str]) -> Optional[int]:
    """
    Normalize driving experience category to number of years.
    Returns the minimum number of years based on the category.
    Examples:
    - "6–12_months" -> 0 (less than 1 year)
    - "more_than_1_year" -> 1
    - "1-2_years" -> 1
    - "2-5_years" -> 2
    - "more_than_5_years" -> 5
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    
    # Remove underscores and normalize
    normalized = raw.replace("_", " ").replace("-", " ")
    
    # Check for "more than" patterns
    if "more than" in normalized or "more_than" in normalized:
        if "5" in normalized or "five" in normalized:
            return 5
        if "3" in normalized or "three" in normalized:
            return 3
        if "2" in normalized or "two" in normalized:
            return 2
        if "1" in normalized or "one" in normalized or "year" in normalized:
            return 1
        return 1  # default for "more than" without specific number
    
    # Check for range patterns like "6-12 months", "1-2 years"
    import re
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)", normalized)
    if range_match:
        min_val = int(range_match.group(1))
        # If it's months (6-12 months), convert to years (0)
        if "month" in normalized:
            return 0
        # If it's years, return the minimum
        return min_val
    
    # Check for specific year values
    year_match = re.search(r"(\d+)\s*year", normalized)
    if year_match:
        return int(year_match.group(1))
    
    # Check for month values (less than 1 year)
    month_match = re.search(r"(\d+)\s*month", normalized)
    if month_match:
        return 0
    
    # Default: if contains "year" or "1", assume at least 1 year
    if "year" in normalized or "1" in normalized:
        return 1
    
    return None


def _is_poland_value(value: Optional[str]) -> bool:
    if not value:
        return False
    raw = value.strip().lower()
    if not raw:
        return False
    aliases = {"poland", "pl", "polska", "польша", "pl.", "pl (poland)"}
    return raw in aliases


def coerce_generic_json_to_meta_normalizer_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrap arbitrary JSON objects so normalize_meta_payload can read field_data (§2.11 webhook v1).
    Accepts Meta leadgen shape unchanged; flat objects become synthetic field_data rows.
    """
    if not isinstance(body, dict):
        raise ValueError("JSON object expected")
    entry = body.get("entry")
    if isinstance(entry, list) and entry:
        return body
    if isinstance(body.get("field_data"), list):
        return {"entry": [{"changes": [{"value": dict(body)}]}]}
    skip = frozenset({"id", "external_id", "lead_id", "leadgen_id"})
    items: List[Dict[str, Any]] = []
    for k, v in body.items():
        if k in skip:
            continue
        if v is None:
            continue
        name = str(k).strip()
        if not name:
            continue
        if isinstance(v, (dict, list)):
            items.append(
                {
                    "name": name,
                    "values": [json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)],
                }
            )
        else:
            items.append({"name": name, "values": [str(v)]})
    inner: Dict[str, Any] = {"field_data": items}
    eid = body.get("id") or body.get("external_id") or body.get("leadgen_id")
    if eid is not None:
        s = str(eid).strip()
        if s:
            inner["leadgen_id"] = s
    return {"entry": [{"changes": [{"value": inner}]}]}


def normalize_meta_payload(
    payload: Dict[str, Any],
    *,
    field_mapping: Optional[Any] = None,
) -> Dict[str, Any]:
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

    ad_id_int: Optional[int] = None
    for raw_ad in (value.get("ad_id"), value.get("adgroup_id"), value.get("adset_id")):
        if raw_ad is None:
            continue
        ad_id_int = parse_meta_export_ad_id(raw_ad)
        if ad_id_int is not None:
            break
    # Flat CSV / coerced payloads put ``ad_id`` only in ``field_data``, not on ``value``.
    if ad_id_int is None:
        raw_from_fields = _first(mapping, "ad_id", "adset_id", "adgroup_id")
        if raw_from_fields:
            ad_id_int = parse_meta_export_ad_id(raw_from_fields)

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
    geo_hint = _first(mapping, *GEO_COUNTRY_ALIASES)
    if geo_hint:
        normalized["geo_country_raw"] = geo_hint
        normalized["geo_country"] = str(geo_hint).strip().upper()
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
    # Handle driving experience in Europe
    driving_experience = _first(mapping, *DRIVING_EXPERIENCE_ALIASES)
    if driving_experience:
        normalized["driving_experience_in_europe"] = driving_experience.strip()
        # Also normalize to number of years for experience_eu_years (опыт по ЕС)
        experience_years = _normalize_driving_experience(driving_experience)
        if experience_years is not None:
            normalized["experience_eu_years"] = experience_years
    if graph_error:
        normalized["graph_error"] = graph_error

    _apply_custom_field_mapping(
        normalized=normalized,
        source_mapping=mapping,
        field_mapping=field_mapping,
    )

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
