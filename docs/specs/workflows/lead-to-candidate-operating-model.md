# HostFlow — Canonical Lead → Candidate Operating Model (Current Architecture)

**Назначение:** единая продуктово-операционная модель: **Lead → Candidate → Handoff → Workforce**, без смешения assignment, stage, ownership и duplicate state. Основа для карт процессов, спецификаций и задач (в т.ч. агенту).

**Связанные документы:** [lead-intake-conversion-flow-audit.md](lead-intake-conversion-flow-audit.md) (аудит реализации vs doctrine: стабильное / долги / срезы), [ADR-013-public-intake-strategy.md](../architecture/ADR-013-public-intake-strategy.md) (публичный intake: Lead-first vs Candidate-first — **Proposed**), [recruitment-domain-model.md](../architecture/recruitment-domain-model.md) (**полная нарративная модель** Lead / Candidate / Application / conversion / примеры — без кода), [lead-conversion-contract.md](lead-conversion-contract.md) (матрица состояний, действий и payload `candidate_created`), [lead_to_candidate.md](lead_to_candidate.md), [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) (**Intake Decision Workspace**, intake resolution vs candidate ops, vacancy confirm, activity continuity на convert), [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md), [handoff-contract.md](../architecture/handoff-contract.md), [applications-operating-model.md](../architecture/applications-operating-model.md) (канон: Application как intent layer), [application-creation-mvp.md](application-creation-mvp.md) (MVP: миграция, создание, duplicate, тесты), [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) (enum / transitions / idempotency Application), [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md) (сверка веток, C1–C4), [slice-4-activity-continuity-guards.md](slice-4-activity-continuity-guards.md) (continuity первого контакта на Candidate, не lifecycle Application), [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md), [person-identity-layer-and-roadmap.md](../architecture/person-identity-layer-and-roadmap.md) (guardrail: Person отложен), [lead-types.md](../lead-types.md), [modules/candidates.md](../modules/candidates.md), [modules/vacancies.md](../modules/vacancies.md), [hr/ADR-001-workforce-employee-vs-app-user.md](../../hr/ADR-001-workforce-employee-vs-app-user.md).

---

## 1. Главный принцип

**Lead ≠ Candidate ≠ WorkforceEmployee** — это разные operational сущности.

| Сущность | Роль |
|----------|------|
| **Lead** | Входящий **сигнал интереса** (intake). |
| **Candidate** | Рабочая **recruitment**-сущность. |
| **WorkforceEmployee** | **Employment / HR**-сущность (после материализации из recruitment). |

**Сейчас:** `Lead → Candidate → WorkforceEmployee` **без** отдельного слоя **Person**. Person намеренно отложен; каноническая формулировка и фазы — [person-identity-layer-and-roadmap.md](../architecture/person-identity-layer-and-roadmap.md) и §13.

### Семантические границы (spec до UI)

Их нельзя размывать в экранах и API — иначе растут костыли и потеря **operational trust** (рекрутер обходит CRM).

| Граница | Смысл |
|--------|--------|
| **ignore duplicate** | ≠ **reject lead** ≠ **close lead** — только «не к suggested candidate»; см. §8. |
| **assignment** | ≠ **pipeline stage** — см. §5. |
| **handoff / ownership** | ≠ **visibility** — см. §10–§11, [handoff-contract.md](../architecture/handoff-contract.md). |
| **Candidate** | ≠ **Application** — в MVP частично слито; канон и миграция: [applications-operating-model.md](../architecture/applications-operating-model.md). |
| **duplicate resolution** | ≠ **merge** — решение + audit + override; не merge studio / fuzzy identity (§8). |

**Operational events** (`lead.duplicate_review_required`, `lead.duplicate_decision`, `candidate.duplicate_lead_intake` и т.д.) — **first-class**: не «логи ради логов», а основа timelines, SLA, автоматизаций, inbox, аналитики и KPI — см. §8.

