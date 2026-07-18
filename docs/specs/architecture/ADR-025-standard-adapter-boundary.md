# ADR-025: Platform Rule P-01 — Standard Adapter Boundary

## Status

**Accepted (platform principle).**  
**2026-07-18:** Сквозное **обязательное правило построения всей платформы HostFlow** — не договорённость по одному модулю. Все последующие ADR и все новые модули реализуются в соответствии с P-01.

## Canonical statement

> **Platform Rule P-01 — Standard Adapter Boundary**
>
> Любое взаимодействие между модулями платформы и любыми внешними системами допускается **только через стандартизированные (канонические) адаптеры**. Внутренние модели, схемы хранения и детали реализации **не** являются частью контракта и **не** могут использоваться другими модулями напрямую.

Коротко: **Standard Adapters Only** — и не «любой локальный wrapper», а **канонический платформенный контракт**.

Два взаимосвязанных уровня канона:

### 1. Поток данных (intake / domain spine)

```text
Endpoint → Submission → Routing → Decision → Business Entity
```

Каждый слой отвечает только за свой участок и **не** использует внутренности соседнего слоя ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)).

### 2. Граница взаимодействия (везде)

```text
Module A  →  Standard Adapter  →  Module B
```

или:

```text
Business Module  →  Provider Adapter  →  External System
```

**Прямой доступ в обход адаптера запрещён.**

- **Endpoint** задаёт универсальный **вход** в систему.  
- **P-01** задаёт универсальный **способ взаимодействия** между всеми частями системы.

## Context

Связанные: [`platform-architecture-principles.md`](platform-architecture-principles.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-007`](ADR-007-forms-platform-capability.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-012`](ADR-012-activity-notification-operating-layer.md), [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md), [`ADR-023`](ADR-023-recruitment-sales-module-separation.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md).

## Decision

### Правило

1. Межмодульные вызовы — **только** через опубликованный **канонический** Adapter / facade / API контракт capability.  
2. Внешние системы — **только** через Integration / Provider Adapter с единым стилем семейства контрактов.  
3. Прямой доступ к чужим таблицам, ORM-моделям, SDK провайдера, внутренним сервисам — **запрещён**.  
4. Замена реализации за адаптером **не** должна требовать переписывания потребителей.  
5. В тестах Adapter заменяется stub/mock; совместимость — **contract tests**.  
6. Изменение публичного контракта — **отдельный архитектурный review**.  
7. Новый адаптер **не** создаётся, если уже существует платформенный контракт того же назначения; дублирование контрактов в модулях — нарушение.

### Что считается нарушением архитектуры (блокер)

В code review / ADR review следующие пункты — **архитектурный блокер**:

| # | Нарушение |
|---|-----------|
| 1 | Прямой импорт внутренних сервисов другого модуля |
| 2 | Запрос к таблицам / SQL другого модуля |
| 3 | Использование ORM-моделей другого модуля |
| 4 | Зависимость от внутреннего формата хранения (JSON shape, column layout) другого модуля |
| 5 | Прямой вызов конкретного внешнего провайдера (SMTP, OpenAI SDK, Meta SDK, S3 client, …) из бизнес-модуля |
| 6 | Создание **локального** адаптера там, где уже есть **платформенный** контракт |
| 7 | Дублирование одинакового интеграционного контракта в разных модулях («свой» Notification / Document / Endpoint wrapper) |

Фраза «работаем через адаптеры» **недостаточна**: P-01 требует использование **канонического** контракта платформы, а не произвольных несовместимых обёрток.

### Порядок разработки нового взаимодействия

1. Определяется **владелец** capability.  
2. Определяется **публичный контракт**.  
3. Контракт оформляется как **канонический adapter interface**.  
4. Потребители зависят **только** от этого интерфейса.  
5. Реализация и провайдеры подключаются **за** границей модуля.  
6. Совместимость покрывается **contract tests**.  
7. Изменение контракта проходит **отдельный архитектурный review**.

Пока Forms / Documents / Notifications / AI не готовы, потребляющий модуль работает против стабильного контракта с **тестовым адаптером**. Реальная реализация подключается без переделки бизнес-логики.

### Важное ограничение: не микросервис ради микросервиса

P-01 регулирует **архитектурную границу**, а не способ физического вызова.

- Адаптер **может** быть локальным Python / TypeScript-интерфейсом внутри **modular monolith**.  
- Позже тот же контракт **можно** реализовать через HTTP, очередь или отдельный сервис.  
- Не каждый внутренний вызов нужно превращать в сетевой API.

