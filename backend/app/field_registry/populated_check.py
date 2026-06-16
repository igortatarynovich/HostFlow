"""Read populated candidate values via Field Registry storage bindings."""

from __future__ import annotations

from typing import Any

from backend.app.models.candidate import Candidate

_LEGACY_QUALIFIED_CODES: dict[str, str] = {
    "phone": "recruitment.candidate.contacts.phone",
    "email": "recruitment.candidate.contacts.email",
    "address": "platform.identity.address",
    "first_name": "recruitment.candidate.first_name",
    "last_name": "recruitment.candidate.last_name",
}


def legacy_field_code_from_qualified(qualified_code: str) -> str:
    code = str(qualified_code or "").strip()
    if not code:
        return ""
    for legacy, qualified in _LEGACY_QUALIFIED_CODES.items():
        if qualified == code:
            return legacy
    return code.split(".")[-1].replace("[]", "")


def qualified_code_from_field_spec(field_spec: dict[str, Any]) -> str:
    qualified = str(field_spec.get("qualified_code") or "").strip()
    if qualified:
        return qualified
    legacy = str(field_spec.get("field_code") or "").strip()
    if not legacy:
        return ""
    return _LEGACY_QUALIFIED_CODES.get(legacy, legacy)


def _candidate_contacts(candidate: Candidate) -> dict[str, Any]:
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    return contacts if isinstance(contacts, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _value_is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if isinstance(value, dict):
        if not value:
            return True
        line1 = str(value.get("line1") or value.get("address") or "").strip()
        return not line1
    return False


def read_candidate_storage_value(candidate: Candidate, storage: dict[str, Any] | None) -> Any:
    """Resolve a candidate attribute using registry storage metadata."""
    if not storage:
        return None

    kind = str(storage.get("kind") or "").strip()
    path = str(storage.get("path") or "").strip()
    contacts = _candidate_contacts(candidate)
    personal = _candidate_personal(candidate)
    extra = _candidate_extra(candidate)

    if kind == "column":
        if path == "phone":
            return candidate.phone or contacts.get("phone") or personal.get("phone")
        if path == "email":
            return candidate.email or contacts.get("email") or personal.get("email")
        return getattr(candidate, path, None)

    if kind == "json_path" and path:
        root, _, remainder = path.partition(".")
        if root == "personal_data":
            current: Any = personal
            for part in remainder.split("."):
                if not part:
                    continue
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            if path == "personal_data.address":
                if not _value_is_empty(current):
                    return current
                return extra.get("address") or getattr(candidate, "address", None)
            return current
        if root == "extra":
            current = extra
            for part in remainder.split("."):
                if not part:
                    continue
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            return current
        if root == "contacts":
            return contacts.get(remainder) if remainder else contacts

    return None


def candidate_field_is_populated(candidate: Candidate, storage: dict[str, Any] | None) -> bool:
    return not _value_is_empty(read_candidate_storage_value(candidate, storage))
