# Handoff Contract: события передачи Recruitment ↔ HR ↔ Client

**Статус:** канон для продуктовых и архитектурных решений; дополняет [ADR-002](ADR-002-modular-recruitment-hr-boundary.md), [ADR-035](ADR-035-module-object-pipeline-settings.md) и [invariants-recruitment-hr-document-hub.md](invariants-recruitment-hr-document-hub.md).  
**Не заменяет** дорожную карту фазы 1 — см. [implementation-roadmap-single-tenant-hr-handoff.md](../workflows/implementation-roadmap-single-tenant-hr-handoff.md).  
**Границы операционных фактов:** [operational-event-boundaries.md](operational-event-boundaries.md).

---

## Target model (ADR-035) — read first

**Handoff is a system transition (event), not a pipeline stage and not the object's board position.**

| Catalog key | Meaning |
|-------------|---------|
| `handoff_to_hr` | Recruitment → HR; may create `WorkforceEmployee`; Candidate lifecycle → `closed` |
| `handoff_to_client` | Recruitment → client portal / client responsibility; Employee optional / often absent |
| `handoff_to_fleet` | HR → Fleet assignment (not a Candidate stage) |
| `close_success` / `close_declined` | Close without cross-module handoff |

Last **operational** Recruitment stages are e.g. `accepted` / `ready_for_client`. Builder wires a **locked** system transition after them. Object never “sits” on the transition node.

**Employee creation is optional:** only when company has `hr` enabled and the process provides for managing the employee in HostFlow.

Legacy stage codes below (`ready_for_hr`, `ready_for_handoff`, …) are **strangler** until Phase C cutover maps writers to catalog transition fire.

---

## Часть A. Продуктовый контракт стадий (Stage mapping) — LEGACY STRANGLER

Цель — чтобы агенты и разработчики **не угадывали**, какая стадия что запускает **в текущем runtime**. Новые pipelines/presets — по Target model выше.

### A.1 `ready_for_hr` (канонический Recruitment → HR)

- **Смысл:** финал зоны Recruitment — кандидат готов к передаче в кадры внутри tenant / company scope.
- **Кто двигает:** рекрутер (при включённом handoff lane) — см. invariants и enforcement в коде.
- **Эффект на Workforce (PR-5):** смена стадии **одна** больше **не** материализует `WorkforceEmployee`. Канон — **`CandidateHandoff` → `accept_handoff` → `handoff_from_candidate`** (T2). Stage `ready_for_hr` остаётся продуктовым/аналитическим кодом; см. [`hr-handoff-runtime-p0.md`](hr-handoff-runtime-p0.md).
- **Не путать с:** «готов к передаче клиенту» — это не обязанность этой стадии; она про **internal HR readiness** в смысле ADR-002.

### A.2 `ready_for_handoff` (универсальная стадия «передача»)

- **Смысл:** воронка / Telegram / пресеты могут использовать код **«готов к передаче»** без привязки к одному продуктовому сценарию.
- **Куда может вести операционно** (не исключают друг друга на уровне продукта, но **материализация Workforce** задаётся настройкой ссылки):

| Режим на tenant link | Поведение для `ready_for_handoff` → Workforce |
|----------------------|-----------------------------------------------|
| **Client portal включён**, internal HR выключен | Workforce **не** из одной только этой стадии по stage-driven правилу; дальше — **CandidateHandoff** (client) по продуктовому flow. |
| **Internal HR включён**, **client portal выключен** (`handoff_to_client: false`) | Стадия **`ready_for_handoff`** **запускает** тот же материализационный путь, что и handoff-стадии (см. `should_workforce_handoff_on_stage_change_resolved`). |
| **Оба включены** | По умолчанию **не** материализуем Workforce только из `ready_for_handoff` (чтобы не создавать сотрудника до выбора сценария). Исключение: флаг **`workforce_handoff_on_ready_for_handoff_stage: true`** на ссылке — тогда funnel/Telegram может запускать internal flow **без** смены кода воронки на `ready_for_hr`. |

- **Канон для документации и аналитики «рекрутинг закрыл»** по-прежнему **`ready_for_hr`** (ADR-002); `ready_for_handoff` — **продуктово настраиваемый** вход в передачу.

### A.3 Сводка для агентов (copy-paste)

- **`ready_for_hr`** = канонический переход Recruitment → internal HR (Workforce) по стадии.
- **`ready_for_handoff`** = универсальная стадия передачи; может вести в client handoff, в internal HR, или в оба — в зависимости от **tenant link** и флага **`workforce_handoff_on_ready_for_handoff_stage`** (см. roadmap §2.1 блок D).

---

## Часть B. Handoff Contract (модель события)

### B.1 Что считается handoff **событием** сейчас

В коде к **событию передачи** относятся (разные уровни, не смешивать):

