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

**Инварианты:** изменение не делает ложным ни один **INV-01…15**.

---

## Чекбоксы

- [ ] P-01…P-05 соблюдены  
- [ ] Non-Goals не расширены «тихо» в Owns  
- [ ] Exposes помечены Stable / Experimental / Internal  
- [ ] Experimental/Internal не единственная опора Business без плана  
- [ ] INV-09…12 (intake spine) если затрагивается intake  
- [ ] L0 freeze: нет правки конституции без RFC / `l0-errata`  
- [ ] Passport / Manifest / docs синхронизированы  

---

## История

- 2026-07-18: L0 closure checklist.  
- 2026-07-18: Final seal — Non-Goals, stability, invariants.
