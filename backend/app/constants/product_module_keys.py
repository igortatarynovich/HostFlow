"""Canonical product module keys for company-scoped configuration (ADR-004 / ADR-005)."""

from __future__ import annotations

# Keys allowed in company_module_settings.module_key
COMPANY_MODULE_SETTING_KEYS: frozenset[str] = frozenset(
    {"recruitment", "hr", "fleet", "services", "finance"}
)