1. **Stage-driven internal continuity (deprecated, PR-5)** — `should_workforce_handoff_on_stage_change` всегда `false`; не добавлять новые stage-only пути без ADR.
2. **Запись `CandidateHandoff` (canonical internal HR)** — явный запрос передачи; для `destination=internal_hr` workforce **не** создаётся на create, только на **`accept_handoff`** → **`handoff_from_candidate`** + `ensure_hr_operational_context` (см. `handoff.py`, `hr_acceptance_orchestrator.py`).
3. **Client portal `CandidateHandoff`** — отдельные правила блокировки recruitment edits (T3).

Доменная таблица **«HandoffEvent»** как единый лог — **вне scope** этого контракта; при появлении — этот документ обновить.

### B.2 Source и Destination (роли)

| Тип | Source (инициатор) | Destination (получатель ответственности) |
|-----|-------------------|------------------------------------------|
| Stage-driven internal | Recruitment (оператор/рекрутер через смену стадии) | HR / Workforce (операционный владелец сотрудника) |
| `CandidateHandoff` → internal HR | Обычно recruitment-side пользователь (запрос) | Internal HR (accept/reject), кандидат в `processing_by_hr` |
| `CandidateHandoff` → client portal | Agency / recruitment | Client processor / портал |

### B.3 Тип передачи (классификация для спек)

- **T1 — Internal HR (stage-only):** **deprecated (PR-5)** — не использовать в новых фичах.
- **T2 — Internal HR (agency record):** `CandidateHandoff` с `destination = internal_hr` + материализация Workforce на **`accept_handoff`** (не на create).
- **T3 — Client portal:** `CandidateHandoff` с client destination + отдельные правила блокировки recruitment edits.

### B.4 Документы и поля

- **Документы:** не копируются; доступ HR через Document Hub + workforce-scoped API; связь сотрудник↔документ — **`document_entity_links`** (MVP), см. roadmap.
- **Requirements & Evidence (ADR-016):** handoff передаёт **`requirement_fulfillments[]`** — для каждого Requirement: `requirement_code`, `chosen_evidence_variant_code`, `document_id`(s), extracted fields, recruitment verification. HR не выводит legal stay из flat document list. Канон: [`requirement-evidence-model-p0.md`](../platform/requirement-evidence-model-p0.md).
- **Candidate Evidence:** operational fact at handoff — см. ADR-016; snapshot materializes fulfillments from `candidate_evidence` rows (Phase 4).
- **Кандидат после передачи:** может оставаться read-only для recruitment в зависимости от handoff state (см. `handoff.py` blocking rules).
- **WorkforceEmployee:** каноническое представление «принятого в HR» файла; **идемпотентно** по `candidate_id` в рамках tenant.

### B.5 Что создаётся автоматически

- При успешном **`handoff_from_candidate`:** строка **`WorkforceEmployee`** (если ещё нет), спутники bundle (как в сервисе), **`DocumentEntityLink`** (`reused_for_hr`); **`meta.employee_pipeline`** — после закрытия [`hr-handoff-runtime-p0.md`](hr-handoff-runtime-p0.md) gate.
- При **`CandidateHandoff` (internal HR):** pending на create; workforce + HR checklist на **`accept_handoff`** (PR-4).

### B.6 Readonly и запреты (forbidden)

- **Forbidden:** копирование бинарных файлов документов при handoff (инвариант 1 invariants).
- **Forbidden:** рекрутер переводит на **`hired`** при включённом agency handoff lane (enforcement в API).
- **Readonly:** смысл «владения документом» не переносится в Recruitment/HR — владеет Hub; handoff добавляет **права и проверки**, не вторую каноническую копию.

### B.7 Идемпотентность

- Повторная смена стадии на уже «handoff»-код или повторный вызов **`handoff_from_candidate`** для того же `candidate_id` **не должен** плодить второго сотрудника.
- **`ensure_hr_operational_context`** и линки документов — идемпотентны по уникальным ключам в БД.

---

## Связанные файлы кода

- `backend/app/services/workforce_employees.py` — `handoff_from_candidate`, `should_workforce_handoff_on_stage_change` (always false)
- `backend/app/services/handoff.py` — create/accept `CandidateHandoff`, internal HR vs client portal
- `backend/app/services/hr_acceptance_orchestrator.py` — accept → `handoff_from_candidate`
- `backend/app/services/hr_employee_funnel_assignment.py` — `meta.employee_pipeline` (handoff gate)
- `backend/app/services/workforce_hr_operational_context.py` — HR case + document links
- `backend/app/api/v1/tenants/router.py` — флаги tenant link (`handoff_to_client`, `workforce_handoff_on_ready_for_handoff_stage`)

---

## AI Agent Notes

- Перед добавлением новой стадии или нового пути handoff — обновить **этот файл** и [invariants…](invariants-recruitment-hr-document-hub.md) согласованно.
- Не смешивать в одном PR **T1** и **T3** без явного продуктового решения и тестов на оба контура.
