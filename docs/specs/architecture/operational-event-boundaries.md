# Operational event boundaries: stage vs handoff vs HR materialization

**Статус:** канон *conceptual layer* — ownership domains, инварианты, границы событий, дисциплина consumers, **command/flow**, **canonical flow ownership** (кто orchestrates lifecycle). По смыслу это operational constitution / domain law для безопасного разрезания монолита, а не только «архитектурные заметки».  
**Не является:** шиной событий, CQRS, инфраструктурой (Kafka/Rabbit), generic workflow engine.

**Связь:** [handoff-contract.md](handoff-contract.md) (продуктовый маппинг стадий и типы T1–T3), [ADR-002](ADR-002-modular-recruitment-hr-boundary.md), [invariants-recruitment-hr-document-hub.md](invariants-recruitment-hr-document-hub.md), [ADR-012](ADR-012-activity-notification-operating-layer.md) и canon [activity-notification-operating-layer.md](activity-notification-operating-layer.md) — **Activity** и **Notification** как два разделённых concept-а; все «activity»/«notifications» столбцы ниже относятся к этому слою (одна `activities` таблица + одна `notifications` таблица), а не к разрозненным task/todo/planner/reminder сущностям.

---

## Ключевой контракт (что считается отдельным фактом)

| Имя (vocabulary) | Смысл | Источник истины |
|------------------|--------|-----------------|
| **candidate_stage_changed** | Факт смены стадии кандидата в recruitment pipeline | Recruitment |
| **ready_for_hr** / **ready_for_handoff** | *Не отдельные события в MVP* — смысловые значения стадии при том же факте `candidate_stage_changed` | — |
| **handoff_created** | Создан конкретный контекст передачи (тип, source/destination, правила) | Handoff |
| **workforce_employee_created** | Материализован сотрудник (связь с `source_candidate_id` и т.п.) | HR |
| **hr_case_created** | Создан HR operational case (onboarding/compliance), отдельно от профиля сотрудника | HR |
| **document_*** | Факты жизненного цикла документа (upload, link, verify, review, …) | Document Hub |

---

## Главный инвариант

**Trigger ≠ business result.**

Стадия может *запустить* процесс, но **не подменяет** результат: появление handoff, employee, case или документного контекста — **отдельные факты**, если они реально произошли в системе.

---

## MVP: не плодить события «готовности»

**Do not** вводить отдельные канонические события `candidate_ready_for_hr` или `candidate_ready_for_handoff`.

Использовать:

- **candidate_stage_changed** с `new_stage = ready_for_hr` или `new_stage = ready_for_handoff` как *триггер* и носитель смысла.

Отдельные события создавать только для **результирующих фактов**:

- `handoff_created`
- `workforce_employee_created`
- `hr_case_created`
- `document_linked` / `document_review_created` / и т.д. по жизненному циклу документа

**Уточнение:** стадия `ready_for_handoff` **не** задаёт направление передачи; направление и тип — из tenant link / правил handoff (client-only, internal-only, mixed).

---

## Канонический минимум имён (текущий слой)

**Не расширять словарь слишком быстро** — иначе event explosion, pseudo-DDD и naming chaos.

На этом этапе **достаточно маленького стабильного набора**; таблицу контрактов (см. ниже) заполнять **только для него**, а не для полного inventory системы.

Минимальный канон для recruitment / handoff / HR / документы:

| Имя |
|-----|
| `candidate_stage_changed` |
| `handoff_created` |
| `workforce_employee_created` |
| `hr_case_created` |
| `document_uploaded` |
| `document_linked` |
| `document_review_created` |
| `document_review_approved` |

Новые имена добавлять только при **новом устойчивом операционном факте**, а не «для удобства логов» или дублирования уже выраженного смысла.

---

## Consumer / side-effect contract (канонический минимум)

Детализация **только для восьми имён** выше. Список событий на этом шаге **не** расширять.

