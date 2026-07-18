# ADR-028: Platform Rule P-04 — Configuration Ownership

## Status

**Accepted (platform principle).**  
**2026-07-18:** Четвёртое правило платформенного канона. Логическое продолжение [`ADR-026`](ADR-026-capability-ownership.md) (P-02): функциональность и **конфигурация** — разные оси владения.

## Canonical statement

> **Platform Rule P-04 — Configuration Ownership**
>
> Каждая настройка платформы принадлежит **ровно одной** capability.  
> Настройки **не** дублируются и **не** переопределяются другими модулями как второй SoT конфигурации.  
> Модуль может **читать эффекты** чужой конфигурации только через Public Contracts / resolved views владельца — не хранить «свою копию SMTP / OCR / LLM» как authoritative config.

| Правило | Вопрос | Ответ |
|---------|--------|--------|
| **P-01** | Как взаимодействовать? | Канонический Standard Adapter |
| **P-02** | Кто владеет **функциональностью**? | Единственный owner capability (SoT) |
| **P-03** | Как строить новое? | Композиция существующих capabilities |
| **P-04** | Кто владеет **конфигурацией**? | Ровно одна capability — раздел **Configures** в паспорте |

P-02 и P-04 различаются:

| | P-02 | P-04 |
|---|------|------|
| Объект | Capability / поведение / SoT данных | Settings / provider bindings / policy knobs |
| Пример | Notifications владеет delivery | SMTP / SMS / Retry / Quiet Hours — только у Notifications |
| Нарушение | Второй Form Builder в Recruitment | SMTP-поля в Recruitment settings |

## Context

Без P-04 раздел Settings размазывается: SMTP в Recruitment, OCR engine в HR, LLM keys в Sales. Это тот же класс дрейфа, что вторая реализация capability, но для **конфигурации**.

В [`platform-capability-catalog.md`](platform-capability-catalog.md) каждая capability имеет четыре независимые границы:

1. **Owns** — функциональный SoT  
2. **Configures** — конфигурационный SoT (**этот ADR**)  
3. **Exposes** — контракты наружу (P-01)  
4. **Consumes** — что композирует (P-03)

Связанные: ADR-005 (иерархия Tenant → Company → Module Settings — **уровни хранения**, не смена владельца), ADR-025…027, catalog passports.

## Decision

### Правило

1. Каждая настройка имеет **ровно одного** configuration owner = capability, в чьём паспорте она в **Configures**.  
2. Добавление настройки в чужой модуль / чужой Configures — **запрещено**.  
3. Business Capability **не** владеет infrastructure/platform config (SMTP, OCR engine, LLM provider, Meta App, …) — только **Consumes** эффекты через adapters.  
4. ADR-005 уровни (Tenant / Company / Module) описывают **где лежит значение**, не **кто владеет семантикой**. Семантика — у capability-owner.  
5. Resolved/effective config для UI других модулей — **derived view** от владельца, помеченный как non-SoT.  
6. Новый knob → обновить **Configures** паспорта владельца в том же PR.

### Примеры (configuration SoT)

| Setting / binding | Owner (Configures) | Нельзя |
|-------------------|-------------------|--------|
| SMTP / SMS / Push / Retry / Quiet Hours / notification templates | **Notifications** | Recruitment «свои» SMTP |
| OCR Engine / e-sign provider binding / retention defaults | **Documents** | HR «свой» OCR SoT |
| Default language / CAPTCHA / consent defaults / form branding | **Forms** | Sales «свой» consent config SoT |
| LLM Provider / model allowlist | **AI** | Модульный API-key SoT |
| Meta App / connector credentials patterns | **Integrations** | Прямые app secrets в Recruitment |
| Endpoint Publishing (HostFlow Form) | **Forms** | Acquisition как SoT form publish config |
| Campaign windows / source defaults | **Acquisition** | Recruitment campaign SMTP |

### Что считается нарушением (блокер)

| # | Нарушение |
|---|-----------|
| 1 | Одна и та же настройка как authoritative в двух capabilities |
| 2 | Business module добавляет infrastructure/platform knobs в свои Module Settings как SoT |
| 3 | «Переопределение» чужого Configures локальным settings blob без контракта владельца |
| 4 | Новая настройка без строки в **Configures** паспорта |
| 5 | Provider SDK config (SMTP, LLM, Meta) в бизнес-модуле в обход владельца |

P-04 **не** запрещает:

- UX, который **открывает** settings владельца (deep link / embedded panel, данные всё ещё у owner);  
- module-owned **domain** settings (pipeline stages Recruitment, tax rules Finance) — они в Configures **этой** Business Capability;  
- tenant/company overrides **внутри** schema владельца (ADR-005).

## Consequences

1. Settings становятся частью архитектурного контракта, не «полями в админке».  
2. Review: «SMTP в Recruitment?» → смотри Configures Notifications → блокер.  
3. P-01…P-04 + Catalog Passport = модель проектирования без размывания ответственности.  
4. Миграции legacy settings → к владельцу Configures (platform epic, не тихий drift).

## Relationship

| ADR | Роль |
|-----|------|
| [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) | Где хранится значение (Tenant/Company/Module) |
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | P-01 — как вызывать |
| [`ADR-026`](ADR-026-capability-ownership.md) | P-02 — кто владеет функциональностью |
| [`ADR-027`](ADR-027-capability-composition.md) | P-03 — как композировать |
| **ADR-028 (этот)** | P-04 — кто владеет конфигурацией |
| [`platform-capability-catalog.md`](platform-capability-catalog.md) | Configures в каждом passport |

## References

[`platform-architecture-principles.md`](platform-architecture-principles.md) · [`architecture-review-checklist.md`](architecture-review-checklist.md) · ADR-005 · ADR-007 · ADR-009 · ADR-012 · ADR-006

## История

- 2026-07-18: P-04 Configuration Ownership accepted; pairs with Capability Passport (Owns / Configures / Exposes / Consumes).
