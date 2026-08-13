# Capability Settings Manifest (Settings Contract schema)

**Status:** canonical (operational contract for **P-05**) · **L0 CLOSED** — schema shape frozen; JSON instances = L2  
**Normative:** [`ADR-029`](ADR-029-settings-contract.md) · [`ADR-028`](ADR-028-configuration-ownership.md) (P-04) · [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) · [`L0-platform-architecture.md`](L0-platform-architecture.md)  
**Catalog:** [`platform-capability-catalog.md`](platform-capability-catalog.md)

Изменение **формы** Manifest (sections, required fields) = L0 → Architecture RFC.  
Добавление keys в outline / JSON Manifest конкретной capability = L2 применение.

---

## Ideal: user configures a capability, not «the system»

| Анти-паттерн (свалка) | Канон HostFlow |
|----------------------|----------------|
| General / SMTP / Meta / Users в одной куче | **Forms** · **Documents** · **Notifications** · **AI** · … — отдельные пространства |
| Любой модуль добавляет «удобные» knobs | Только owner через **Settings Manifest** |
| Лицензия скрывает пункт меню вручную | Выключенная capability → Manifest **не** участвует в shell |

---

## Manifest document shape

Каждая capability с конфигурацией публикует Manifest:

```text
capability_id: forms | documents | notifications | ai | …
version: semver of manifest schema
sections:
  general: [...]
  integrations: [...]
  defaults: [...]
  policies: [...]
  feature_flags: [...]
  license_gates: [...]
  validation_rules: [...]   # cross-field / async rules (optional top-level)
```

### Setting entry (минимум)

| Field | Required | Description |
|-------|----------|-------------|
| `key` | yes | Stable id, e.g. `notifications.email.smtp.host` |
| `section` | yes | `general` \| `integrations` \| `defaults` \| `policies` \| `feature_flags` |
| `label_key` | yes | i18n key for admin UI |
| `type` | yes | `string` \| `number` \| `boolean` \| `enum` \| `secret` \| `json` \| `url` \| … |
| `required` | yes | boolean |
| `default` | no | Default value (or ref) |
| `allowed_values` | if enum | Closed set |
| `scope` | yes | `tenant` \| `company` \| `module` (ADR-005 storage level) |
| `license` | no | Plan / entitlement keys required to show & edit |
| `restart_required` | no | boolean |
| `migration_required` | no | boolean / note |
| `sensitive` | no | Redact in export logs |
| `description_key` | no | i18n help |

**Write path:** только owner capability.  
**Read path:** admin shell, export/import, resolved views для consumers (non-SoT).

---

## Sections (операционные группы)

| Section | Назначение | Примеры |
|---------|------------|---------|
| **General** | Базовые knobs пространства | Default language (Forms), quiet hours (Notifications) |
| **Integrations** | Provider bindings | SMTP, SMS, OCR engine, LLM provider, Meta App |
| **Defaults** | Стартовые значения для новых объектов | Default form theme, default retention |
| **Policies** | Правила поведения | Consent policy, retention/deletion, AI usage policy |
| **Feature Flags** | Вкл/выкл capability features | Advanced OCR, Prompt Library |
| **License Gates** | Какие keys видны при каком плане | Basic vs Advanced document management |
| **Validation Rules** | Кросс-полевые / async проверки | «SMTP host required if email channel on» |

---

## Example outlines (canonical IA — not full JSON yet)

### Forms

**Sprint 1 status:** concrete keys below (code mirror: `backend/app/forms_platform/manifest.py`).  
**Public Contract:** [`forms-public-contract.md`](forms-public-contract.md) · Adapter `forms.endpoint_adapter_v1`.  
**Builder:** `forms.feature_flags.builder_enabled` default **`true`** (P2 MVP). P3 Publish UI / P4 Themes / P5 Analytics remain **LOCKED**.

| Section | Key | Type | Default | Scope |
|---------|-----|------|---------|-------|
| General | `forms.general.default_language` | string | `pl` | tenant |
| General | `forms.general.public_url_base` | url | — | tenant |
| Defaults | `forms.defaults.tier` | enum(`basic`,`advanced`) | `basic` | tenant |
| Defaults | `forms.defaults.consent_required` | boolean | `true` | tenant |
| Policies | `forms.policies.consent_version_pin` | boolean | `true` | tenant |
| Policies | `forms.limits.max_active_publications` | number | `50` | tenant |
| Feature Flags | `forms.feature_flags.builder_enabled` | boolean | **`true`** (P1.3+) | tenant |
| Feature Flags | `forms.feature_flags.themes_advanced` | boolean | `false` | tenant |
| Feature Flags | `forms.feature_flags.multi_language` | boolean | `false` | tenant |
| Integrations | `forms.adapter.contract_id` | string | `forms.public_contract.v1` | module |
| Integrations | `forms.adapter.id` | string | `forms.endpoint_adapter_v1` | module |
| License Gates | `forms.license.advanced_forms` | boolean | `false` | tenant |

CAPTCHA provider / branding themes remain **Advanced** backlog — not Sprint 1 unlock.

### Documents

| Section | Keys (illustrative) |
|---------|---------------------|
| Integrations | OCR engine, e-sign provider, storage backend |
| Policies | Retention, auto-deletion |
| Defaults | Default sensitivity |
| License Gates | Document Hub Basic / Advanced |

### Notifications

| Section | Keys (illustrative) |
|---------|---------------------|
| Integrations | Email (SMTP), SMS, WhatsApp, Push |
| Policies | Retry policy, quiet hours / working hours |
| Defaults | Default templates locale |
| License Gates | Channel packs |

### AI

| Section | Keys (illustrative) |
|---------|---------------------|
| Integrations | Provider, model |
| Policies | Usage policies |
| Defaults | Default model |
| Feature Flags | Prompt Library |
| License Gates | AI entitlement / limits |

Полные паспорта ownership — в каталоге; эти таблицы — **IA манифеста**, подлежащая детализации в JSON Schema epic.

---

## Platform consumers of Manifests

| Consumer | Behavior |
|----------|----------|
| **Admin Settings Shell** | Compose navigation + forms from Manifests of **enabled** capabilities |
| **Export / Import / Backup / Clone** | Serialize values by Manifest `key` + owner |
| **License / Entitlement** | Filter Manifest entries by `license` / capability enablement |
| **Docs / Catalog** | Configures pointer → this Manifest |

---

## Relationship to Capability Passport

```text
Capability Passport          Settings Manifest
─────────────────            ─────────────────
Purpose                      General
Owns                         Integrations
Exposes / Consumes           Defaults
Events                       Policies
Forbidden / kind             Feature Flags
Data Ownership               License Gates
Configures ───────────────►  Validation Rules (+ all keys)
     (pointer only)
```

---

## History

- **2026-07-18** — introduced with **P-05** ([`ADR-029`](ADR-029-settings-contract.md)); operational half of capability configuration model.
- **2026-07-18** — Forms Sprint 1: concrete Manifest keys (builder default `false`; adapter contract ids).
