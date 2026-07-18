# ADR-026: Platform Rule P-02 — Capability Ownership

## Status

**Accepted (platform principle).**  
**2026-07-18:** Сквозное правило платформы HostFlow. Логическое продолжение [`ADR-025`](ADR-025-standard-adapter-boundary.md) (P-01). Вместе P-01 + P-02 задают канон: **как** взаимодействовать и **к кому** обращаться.

## Canonical statement

> **Platform Rule P-02 — Capability Ownership**
>
> Каждая платформенная capability имеет **единственного владельца** (Single Source of Truth).  
> Нельзя иметь две реализации одной и той же capability.  
> Если модулю нужна эта возможность, он обязан использовать **публичный контракт владельца** (через адаптер по P-01).

| Правило | Вопрос | Ответ |
|---------|--------|--------|
| **P-01** | Как взаимодействовать? | Только через **канонический** Standard Adapter |
| **P-02** | К кому обращаться? | Только к **владельцу** capability |
| **P-03** | Как строить новое? | **Композицией** существующих capabilities ([`ADR-027`](ADR-027-capability-composition.md)) |

Сочетание P-01 + P-02 практически исключает дублирующие реализации и удерживает архитектуру чистой.

**Capability Boundary (обязательное уточнение P-02):** одного имени владельца недостаточно. У каждой capability в [`platform-capability-catalog.md`](platform-capability-catalog.md) зафиксирован состав **Owned / Forbidden / Settings / Data / Contracts / Events**. Review дополнительно спрашивает: *не пытается ли модуль забрать чужую ответственность?*

## Context: platform of capabilities

HostFlow проектируется не как «набор хороших модулей», а как **платформа capabilities**: фундаментальные возможности, которые **переиспользуют** любые бизнес-модули.

| Platform Capability | Владелец (SoT) | Типичные потребители |
|---------------------|----------------|----------------------|
| **Endpoint** | Intake / Acquisition boundary ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) | Acquisition, Forms (HostFlow Form is-a Endpoint), API, Mobile, Meta, … |
| **Submission** (universal intake record) | Shared Intake (ADR-021/022/024) | Recruitment, Sales, HR, Services, … |
| **Forms** (builder, version, consent, form surface) | Forms Core Platform Module ([`ADR-007`](ADR-007-forms-platform-capability.md)) | Все модули |
| **Documents** | Document Hub ([`ADR-009`](ADR-009-document-hub-platform-layer.md)) | Recruitment, HR, Fleet, Finance, … |
| **Notifications** | Activity & Notification layer ([`ADR-012`](ADR-012-activity-notification-operating-layer.md)) | Все модули |
| **Automations** | Automations capability ([`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md)) | Все модули |
| **AI** | AI platform capability (через AI Adapter, P-01) | Все модули |
| **Search** | Global Search capability | Все модули |
| **Activity** | Activity & Notification layer (ADR-012) | Все модули |
| **Acquisition / Campaigns** | Acquisition ([`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)) | Growth / demand flow; не владеет Result objects |

**Каталог границ (SoT):** [`platform-capability-catalog.md`](platform-capability-catalog.md) — passport 1–8 на capability.  
**Индекс владельцев:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1.  
**Forms vs Submission:** Forms владеет form surface + consent pinning; universal Submission object — Shared Intake (не второй Form Builder).

Бизнес-модули (Recruitment, Sales, HR, Fleet, Finance) **владеют** своими domain entities и **композируют** platform capabilities (**P-03**, [`ADR-027`](ADR-027-capability-composition.md)) — не копируют их.

Связанные: [`platform-architecture-principles.md`](platform-architecture-principles.md), [`ADR-025`](ADR-025-standard-adapter-boundary.md), ADR-004, ADR-006, ADR-007, ADR-009, ADR-012, ADR-019, ADR-023, ADR-024.

## Decision

### Правило

