# Recruitment: цели, порядок работ и requirements-driven flow

**Status:** canonical operating order — **обязателен для чтения в любой ветке** (Lead, Candidate, Handoff, Forms, Requirements).  
**Hierarchy:** L2 workflow canon.  
**Owner:** Product + Recruitment module + Platform (Requirement Rules).

**Назначение:** зафиксировать **продуктовую цель**, **правильный порядок этапов** и **кто решает, что обязательно** — чтобы контекст не терялся между ветками и PR.

**Связанные документы (не дублировать, а следовать):**

| Документ | Роль |
|----------|------|
| [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) | Границы сущностей Lead / Candidate / Employee |
| [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) | Intake Decision Workspace, срезы 2–6 |
| [recruitment-document-collection-handoff.md](recruitment-document-collection-handoff.md) | Requirements → Evidence → handoff |
| [requirement-rules-engine-p0.md](../platform/requirement-rules-engine-p0.md) | Кто объявляет правила, кто оценивает |
| [requirement-evidence-model-p0.md](../platform/requirement-evidence-model-p0.md) | 4 сущности: Requirement / Accepted Evidence / Candidate Evidence / Document |
| [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md) | Контур Recruitment → Document Hub → HR |
| [hr-handoff-runtime-p0.md](../architecture/hr-handoff-runtime-p0.md) | Следующий architecture gate для employee pipeline после handoff |
| [PR17-candidate-to-employee-handoff-spec.md](../../PR17-candidate-to-employee-handoff-spec.md) | Обогащение employee card при передаче |

---

## 1. Продуктовая цель (одна формулировка)

**Рекрутер ведёт человека по цепочке решений и закрываемых требований** — не по «карточке со статусами и виджетами».

Система **сама формирует список того, что нужно сделать** (получить документ, внести данные, позвонить, написать, подтвердить квалификацию), **оценивает выполнение** и **блокирует переход** (в кандидата, на handoff, в HR), пока обязательное не закрыто.

Handoff **работает технически**, но **не является целью сам по себе**: передача в HR допустима только когда recruitment **доказал выполнение требований** и экспортирует **`requirement_fulfillments[]`**, а не «снимок карточки как есть».

---

## 2. Каноническая цепочка (порядок не переставлять)

```text
[1] LEAD — intake / triage / RODO / fit / contact / reject | convert
         ↓ (только после положительного intake-решения)
[2] CANDIDATE — requirements fulfillment (данные + документы + операционные действия)
         ↓ (только когда readiness / transfer gates зелёные)
[3] HANDOFF — явная передача в HR (CandidateHandoff → accept)
         ↓
[4] HR EMPLOYEE — верификация, доработка, employment lifecycle
```

**Жёсткие неравенства:**

| Запрещено | Почему |
|-----------|--------|
| Lead = мини-Candidate | Смешивает intake и recruitment ops |
| Candidate card = главный UI для требований | Требования — отдельный operational слой, карточка — контекст |
| Handoff до закрытия обязательных requirements | HR получает мусор и дублирует работу рекрутёра |
| Рекрутер вручную «составляет список документов» | Список выводится из правил (§5) |
| Обязательность в Form Presentation (P10A) | Только UX формы; бизнес-обязательность — Requirement Rules Engine |

---

## 3. Этап 1 — Lead (ревью лида)

**Вопрос этапа:** подходит ли сигнал и что делать дальше?

**Правильный порядок операций на Lead:**

| Шаг | Действие | Примечание |
|-----|----------|------------|
| L1 | Получить лид (канал: Meta, форма, CSV, …) | Ingest → нормализация |
| L2 | Отправить **RODO** (art. 14) | Gate до process / request_info / contacted — см. intake spec §8.0.1 |
| L3 | **Оценить** fit (гражданство, опыт, маршрут, вакансия-hint) | Qualification summary — read-only, Slice 3 |
| L4 | При необходимости — **связаться** с лидом | Звонок / сообщение — **Activity**, не статус |
| L5 | **Решение:** отклонить **или** перевести в Candidate | Intake decision rail — Slice 2 |

