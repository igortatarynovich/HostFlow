

# Workflows — Overview

Этот документ является обзором всех бизнес-процессов (workflow) в системе HostFlow. Он связывает модули, события и автоматизации, описанные в отдельных спецификациях.

---

## Цель
Собрать в одном месте краткое описание всех рабочих процессов, чтобы можно было быстро понять, как движутся данные и как взаимодействуют модули системы.

---

## Список Workflow-документов

| Документ | Назначение | Основные сущности | Автоматизация |
|-----------|-------------|-------------------|----------------|
| [**adr022-phase2-sales-only-capability-flow.md**](adr022-phase2-sales-only-capability-flow.md) | **ADR-022 Phase 2 / F3-B-10:** Sales-only spine SalesInquiry → Flights → Capability → Review → Convert → Traceability; contracts; fail-closed; no shared wizard | SalesInquiry, Flights destination, ClientAccount | Flights dispatch; Sales convert (next PR) |
| [**recruitment-operational-goals-and-order.md**](recruitment-operational-goals-and-order.md) | **Hub:** цели, порядок этапов Lead → Candidate → Handoff → HR; requirements-driven flow; кто решает обязательность; очередь работ по трём направлениям | Lead, Candidate, Requirement, Handoff, WorkforceEmployee | Requirement Engine gates; читать **в любой ветке** |
| [a3-requirements-workspace-backlog.md](../tasks/a3-requirements-workspace-backlog.md) | **A3 backlog:** экраны, API bundle, срезы PR, acceptance по типам требований | Candidate, Requirement, CandidateEvidence | Workspace route + evidence flow |
| [document_expiry.md](document_expiry.md) | Срок действия как свойство Document Hub; reminders в Activity layer | Document Hub, Document Link, Catalog `document.expired` | Evaluation на public resolve; Hub не владеет reminder table |
| [reminders.md](reminders.md) | Подсистема напоминаний и уведомлений | Reminder, Candidate, Document | Cron-задачи, уведомления, RLS |
| [reminders_matrix.md](reminders_matrix.md) | SLA и эскалации напоминаний | Reminder, Notification | Каналы доставки, дедупликация |
| [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) | Семантика жизненного цикла **Application** (intent/cycle), матрица переходов, идемпотентность; не пайплайн кандидата | RecruitmentApplication, Candidate | Без workflow engine; см. документ |
| [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md) | Reconciliation: **ветки/код ↔ канон**, таблица контракта, **C1–C4 / C2b / I1** (без молчаливого merge) | Application writers, PR planning | Перед merge параллельных PR по Application |
| [application-creation-mvp.md](application-creation-mvp.md) | Когда создаётся строка Application, миграция MVP, duplicate, тесты | Lead, Candidate, RecruitmentApplication | См. [applications-operating-model.md](../architecture/applications-operating-model.md) |
| [lead-conversion-contract.md](lead-conversion-contract.md) | Контракт **Lead → Candidate** (матрица, `candidate_created`) | Lead, Candidate | С Application intent: см. lifecycle + MVP |
| [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md) | Все точки INSERT Candidate | Candidate | + ссылки на Application / continuity |
| [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) | Операционная модель Lead → Candidate → … | Lead, Candidate, Application | Hub-документ |
| [lead-lifecycle-email-policy.md](lead-lifecycle-email-policy.md) | **ADR-033:** Own-company SoT lifecycle email (RODO + ops); optional client + Vacancy override; Control Center; fail-closed + operator signal | Lead, OwnCompany, Company, Vacancy, Communication Pipeline | Resolver; Pipeline only (INV-17) |
| [compliance-obligations-ops.md](compliance-obligations-ops.md) | **Ops projection** of open RODO obligations (queue / retry / escalation / SLA). Not a second state-machine; freeze: six `compliance_state` values + no mark-resolved | Lead (`normalized.rodo`) | Queue + SMTP-exhaustion alert; retry only `delivery_failed` / `delivery_required` |
| [slice-4-activity-continuity-guards.md](slice-4-activity-continuity-guards.md) | Continuity первого контакта (UOS) на convert | Lead, Candidate | **Не** статусы Application (см. §1.1) |
| [candidate-intake-via-telegram-execution-plan.md](candidate-intake-via-telegram-execution-plan.md) | _Operational backlog (execution plan)._ Telegram-based intake кандидатов: implementation slices, DoD по фазам | Candidate, TelegramBot, Application | Status: **Plan** — не источник истины архитектуры; canon границ см. ADR-002 / ADR-013 |
| [email-client-outlook-style-research.md](email-client-outlook-style-research.md) | _Research draft._ Outlook-style email-клиент внутри HostFlow: модели почтовых ящиков, протоколы, запросы UX | Communications, Mailbox | Status: **Research draft** — не часть канона; служит источником вопросов для будущего ADR |
| [recruitment-document-collection-handoff.md](recruitment-document-collection-handoff.md) | Requirements → Accepted Evidence → Candidate Evidence → handoff `requirement_fulfillments[]` | Candidate, Requirement, CandidateEvidence, Document | ADR-016 |
| [requirement-evidence-model-p0.md](../platform/requirement-evidence-model-p0.md) | Platform canon: 4 entities |
| [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md) | Первый operational контур Tenant → Recruitment → Document Hub → HR (ownership, без копирования файлов) | Candidate, WorkforceEmployee, DocumentEntityLink | Stage handoff, document links |

**Канон Application (один контур):** семантика статусов и переходов — [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md); границы сущности — [applications-operating-model.md](../architecture/applications-operating-model.md) (раздел про статус **не** дублирует enum); сверка с кодом, resolved/open конфликты и gaps (C1–C4, C2b, I1 и т.д.) — [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md).

---

## Общие принципы Workflow
- Все процессы запускаются событиями (Event-driven architecture).  
- Любое изменение статуса, срока или данных создаёт событие (`event_log`).  
- Напоминания и уведомления являются реакцией на события.  
- Вся логика автоматизации должна быть **идемпотентной** и безопасной в многопоточном режиме.  
- Все workflow связаны с конкретным `tenant_id` и подчиняются RLS.  
- Любой workflow может быть приостановлен или перезапущен вручную через админку.

---

## Взаимосвязь Workflow

```
Lead → Candidate → Documents → Reminders → Hiring
```

1. **Lead** создаётся через webhook и конвертируется в **Candidate**.  
2. **Candidate** проходит статусы пайплайна (канон: `../architecture/recruitment-domain-model.md` + `../architecture/ADR-002-modular-recruitment-hr-boundary.md`).  
3. **Documents** добавляются в Document Hub и отслеживаются по сроку Hub (см. `document_expiry.md`).  
4. Напоминания живут в Activity layer (см. `reminders.md` / ADR-012), не в таблице Document Hub.  
5. После успешного завершения всех этапов кандидат становится “Трудоустроен”.

---

## Метрики системы Workflow
- Время прохождения полного цикла кандидата (Lead → Hire).  
- Количество просроченных документов.  
- Среднее время реакции на напоминания.  
- Количество невалидных лидов.  
- Конверсия между этапами пайплайна.

---

## AI Agent Notes
- Этот документ является картой связей между workflow.  
- Использовать его при генерации новых сценариев автоматизации.  
- Любой новый workflow должен быть добавлен сюда с кратким описанием.  
- Все изменения должны быть отражены в `core.md` и `rules.md`.  
- Workflow нельзя изменять без согласования зависимых модулей.
