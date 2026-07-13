# Platform Backlog

**Status:** canonical (L2 — platform evolution queue).  
**Owner:** Platform + Product + Architecture.  
**Parent:** [`hostflow-operational-model.md`](../architecture/hostflow-operational-model.md), [`operational-model-adoption-register.md`](../architecture/operational-model-adoption-register.md).

**Назначение:** очередь **платформенных** изменений — не module features, не UX polish. Каждый item устраняет нарушение инварианта или закрывает platform capability gap, выявленный flow audit.

**Не дублирует:** module backlogs (`a3-requirements-workspace-backlog.md`, …), ADR (фиксируют решение после принятия), Adoption Register (журнал аудитов и surfaces).

**Граница слоя:** Platform Invariants принадлежат **Platform Layer**, не Onboarding, не Recruitment, не HR, не Fleet. Flow audit **обнаруживает** нарушение; **исправление** — платформа.

---

## 0. Что такое Platform Invariant

**Platform Invariant** — это **не** архитектурное правило и **не** UX-правило.

Это **гарантия, которую платформа даёт любому модулю.**

Модуль (Recruitment, HR, Fleet, …) определяет **смысл** следующего шага и передаёт кандидата в платформу:

```text
«Вот Next Action.»
```

Дальше ответственность **полностью** на платформе: публикация, проверки, маршрут, согласованность с policy — модуль **не** должен знать, как это устроено.

### Как появляются Platform Invariants

**Правило (freeze):**

> Новый платформенный инвариант появляется **только** когда его необходимость подтверждена **хотя бы одним воспроизводимым экспериментом** (flow audit по протоколу Adoption Register §4).

| Источник | Допускается как основание для PI? |
|----------|----------------------------------|
| Наблюдаемое поведение продукта (reproducible dead end, контрольный прогон) | ✅ |
| Flow audit с зафиксированным FAIL и root cause | ✅ |
| Архитектурная сессия, «полезная идея», предположение | ❌ |

**PI-1** — первый инвариант этого класса: обнаружен в Flow 1 (Onboarding), но **относится ко всей платформе**, не к onboarding.

---

## 1. PI-1 — Next Action Contract (Platform Layer)

Нарушение PI-1 = **баг платформы**, не «плохой экран onboarding» и не «баг Recruitment».

| ID | Scope | Источник |
|----|-------|----------|
| **PI-1** | **Platform Layer** — любой published Next Action (readiness snapshot, Status Rail, setup hub, workspace next-action block, …) | Flow 1 Re-Audit v4 — [`operational-model-adoption-register.md`](../architecture/operational-model-adoption-register.md) §4.6 |

PI-1 — **один** контракт, **две** части (не два отдельных инварианта):

| Part | Имя | Гарантия |
|------|-----|----------|
| **PI-1A** | **Reachability** | Можно **открыть место** выполнения действия (handler, access, no redirect, no lock). **Необходимо**, но **недостаточно**. |
| **PI-1B** | **Completeness** | Опубликованного Next Action **достаточно**, чтобы пользователь **завершил** следующий переход состояния **без скрытых обязательных действий** (Type 2 в протоколе audit). |

**v4 показал оба нарушения:**

| Наблюдение | Часть PI-1 |
|------------|------------|
| `/settings/funnels` опубликован, но redirect (activation lock) | **PI-1A** — Reachability |
| После клиента / вакансии пользователь не знает, как продолжить (нет return, Confidence «Нет») | **PI-1B** — Completeness |

### Формулировка контракта (верхний уровень)

> Платформа имеет право опубликовать Next Action **только** если может **гарантировать его успешное выполнение** до момента передачи управления **следующему состоянию системы**.

Reachability — лишь **часть** этой гарантии. Handler «достижим», но action **ложный** (недостаточен для перехода) — PI-1 **нарушен** (PI-1B).

### PI-1A — Reachability (вопросы перед публикацией)

| # | Вопрос |
|---|--------|
| 1 | Достижим ли `handler_ref` / target surface? |
| 2 | Есть ли у пользователя доступ (RBAC, module scope)? |
| 3 | Не будет ли redirect away от цели? |
| 4 | Не блокирует ли activation lock / route policy? |
| 5 | Существует ли целевой ресурс (entity, settings surface, capability)? |