**Порядок продуктовой зрелости:** operational meaning → ownership / handoff semantics → audit & event model → **затем** UI (для duplicate: ultra-fast, queue-oriented, decision-first — не страница сравнения людей).

---

## 2. Canonical Entity Roles

### LEAD

**Что это:** intake signal, входящий интерес, источник контакта.

**Что хранит (концептуально):**

- source, campaign, external ids;
- intake metadata;
- consent / RODO;
- queue state;
- assignment state (отдельно от stage);
- duplicate state;
- initial vacancy context.

**Lead не является «человеком».** Один человек может создать много lead, много applications, несколько recruitment cycles.

### CANDIDATE

**Что это:** recruitment operational entity.

**Что хранит:**

- pipeline **stage**;
- recruiter ownership;
- vacancy relation;
- recruitment lifecycle;
- qualification state;
- recruitment tasks;
- document workflow;
- handoff readiness.

**Сейчас** Candidate — **identity anchor** и recruitment object; в будущем identity может быть вынесена в Person (§13).

### WORKFORCE EMPLOYEE

**Что это:** HR / employment operational entity.

**Что хранит:**

- employment state;
- HR ownership;
- contracts, payroll, ZUS, leaves;
- employment lifecycle.

**Recruitment ownership здесь заканчивается.**

---

## 3. Источники Lead

| Источник | Поведение (канон) |
|----------|-------------------|
| **Meta Lead Ads** | Auto intake; lead / candidate draft по политике |
| **Website Form** | Lead + vacancy context |
| **Telegram Bot** | Lead draft; document intake |
| **WhatsApp** | В основном manual |
| **Manual Recruiter Entry** | Прямое создание lead/candidate |
| **Import** | Импорт в candidate pool / batch |
| **Referral** | Lead с referrer |
| **Reactivation** | Существующий candidate + new application |
| **Employer/Client Source** | Кандидат из внешнего employer-источника |

*Флаги в БД/API (draft vs сразу candidate) задаются политикой источника и режимом §4.*

---

## 4. Processing Modes

### MANUAL

Рекрутер: создаёт lead/candidate, выбирает vacancy, назначает owner, запускает процесс.

**Когда:** WhatsApp, phone leads, old candidates, edge cases.

### SEMI-AUTO

Система: создаёт lead, проверяет duplicate, предлагает recruiter и vacancy, ставит в queue, показывает next action.

Рекрутер подтверждает: assignment, vacancy, conversion, document request.

**Это основной MVP mode.**

### AUTO

Система: создаёт candidate, назначает recruiter и vacancy, ставит stage, first contact, reminders/tasks.

**Только если:** source trusted, vacancy mapped, recruiter available, consent valid, duplicate clear (в смысле §8).

---

## 5. Assignment State

**Assignment ≠ Recruitment Stage** — это критично.

| State | Смысл |
|-------|--------|
| **unassigned** | Нет recruiter; lead в queue |
| **assigned** | Система назначила recruiter |
| **claimed** | Рекрутер сам взял lead |

Assignment **не** влияет на pipeline stage кандидата.

---

## 6. Vacancy Matching

| Режим | Условие |
|-------|---------|
| **DIRECT** | Lead с job page, mapped campaign, public vacancy form → vacancy автоматически |
| **SUGGESTED** | Система предлагает по category, route, language, citizenship, salary, location, experience → рекрутер подтверждает |
| **MANUAL** | Рекрутер выбирает вручную |
| **NO VACANCY** | Pool / waiting_for_match / talent_pool; task «find matching vacancy» |

**Vacancy vs route (transport):** vacancy = потребность в человеке; route/job config может быть частью vacancy. Кто создаёт vacancy/route — по RBAC (manager, recruiter с правом, employer, admin); без route/details — **draft vacancy**. Подробнее: [modules/vacancies.md](../modules/vacancies.md).

---

## 7. Candidate Pool Philosophy

Кандидат **без вакансии ≠ мусор** — это **talent asset**.