| Event | Publisher | Allowed consumers | Allowed side effects | Forbidden |
|-------|-------------|-------------------|----------------------|-----------|
| `candidate_stage_changed` | Recruitment | Handoff, Activity, Notifications, Audit, Automations | создать activity; уведомить ответственных; инициировать handoff rule evaluation | напрямую создавать Employee без handoff/HR contract |
| `handoff_created` | Handoff domain | HR, Document Hub, Activity, Notifications, Audit | создать HR materialization request; открыть visibility; создать task | менять Candidate pipeline; копировать документы |
| `workforce_employee_created` | HR | Activity, Notifications, Audit, Fleet | создать HR timeline item; уведомить HR/Fleet; открыть employee context | менять Candidate; создавать новые документы-копии |
| `hr_case_created` | HR | Document Hub, Activity, Notifications, Audit | создать HR checklist; создать document review contexts; назначить ответственного | менять recruitment stage; копировать candidate documents |
| `document_uploaded` | Document Hub | Recruitment, HR, Fleet, Activity, Notifications, Audit | показать документ в linked context; создать review task | менять stage/entity ownership |
| `document_linked` | Document Hub | Recruitment, HR, Fleet, Activity, Audit | дать видимость документа в linked entity context | копировать файл; менять владельца документа |
| `document_review_created` | Document Hub | Recruitment, HR, Fleet, Activity, Notifications, Audit | создать review task; уведомить reviewer | менять общий document ownership |
| `document_review_approved` | Document Hub | Recruitment, HR, Fleet, Activity, Notifications, Audit, Automations | обновить readiness/checklist status; уведомить следующий domain | менять pipeline stage автоматически без явного rule |

### Главные инварианты

1. **Consumer can react, but cannot become source of truth.**
2. **Side effect must stay inside consumer’s ownership domain.**
3. **Cross-domain mutation requires canonical command/flow, not direct write.**
4. **Document events never create file copies.**
5. **Stage events can trigger handoff evaluation, but not bypass handoff contract.**
6. **Automation is a consumer, not an owner.**
7. **Notification is delivery, not state.**
8. **Activity is work item, not source of truth.**

### Практическая формула для агента

When handling an operational event, a consumer may create tasks, notifications, timeline items, review requests or visibility links **only inside its allowed domain**. It must **not** directly mutate another domain’s source-of-truth entities. Cross-domain effects must go through **canonical commands/flows** such as handoff creation, HR materialization, or Document Hub linking.

---

## Command / flow contract (следующий контур)

После разведения **event** (факт), **consumer** (кто реагирует) и **side effect** (что разрешено в своей зоне) нужно явно развести **намерение** и **разрешённый путь смены state**.

| Понятие | Смысл |
|---------|--------|
| **Command** | Намерение что-то сделать (запрос операции): пользователь, UI, интеграция или автоматизация вызывают **именованную операцию** домена, а не «просто пишут в таблицу». |
| **Flow** | Разрешённый путь изменения state: проверки правил, порядок шагов, какой домен **владеет** записью, какие последующие команды или оценки правил допустимы. |
| **Event** | Неизменяемый **факт**, что изменение уже произошло (см. канонический минимум и consumer contract). |

**Инвариант:** **State changes happen through commands/flows, not by consumers directly mutating foreign domains.**

Automation, Telegram handlers и UI shortcuts **не** получают исключения: они подают **command** (или вызывают тот же API/command layer), проходят **flow** домена-владельца; только после этого публикуются **events**. Обход command/flow («просто поменять статус» в чужом домене) — тот же класс нарушений, что и прямые cross-domain writes из consumer contract.

### Пример (логический порядок)

1. **`MarkCandidateReadyForHr`** — *command* (намерение; имя условное, в коде может быть PATCH стадии под политикой Recruitment).
2. **Recruitment** проверяет правила и **меняет** stage в рамках своего flow.
3. Появляется факт **`candidate_stage_changed`** — *event*.
4. **Handoff** (как домен/резолвер) **оценивает** правила (часть flow после факта стадии).
5. При выполнении условий выполняется команда/flow создания передачи → факт **`handoff_created`** — *event*.

Цепочки в § «Примерные цепочки MVP» ниже описывают **порядок событий (фактов)**; перед ними в реальной системе стоят **commands и flows** владеющих доменов.

### Практическая формула для агента

If a change touches **source of truth** in domain A, it must be executed by **A’s command/flow** (API, service use-case, explicit policy). Other domains, automations, and channels may only **invoke that command** or react to **events** within their allowed side effects — never replace the command with a direct write.

**Каноническая цепочка для внешних актёров** (UI, Telegram, cron, automation, scripts):

`External actor → command → owner flow → events` — **не** `Telegram handler → directly create Employee`.

Automation, Telegram, UI shortcuts и background jobs **официально не «особые случаи»**: они обязаны входить в ту же цепочку, что и человек через API.

---

## Canonical flow ownership (orchestration)

Слой **после** events, consumers и command/flow: **кто имеет право orchestrate multi-step flows** (последовательность шагов, политики, порядок смены state внутри одного жизненного цикла).

