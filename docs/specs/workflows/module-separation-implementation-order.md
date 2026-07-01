# Порядок реализации до полного разделения модулей

**Статус:** канон для планирования работ и постановки задач агентам.  
**Цель первого этапа (не «переписать всё»):** чистая рабочая связка **Recruitment → Document Hub → HR** внутри одного **tenant / company scope**.

Связанные документы: [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md), [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md), [**handoff-contract.md**](../architecture/handoff-contract.md), [ADR-002](../architecture/ADR-002-modular-recruitment-hr-boundary.md), [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md), [invariants-recruitment-hr-document-hub.md](../architecture/invariants-recruitment-hr-document-hub.md).

---

## Этап 0. Зафиксировать границы

До кода зафиксировать **три ownership domain**.

### Recruitment владеет

- Lead  
- Candidate  
- Vacancy  
- Application *(продуктовая сущность; в коде может быть частично / под другим именем — не смешивать с HR)*  
- Recruitment Pipeline  
- Recruitment Status  
- Recruiter Activity  

### Recruitment не владеет

- Employee  
- HR Case  
- Contract  
- Payroll  
- HR Checklist  
- **Document** как каноническая сущность Hub *(только links / requirements / reviews)*  

---

### HR владеет

- Employee  
- HR Case  
- HR Onboarding  
- Contract  
- Work Permit  
- ZUS data  
- HR Checklist  
- Employment lifecycle  

### HR не владеет

- Candidate  
- Vacancy  
- Recruitment Pipeline  

---

### Document Hub владеет

- Document  
- Document Type  
- Document Link  
- Document Requirement  
- Document Review  
- Expiration  
- Verification  
- File metadata  

Recruitment и HR **только используют** документы через links / requirements / reviews.

---

## Платформенный слой: Team / Work Management (Shared Platform Layer)

**Правило для плана разработки:** управление командой **не отдаётся** модулям Recruitment, HR или Fleet. Правильнее трактовать **Team / Work Management** как **общий слой платформы** (shared platform layer). Модули **только используют** этот слой.

### Зона ответственности слоя

- пользователи и идентичность в рабочем контексте;
- роли и привязка к **company + module**;
- рабочее время, availability, presence (online/offline);
- отсутствия (absences);
- workload;
- назначение задач (task assignment);
- напоминания (reminders);
- календарь;
- activity / аудит операций в единой модели;
- правила автораспределения (auto-distribution).

### Как это работает для модулей

**Recruitment** не хранит «кто сейчас на работе». Recruitment обращается к общему слою, например:

- кто доступен;
- кто может брать лиды;
- у кого какая нагрузка;
- кто в этом модуле имеет роль recruiter;
- кому можно назначить кандидата.

**HR** делает то же для HR-задач. **Fleet** — для assignments / incidents.

### Главная модель

- **Пользователь один.**
- **Availability одна** (глобальная для рабочего профиля на платформе).
- **Права и нагрузка** — в разрезе **company + module** (и при необходимости tenant).

**Примеры (иллюстрация):**

- User Anna, available yes, часы 09:00–17:00. В Recruitment / Focus Personnel — recruiter; в HR / Focus Personnel — нет доступа; Fleet / Poltrakt — нет доступа.
- User Edyta, available yes. HR / Poltrakt — HR officer; Recruitment / Poltrakt — readonly; Fleet / Poltrakt — нет доступа.

### Calendar / Tasks / Reminders — где живут

Не отдельными копиями в каждом модуле. Зафиксировано в [`../architecture/ADR-012-activity-notification-operating-layer.md`](../architecture/ADR-012-activity-notification-operating-layer.md): целевая **одна** платформенная сущность:

- **Activity** — единственная таблица для задач / напоминаний / follow-up / звонков / встреч / проверок документов / custom todo. См. canon [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md).
- **Notification** — отдельная таблица для in-app сигналов; ссылается на Activity через `activity_id`.

Параллельных таблиц «Task», «Reminder», «Calendar Event», «Todo», «Planner item» в каркасе платформы **не существует**. «Tasks», «Today», «Planner», «Calendar», «Notification Center» — это **представления** (views) над `activities` и `notifications`. См. canon §5.

Привязка к домену — через `related_entity_type` + `related_entity_id` + `source_module` (closed enum: `leads` / `candidates` / `documents` / `comms` / `workforce` / `automation` / `user`).

Задача — не «рекрутинговая таблица задач», а **общая Activity** с контекстом Recruitment (`source_module='leads'`/`'candidates'`, `related_entity_type='lead'`/`'candidate'`/`'vacancy'`); аналогично для HR (`source_module='workforce'`) и других модулей.

