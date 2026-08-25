# Architecture Invariants (L0 axioms)

**Status:** canonical · **L0 FROZEN** — [`L0-platform-architecture.md`](L0-platform-architecture.md)  
**Owner:** Architecture canon owner  

Это **не** ADR и не «желательные практики». Это аксиомы: утверждения, которые **никогда не могут стать ложными** без Architecture RFC, переписывающего конституцию.

Нарушение любого инварианта в коде или дизайне — **блокер** merge / ADR accept, наравне с P-01…P-05.

---

## Ownership & boundaries

| ID | Invariant |
|----|-----------|
| **INV-01** | У каждой capability ровно один SoT (функциональный owner). |
| **INV-02** | Каждая настройка платформы имеет ровно одного configuration owner. |
| **INV-03** | Capability публикует наружу только свои контракты (**Exposes**); чужие контракты не переиздаёт как свои. |
| **INV-04** | Business Module / Business Capability **не** владеет Platform или Infrastructure Capability. |
| **INV-05** | Внутренние модели, таблицы и форматы хранения **не** являются публичным API. |

## Interaction & composition

| ID | Invariant |
|----|-----------|
| **INV-06** | Межмодульное и внешнее взаимодействие — только через канонические adapters (**P-01**). |
| **INV-07** | Новая функциональность по умолчанию — композиция существующих capabilities (**P-03**), не вторая реализация. |
| **INV-08** | Settings публикуются только через Settings Contract владельца (**P-05**); техническая «свалка» settings не является SoT IA. |

## Intake spine

| ID | Invariant |
|----|-----------|
| **INV-09** | Routing выполняется **один раз** при создании нового Lead (continuation наследует context). |
| **INV-10** | Submission **неизменяем** в части происхождения / attribution (origin stamp); исправления — новым событием / correction path, не переписью origin. |
| **INV-11** | **Endpoint** никогда не принимает бизнес-решение (не создаёт Application/Inquiry/Employee как domain outcome). |
| **INV-12** | **Decision Layer** не принимает внешние запросы напрямую (только после Endpoint → Submission → Routing). |

## Stability & scope

| ID | Invariant |
|----|-----------|
| **INV-13** | Контракт с уровнем **Stable** не ломается без major + RFC/review по ADR-030 versioning. |
| **INV-14** | **Experimental** / **Internal** контракты не могут быть единственной опорой Business Capability без плана стабилизации. |
| **INV-15** | Passport **Non-Goals** не превращаются в Owns без Architecture RFC (расползание scope запрещено «тихо»). |

## Decision priority (accept / reject)

| ID | Invariant |
|----|-----------|
| **INV-16** | Локальное удобство, ускорение PR или «временное» упрощение **не** имеют приоритета над L0, модульной независимостью и утверждёнными границами. Порядок проверки: (1) L0 · (2) L1/ADR ownership · (3) межмодульные контракты · (4) локальная реализация. Решение с прямым знанием внутренностей другого модуля, cross-package domain import, общим доменным SoT или скрытым fallback между destinations — **архитектурно неверно**, даже если функционально работает. SoT: [`decision-priority-rule.md`](decision-priority-rule.md). |

## Outbound communication

| ID | Invariant |
|----|-----------|
| **INV-17** | Единственная допустимая точка входа в любую исходящую коммуникацию — **Communication Pipeline** (Thread Result Link → CommunicationContext → Module Policy → Template Metadata → transport). PR автоматически отклоняется, если: вызывает transport напрямую из business-модуля; самостоятельно определяет `module_owner`; выбирает template вне pipeline; пропускает Policy или Template Metadata Gate; использует Lead / `application_kind` / FormPurpose / иные legacy-признаки для определения коммуникации. SoT: [`../tasks/intake-communication-context-c5.md`](../tasks/intake-communication-context-c5.md). |

---

## How to use

1. Перед ADR/PR — сверить изменение с INV-01…17 ([`architecture-review-checklist.md`](architecture-review-checklist.md)).  
2. Если фича требует ложности инварианта — это не feature: это **L0 RFC**.  
3. Errata: опечатка в формулировке — `l0-errata`; смена смысла инварианта — полный RFC.

---

## History

- **2026-07-18** — приняты как финальный слой L0 перед полной заморозкой конституции.
- **2026-07-19** — **INV-16** Decision Priority Rule (после L0-коррекции Intake / Flights R3.5).
- **2026-07-19** — **INV-17** Communication Pipeline sole outbound entry (после C5 send-path migration).