1. У каждой platform capability — **один** владелец SoT (модуль / shared capability / bounded context).  
2. Вторая реализация той же capability в другом модуле — **запрещена**.  
3. Потребление — только через **Public contracts** владельца + **Standard Adapter** (P-01).  
4. Бизнес-модуль **не** создаёт «свой» Form Builder, Document store, Notification SMTP-стек, Search index, AI client, Endpoint pipeline.  
5. Реестр capabilities: индекс §0.1 + **полный passport** в [`platform-capability-catalog.md`](platform-capability-catalog.md); новый capability = ADR + owner + public contracts (шаблон ADR-025) + passport 1–8 **до** кода.  
6. Споры о ownership / границах Owned vs Forbidden разрешаются архитектурным review до кода.  
7. Модуль не расширяет чужой **Capability Boundary** «для удобства» — только compose через Public Contracts.

### Примеры (SoT)

| Capability | Единственный владелец | Нельзя |
|------------|----------------------|--------|
| Forms (Builder, Version, Consent, Form Submission surface) | Forms | Recruitment «своя анкета» / Sales «своя форма» |
| Documents | Document Hub | Локальные file tables в модулях как второй SoT |
| Notifications (delivery) | Notifications / Operating Layer | Прямой SMTP/SMS из Recruitment |
| Search (index & query) | Search | Модульный полнотекст вместо платформенного |
| Activity (audit / operational history surface) | Activity layer | Параллельные «истории» без контракта |
| AI (LLM interaction) | AI capability | Прямой SDK в бизнес-коде |
| Endpoint (точка входа) | Endpoint / Intake model | Второй intake pipeline в модуле |
| Campaign / Attribution / Routing Context | Acquisition | Campaign SoT внутри Recruitment |

### Что считается нарушением (блокер)

| # | Нарушение |
|---|-----------|
| 1 | Вторая реализация capability, у которой уже есть владелец |
| 2 | Модуль объявляет «локальный SoT» для Documents / Forms / Notifications / Search / AI / Endpoint |
| 3 | Потребление capability в обход владельца (даже через «свой» адаптер — см. P-01 § локальный vs канонический) |
| 4 | ADR / feature без явного Ownership для затрагиваемой capability |
| 5 | Бизнес-модуль хранит канонические данные чужой capability «для удобства» как второй SoT |
| 6 | Реализация ответственности из **Forbidden** паспорта чужой или своей capability |
| 7 | Отсутствие / устаревание passport в Platform Capability Catalog при новой capability surface |

P-02 **не** запрещает кэш / проекции / read models **явно** помеченные как derived (не SoT), если владелец и invalidation определены в контракте.

### Связь с шаблоном модуля (ADR-025)

В разделе **Ownership** каждого модуля:

- перечислить capabilities, которыми модуль **владеет**;  
- перечислить capabilities, которые **только потребляет** (Required contracts);  
- запретить владение чужими capabilities в **Forbidden dependencies**.

## Consequences

1. Мышление сдвигается: проектируем **capabilities платформы**, затем бизнес-модули на них.  
2. P-01 + P-02 = нет дублирующих стеков и нет прямых внутренних зависимостей.  
3. Новые каналы / LLM / storage подключаются у **владельца** capability, не размазываются по модулям.  
4. Code review: вторая Forms/Documents/Notifications реализация — блокер наравне с нарушением P-01.  
5. Catalog capabilities обновляется при каждом новом platform epic (`platform-capability-catalog.md` + §0.1 index).  
6. Capability Boundary делает P-02 проверяемым в каждом PR.

## Relationship

| ADR | Роль |
|-----|------|
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | **Как** вызывать (adapter) |
| **ADR-026 (этот)** | **Кого** вызывать (owner SoT) + **что** ему принадлежит (Boundary via catalog) |
| [`ADR-027`](ADR-027-capability-composition.md) | **Как** строить новое (compose) |
| ADR-007 / 009 / 012 / 019 / 024 | Конкретные owners |

## References

[`platform-capability-catalog.md`](platform-capability-catalog.md) · [`platform-architecture-principles.md`](platform-architecture-principles.md) · ADR-004 · ADR-006 · ADR-007 · ADR-009 · ADR-012 · ADR-019 · ADR-023 · ADR-024 · ADR-025 · ADR-027

## История

- 2026-07-18: P-02 Capability Ownership accepted; HostFlow as platform of capabilities; pairs with P-01.
- 2026-07-18: Capability Boundary + Platform Capability Catalog (passports) — P-02 operationalized.