### Автораспределение лидов

**Shared capability:** Assignment Engine / Work Distribution. Использует availability, рабочие часы, роль, доступ к модулю, текущую нагрузку, round-robin, ручной приоритет, company scope.

Recruitment формулирует намерение: *«Новый lead — назначь recruiter»*; движок выбирает исполнителя.

### Первый практический срез (без «большой архитектуры» сразу)

**Следующий контур внедрения:** не выстраивать целиком Team/Work UI и не плодить абстракции, а **один end-to-end flow** — **автоназначение новых лидов только доступным рекрутёрам** (в рамках company / tenant scope).

**Минимальная цель среза:**

- при появлении нового lead Recruitment вызывает **один** сервис/процедуру назначения (зачаток Assignment Engine);
- в пул кандидатов попадают только пользователи с ролью **recruiter** в контексте Recruitment и **доступностью** (по согласованному определению: флаг, рабочие часы, или и то и другое — зафиксировать в задаче);
- политика распределения на первом шаге может быть простой (например round-robin или минимальная текущая нагрузка по открытым лидам), без полного продукта «правил»;
- результат **наблюдаем**: кто назначен, почему отфильтрованы недоступные, fallback если пул пуст.

**Вне среза (позже):** общий календарь платформы, единая таблица Task/Activity для всех модулей, Fleet/HR assignment, полноценный UI раздела Team.

Этот срез **подкрепляет** целевой shared layer данными и поведением, не заменяя его полным проектированием заранее.

### Навигация (ориентир)

В общем меню платформы, например: Team, Tasks, Calendar, Notifications, Settings → working hours / availability / assignment rules.

В модулях — **фильтрованные представления** того же слоя: Recruitment → recruitment tasks; HR → HR tasks; Fleet → fleet tasks.

### Ключевой принцип

**Не делать отдельные системы задач в каждом модуле** — иначе хаос дублирования и расхождения workload.

**Делать:** одна система работы, **разные контексты** → единый workload, календарь, напоминания, автораздача лидов, контроль доступности, меньше дублирования, понятная архитектура.

*Связь с этапом 8 ниже: по мере готовности контура handoff этот слой выносится и подключается модулями, а не копируется внутри них.*

---

## Этап 1. Вынести Document Hub как общий слой

**Первый технический приоритет** после границ.

Документы перестают быть только «документами кандидата» или «документами сотрудника».

**Целевая модель:**

- **Document** — самостоятельная сущность  
- **Document** имеет `owner_company_id`  
- **Document** имеет `source_module`  
- **Document** связывается с разными сущностями через **Document Link**  

**Минимальный набор сущностей Hub:**

- Document  
- DocumentType  
- DocumentLink  
- DocumentRequirement  
- DocumentReview  

*(Текущий код частично совпадает: см. AS-IS в [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md).)*  

**Фиксация прогресса (логический блок, не полный этап 1):** в контуре фазы 1 single-tenant уже есть **MVP Document Link** (`document_entity_links`, связь документа с `workforce_employee`) и **разведённый HR review** (`DocumentCheck` с `review_module=hr`). Целевая строка таблицы выше (`source_module` на документе, универсальный `DocumentReview` и т.д.) — **фаза 2** [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md).

---

## Этап 2. Очистить Recruitment

После выделения Hub убрать из Recruitment всё, что **не принадлежит** Recruitment.

**Recruitment должен:**

- создавать Candidate  
- вести pipeline  
- собирать документы **через Document Hub**  
- линковать документы к Candidate  
- менять статус Candidate  
- запускать handoff в HR  

**Recruitment не должен:**

- создавать employee-данные напрямую без HR flow  
- хранить HR checklist  
- хранить contract logic  
- хранить employee lifecycle  
- хранить document verification как **свою** внутреннюю таблицу без Hub  

---

## Этап 3. Создать HR module как отдельный domain

**Минимальная первая версия HR:**

- Employee Profile  
- HR Case  
- HR Onboarding Status  
- HR Checklist  
- HR Document Requirements  
- связь с Candidate через `source_candidate_id` (или эквивалент: `candidate_id` на Employee только как **ссылка**, не владение пайплайном)  

**Источники Employee:**

- из Candidate  
- вручную  
- позже import / API  

**Для первого flow достаточно:**  
**Candidate Ready for HR → Employee + HR Case**  

---

## Этап 4. Реализовать Handoff внутри одной company

Первый handoff — **максимально простой**.

