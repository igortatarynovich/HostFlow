"""Canonical marketplace / integration offer keys (ADR-006).

Использование: валидация `offer_key` при записи в `tenant_integration_installations` /
`company_integration_enablements`, витрина Marketplace, сидирование каталога.

Секреты провайдеров не хранятся в `settings_json` таблиц установок — только
несекретные флаги и метаданные; креды остаются в специализированных таблицах
до унификации.
"""

from __future__ import annotations

# Категории витрины HostFlow Marketplace (UI секции).
MARKETPLACE_CATEGORIES: frozenset[str] = frozenset(
    {
        "communication",
        "productivity",
        "hr",
        "fleet",
        "accounting",
        "ai",
        "automation",
        "storage",
        "compliance",
    }
)

# Тип оффера в смысле ADR-006 (не путать с product module ADR-004).
OFFER_KIND_CORE_INTEGRATION: str = "core_integration"
OFFER_KIND_MARKETPLACE_APP: str = "marketplace_app"

OFFER_KINDS: frozenset[str] = frozenset({OFFER_KIND_CORE_INTEGRATION, OFFER_KIND_MARKETPLACE_APP})

# Базовые (free / baseline) интеграции — platform capabilities.
CORE_INTEGRATION_OFFER_KEYS: frozenset[str] = frozenset(
    {
        "whatsapp",
        "telegram",
        "viber",
        "email",
        "gmail",
        "google_workspace",
        "google_calendar",
        "google_contacts",
        "microsoft_teams",
        "outlook",
        "outlook_calendar",
        "slack",
        "zoom",
        "meta_leads",
        "google_drive",
        "dropbox",
        "onedrive",
    }
)

# Плейсхолдеры для каталога приложений (расширяется продуктом).
MARKETPLACE_APP_OFFER_KEYS_EXAMPLES: frozenset[str] = frozenset(
    {
        "payroll_generic",
        "tms_generic",
        "erp_generic",
        "accounting_generic",
        "ocr_generic",
        "ai_assistant_generic",
        "compliance_country_generic",
        "driver_compliance_generic",
        "sms_provider_generic",
        "voip_provider_generic",
    }
)
