# Lead Conversion Contract (Canonical Matrix)

**Назначение:** зафиксировать **операционный контракт** границы **Lead → Candidate** (и смежные действия) без введения отдельного «matching engine» и без обязательного event bus на первом шаге. Документ задаёт инварианты, допустимые переходы и минимальный payload события `candidate_created`, чтобы ingestion-пути не создавали **Candidate** как побочный эффект.

**Связанные документы:** [lead-to-candidate-operating-model.md](lead-to-candidate-operating-model.md), [lead_to_candidate.md](lead_to_candidate.md), [person-identity-layer-and-roadmap.md](../architecture/person-identity-layer-and-roadmap.md), [handoff-contract.md](../architecture/handoff-contract.md), [applications-operating-model.md](../architecture/applications-operating-model.md), [application-creation-mvp.md](application-creation-mvp.md), [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) (Application status/transition **canon**), [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md) (reconciliation: ветки/код ↔ канон, C2b / I1 и др.), [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md).

**Версионирование:** поле `conversion_contract_version` в audit / событиях должно ссылаться на версию этого документа (например `lead-conversion-contract@1` до первого пересмотра матрицы).

---

## 1. Главная граница

**Webhook / форма / бот не создаёт `Candidate` напрямую как побочный эффект.**

Они создают **lead** и/или **intake record**. Дальше единственный **conversion use-case** решает:

- новый **Candidate**;
- **attach** к существующему **Candidate**;
- **application event** (без нового dossier);
- **duplicate review**;
- **reject**;
- **ожидание недостающих данных** (`request_missing_data` / `keep_as_lead`).

---

## 2. Четыре оси матрицы

### 2.1. Lead state

- `new`
- `assigned`
- `unassigned`
- `in_review`
- `duplicate_review`
- `qualified`
- `rejected`
- `converted`
- `attached_to_existing`

### 2.2. Duplicate resolution

- `no_duplicate`
- `exact_duplicate`
- `possible_duplicate`
- `existing_employee`
- `active_handoff`
- `unclear_identity`

### 2.3. Action

- `create_candidate`
- `attach_to_existing_candidate`
- `create_application_event`
- `move_to_duplicate_review`
- `keep_as_lead`
- `reject_lead`
- `request_missing_data`
- `reactivate_existing_candidate`

(При необходимости отдельно фиксируется `convert_draft_to_candidate` как вариант `create_candidate` с предикатом «есть черновик/квалификация» — см. строку матрицы для `qualified`.)

### 2.4. Required context (минимум)

| Поле | Смысл |
|------|--------|
| `owner_company_id` | Компания-владелец операционного контекста |
| `source` | Канал / кампания / внешний источник |
| `contact` | Достаточный контакт для идентичности и связи |
| `actor/system source` | Кто инициировал (пользователь, система, интеграция) |
| `duplicate decision` | Результат и, при review, ссылка на решение |
| `vacancy context, if known` | Если известна — передаётся; иначе явно «unknown» |
| `assignment_state` | **Уточнять область:** состояние очереди **lead** vs политика на стороне **candidate** после конверсии; в payload не смешивать в одном поле без префикса (`lead_assignment_state` / `candidate_assignment_state`) |
| `conversion_contract_version` | Версия контракта для audit и replay |

---

## 3. Практическая матрица

| Lead state | Duplicate result | Allowed action | Required context | Forbidden |
|------------|------------------|----------------|------------------|-----------|
| `new` / `unassigned` | `no_duplicate` | `create_candidate` | `owner_company_id`, `source`, `contact`, `assignment_state` (с явной областью) | создать без `owner_company_id` |
| `new` / `unassigned` | `exact_duplicate` | `attach_to_existing_candidate` + lead/application event | `matched_candidate_id`, `duplicate_reason` | создать второй **Candidate** |
| `new` / `unassigned` | `possible_duplicate` | `move_to_duplicate_review` | `matched_candidates[]`, `matched_fields` | авто-создание **Candidate** |
| `assigned` | `no_duplicate` | `create_candidate` | ответственный рекрутер/система, `owner_company_id` | обход assignment / ownership |
| `assigned` | `exact_duplicate` | `attach_to_existing_candidate` | `matched_candidate_id` | создать новый dossier |
| `duplicate_review` | рекрутер подтвердил того же человека | `attach_to_existing_candidate` | `actor_id`, `decision_reason` | «тихий» merge без audit |
| `duplicate_review` | рекрутер подтвердил нового человека | `create_candidate` | `actor_id`, `decision_reason` | создать без audit решения |
| `unclear_identity` | любой | `request_missing_data` / `keep_as_lead` | `missing_fields` | `create_candidate` |
| `existing_employee` | exact match | `create_application_event` / reactivation review | `employee_id`, HR owner status | создать нового **Candidate** как дубликат сотрудника |
| `active_handoff` | exact match | attach event / notify owner | `handoff_id`, `operational_owner` | создать конкурирующий dossier |
| `qualified` | `no_duplicate` | `create_candidate` или `convert_draft_to_candidate` | `qualification_result` | создать без события / без фиксации контекста |
| `rejected` | запрошена реактивация | `reactivate_existing_candidate` или новая application | `previous_rejection_reason`, `actor_id` | молча перезаписать старый reject |
| `converted` | любой | no-op / attach new source event | `candidate_id` | создать ещё одного **Candidate** для того же контура без явного правила |

