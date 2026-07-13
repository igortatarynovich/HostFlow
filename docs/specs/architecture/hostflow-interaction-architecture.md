# HostFlow Interaction Architecture

**Status:** canonical (L1 architecture overview).  
**Owner:** Product + Platform UX + Architecture.

**Родительский принцип:** [`hostflow-operational-model.md`](hostflow-operational-model.md) — порядок решений; §0.1 — новые UX-паттерны только в operational model. **Evolution map (L2):** [`operational-model-adoption-register.md`](operational-model-adoption-register.md).

**Назначение:** Platform Standards (ADR-010, ADR-011, ADR-017, …) — **шаг 2** цепочки решений; не отправная точка архитектуры.

| ADR | Часть операционной модели | Вопрос |
|-----|---------------------------|--------|
| [`ADR-010`](ADR-010-unified-resource-list-shell.md) | **Коллекции** | Как **найти** запись? |
| [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) | **Компоненты** | Как элементы **выглядят и ведут себя**? |
| [`ADR-017`](ADR-017-workspace-layer.md) | **Рабочая сущность** | Как **композировать** sections, status, actions на экране записи? |

**Продуктовое поведение внутри Workspace** — [`people-lifecycle-workflow.md`](../workflows/people-lifecycle-workflow.md).  
**Настройка до первого контакта** — [`consumer-setup-flow-people-to-employee.md`](../workflows/consumer-setup-flow-people-to-employee.md).

---

## 1. Принцип

> **Один способ работы — разные модули и роли.**

Оператор видит HostFlow, не «Recruitment UI» vs «HR UI». Модули независимы в коде; **операционная модель** общая — см. [`hostflow-operational-model.md`](hostflow-operational-model.md) §1–§3.

---

## 2. Каноническая цепочка слоёв

```text
┌─────────────────────────────────────────────────────────────┐
│  User                                                        │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│  LIST LAYER (ADR-010)                                        │
│  Найти запись: таблица, фильтры, поиск, saved views          │
└───────────────────────────────┬─────────────────────────────┘
                                │ open record
┌───────────────────────────────▼─────────────────────────────┐
│  WORKSPACE LAYER (ADR-017) — контракты композиции записи           │
│  Sections · Status · Next action (на экране модуля, не новый Shell)│
└───────────────────────────────┬─────────────────────────────┘
                                │ consumes declarations
┌───────────────────────────────▼─────────────────────────────┐
│  MODULE CAPABILITIES                                         │
│  SectionDeclaration · ReadinessContribution · NextAction     │
│  Capability renderers (module-owned UI slots)                │
└───────────────────────────────┬─────────────────────────────┘
                                │ owns
┌───────────────────────────────▼─────────────────────────────┐
│  DOMAIN LOGIC & DATA (ADR-004 modules)                       │
│  Recruitment · HR · Fleet · Services · Finance               │
│  + Platform: Document Hub, Forms, Activity, Process Engine   │
└─────────────────────────────────────────────────────────────┘

         VISUAL LAYER (ADR-011) — сквозной: поведение и токены компонентов
```

**Направление зависимостей (жёстко):**

```text
Domain Logic  →  Module Capabilities  →  Workspace  →  List  →  User
                     (declaration)      (composition)

Workspace НЕ → Module domain services
Module НЕ → Workspace layout
```

---

## 3. Роль каждого слоя

### 3.1 List Layer (ADR-010)

**Когда:** пользователь работает с **множеством** однотипных записей.

**Примеры:** список кандидатов, лидов, сотрудников, вакансий, ТС.

**Ответственность:**

- единый List Shell (header, toolbar, table, pagination, bulk);
- List Definition per resource;
- переход **в** Workspace по клику на строку.

**Не отвечает за:** детальную работу с записью, readiness, domain gates.

### 3.2 Workspace Layer (ADR-017)

**Когда:** пользователь работает с **одной** записью в **своём** модуле (рекрутер — кандидат, HR — сотрудник, …).

**Продуктовое правило:** единый паттерн **информация → требования → состояние → действия** — не единый экран для всех ролей.