**На Lead не доминируют:** стадия пайплайна кандидата, тяжёлый dossier, checklist документов водителя, handoff, HR-поля.

**Критерий готовности этапа:** Intake Resolution MVP стабилен (срезы 4–6), Lead detail = **Intake Decision Workspace**.

---

## 4. Этап 2 — Candidate (довести до соответствия требованиям)

**Вопрос этапа:** выполнены ли все **применимые** требования для этой вакансии / профиля / контекста?

### 4.1 Что может быть требованием

Требование — **атом работы**, который система отслеживает и закрывает. Не «поле на карточке».

| Тип | Примеры | Закрытие |
|-----|---------|----------|
| **Данные** | Контакты, адрес, PESEL, паспортные поля, опыт работы | Заполнение канонических полей (Field Registry) |
| **Документ** | Паспорт, права с категорией, Code 95, медкомиссия, психотесты, chip card | Document Instance + Candidate Evidence |
| **Документ + данные** | Виза / karta pobytu / decyzja wojewody — файл **и** извлечённые поля | Evidence variant + extraction + approve |
| **Операционное действие** | Позвонить, написать, запросить документ | Activity с типом и SLA; не дублировать fake tasks |

### 4.2 Типовой набор для driver CE (Польша) — иллюстрация, не жёсткий список

Конкретный набор **всегда** резолвится правилами (§5), а не хардкодом в UI:

- контактные данные, адрес;
- паспортные данные;
- опыт работы;
- PESEL (если applicable);
- основание пребывания (другая страна — другие evidence variants);
- decyzja wojewody (если applicable);
- квалификация: права с категорией, Code 95, психотесты, результат медкомиссии, chip card;
- все документы **получены и проверены** (recruitment approve на Candidate Evidence);
- все обязательные **поля** внесены.

### 4.3 Как должен выглядеть UX (целевой)

| Правильно | Неправильно (текущий долг) |
|-----------|----------------------------|
| **Requirements workspace** / checklist — первичный рабочий экран | Требования «навешаны» поверх Candidate card |
| Прогресс = % закрытых requirements + blockers | Прогресс = стадия воронки без связи с данными |
| Переход стадии / handoff **заблокирован** engine с понятной причиной | Рекрутер двигает стадию «как раньше» |
| Один звонок на Lead **переносится** на Candidate (continuity) | Дублирующиеся call tasks после convert |

**Критерий готовности этапа:** рекрутер открывает Candidate и видит **что закрыть**, а не «где кликнуть на карточке»; `transfer-readiness` / package readiness опираются на Requirement Engine, не на legacy validators.

---

## 5. Кто и как решает, что обязательно

**Единый ответ:** обязательность определяет **Requirement Rules Engine** из **зарегистрированных источников правил**. Не рекрутер, не произвольный JSON в карточке, не Form Builder.

### 5.1 Источники правил (порядок слияния)

```text
Field Registry (канон полей)
        ↓
Entity Profile (базовый состав: поля, document_pack, process_profile)
        ↓
+ Document Pack (какие типы документов в пакете)
+ Process Profile (что нужно для стадии / handoff)
+ Vacancy binding (профиль вакансии → entity_profile_code, страна, категория)
+ Tenant override (ослабление / дополнение — с аудитом)
        ↓
Requirement Engine → applicable requirements[]
        ↓
Recruiter checklist + blockers + readiness
```

Подробно: [requirement-rules-engine-p0.md](../platform/requirement-rules-engine-p0.md) §4–§5.

### 5.2 Матрица «кто что настраивает»

