

# Workflows — Overview

Этот документ является обзором всех бизнес-процессов (workflow) в системе HostFlow. Он связывает модули, события и автоматизации, описанные в отдельных спецификациях.

---

## Цель
Собрать в одном месте краткое описание всех рабочих процессов, чтобы можно было быстро понять, как движутся данные и как взаимодействуют модули системы.

---

## Список Workflow-документов

| Документ | Назначение | Основные сущности | Автоматизация |
|-----------|-------------|-------------------|----------------|
| [document_expiry.md](document_expiry.md) | Контроль сроков действия документов и напоминания | Document, Candidate, Reminder | Автоматические напоминания, изменение статуса |
| [reminders.md](reminders.md) | Подсистема напоминаний и уведомлений | Reminder, Candidate, Document | Cron-задачи, уведомления, RLS |
| [reminders_matrix.md](reminders_matrix.md) | SLA и эскалации напоминаний | Reminder, Notification | Каналы доставки, дедупликация |
| [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) | Семантика жизненного цикла **Application** (intent/cycle), матрица переходов, идемпотентность; не пайплайн кандидата | RecruitmentApplication, Candidate | Без workflow engine; см. документ |
| [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md) | Reconciliation: **ветки/код ↔ канон**, таблица контракта, **C1–C4 / C2b / I1** (без молчаливого merge) | Application writers, PR planning | Перед merge параллельных PR по Application |
| [application-creation-mvp.md](application-creation-mvp.md) | Когда создаётся строка Application, миграция MVP, duplicate, тесты | Lead, Candidate, RecruitmentApplication | См. [applications-operating-model.md](../architecture/applications-operating-model.md) |
| [lead-conversion-contract.md](lead-conversion-contract.md) | Контракт **Lead → Candidate** (матрица, `candidate_created`) | Lead, Candidate | С Application intent: см. lifecycle + MVP |
| [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md) | Все точки INSERT Candidate | Candidate | + ссылки на Application / continuity |
| [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md) | Операционная модель Lead → Candidate → … | Lead, Candidate, Application | Hub-документ |
| [slice-4-activity-continuity-guards.md](slice-4-activity-continuity-guards.md) | Continuity первого контакта (UOS) на convert | Lead, Candidate | **Не** статусы Application (см. §1.1) |

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
3. **Documents** добавляются и отслеживаются (см. `document_expiry.md`).  
4. При приближении срока создаются **Reminders** (см. `reminders.md`).  
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
