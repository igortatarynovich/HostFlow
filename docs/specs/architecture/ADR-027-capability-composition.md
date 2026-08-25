# ADR-027: Platform Rule P-03 — Capability Composition

## Status

**Accepted (platform principle).**  
**2026-07-18:** Третье правило платформенного канона. Вместе с [`ADR-025`](ADR-025-standard-adapter-boundary.md) (P-01) и [`ADR-026`](ADR-026-capability-ownership.md) (P-02) образует фундамент архитектуры HostFlow.

## Canonical statement

> **Platform Rule P-03 — Capability Composition**
>
> Новая функциональность создаётся **композицией существующих capabilities**.  
> Создание новой capability допускается **только** когда существующие платформенные возможности не могут решить задачу **без нарушения** Ownership (P-02) или Adapter Boundary (P-01).

| Правило | Вопрос | Ответ |
|---------|--------|--------|
| **P-01** | Как взаимодействовать? | Через **канонические** Standard Adapters |
| **P-02** | К кому обращаться? | Только к **владельцу** capability |
| **P-03** | Как строить новую функциональность? | **Композицией** существующих capabilities, не дубликатами |
| **P-04** | Кто владеет конфигурацией? | Ровно одна capability — **Configures** ([`ADR-028`](ADR-028-configuration-ownership.md)) |

Три вопроса перед реализацией любого модуля / фичи:

1. Использует ли только стандартные адаптеры?  
2. Обращается ли только к владельцам соответствующих capabilities?  
3. Не создаёт ли новую capability там, где уже есть подходящая?

Если на все три — «да», модуль почти наверняка вписывается в платформу. Если хотя бы на один — «нет» → архитектурный review **до** кода.

## Context

После фиксации Endpoint spine и P-01/P-02 естественный следующий запрет: бизнес-модуль не «достраивает» Forms / Documents / Notifications / AI / Search / Automations локально «потому что быстрее». Он **композирует** владельцев.

Пример: Recruitment **не** реализует собственные формы, документы, уведомления, AI, поиск, автоматизации — он их **композирует**.

Связанные: [`platform-architecture-principles.md`](platform-architecture-principles.md), [`architecture-review-checklist.md`](architecture-review-checklist.md), ADR-007, ADR-009, ADR-012, ADR-019, ADR-024, ADR-025, ADR-026.

## Decision

### Правило

1. Default path: compose existing capabilities via their Public contracts.  
2. Новая capability = ADR + Owner (P-02) + Public contracts (P-01 template) + Catalog entry.  
3. «У нас уже почти есть X, сделаем свой X' в модуле» — **запрещено**, если X уже в [`platform-capability-catalog.md`](platform-capability-catalog.md).  
4. Допустимы **тонкие domain facades** в бизнес-модуле, которые **только** оркестрируют чужие adapters (не второй SoT).  
5. Review checklist: [`architecture-review-checklist.md`](architecture-review-checklist.md).  
6. Перед новой capability — сверить **Capability Boundary** (Owned/Forbidden) в каталоге; расширение чужой границы запрещено.

### Когда новая capability допустима

- Нет существующей capability, покрывающей ответственность; **или**  
- Расширение существующей нарушило бы P-02 (смешение SoT); **или**  
- Нужен новый класс cross-cutting concern (новый owner в catalog).

В этих случаях: ADR → Catalog → Owner → Contracts → затем код.

### Что считается нарушением (блокер)

| # | Нарушение |
|---|-----------|
| 1 | Бизнес-модуль реализует Forms / Documents / Notifications / AI / Search / Automations / Endpoint «для себя» |
| 2 | Новая capability без ADR + Catalog + Owner |
| 3 | Оркестрация, которая копирует storage / delivery логику владельца вместо adapter |
| 4 | Feature PR без ответа на три вопроса P-01/P-02/P-03 |

## Consequences

1. Product design начинается с **composition map**, не с greenfield stack.  
2. Platform epics (Forms, AI, …) разблокируют все модули сразу.  
3. Review: «можно ли собрать из существующего?» — первый вопрос.  
4. P-01…P-04 + Catalog Passport = фундамент канона HostFlow.

## References

ADR-025 · ADR-026 · ADR-028 · [`platform-capability-catalog.md`](platform-capability-catalog.md) · [`architecture-review-checklist.md`](architecture-review-checklist.md)

## История

- 2026-07-18: P-03 Capability Composition accepted.
- 2026-07-18: Aligned with P-04 and Consumes boundary.
