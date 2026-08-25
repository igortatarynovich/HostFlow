# ADR-029: Platform Rule P-05 — Settings Contract

## Status

**Accepted (platform principle).**  
**2026-07-18:** Пятое правило платформенного канона. Продолжение [`ADR-028`](ADR-028-configuration-ownership.md) (**P-04**): ownership конфигурации уже зафиксирован; **P-05** задаёт, *как* настройки **публикуются** и потребляются платформой.

> **Важно:** «Configuration Ownership» = **P-04** ([`ADR-028`](ADR-028-configuration-ownership.md)).  
> **P-05** — не второе имя P-04, а **Settings Contract**: единый контракт публикации манифеста настроек.

## Canonical statement

> **Platform Rule P-05 — Settings Contract**
>
> Каждая capability, у которой есть конфигурация, публикует её **только** через **Settings Contract** владельца (machine-readable **Settings Manifest**).  
> Другие модули **не** создают, **не** изменяют и **не** дублируют чужие настройки; UI, экспорт/импорт, бэкап и лицензирование читают **только** опубликованные манифесты.  
> Админ-интерфейс строится как **набор независимых конфигурационных пространств по capability**, а не как техническая свалка («SMTP», «Meta», «General»).

| Правило | Вопрос | Ответ |
|---------|--------|--------|
| **P-01** | Как вызывать поведение? | Standard Adapter (**Exposes**) |
| **P-02** | Кто владеет функциональностью? | Owner (**Owns**) |
| **P-03** | Как строить новое? | Композиция (**Consumes**) |
| **P-04** | Кто владеет конфигурацией? | Одна capability (**Configures**) |
| **P-05** | Как конфигурация **публикуется**? | Единый **Settings Contract** / Manifest |

## Context

Большинство продуктов организуют settings по **техническому** признаку (SMTP, Meta, Users, General). Это превращает админку в свалку и ломает ownership.

После P-04 у HostFlow есть ответ «кому принадлежит knob». Без P-05 knobs всё ещё могут жить разрозненными формами в SPA без контракта → ручной UI, нет единого export/import, лицензии не отключают settings surface автоматически.

Модель пользователя:

> Пользователь **не** настраивает «систему». Он настраивает **конкретную capability**.

Примеры пространств:

| Capability | Примеры настроек (пространство владельца) |
|------------|-------------------------------------------|
| **Forms** | Брендинг, язык по умолчанию, CAPTCHA, политика согласий, публичные URL, темы |
| **Documents** | OCR, хранилище, retention, автоудаление, e-sign |
| **Notifications** | Email, SMS, WhatsApp, Push, рабочие часы, Retry Policy |
| **AI** | Провайдер, модель, лимиты, Prompt Library, политики использования |

Связанные: ADR-005 (уровни хранения), ADR-028 (P-04 ownership), [`platform-capability-catalog.md`](platform-capability-catalog.md), [`capability-settings-manifest.md`](capability-settings-manifest.md).

## Decision

### 1. Два артефакта на capability

| Артефакт | Роль | Содержание |
|----------|------|------------|
| **Capability Passport** | Архитектурный документ | Purpose · Ownership (Owns) · Contracts (Exposes/Consumes) · Events · Boundaries (Forbidden / kind) · Data Ownership; **Configures** = краткий указатель на Manifest |
| **Settings Manifest** | Эксплуатационный документ / контракт | General · Integrations · Defaults · Policies · Feature Flags · License Gates · Validation Rules · restart/migration flags |

Passport **не** раздувается списками knobs. Детали knobs — только в Manifest (**P-05**).

### 2. Settings Contract (норматив)

Владелец **обязан** объявить для каждого published setting:

| Поле контракта | Смысл |
|----------------|--------|
| `key` / path | Стабильный идентификатор |
| `required` | Обязательность |
| `type` / `allowed_values` | Допустимые значения |
| `default` | Значение по умолчанию |
| `license` / entitlement | Какие лицензии / планы нужны |
| `restart_required` / `migration_required` | Побочные эффекты изменения |
| `scope` | Tenant / Company / Module (ADR-005) — **где хранится**, не кто владеет |
| `section` | General \| Integrations \| Defaults \| Policies \| Feature Flags \| … |

Формат манифеста — [`capability-settings-manifest.md`](capability-settings-manifest.md). Реализация (JSON Schema / registry API) — platform epic; **контракт и принцип** каноничны с этого ADR.

### 3. Правила

1. Нет Settings Contract → capability **не** может добавлять admin settings UI / storage knobs.  
2. Чужой Manifest **immutable** для других модулей (write только owner).  
3. Admin shell **композирует** UI из Manifests включённых capabilities (license off → Manifest не участвует).  
4. Export / import / backup / clone tenant config — только через Manifest keys владельцев.  
5. Technical dump pages («все SMTP в General») — **запрещены** как SoT UX; допустим только index/hub, ведущий в capability spaces.  
6. Business Capability Manifest содержит **только** свои domain settings (pipeline, tax, …), не infrastructure knobs.

### Что считается нарушением (блокер)

| # | Нарушение |
|---|-----------|
| 1 | Settings UI / storage без Manifest владельца |
| 2 | Дублирующий knob вне Settings Contract владельца |
| 3 | Модуль пишет в чужой Manifest / чужие keys |
| 4 | Техническая «свалка» settings как единственная модель IA |
| 5 | Лицензирование модуля не отключает его Manifest от shell |
| 6 | Раздувание Passport полным списком knobs вместо Manifest |

## Consequences

1. Фундамент admin UI HostFlow: **конфигурационные пространства по capability**.  
2. Автогенерация / schema-driven settings screens.  
3. Единый export/import/backup/clone конфигурации.  
4. Лицензирование естественно: выключенный модуль → Manifest не в shell.  
5. P-01…P-05 + Passport + Manifest = полная модель границ для поведения **и** админки.

## Relationship

| ADR | Роль |
|-----|------|
| [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) | Где хранится значение |
| [`ADR-028`](ADR-028-configuration-ownership.md) | **P-04** — кто владеет конфигурацией |
| **ADR-029 (этот)** | **P-05** — как конфигурация публикуется (Settings Contract) |
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | P-01 — adapters (аналог: Settings Contract ≈ «adapter для настроек») |

## References

[`capability-settings-manifest.md`](capability-settings-manifest.md) · [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`architecture-review-checklist.md`](architecture-review-checklist.md)

## История

- 2026-07-18: P-05 Settings Contract accepted; Passport vs Settings Manifest split; capability-scoped admin IA.
