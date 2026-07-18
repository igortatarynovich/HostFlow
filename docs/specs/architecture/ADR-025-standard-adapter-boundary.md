# ADR-025: Platform Rule P-01 — Standard Adapter Boundary

## Status

**Accepted (platform principle).**  
**2026-07-18:** Введён как **сквозной платформенный принцип** HostFlow. Применяется ко всем модулям, shared capabilities и внешним системам — не только к Forms / Acquisition.

## Canonical statement

> **Platform Rule P-01 — Standard Adapter Boundary**
>
> Любое взаимодействие между модулями платформы и любыми внешними системами допускается **только через стандартизированные адаптеры**. Внутренние модели, схемы хранения и детали реализации **не** являются частью контракта и **не** могут использоваться другими модулями напрямую.

Коротко: **Standard Adapters Only.**

```text
Consumer Module / Capability
        ↓
   Typed Adapter (public contract)
        ↓
Provider Module / External System
```

Ни один модуль не должен знать внутреннюю реализацию другого. Он работает только через **публичный контракт (Adapter)**.

## Context

По мере выделения Forms как Core Platform Module и Endpoint как intake-абстракции ([`ADR-007`](ADR-007-forms-platform-capability.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) стало ясно: то же правило должно действовать для Documents, Notifications, Automations, AI, Integrations и всех будущих каналов. Иначе каждый контур снова изобретёт прямой доступ к SQL, SMTP, S3 или чужим ORM-моделям.

Связанные: [`platform-architecture-principles.md`](platform-architecture-principles.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-012`](ADR-012-activity-notification-operating-layer.md), [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md), [`ADR-023`](ADR-023-recruitment-sales-module-separation.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md).

## Decision

### Правило

1. Межмодульные вызовы — **только** через опубликованный Adapter / facade / API контракт capability.  
2. Внешние системы (Meta, SMS, WhatsApp, LLM, storage, SMTP, …) — **только** через Integration / Provider Adapter с единым стилем контракта.  
3. Прямой доступ к чужим таблицам, внутренним моделям, SDK провайдера или «тихому» SQL из другого bounded context — **запрещён**.  
4. Замена реализации за адаптером (OpenAI → Azure, S3 → другой store, SMTP → ESP) **не** должна требовать переписывания бизнес-модулей.  
5. В тестах Adapter заменяется stub/mock — бизнес-логика тестируется без реальных провайдеров.

### Примеры адаптеров

| Adapter | Consumer работает с | Provider скрывает |
|---------|---------------------|-------------------|
| **Endpoint Adapter** | `Endpoint → Submission` | Form Builder, версии, publish, consents, Meta internals |
| **Document Adapter** | create/link/require/review document | S3, OCR, file versions, storage layout |
| **Notification Adapter** | «notify actor / channel intent» | SMTP, SMS, WhatsApp, Push, Telegram |
| **Automation Adapter** | emit/subscribe events, schedule rules | прямые вызовы бизнес-логики модулей |
| **AI Adapter** | prompt / structured task | OpenAI, Azure, Anthropic, local LLM |
| **Integration Adapters** | Meta / SMS / WhatsApp / TikTok / Google / … | credentials, provider SDK quirks |

Каждый внешний сервис реализует **один и тот же класс контракта** своего семейства (например все messaging adapters — единый Notification/Messaging shape).

### Forms / Acquisition (частный случай P-01)

```text
Forms  →  Endpoint Adapter  →  Submission  →  Universal Routing
```

Acquisition **не знает**: где хранится форма, как опубликована, какая версия, какие согласия. Получает типовой **Submission**.

Это частный случай P-01; Endpoint Model ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) подчиняется этому правилу.

### Documents

```text
Recruitment (или HR / Fleet / …)  →  Document Adapter  →  Documents Module
```

Модуль не знает S3 / OCR / версии хранения.

### Notifications

```text
Any module  →  Notification Adapter  →  Notifications capability
```

Каналы (Email, SMS, WhatsApp, Push, Telegram) выбирает Notifications, не caller.

### Automations

```text
Any module  →  Automation Adapter  →  Automations
```

Automations не вызывают внутренние сервисы модулей в обход их adapters.

### AI

```text
Any module  →  AI Adapter  →  LLM Provider
```

Смена провайдера без каскада по бизнес-коду.

### Integrations

```text
Platform  →  Meta Adapter / SMS Adapter / WhatsApp Adapter / …
```

Единый стиль; новый канал = новый adapter type в registry, не fork потребителя.

## Anti-patterns (запрещено)

- Recruitment читает таблицы Forms / Documents напрямую.  
- Acquisition импортирует Form Builder models или пишет в `tenant_lead_forms` как SoT владельца.  
- Модуль шлёт SMTP/SMS сам, минуя Notification Adapter.  
- Automation rule вызывает private service function другого модуля.  
- Бизнес-код знает имя LLM SDK или bucket path.

## Consequences

1. Модули **независимы**; внутреннюю реализацию можно менять без каскада.  
2. Новые реализации (каналы, провайдеры, storage) добавляются **адаптером**, не переписыванием callers.  
3. Тестирование упрощается (swap adapter → mock).  
4. Единый стиль интеграции по всей платформе.  
5. Endpoint / Forms / Documents / Notifications / AI / Integrations подчиняются **одному** правилу.  
6. Нарушение P-01 в code review — блокер наравне с cross-module SoT ownership.

## Relationship to other ADRs

| ADR | Как связан с P-01 |
|-----|-------------------|
| [`ADR-007`](ADR-007-forms-platform-capability.md) | Forms SoT; consumers → Endpoint / Forms via adapters |
| [`ADR-009`](ADR-009-document-hub-platform-layer.md) | Document Adapter boundary |
| [`ADR-012`](ADR-012-activity-notification-operating-layer.md) | Notification / Activity adapters |
| [`ADR-006`](ADR-006-marketplace-and-integration-platform.md) | Integration adapters + marketplace apps |
| [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) | Automation Adapter / entitlement |
| [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) | Endpoint Adapter; `Endpoint → Submission → Routing → Decision → Business Entity` |

## References

[`platform-architecture-principles.md`](platform-architecture-principles.md) · ADR-006 · ADR-007 · ADR-009 · ADR-012 · ADR-019 · ADR-023 · ADR-024

## История

- 2026-07-18: **P-01 Standard Adapter Boundary** accepted as platform-wide principle (Standard Adapters Only).
