"""Billing snapshot for invoices created from service orders."""

from __future__ import annotations

import json
from typing import Any


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _candidate_extra(candidate: Any) -> dict:
    getter = getattr(candidate, "_get_extra", None)
    if callable(getter):
        try:
            return _as_dict(getter())
        except Exception:
            pass
    return _as_dict(getattr(candidate, "extra", None))


def _normalized_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _format_address_blob(value: Any) -> str | None:
    if isinstance(value, str):
        return _normalized_text(value)
    blob = _as_dict(value)
    if not blob:
        return None
    parts = [
        _normalized_text(blob.get("country")),
        _normalized_text(blob.get("city")),
        _normalized_text(blob.get("street") or blob.get("house")),
        _normalized_text(blob.get("zip")),
    ]
    merged = ", ".join(part for part in parts if part)
    return merged or None


def _candidate_tax_id(candidate: Any) -> str | None:
    extra = _candidate_extra(candidate)
    personal = _as_dict(getattr(candidate, "personal_data", None))
    for source in (extra, personal):
        for key in ("tax_id", "nip", "pesel"):
            value = _normalized_text(source.get(key))
            if value:
                return value
    return None


def _candidate_address(candidate: Any) -> str | None:
    extra = _candidate_extra(candidate)
    personal = _as_dict(getattr(candidate, "personal_data", None))
    for source in (personal, extra):
        formatted = _format_address_blob(source.get("address"))
        if formatted:
            return formatted
    raw = getattr(candidate, "address", None)
    return _format_address_blob(raw)


def _employee_billing(employee: Any) -> dict[str, Any]:
    meta = _as_dict(getattr(employee, "meta", None))
    billing = _as_dict(meta.get("billing"))
    name = _normalized_text(getattr(employee, "display_name", None))
    return {
        "company_name": name,
        "email": _normalized_text(billing.get("invoice_email") or meta.get("email")),
        "tax_id": _normalized_text(billing.get("tax_id") or meta.get("pesel") or meta.get("nip")),
        "address": _format_address_blob(billing.get("address") or meta.get("address")),
        "recipient_name": name,
    }


def build_service_order_invoice_billing(
    *,
    company: Any | None,
    candidate: Any | None,
    employee: Any | None = None,
) -> dict[str, Any]:
    """Bill-To (customer) billing block for POST /invoices/from-service-order/{id}."""
    if company:
        extra = _as_dict(getattr(company, "extra", None))
        billing = _as_dict(extra.get("billing"))
        billing_address = billing.get("billing_address") or getattr(company, "address", None)
        return {
            "company_name": _normalized_text(
                getattr(company, "legal_name", None) or getattr(company, "name", None)
            ),
            "email": _normalized_text(billing.get("invoice_email") or getattr(company, "email", None)),
            "tax_id": _normalized_text(getattr(company, "tax_id", None)),
            "address": billing_address,
            "recipient_name": _normalized_text(
                getattr(company, "name", None) or getattr(company, "legal_name", None)
            ),
        }

    if candidate:
        recipient_name = (
            f"{getattr(candidate, 'first_name', '')} {getattr(candidate, 'last_name', '')}".strip()
        )
        return {
            "company_name": recipient_name or None,
            "email": _normalized_text(getattr(candidate, "email", None)),
            "tax_id": _candidate_tax_id(candidate),
            "address": _candidate_address(candidate),
            "recipient_name": recipient_name or None,
        }

    if employee:
        return _employee_billing(employee)

    return {}