**Техническая реализация (platform):**

- `SectionDeclaration` → navigation / work area;
- `ReadinessContribution` → status (blockers, readiness);
- `NextActionDeclaration` → одно отображаемое действие;
- capability renderers на существующих экранах модулей.

**Два принципа (ADR-017 §1):**

1. Модули владеют данными и логикой; Workspace владеет **композицией паттерна**.
2. Workspace **не создаёт** бизнес-правил — только отображает capabilities модулей.

### 3.3 Module Capabilities

**Не отдельный продуктовый модуль ADR-004** — **паттерн публикации** возможностей модуля в Workspace.

| Артефакт | Кто владеет смыслом | Кто отображает |
|----------|---------------------|----------------|
| `SectionDeclaration` | Module | Workspace (navigation + mount) |
| `ReadinessContribution` | Module | Workspace Status rail |
| `NextActionDeclaration` | Module (решение) | Workspace (приоритет отображения) |
| Capability renderer | Module (UI slot) | Workspace (mount point) |

### 3.4 Domain Logic & Data

Модули ADR-004 + platform capabilities (Document Hub, Forms, Activity, Requirement Engine, …).

Вся **валидация, gates, handoff, billing** — здесь. API enforce — здесь. Workspace **никогда** не дублирует эти правила для «удобства UI».

---

## 4. Platform Readiness (сквозная capability)

**Readiness** — не фича Recruitment. Это **единый паттерн** «готовности к следующему шагу»:

| Модуль | Пример readiness question |
|--------|---------------------------|
| Recruitment | Требования закрыты? |
| HR | Данные и контракт подтверждены? |
| Fleet | Назначение выполнено? |
| Finance | Оплата получена? |
| Services | Заказ готов? |

Workspace Status **агрегирует** contributions. Семантика каждого blockers — **в модуле-источнике**.

---

## 5. Типичный путь оператора (по роли)

**Рекрутер** (только Recruitment):

```text
Candidates List → Candidate Card → requirements / documents / blockers / next action → handoff
```

**HR** (только HR, после handoff):

```text
Employees List → Employee Dossier → verification items / blockers / next action → employment
```

Один и тот же **паттерн**, разные экраны и модули. Рекрутер **не обязан** открывать HR UI.

**Platform path** (данные, не один пользователь):

```text
Candidate (Recruitment) → handoff event → WorkforceEmployee (HR)
```

Handoff передаёт документы и audit; UX каждого модуля остаётся **своим primary path**.

---

## 6. Расширение без переписывания

| Событие | Что меняется |
|---------|--------------|
| Подключён Fleet | + Fleet `SectionDeclaration` + Readiness; Recruitment без изменений |
| Mobile app | Новый Workspace **presenter**; declarations те же |
| Company Workspace | Новый `WorkspaceContextKey=company`; CRM module declarations |
| Новый раздел в Recruitment | +1 declaration; shell без изменений |

---

## 7. Анти-паттерны

| Анти-паттерн | Почему запрещён |
|--------------|-----------------|
| Бизнес-gate в Workspace shell | Нарушает ADR-017 §1 principle 2 |
| Workspace импортирует `handoff.py` / requirement engine | Обратная зависимость |
| Отдельная «карточка» на каждую сущность | Дублирование shell; drift ADR-011 |
| Next action вычисляется в Workspace по эвристикам | Доменная логика в UI |
| `CandidateWorkspace` class hierarchy | Entity coupling; не масштабируется на Vehicle/Company |

---

## 8. Чеклист для PR (interaction-level)

- [ ] Изменение в **списке** → соответствует ADR-010?
- [ ] Визуальные токены → ADR-011?
- [ ] Детальная работа с записью → declaration + context (ADR-017), не новая card?
- [ ] Readiness / next action → payload от модуля?
- [ ] Нет импорта domain services в Workspace composition layer?
- [ ] Поведение согласовано с `people-lifecycle-workflow`?

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-07-03 | Parent doc: hostflow-operational-model.md; ADR-010/011/017 as implementation parts |
| 2026-07-03 | Initial canon: List → Workspace → Capabilities → Domain |