Независимость модулей сохраняется **без** преждевременного усложнения инфраструктуры.

### Примеры канонических адаптеров

| Adapter | Consumer | Provider скрывает |
|---------|----------|-------------------|
| **Endpoint Adapter** | Acquisition / Intake | Form Builder, versions, consents, Meta internals |
| **Document Adapter** | Recruitment / HR / Fleet / … | S3, OCR, file versions, storage |
| **Notification Adapter** | Any module | SMTP, SMS, WhatsApp, Push, Telegram |
| **Automation Adapter** | Any module | прямые вызовы чужой бизнес-логики |
| **AI Adapter** | Any module | OpenAI, Azure, Anthropic, local LLM |
| **Integration Adapters** | Platform | Meta / SMS / WhatsApp / TikTok / Google / … credentials & SDK |

Частный случай Forms / Acquisition:

```text
Forms → Endpoint Adapter → Submission → Universal Routing
```

Acquisition не знает хранение формы, publish, version, consents — только типовой Submission ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)).

### Обязательный шаблон каждого модуля / capability

У каждого платформенного или бизнес-модуля в ADR / module-scope **явно** фиксируются:

| Раздел | Содержание |
|--------|------------|
| **Ownership** | Какие данные и capability принадлежат модулю |
| **Public contracts** | Какие канонические адаптеры он **предоставляет** |
| **Required contracts** | Какие канонические адаптеры он **потребляет** |
| **Events** | Какие доменные события публикует и принимает |
| **Forbidden dependencies** | К каким внутренностям других модулей обращаться нельзя |
| **Contract tests** | Как проверяется совместимость публичного контракта |
| **Versioning policy** | Как изменяется публичный контракт (breaking / additive / review) |

Новые ADR **должны** включать эти разделы (или явную ссылку на заполненный module-scope). Отсутствие публичного контракта при межмодульном доступе — нарушение P-01.

## Consequences

1. P-01 — правило для **всех** последующих ADR и модулей, не только Forms / Acquisition.  
2. Модули независимы; реализацию за адаптером можно менять без каскада.  
3. Новый канал / провайдер = новый adapter за **существующим** или **зарегистрированным** каноническим контрактом.  
4. Тестирование: swap → mock / fake adapter + contract tests.  
5. Нарушения из таблицы blockers — стоп в review наравне с SoT ownership.  
6. Endpoint + P-01 вместе: универсальный вход **и** универсальный способ взаимодействия.  
7. Владелец capability и запрет дублей — **P-02** ([`ADR-026`](ADR-026-capability-ownership.md)).

## Relationship to other ADRs

| ADR | Связь с P-01 |
|-----|----------------|
| [`ADR-007`](ADR-007-forms-platform-capability.md) | Forms SoT; consumers → Endpoint / Forms adapters |
| [`ADR-009`](ADR-009-document-hub-platform-layer.md) | Document Adapter |
| [`ADR-012`](ADR-012-activity-notification-operating-layer.md) | Notification / Activity adapters |
| [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) | Integration adapters |
| [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) | Automation Adapter |
| [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) | Endpoint spine; Endpoint Adapter |
| [`ADR-026`](ADR-026-capability-ownership.md) | **P-02** — кто владеет capability (SoT / Owns) |
| [`ADR-027`](ADR-027-capability-composition.md) | **P-03** — как строить новое (композиция / Consumes) |
| [`ADR-028`](ADR-028-configuration-ownership.md) | **P-04** — кто владеет конфигурацией (Configures) |

## References

[`platform-architecture-principles.md`](platform-architecture-principles.md) · ADR-006 · ADR-007 · ADR-009 · ADR-012 · ADR-019 · ADR-023 · ADR-024

## История

- 2026-07-18: P-01 accepted.  
- 2026-07-18: Strengthened — blockers table; canonical (not ad-hoc) adapters; development order; modular-monolith local adapters OK; mandatory module contract template; P-01 governs all future ADRs/modules.  
- 2026-07-18: Paired with **P-02** ([`ADR-026`](ADR-026-capability-ownership.md)) and **P-03** ([`ADR-027`](ADR-027-capability-composition.md)); platform canon milestone.
- 2026-07-18: Linked **P-04** ([`ADR-028`](ADR-028-configuration-ownership.md)); Exposes axis of Capability Passport.