| Домен (owner) | Что orchestrates (канонический flow) |
|----------------|--------------------------------------|
| **Recruitment** | Жизненный цикл кандидата в pipeline (стадии, правила смены стадии в своей зоне). |
| **Handoff** | Передача operational ownership / visibility (контекст передачи, тип T1–T3, правила согласования с recruitment и HR). |
| **HR** | Материализация сотрудника, HR case, онбординг в своей зоне (Employee / case lifecycle). |
| **Document Hub** | Жизненный цикл документа (upload, link, review, approval, visibility) как единственный orchestrator документного state. |
| **Automation** | **Не** orchestrates чужие lifecycle: может **инициировать command** (тот же entrypoint, что UI), подписываться на **events** и делать разрешённые side effects **в своей зоне** — см. consumer contract. |

**Инвариант:** **Only the owner domain orchestrates its canonical flow.**

- **HR** orchestrates **Employee** (и связанный HR operational case) lifecycle.  
- **Recruitment** orchestrates **Candidate** pipeline lifecycle.  
- **Document Hub** orchestrates **Document** lifecycle.

**Чужие домены** могут:

- вызвать **command** владельца (явный API / use-case);
- **реагировать** на **events** в рамках allowed consumers и side effects.

**Не должны:**

- **orchestrate** чужой lifecycle (не задавать скрытую многошаговую логику «от имени» другого домена: ни UI, ни Telegram, ни cron, ни automation).

### Риски при нарушении

- Дублирование orchestration в двух местах.  
- Recursive automations (цепочки, которые снова запускают себя в обход политик владельца).  
- UI-driven или Telegram-driven «тихие» многошаговые сценарии вне owner flow.  
- Скрытая async-логика, меняющая чужой state.

### Практическая формула для агента

If a process spans multiple steps inside **one** bounded lifecycle (candidate stages, handoff, employee onboarding, document review), the **owning domain** defines and runs that orchestration. Cross-domain work is **chained** via **commands** and **events**, not by embedding another domain’s step sequence inside a consumer.

---

## Порядок и идемпотентность

- **Логический порядок** цепочки событий важен для модели (что обычно следует за чем).
- **Одна транзакция** для всей цепочки **не** требуется.
- **Идемпотентность** задаётся **корреляционными ключами**, а не «запретом дублей в UI»:  
  `candidate_id`, `handoff_id`, `employee_id`, `hr_case_id`, `document_id` (и согласованные составные ключи там, где один факт привязан к паре сущностей).

---

## Примерные цепочки MVP (логический порядок)

**Канон `ready_for_hr`:**

1. `candidate_stage_changed` (`new_stage = ready_for_hr`)
2. `handoff_created` (type = internal HR continuity, если продукт требует явного контекста)
3. `workforce_employee_created`
4. `hr_case_created`
5. при необходимости — `document_linked` / `document_review_created` для HR review contexts

**`ready_for_handoff`, internal-only:**

1. `candidate_stage_changed`
2. `handoff_created` (internal_hr или internal_workforce — по продуктовому правилу)
3. `workforce_employee_created`
4. `hr_case_created`

**`ready_for_handoff`, client-only:**

1. `candidate_stage_changed`
2. `handoff_created` (client portal)

Без `workforce_employee_created`, если не включён явный workforce-путь.

*Примечание:* `handoff_created` может **не** совпадать по времени с `workforce_employee_created` (например, manual HR acceptance) — это нормально, пока факты разведены.

---

## Различие типов сущностей (anti-coupling)

- **Event (operational)** — неизменяемый факт в операционной истории; не «редактируется», новый факт добавляется при новом изменении состояния.
- **Activity** — элемент работы (задача / звонок / встреча / follow-up / проверка документа / подтверждение приезда / любая операционная единица) в **единой** `activities`-таблице (см. [`ADR-012`](ADR-012-activity-notification-operating-layer.md), canon [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md)). Может меняться и закрываться. **Не** имеет параллельных таблиц `todos` / `planner_items` / `reminders` / `candidate_tasks`.
- **Notification** — in-app сигнал в `notifications`-таблице (`title`, `body`, `severity`, опциональный `activity_id`). Доставка наружу (push, Telegram, email) — отдельный delivery layer; `notifications.channel` хранит UI-факт получения, не сам outbound transport.
- **Communication** — диалог/переписка (recruiter ↔ HR и т.д.); `communication_thread` живёт в своём домене и **публикует** Activity / Notification через consumer contract ниже.