Любой «нет» → этот candidate **не публикуется**.

### PI-1B — Completeness (вопросы перед публикацией)

| # | Вопрос |
|---|--------|
| 1 | Достаточно ли **одного** опубликованного action для gate / state transition? |
| 2 | Нет ли скрытых обязательных шагов (Type 2), не названных в action? |
| 3 | После выполнения пользователь понимает следующий шаг **без внешних знаний**? |

Любой «нет» → action **не публикуется** (или публикуется **другое**, более полное action — решение evaluator, не ослабление контракта).

### Acceptance (платформенный контракт — любой flow)

Для **каждого** опубликованного Next Action:

```text
1. опубликован
2. достижим          (PI-1A)
3. выполняется
4. изменяет состояние
5. публикует следующий Next Action
```

Slice B audit также проверяет **Completeness** (Confidence, Type 2) — это PI-1B. Повтор Flow 1 Re-Audit v4 — протокол **frozen**.

### Контракт публикации (интерфейс для реализации)

Платформа вводит **единую точку** публикации Next Action (не разрозненные handlers в модулях):

```text
Module / readiness engine  →  candidate NextAction
                                    ↓
                         Platform NextActionPublisher
                                    ↓
                    evaluate(Reachability)   ← slice phase 1
                    evaluate(Completeness)   ← slice phase 2+ (interface готов в phase 1)
                                    ↓
                         published NextAction | suppressed + fallback
```

**Правило реализации slice:** phase 1 реализует **только PI-1A**, но **интерфейс evaluator’ов** не должен мешать добавить PI-1B без смены архитектуры (избежать «PI-2», который окажется второй половиной PI-1).

**Механизм (после контракта):** allowlist, bypass, alternative handler — детали **под** Reachability evaluator, не первая задача slice.

---

## 2. Open platform slices

| Slice | Цель | Invariant | Статус | После merge |
|-------|------|-----------|--------|-------------|
| **Enforce Next Action Reachability** | Platform **NextActionPublisher** + PI-1A enforce-at-publish; интерфейс готов к PI-1B. | PI-1 (phase 1: 1A) | **open** | Повтор Flow 1 Re-Audit v4 — протокол без изменений |

**Имя slice** отражает **первую фазу** (1A). Цель slice — **PI-1 целиком**; Completeness — следующая фаза **в том же** контракте, не новый PI.

### Архитектура slice (сверху вниз)

**Шаг 1 — Контракт публикации:**

- `NextActionPublisher` (или эквивалент) — единая точка перед snapshot / rail / hub.
- `ReachabilityEvaluator` — обязателен в phase 1.
- `CompletenessEvaluator` — интерфейс + stub / no-op в phase 1; реализация — phase 2.

**Шаг 2 — Механизм:**

- Route policy, activation lock, RBAC, resource existence — внутри ReachabilityEvaluator.
- CI: **нет** published next action без passing PI-1A.

**Out of scope slice (phase 1):**

- Полная реализация PI-1B (может частично улучшиться как побочный эффект return-path UX — отдельный debt в Adoption Register §2).
- Переписывание Funnels UI; новый wizard; изменение G0–G8.
- Allowlist/guard **как первая задача** без publisher + evaluator contract.

---

## 3. Completed platform slices

| Slice | Closed | Notes |
|-------|--------|-------|
| Flow 1 FE-1 — setup readiness projection | 2026-07-03 | Backend snapshot + Setup Status UI — **consumer** будущего publisher |
| Flow 1 Slice A — entry point collapse | 2026-07-03 | Exposed PI-1A (publish without reachability check) |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-03 | PI-1 = Platform Layer contract; PI-1A Reachability + PI-1B Completeness; publisher/evaluator interface; slice phase 1 = 1A only |
| 2026-07-03 | PI-1 enforce-at-publish; slice Enforce Next Action Reachability; §0 experiment-first rule |
| 2026-07-03 | Initial backlog; PI-1 from v4 |
