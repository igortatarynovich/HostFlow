# Первый operational flow: Recruitment → Document Hub → HR (внутри одного tenant)

**Статус:** канон для постановки задач агентам и разработчикам на этапе запуска цепочки.

**Самый правильный первый шаг:** настроить связку **внутри одного tenant** (и в рамках одного **company scope** для operational handoff), без внешнего sharing и без межаккаунтных сценариев.

---

## 0. Вне scope сейчас (не трогать)

До тех пор, пока внутренний контур не работает «чисто»:

- **inter-tenant sharing** (обмен данными между tenant’ами);
- **внешний client portal**;
- **сложный marketplace**;
- **передача между независимыми аккаунтами** / внешние получатели как продуктовый сценарий.

Цель на данном этапе проще и правильнее: **передача ответственности внутри tenant**, без внешнего sharing.

---

## 1. Первый рабочий контур

```
Tenant → Company → Recruitment → Document Hub → HR
```

На этом контуре проверяется **внутренняя operational continuity** между Recruitment и HR: это не «передача клиенту», а смена **operational ownership** и прав доступа к уже существующим артефактам (документы, контекст), в границах одного tenant и одного company scope.

---

## 2. Цель (цепочка сущностей)

Рабочая **continuity chain**:

`Lead → Candidate → Handoff → HR Case → Employee`

с:

- **shared documents** (общий слой документов, без копирования файлов при handoff);
- **continuity** контекста (коммуникации и история не дублируются как новые канонические сущности);
- **ясным ownership** (кто владеет какой сущностью на каждом этапе);
- **без дублирования** документов и активностей при передаче.

---

## 3. Критерии готовности внутри одного tenant

Внутри одного tenant (и согласованного company scope) должно выполняться:

1. **Recruitment** создаёт **Candidate**.  
2. **Document Hub** хранит документы (каноническая запись и файлы).  
3. **Recruitment** только **линкует** документы к Candidate (links / requirements), не подменяя владение Document Hub.  
4. Candidate получает статус **Ready for HR** / **Hired** (или согласованные коды стадий — см. [ADR-002](../architecture/ADR-002-modular-recruitment-hr-boundary.md)).  
5. **HR** создаёт **Employee** и **HR Case** (профиль сотрудника + кадровый кейс).  
6. Документы **не копируются** при handoff.  
7. **HR** получает доступ через **document links** и при необходимости **HR review context** в Document Hub.  
8. Ответственность меняется через явный **handoff event** (а не через неявное дублирование сущностей).

### 3.1 MVP в коде (как закрываются п.5–8 без полного ADR-009)

- **П.5 HR Case + Employee:** помимо `WorkforceEmployee` и bundle, в БД есть строка **`workforce_hr_cases`** (связь с сотрудником и `source_candidate_id`).  
- **П.7 links + HR review:** связь документа с сотрудником для повторного использования — **`document_entity_links`** (`reused_for_hr`); отдельная проверка в контуре HR — **`DocumentCheck`** с `payload.review_module=hr` (не меняет `Document.status` от рекрутинга). Доступ HR к списку документов — `GET /workforce/employees/.../documents`.  
- **П.8 handoff event:** при смене стадии в наборе handoff вызывается `handoff_from_candidate` и логируется активность; материализация HR context (`ensure_hr_operational_context`) — на handoff и лениво при открытии HR API. Подробнее — [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md) §2.1.

---

## 4. Три домена владения (не смешивать)

### 4.1 Recruitment

**Владеет:**

- Lead  
- Candidate  
- Vacancy  
- Recruitment pipeline / этапы рекрутмента  
- Recruiter activities  
- Candidate communication (в зоне рекрутмента)  
- Qualification status (в зоне рекрутмента)

**Не владеет:**

- Employee (Workforce)  
- HR Case (как отдельная HR-сущность)  
- Contracts / payroll / ZUS как HR-процессы  
- Fleet assignment

### 4.2 HR

**Владеет:**

- Employee  
- HR Case  
- Onboarding  
- Contracts (трудовые / оформительские в зоне HR)  
- Work permits / ZUS / payroll-related данные в зоне HR  
- HR checklists

