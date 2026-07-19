# Architecture Review Checklist (L0)

**Status:** canonical · **обязателен** перед каждым **ADR** и **PR** (modules / capabilities / settings / contracts)  
**L0 FROZEN:** [`L0-platform-architecture.md`](L0-platform-architecture.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)  
**Invariants:** [`architecture-invariants.md`](architecture-invariants.md)  

Без чеклиста — **не merge** / **не accept ADR**.

---

## Десять вопросов (+ invariants)

| # | Вопрос |
|---|--------|
| 1 | Кто **владелец** capability? |
| 2 | Не существует ли уже такая capability? |
| 3 | Через какой **Adapter** (и какой **Stable/Experimental/Internal**)? |
| 4 | Не нарушает ли **Boundary** / **Forbidden** / **Non-Goals**? |
| 5 | Не дублируются ли **настройки**? |
| 6 | Не нарушается ли **SoT**? |
| 7 | Какие **Events**? |
| 8 | Какие **Requires / Optional**? |
| 9 | Нужна ли новая **лицензия**? |
| 10 | Меняется ли **публичный контракт** (additive/deprecated/breaking)? |

**Инварианты:** изменение не делает ложным ни один **INV-01…16**.

---

## Приоритет принятия решений (обязателен)

См. [`decision-priority-rule.md`](decision-priority-rule.md) · **INV-16**.

1. L0 и фундаментальные принципы  
2. Канонические L1 / ADR и ownership  
3. Контракты между независимыми модулями  
4. Только затем локальная реализация и удобство  

**Reject без обсуждения «но оно работает»:** знание внутренностей чужого модуля · cross-package domain import · общий доменный SoT · скрытый fallback между destinations.

---

## Чекбоксы

- [ ] P-01…P-05 соблюдены  
- [ ] Non-Goals не расширены «тихо» в Owns  
- [ ] Exposes помечены Stable / Experimental / Internal  
- [ ] Experimental/Internal не единственная опора Business без плана  
- [ ] INV-09…12 (intake spine) если затрагивается intake  
- [ ] **INV-16** Decision Priority соблюдён (удобство не выше L0 / ownership / contracts)  
- [ ] ADR **ссылается** на P-01…P-05 / INV / Catalog — не дублирует L0  
- [ ] L0 freeze: нет правки конституции без RFC / `l0-errata`; нет «ещё одного маленького правила» в L0 под задачу модуля  
- [ ] Passport / Manifest / docs синхронизированы  
- [ ] Новый модуль/capability: полный шаблон (Passport, Exposes, Data Ownership, deps, license; Manifest если config)  
- [ ] **L1 delivery:** Passport → Manifest → **Public Contract** → Adapter → Contract Tests → **только потом** UI ([`capability-contract.md`](capability-contract.md))  
- [ ] Public Contract зафиксирован до merge Adapter; contract tests покрывают публичную цепочку  

---

## История

- 2026-07-18: L0 closure checklist.  
- 2026-07-18: Final seal — Non-Goals, stability, invariants.  
- 2026-07-18: Capability Contract sequence added (Phase 1).  
- 2026-07-19: INV-16 Decision Priority Rule + reject signals (Intake/Flights L0 correction).