| Роль / артефакт | Что решает | Пример |
|-----------------|------------|--------|
| **Platform seed** | Каталог Requirement, Accepted Evidence variants | `legal_stay_confirmation`, `driving_qualification` |
| **Entity Profile** | Базовый профиль кандидата для роли | `recruitment.candidate.driver_ce` |
| **Document Pack** | Набор документов для профиля | `recruitment.driver_ce_documents` |
| **Process Profile** | Требования по стадиям / к handoff | enter `ready_for_handoff` |
| **Vacancy** | Привязка вакансии к профилю + контекст (страна, категория) | Вакансия PL driver CE vs DE driver CE |
| **Tenant admin** | Override (waive / доп. пакет) | Клиент требует extra medical |
| **Рекрутер** | **Закрывает** требования, **не объявляет** их | Выбор evidence variant, upload, approve |
| **Form Builder (P10A)** | Только видимость полей на **публичной форме** | show/hide — **не** бизнес-обязательность |
| **HR** | Верификация после handoff, не переопределение recruitment catalog | HR review на том же `document_id` |

### 5.3 Разные вакансии и страны

Один и тот же человек — разные **наборы applicable requirements**:

- **Vacancy** → `entity_profile_code` + route/country modifiers;
- **Citizenship / work country** → eligibility (например legal stay);
- **Role / position category** → driver pack vs office pack.

Рекрутер видит **уже отфильтрованный** checklist. Смена вакансии может **пересчитать** requirements (policy gap **I1** — см. application lifecycle sync note).

---

## 6. Этап 3 — Handoff (передача в HR)

**Вопрос этапа:** можно ли передать **доказанный** пакет в кадры?

**Предусловия (все обязательны):**

1. Обязательные recruitment requirements **satisfied** (данные + evidence + operational, где applicable).
2. `transfer-readiness` / recruitment package **без blockers** от Requirement Engine.
3. Явное действие: **`CandidateHandoff`** `destination=internal_hr` → HR **accept**.
4. В snapshot уходит **`requirement_fulfillments[]`**, не угадывание по типам файлов ([ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md)).

**Текущий долг (честно):**

| Проблема | Статус | Следующий шаг |
|----------|--------|---------------|
| Handoff materializes employee, но без `meta.employee_pipeline` | OPEN | [hr-handoff-runtime-p0.md](../architecture/hr-handoff-runtime-p0.md) |
| Employee card не полностью заполнена из candidate | Partial | PR17 |
| Handoff возможен до идеального requirements closure | Риск в UX/enforcement | Усилить PE gates + UI blockers |

Handoff **не чинить в отрыве** от requirements: сначала честные gates на Candidate, потом runtime pipeline на HR.

---

## 7. Этап 4 — HR (сотрудник)

HR **не собирает заново** то, что recruitment уже закрыл:

- читает `requirement_fulfillments[]` и linked documents;
- верифицирует / дополняет в своём контуре;
- ведёт employment lifecycle (отдельный module scope).

Экспорт = **структурированные fulfillments + ссылки на Document Hub**, не копирование файлов.

---

## 8. Три направления разработки — цели и очередь

Использовать как **шапку ветки** (copy в описание PR / задачи агенту).

### Направление A — Lead + Candidate flow (приоритет продукта сейчас)

**Цель:** правильный порядок Lead → Candidate и **requirements как primary workflow**, не overlay на карточке.

| # | Работа | Зависимости |
|---|--------|-------------|
| A1 | Slice 4 — activity continuity (Lead → Candidate) | Intake 2–3 done | **Done (2026-07-02)** |
| A2 | Slice 6 — Lead workspace = intake decision first | A1 желательно | **Done (2026-07-02)** |
| A3 | Requirements workspace UX (checklist-first на Candidate) | Requirement Engine API — **backlog:** [a3-requirements-workspace-backlog.md](../tasks/a3-requirements-workspace-backlog.md) | **Done (2026-07-01)** |
| A4 | Закрыть gaps: stage/handoff gates ← engine blockers | A3 | **Done (2026-07-01)** |
| A5 | ADR-013 + выравнивание public intake | После A2 стабилизации | **Done (2026-07-02)** |
| A6 | Application lifecycle I1 / C2b / C3 | После A4 | **Done (2026-07-02)** |