**Не владеет:**

- Candidate pipeline как «источник истины» после закрытия рекрутмента  
- Recruitment-only статусы и логика вакансий как замена HR-процессов

### 4.3 Document Hub

**Владеет:**

- Document (каноническая запись)  
- Document type, file, expiration, verification  
- Templates, required sets, reviews (в рамках платформенного слоя документов)

**Recruitment и HR не «владеют» документами** в смысле копирования или второй канонической копии файла.

Они:

- создают **links** к документам;
- создают **requirements** (что нужно собрать);
- создают **reviews** / контексты проверки.

Документы привязаны к operational контексту (например `candidate_id`, `own_company_id`, `source_module` / аналог в вашей модели данных) согласно [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md).

---

## 5. Ключевой flow

### 5.1 Этап Recruitment

- Создаётся **Candidate** (из Lead или вручную).  
- Собираются требования к документам; создаются **ссылки** и заказы в Document Hub.  
- Ведётся qualification до точки handoff.

**Документы:** хранятся в Document Hub; у записи указывается operational привязка (например `own_company_id`, связь с candidate, источник/модуль инициации — по вашей схеме БД).

**Детальный flow:** [`recruitment-document-collection-handoff.md`](recruitment-document-collection-handoff.md) + [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) + [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md). Рекрутер закрывает **Requirements** через **Candidate Evidence** (выбор Accepted Evidence → Document Instance); в HR уходит `requirement_fulfillments[]`, не угадывание по типам документов.

### 5.2 Handoff event

**Recruitment** доводит кандидата до **`ready_for_hr`** (готовность к передаче в кадры) — это **финал воронки рекрутера**, не действие HR. При включённом agency handoff рекрутер **может** выставить `ready_for_hr`; **`hired`** / **`employed`** — зона **HR** (рекрутер не переводит на них через PATCH). См. [invariants…](../architecture/invariants-recruitment-hr-document-hub.md).

**Не путать с `ready_for_handoff`:** в воронке/автоматике (в т.ч. Telegram) может быть отдельный код **«готов к передаче»**. Канон для контракта ADR-002 — **`ready_for_hr`**. Чтобы **тот же** operational эффект (появление `WorkforceEmployee`) наступал уже на стадии **`ready_for_handoff`**, на **tenant link** (компания) задаётся одно из: **`handoff_to_client: false`** при включённом internal HR (только внутренняя передача), либо **`workforce_handoff_on_ready_for_handoff_stage: true`** (если client portal на ссылке остаётся включённым). Подробнее — [implementation-roadmap…](implementation-roadmap-single-tenant-hr-handoff.md) §2.1 блок D.

Далее **HR** принимает контур: оформление, reviews, переходы в т.ч. **`hired`** (подтверждение трудоустройства). Детали стадий — [ADR-002](../architecture/ADR-002-modular-recruitment-hr-boundary.md).

**Создаётся:**

- **HR Case** и/или  
- **Employee + HR Case** (по правилам Workforce handoff — константы и сервисы в коде).

**Не копируются:**

- файлы документов;
- треды коммуникаций «как новый объект»;
- recruitment activities.

**Создаются:**

- ссылки и права доступа HR к shared documents;
- HR requirements / чеклисты;
- явная запись handoff (событие смены operational responsibility).

### 5.3 Этап HR

- HR видит **контекст кандидата** (read / linked) и **shared documents**.  
- HR создаёт **HR-only** документы и процессы через Document Hub.  
- Запускается onboarding.

Документы рекрутмента **не копируются**; при необходимости — новый **review context** в Document Hub.

---

## 6. Tenant, Company, Department (напоминание)

- **Tenant** — граница workspace (подписка, пользователи, модули на уровне тенанта, RLS). Не заменяет бизнес-роль.  
- **Company** — operational / legal entity со своим scope; `company_type` — **preset**, а не жёсткий запрет на модули (см. [ADR-003](../architecture/ADR-003-tenant-company-module-data-boundaries.md)).  
- **Department** ≠ Company: отдел кадров может быть **внутренней единицей** одной company, а не отдельной строкой `companies`.