*(Матрица не исчерпывает все комбинации: новые строки добавляются только с обновлением `conversion_contract_version`.)*

---

## 4. Сквозные правила (обязательные к инженерной реализации)

### 4.1. Идемпотентность ingestion

Для webhook / form / bot: ключ идемпотентности (например `(source, external_id)` или стабильный хэш payload), чтобы повторная доставка не порождала второй lead и не запускала гонку конверсии дважды.

### 4.2. Согласованность `duplicate_review`

При параллельных решениях: optimistic lock по lead или явная семантика «первое решение победило / второе отклонено с причиной».

### 4.3. Один путь создания Candidate

Все ingestion-пути вызывают **один** conversion use-case; создание строки **Candidate** в обход — запрещено политикой контракта.

---

## 5. Событие `candidate_created` (payload)

Полноценный event bus не обязателен на старте; достаточно **единого audit-записываемого payload** (таблица audit / outbox позже).

| Поле | Смысл |
|------|--------|
| `event_name` | `candidate_created` |
| `schema_version` / `conversion_contract_version` | Версия payload и контракта |
| `tenant_id` | Tenant |
| `owner_company_id` | Компания-владелец |
| `source_lead_id` | Исходный lead |
| `source_channel` | Канал |
| `actor_type` | `system` / `user` / `webhook` / `bot` |
| `actor_id` | Если есть |
| `creation_mode` | `manual` / `semi_auto` / `auto` |
| `duplicate_result` | Из оси duplicate resolution |
| `duplicate_decision_id` | Если был review |
| `vacancy_id` | Если известна |
| `assignment_state` | С **явной областью** (lead vs candidate) |
| `recruiter_id` | Если уже назначен |
| `reason` | Человекочитаемое / структурированное обоснование |

---

## 6. Первый engineering slice

**Цель:** убрать «тихое создание кандидата» из разных ingestion paths.

**Реализация v1 (lead processing):** `backend/app/modules/leads/lead_candidate_conversion.py` — `create_candidate_from_lead_conversion` (вызов из `modules/leads/service/_processing.py` и `_reroute.py`); audit через `activity_log` / `candidate_created`.

**Реализация (public / Telegram intake):** `backend/app/services/intake_channel_candidate.py` — `create_public_intake_draft_via_service`, `create_telegram_intake_bootstrap_via_service`; тот же `candidate_created` с `intake_bootstrap=True`, `source_channel` `public_intake` / `telegram`, `creation_mode` `semi_auto` / `manual_bot`, `stable_intake_id` + `stable_intake_id_kind`.

**Conversion use-case wrapper** — единая функция/сервис, который:

1. Принимает lead/intake input.
2. Проверяет `owner_company_id`.
3. Проверяет duplicate result (или инициирует `move_to_duplicate_review`).
4. Решает: create vs attach vs review vs reject vs wait.
5. Создаёт **Candidate** только через один путь.
6. Пишет audit payload с `conversion_contract_version`.

**Вне scope первого слайса:** smart routing, skills/geo, AI, отдельная сущность `CandidateVacancyMatch`, нагрузочное вешание на все channel-specific адаптеры сразу — только маршрутизация вызовов в единый wrapper.

---

## 7. Несоответствия с текущим кодом

Сегодня часть путей может всё ещё создавать **Candidate** напрямую (см. [lead_to_candidate.md](lead_to_candidate.md)). Этот документ — **целевой контракт**; миграция ingestion на wrapper выполняется поэтапно с чеклистом путей: Meta, manual, Telegram, public intake, import, duplicate attach, reactivation.

**Инвентаризация точек создания (аудит):** [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md).

**Идемпотентность ingestion по `external_id`:** [lead-ingestion-external-id-idempotency.md](lead-ingestion-external-id-idempotency.md).

**Уточнение по audit `candidate_created`:** поле `assignment_state` в payload отражает состояние **на момент INSERT dossier** (сразу после `create_candidate_full`), а не итог после полного каскада `record_candidate_reassignment` в lead-processing.