### Направление B — Handoff + Employee flow

**Цель:** handoff **после** requirements; employee **в воронке HR** с полным контекстом.

| # | Работа | Зависимости |
|---|--------|-------------|
| B1 | Усилить handoff gates (не пускать без package readiness) | A4 |
| B2 | HR Handoff Runtime P0 — `meta.employee_pipeline` | B1 |
| B3 | PR17 — mapping fields + documents на employee card | B2 |
| B4 | Phase 1 manual stand sign-off | B3 |

### Направление C — Form Constructor

**Цель:** intake формы питают **Lead**, поля из Entity Profile; не второй движок требований.

| # | Работа | Зависимости |
|---|--------|-------------|
| C1 | ADR-013 (связка public form → Lead-first) | A5 | **Done (2026-07-02)** |
| C2 | Bridge removal: deprecate `CandidateProfile.config` | C1 | **Done (2026-07-02)** |
| C3 | Mapping / smoke для новых профилей (страна, роль) | Entity Profile seeds | **Done (2026-07-02)** |
| C4 | ADR-007 universal Forms platform | После C2 closure |

### Рекомендуемая последовательность спринтов

```text
Спринт 1–2:  A1 + A2 + A3 (intake стабилен + requirements workspace)
Спринт 3:    A4 + B1 (gates: нельзя handoff без closure)
Спринт 4:    B2 + B3 (handoff runtime + employee card)
Параллельно: C1 после ADR-013 decision
```

**Не начинать раньше времени:** Person layer, Telegram intake, universal Forms platform, cross-product Activities mega-engine.

---

## 9. AS-IS vs TO-BE (для веток)

| Область | AS-IS (сейчас) | TO-BE (цель) |
|---------|----------------|--------------|
| Lead | Intake 2–3 готовы; UI ещё перегружен | Intake Decision Workspace |
| Candidate requirements | Engine v1 есть; UI буквальный, на карточке | Checklist-first requirements workspace |
| Operational actions | Частично Activities; fake tasks после convert | Continuity + typed requirements |
| Handoff | E2E работает; pipeline gap; слабая связь с gates | Только после readiness; fulfillments + pipeline |
| Кто решает обязательность | Задокументировано в engine; не везде enforced в UI | Все transitions читают engine |
| Forms | P6–P10A для intake; dual-stack | **Lead-first** для Form Constructor; legacy candidate reuse только без lead form |

---

## 10. Контекст для ветки (шаблон)

При открытии ветки вставить в PR / задачу:

```markdown
## Operating context
Canon: docs/specs/workflows/recruitment-operational-goals-and-order.md

Направление: A | B | C
Этап цепочки: Lead | Candidate | Handoff | HR
Не нарушать: Lead ≠ Candidate; requirements ≠ card overlay; handoff после closure

Критерий done: [конкретный пункт из §8 таблицы]
Связанные спеки: [ссылки]
```

---

## 11. Anti-patterns (блокировать в review)

1. Новые обязательные поля только в `CandidateProfile.config` без Field Registry + Requirement rule.
2. Новый «виджет на карточке» вместо requirement / activity.
3. Handoff или stage PATCH без проверки Requirement Engine.
4. Дублирование списка документов в frontend.
5. P10A `required_if` для бизнес-правил (work permit, medical, …).
6. Копирование документов при handoff.
7. Превращение Lead detail в candidate pipeline UI.

---

## 12. Метрики успеха

- Время от Lead до convert (intake decision).
- % кандидатов с handoff **без** HR rework из-за missing data.
- Доля stage transitions, заблокированных engine (ожидаемо растёт — это здоровье системы).
- Среднее число fake / duplicate activities на convert (должно → 0).
- Все handoff snapshots содержат валидный `requirement_fulfillments[]`.

---

*Документ обновлять при смене порядка этапов или при закрытии architecture gate. Любой PR, меняющий Lead/Candidate/Handoff flow, должен ссылаться на этот файл.*