Первый flow **намеренно** в рамках **одной company**, чтобы не смешивать cross-company handoff с отладкой ownership.

---

## 7. Постановка задач ИИ-агентам (обязательно)

**Главное правило для агента:** сейчас делаем не «передачу клиенту», а **внутреннюю operational continuity** между Recruitment и HR внутри одного **tenant / company scope**.

**Нельзя** давать абстрактные задачи уровня:

- «раздели модули»;
- «сделай HR отдельно»;
- «разведи recruitment и documents».

**Нужно** ставить задачу в терминах этого контракта: какие сущности создаются, какие ссылки, какой handoff event, что запрещено (копии документов, перенос document logic в recruitment как ownership).

### Каноническая формулировка задачи (copy-paste)

Развести **Recruitment**, **HR** и **Document Hub** как отдельные **ownership domains** и реализовать **первый рабочий flow внутри одного tenant**: Candidate из Recruitment после статуса **Ready for HR** должен создавать **HR Case** и **Employee Profile** в HR, при этом документы **не копируются**, а переиспользуются через **Document Links** и **HR Review Context**. Recruitment не должен владеть Employee / HR Case, HR не должен владеть Candidate Pipeline, Document Hub должен быть **единым владельцем документов**.

Краткий принцип:

> Recruitment, HR и Document Hub — **разные домены владения**, связанные **links, handoffs и shared operational context**, а не дублированием сущностей.

---

## 8. Расширение после стабилизации

Когда внутренний контур в одном tenant работает **чисто**, тот же механизм (handoff, links, review context, без копирования документов) расширяется по очереди на:

- **company → company** внутри одного tenant;
- **agency → employer**;
- **tenant → tenant**;
- **shared access**;
- **client portal**.

Без явного решения в спеке эти направления **не смешивать** с первым шагом.

---

## 9. Связанные документы

| Документ | Зачем |
|----------|--------|
| [module-separation-implementation-order.md](module-separation-implementation-order.md) | **Полный порядок этапов 0–10** до разделения модулей (Hub → Recruitment → HR → UI → permissions → расширения) |
| [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md) | **AS-IS / GAP / DOD фазы 1** и очередность фаз до модулей |
| [handoff-contract.md](../architecture/handoff-contract.md) | **Продуктовый маппинг стадий** и **модель handoff** (internal vs client, source/destination, idempotent) |
| [ADR-002](../architecture/ADR-002-modular-recruitment-hr-boundary.md) | Граница Recruitment / HR, стадии handoff, Workforce |
| [invariants-recruitment-hr-document-hub.md](../architecture/invariants-recruitment-hr-document-hub.md) | **Hard invariants** (документы, ownership, стадии ready_for_hr vs hired) |
| [ADR-003](../architecture/ADR-003-tenant-company-module-data-boundaries.md) | Tenant vs company vs модули |
| [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) | Document Hub как общий слой |
| [documents_workflow_contract.md](../modules/documents_workflow_contract.md) | Поля workflow документов (шаги, статусы) |
| [glossary.md](../glossary.md) | Термины |
| [recruitment-domain-model.md](../architecture/recruitment-domain-model.md) + [ADR-002](../architecture/ADR-002-modular-recruitment-hr-boundary.md) | Канон пайплайна кандидата (бывший `candidate_pipeline.md` архивирован 2026-05-12) |
| [recruitment-document-collection-handoff.md](recruitment-document-collection-handoff.md) | Слоты документов, variant selection, handoff payload |
| [requirement-evidence-model-p0.md](../platform/requirement-evidence-model-p0.md) | Platform canon: 4 entities |
| [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md) | Requirement / Evidence / Document Instance / Candidate Evidence |

---

## AI Agent Notes

- Перед работой над цепочкой **рекрутинг → документы → кадры** читать этот файл и ADR-002/009.  
- Первый шаг — только **внутри tenant**; не трогать inter-tenant sharing, client portal, marketplace и передачу между независимыми аккаунтами, пока чеклист в разделе «Критерии готовности внутри одного tenant» не закрыт.  
- При сомнении в терминах — `docs/specs/glossary.md` и свежие файлы в `docs/specs/architecture/`.