**Событие:** Candidate отмечен как **Ready for HR**.

**Система создаёт:**

- Handoff Event  
- Employee Profile  
- HR Case  
- Document Links для HR context  
- HR Document Requirements / Reviews  

**Нельзя копировать документы.**

**Логика:**

- паспорт собран в Recruitment  
- HR получает **link** к тому же Document  
- HR создаёт свой **DocumentReview**  
- HR может запросить дополнительные документы  

---

## Этап 5. Общий operational context

После handoff HR видит не «пустого employee», а **context**:

- исходный Candidate  
- vacancy / source  
- recruiter  
- recruitment status  
- документы  
- notes (если разрешено)  
- activity history (если разрешено)  

**Ownership не смешивать:** HR видит context через links, readonly references, permissions.

---

## Этап 6. Развести UI

| Зона | Экраны |
|------|--------|
| **Recruitment** | Leads, Candidates, Vacancies, Applications, Candidate Profile, блок Recruitment Documents |
| **HR** | Employees, HR Cases, HR Onboarding, Employee Profile, блок HR Documents |
| **Document Hub** | All Documents, Document Types, Required Sets, Expirations, Verification Queue |

Документы **отображаются** в карточках Candidate/Employee, но **живут** в Document Hub.

---

## Этап 7. Настроить permissions

**Минимально:**

**Recruiter** — может: candidates, добавлять документы к candidate (через Hub), recruitment statuses, запускать handoff.  
Не может: редактировать HR Case, редактировать employee contract data в зоне HR.

**HR** — может: Employee, HR Case, проверка HR documents, запрос недостающих документов.  
Не должен: менять recruitment pipeline как владелец.

**Admin / Owner** — видит оба модуля (в рамках политики tenant/company).

---

## Этап 8. Team / Work Management platform (Activity & Notification Operating Layer)

**Не первым** относительно первого operational flow **Recruitment → Document Hub → HR** (сначала: Candidate, Document, HR Case, Employee, Handoff).

**Целевое направление** зафиксировано в разделе **«Платформенный слой: Team / Work Management»** выше и нормативно — в [`../architecture/ADR-012-activity-notification-operating-layer.md`](../architecture/ADR-012-activity-notification-operating-layer.md) + canon [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md): **одна** сущность `Activity` (для всех типов работы) + одна сущность `Notification` (для сигналов) с **контекстом модуля** (`related_entity_type`, `source_module`); Assignment Engine для лидов, availability и workload на платформе — **не** дублировать «свои задачи» внутри Recruitment, HR и Fleet.

Когда контур handoff и границы модулей стабилизированы — выносить и подключать этот слой; иначе агент смешивает слишком много слоёв слишком рано.

---

## Этап 9. Расширить handoff: company-to-company внутри tenant

Только после **чистой** связки внутри одной company.

**Вторая версия:** Agency Company → Employer Company в одном tenant.

Понадобятся, среди прочего: `from_company_id`, `to_company_id`, shared fields, shared documents, `access_scope`, `expires_at`, status.

---

## Этап 10. Только потом inter-tenant sharing

**Последний этап. Не сейчас.**

Сложность: legal boundary, data access, consent, expiry, audit, external company access, document sharing permissions.

---

## Правильный порядок (кратко)

1. Зафиксировать ownership domains  
2. Вынести Document Hub  
3. Очистить Recruitment  
4. Создать HR domain  
5. Сделать Candidate → HR Case / Employee flow  
6. Передавать документы через links, не копии  
7. Развести UI  
8. Настроить role / module / company permissions  
9. Вынести Team / Work Management (shared): единый Activity & Notification Operating Layer + assignment engine — см. раздел платформенного слоя выше и [ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md)  
10. Расширить до company-to-company handoff  
11. Потом inter-tenant sharing  

---

## Главная формула для агента

Сначала сделать **чистый internal flow** внутри одного tenant/company: **Recruitment → Document Hub → HR**.  
Только после этого расширять ту же модель на **company-to-company** и **inter-tenant** handoff.

---

## AI Agent Notes

- Нумерация **этапов 0–10** в этом файле — продуктово-технический порядок; дорожная карта «фаза 1 DOD» в [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md) описывает **текущий** первый измеримый кусок кода и тестов.  
- Не начинать этапы 8–10, пока не закрыт осмысленный минимум этапов 0–5 для одной company.  
- **Team / Work Management** — платформенный слой (см. раздел выше); не реализовывать как «внутренность» Recruitment/HR/Fleet.  
- Любая задача должна явно указывать **номер этапа** из этого файла.