Pool, если: сильный кандидат, нет подходящей vacancy сейчас, рынок может запросить позже, рекрутер хочет сохранить контакт.

Система поддерживает: reminders, tags, desired route, desired salary, follow-up dates.

---

## 8. Duplicate Resolution MVP

Duplicate Resolution — **отдельный operational slice**.

### Уровни

1. **exact**
2. **probable**
3. **none**

### EXACT DUPLICATE

Совпадение: email, operational phone, passport, tachograph (по правилам продукта).

Тогда:

- новый **Candidate** не создаётся;
- фиксируется trail к **existing** candidate: lead intake / application / source / vacancy interest / contact (см. реализацию ниже).

### PROBABLE DUPLICATE

Например: same name, partial phone, transliteration mismatch.

Тогда: lead → **`duplicate_review`** queue; решение вручную: merge later / create new / ignore.

### HR PROTECTION

Если candidate: already workforce, active blocking handoff, HR-owned materialization — рекрутер **не** может тихо получить второго кандидата; lead → **`duplicate_review`**.

### Реализация MVP (код)

Модуль: [`duplicate_resolution.py`](../../../backend/app/modules/leads/duplicate_resolution.py) · вызовы: [`_processing.py`](../../../backend/app/modules/leads/service/_processing.py), [`_reroute.py`](../../../backend/app/modules/leads/service/_reroute.py).

| Уровень | Поведение |
|---------|-----------|
| **exact**, нет HR-блокеров | `Lead.status = duplicated`, `candidate_id`; `Candidate.origin.lead_duplicate_intakes_v1`; события `lead.duplicate_matched_exact`, `candidate.duplicate_lead_intake` |
| **exact** + HR-блокер (workforce по candidate, handoff `pending_review` / `accepted`) | `duplicate_review`, `DUPLICATE_REVIEW_HR_PROTECTED`, `normalized.duplicate_match_v1`, `lead.duplicate_review_required` |
| **probable** | `duplicate_review`, `DUPLICATE_REVIEW_PROBABLE`, тот же `duplicate_match_v1` |

### Семантика решений `duplicate_review` (MVP)

**Ignore duplicate** ≠ **reject lead** ≠ **close lead**.

- **Ignore** означает только: *не прикреплять этот lead к suggested candidate*; конфликт дубликата снят с точки зрения матча; lead возвращается в **routing** (`needs_routing`), чтобы оператор мог продолжить intake / `POST /process` без потери контекста. Это operationally безопаснее, чем сразу переводить lead в терминальный статус («пропал лид», «кто закрыл?», необработанный кандидат).
- **Attach to existing** — явная привязка к существующему candidate + trail intake + audit.
- **Create new** — suggested candidate в override; новый candidate при последующей обработке; audit + persistent `duplicate_override_v1` (переживает re-process).

Отдельные статусы вроде `duplicate_ignored` / `discarded` / terminal «closed по дубликату» — **не** вводим на этом этаже (premature complexity). При необходимости — после стабилизации Applications и очередей.

### События и audit (foundation)

Решения и вехи дубликата должны оставаться **событийно-аудируемыми** (например `lead.duplicate_decision`, `lead.duplicate_review_required`, `candidate.duplicate_lead_intake`) — это база для аналитики, SLA, автоматизаций, inbox / activity feed и operational timeline, а не только для строки в таблице лидов.

### MVP UI (duplicate review)

Минимум на карточке лида: badge уровня дубликата, suggested candidate, reasons, индикатор HR blocker, последнее решение и короткая decision history; действия: **Attach to existing**, **Create new candidate**, **Ignore duplicate**. Без merge studio, diff engine, AI compare, тяжёлых side-by-side modal — UX должен быть **быстрым** (минуты не тратим на один duplicate).

**Вне scope:** auto-merge, AI matching, тяжёлый fuzzy, graph identity.

---

## 9. Lead → Candidate Conversion Rules

**Минимум:**