`candidate_stage_changed` — **event** в смысле pipeline. Созданная задача HR — **Activity** (`type='task'`/`'document_check'`/`'arrival_action'`/…, `source_module='candidates'` или `'workforce'`). Push в Telegram — **outbound delivery** на основе **Notification**, у которого `activity_id` ссылается на ту же Activity (если действие требуется) или на `related_entity_*` (если только информирование).

---

## Дисциплина потребителей (следующий инвариант)

Следующая зона риска — **не vocabulary**, а **кто имеет право на что реагировать и как**.

**Инвариант:** **Consumers do not redefine source of truth.**

Потребитель события **не** становится авторитетом за чужой домен: он может инициировать *свой* разрешённый side effect (уведомление, задачу, интеграционный вызов), но **не** переписывает каноническое состояние другого модуля в обход его контрактов.

Примеры нарушений (запрещённый coupling):

- Сервис уведомлений **меняет** стадию `Candidate`.
- Activity (operational layer) **создаёт** `Employee` напрямую, минуя HR flow и правила handoff. (Activity может породить **command** в HR-домен, но никогда — прямую запись в `workforce_employees`.)
- Telegram handler **материализует** Workforce, обходя правила `CandidateHandoff` / stage resolver.
- UI shortcut **создаёт** владение документом вне Document Hub.
- Автоматизация **создаёт** HR Case без канонического HR-пути (явный сервис/API и идемпотентность).
- Любой код вводит параллельную task-таблицу (`todos`, `planner_items`, `reminders`, `candidate_tasks`) — нарушение [`ADR-012`](ADR-012-activity-notification-operating-layer.md): единственный source of truth — `activities`.
- `Notification` создаётся без `activity_id` И без `related_entity_*` — нарушение canon §3.4.1 (notification без действия и без сущности — мусор).

Для восьми канонических имён детализация **allowed consumers / side effects / forbidden** уже задана в § **Consumer / side-effect contract** выше.

---

## Следующий слой (шаблон полей для расширения и ревью кода)

При добавлении **нового** имени (редко) или при сверке имплементации с каноном используйте **полный шаблон строки** — по **одной строке на событие**:

| Поле | Назначение |
|------|------------|
| event_name | Каноническое имя факта |
| domain | Recruitment / Handoff / HR / Document Hub / Fleet / … |
| source_of_truth | Где авторитетное состояние после факта |
| trigger | Что обычно запускает факт (в т.ч. stage как trigger, не result) |
| correlation_keys | Ключи идемпотентности и трассировки |
| allowed_consumers | Кто может реагировать (категории), без смешения с publisher |
| side_effects | Что разрешено порождать (не путать с самим событием) |
| idempotency_rule | Дубликат того же факта / повторная доставка |
| audit_required | Обязательность следа для compliance / разборов |
| notification_allowed | Может ли породить уведомление и какого класса |

Полный inventory по коду **намеренно** не раздувается: для текущего слоя достаточно **восьми строк** consumer contract + этот шаблон для редких новых фактов.

---

## Зачем этот слой (governance)

Формируются не только «схемы», а **operational constitution** / **domain law** / **anti-chaos governance**: связка **ownership → invariants → event boundaries → consumer discipline → command/flow → flow ownership** даёт безопасное разрезание монолита и онбординг людей и агентов без разрушения semantics через год.

Монолит деградирует не от числа таблиц, а когда теряется semantic ownership, любой слой orchestrates чужие lifecycle, события теряют смысл, потребители **мутируют чужие домены**, а Telegram/cron/UI становятся скрытыми источниками истины.

---

<a id="review-checklist"></a>

## Чеклист при ревью (PR / интеграция / automation)

Использовать **после** закрытия текущей итерации governance-дока: не расширять архитектурный текст, а **проверять изменения** по канону.

1. **Кто владелец lifecycle?** (canonical flow ownership)  
2. **Кто инициировал command?** (не скрытый write)  
3. **Кто изменил source of truth?** (только домен-владелец через свой flow)  
4. **Кто выпустил event?** (факт после изменения; не путать с notification)  
5. **Кто consumer?** (в пределах allowed consumers / side effects)  
6. **Нет ли прямой записи в чужой домен?** (consumer discipline)  
7. **Нет ли hidden orchestration** через UI / Telegram / cron / automation? (вне owner flow)  
8. **Нет ли копирования документов** вместо links? (Document Hub)

**Anti-patterns:** см. § Consumer / side-effect contract, § Command / flow contract, § Canonical flow ownership.