- контакт или имя;
- **owner_company_id** (канон поля компании-владельца);
- source;
- duplicate conflict разрешён или в очереди (§8);
- consent обработан;
- assignment state или queue определены;
- intake path определён (vacancy / pool / manual review).

**Можно** создать candidate без vacancy. **Нельзя** без owner_company_id.

---

## 10. Recruitment Pipelines

### LEAD INTAKE FUNNEL

- new  
- duplicate_check  
- assigned / unassigned  
- first_contact_pending  
- contacted  
- no_answer  
- converted  
- **duplicate_review**  
- rejected  

### RECRUITMENT FUNNEL

- new_candidate  
- contact_established  
- qualification  
- documents_requested  
- documents_received  
- qualified  
- ready_for_handoff  
- ready_for_hr  
- rejected  
- talent_pool  

### HANDOFF / POST-RECRUITMENT

- internal_hr_handoff  
- client_handoff  
- waiting_for_feedback  
- returned_to_recruitment  
- hired  
- rejected_by_hr  

Детали ownership: [handoff-contract.md](../architecture/handoff-contract.md).

---

## 11. Ownership Model

| Состояние | Owner |
|-----------|--------|
| Lead **unassigned** | Recruitment queue, supervisor, manager |
| Lead **assigned** | Recruiter |
| Qualified **Candidate** | Recruiter |
| **Ready for HR** | Recruitment → HR |
| **Client handoff** | Shared или employer-controlled |
| **Returned to recruitment** | Ownership обратно recruitment |

---

## 12. Current Canonical Architecture

**CURRENT:**

```text
Lead → Duplicate Resolution → Candidate → Handoff → WorkforceEmployee
```

**FUTURE (optional):**

```text
Person
  ├── Leads
  ├── Applications
  ├── Candidate Cycles
  ├── Workforce Records
  └── Documents
```

Person **сейчас не обязателен**.

---

## 13. Почему Person пока отложен

**Person identity layer is intentionally deferred.** Current MVP uses **Candidate** as the operational identity anchor. **Person** may be introduced later after **Applications**, **Rehire flows**, and the **ownership model** are stable.

Подробнее (что такое Person, что не класть в него, фазы до внедрения, сигналы «пора», явные non-goals): [person-identity-layer-and-roadmap.md](../architecture/person-identity-layer-and-roadmap.md).

Кратко:

- лишняя сложность для MVP;
- migration overhead;
- потеря скорости.

Текущей модели достаточно для MVP.

Person понадобится при: rehire, multi-application на уровне экосистемы, shared ecosystems, multi-agency, cross-company identity, advanced analytics.

---

## 14. Canonical Rules (инварианты)

1. **Lead intake** не зависит от availability рекрутера в момент входа.  
2. **Assignment** не равен pipeline **stage**.  
3. **Vacancy match** не обязателен для сохранения candidate (pool / talent asset).  
4. **Duplicate handling** не должен silently создавать второй кандидат там, где это ломает HR / handoff.  
5. **Candidate без vacancy** = talent pool asset.  
6. **Handoff** = переход operational ownership.  
7. **Recruitment lifecycle ≠ HR lifecycle.**  
8. **Identity** (в перспективе Person) не должна смешиваться с recruitment process.

---

## Первый практический контур внедрения (напоминание)

1. Lead source mapping  
2. Vacancy mapping  
3. Duplicate check (§8)  
4. Auto-assign / unassigned queue  
5. Manual claim  
6. Convert / confirm Candidate (explicit в semi-auto)  
7. No vacancy → candidate pool  
8. Ready for HR / handoff  

---

## AI Agent Notes

- Проектировать отдельные оси: **assignment**, **duplicate**, **pipeline stage**, **handoff ownership**.  
- Автоконверсия в Candidate: §9 + режим §4 + §8.  
- События и границы модулей: [operational-event-boundaries.md](../architecture/operational-event-boundaries.md), [workflows/index.md](index.md).
