# Audit: где создаётся `Candidate` (обход conversion wrapper)

**Цель:** инвентаризация точек **INSERT** в `candidates` / создания ORM-объекта `Candidate`, чтобы позже завести единый **conversion wrapper** (см. [lead-conversion-contract.md](lead-conversion-contract.md)) и не оставлять «тихих» путей.

**Связанные документы (Application intent):** [application-creation-mvp.md](application-creation-mvp.md), [recruitment-application-lifecycle.md](recruitment-application-lifecycle.md), [recruitment-application-lifecycle-sync-note.md](recruitment-application-lifecycle-sync-note.md), [applications-operating-model.md](../architecture/applications-operating-model.md), [slice-4-activity-continuity-guards.md](slice-4-activity-continuity-guards.md) (first-contact continuity на Candidate — не путать со статусом Application).

**Метод:** статический поиск по `backend/app` на `create_candidate_full`, `insert(Candidate)`, `Candidate(` + `db.add`, вызовы пайплайна лидов. Тесты и `backend/tests/**` в таблицу не входят.

**Канонический writer сегодня:** `backend/app/api/v1/candidates/service.py::create_candidate_full` — выполняет `insert(Candidate).values(...)`, quota, stage/RODO guards, recruiter assignment, `record_candidate_reassignment` / activity. Все вызовы `create_candidate_full` считаются **одним семейством** (wrapper должен оборачивать именно финальное решение «создать dossier», а не обязательно заменять функцию в один шаг).

---

## Таблица entry points

| Entry point | Текущее поведение | Создаёт `Candidate` напрямую? | Должен идти через conversion wrapper? | Риск |
|-------------|-------------------|-------------------------------|----------------------------------------|------|
| **POST `/api/v1/candidates`** — `candidates/router.py` → `cand_service.create_candidate_full` | Ручное создание из UI/API: валидация, vacancy/company, auto-assign recruiter, история стадий | Да (`create_candidate_full` → `insert`) | Да: предикаты конверсии + явный `candidate_created` / `conversion_contract_version` | Средний: осознанное действие пользователя, но обход «lead → conversion» если форма не привязана к lead |
| **`process_normalized_lead`** — `modules/leads/service/_processing.py` | Единый пайплайн лида: Lead в БД, дубликаты, routing, затем при конверсии **`create_candidate_full`**; ветки duplicate могут только **привязать** существующего кандидата | Да, **если** дошли до конверсии (не duplicate-only) | Да — **центральный high-volume путь** | Высокий: объём ingress, политики auto/semi-auto, повторная доставка |
| **Meta GET/POST webhook** — `modules/leads/webhook.py` → `service.process_meta_lead` | Hydrate → тот же пайплайн, что Meta POST | Как у `process_normalized_lead` | Да | Высокий |
| **POST `/api/v1/leads/meta`** — `modules/leads/router.py::ingest_meta_lead` | Прямой JSON Meta → `process_meta_lead` | Как выше | Да | Высокий |
| **POST `/public/leads/inbound/{webhook_secret}`** — `modules/leads/inbound_public.py` | Generic JSON → `process_generic_inbound_webhook_lead` → `process_normalized_lead` | Как выше | Да | Высокий |
| **Lead CSV import** — `services/imports/leads.py` | Строка → `leads_service.process_normalized_lead` | Как выше | Да | Высокий |
| **Reprocess / manual process lead** — `modules/leads/router.py` + `service/_bulk.reprocess_stored_lead_payload` | Повторный прогон сохранённого payload | Как у `process_normalized_lead` | Да | Средний: риск двойной конверсии при неверном idempotency |
| **Bulk auto-process Meta queue** — `service/_bulk.bulk_auto_process_meta_lead_queue` | Пакетный `process_meta_lead` | Как выше | Да | Высокий |
| **Lead retry** — `service/_retry.py` (вызов `process_meta_lead`) | Повтор неуспешных лидов | Как выше | Да | Средний |
| **Lead reroute (создание нового кандидата)** — `modules/leads/service/_reroute.py` | При определённых re-route ветках вызывается **`create_candidate_full`** напрямую (не только update) | Да | Да | Средний: **второй прямой вызов** `create_candidate_full` вне «очевидного» ingest тела `_processing` |
| **Public intake «новая анкета»** — `api/public/intake.py` | Через `services/intake_channel_candidate.create_public_intake_draft_via_service` → `create_candidate_full` + PATCH intake-колонок; audit `candidate_created` (`intake_bootstrap`, `source_channel=public_intake`, `creation_mode=semi_auto`) | Да (канонический INSERT) | — | Повтор с тем же контактом — существующий `_find_candidate_by_contact` + audit `idempotent_replay` на reuse |
| **Telegram intake** — `candidate_link._create_candidate_from_telegram_intake` | Делегирует в `create_telegram_intake_bootstrap_via_service` → `create_candidate_full` + link; audit (`source_channel=telegram`, `creation_mode=manual_bot`); idempotent по `telegram_chat_id` | Да (канонический INSERT) | — | — |
| **`candidates.repo`** — `api/v1/candidates/repo.py` | Только list/get/update/delete; **INSERT кандидата в repo нет** (удалён мёртвый `create_candidate`) | Нет | — | — |
| **Seeds / demo** — `db/seeds/recruitment_team_flow_scenario.py`, `services/onboarding_demo_seed.py` | Прямой ORM для сценариев/онбординга | Да | Нет для production (исключение для фикстур) | Низкий для эксплуатации |

**Не создают нового Candidate (для полноты):** ветки `process_normalized_lead`, где лид помечается как duplicate и указывается существующий `candidate_id` (attach / review) — INSERT нет, риск «лишнего dossier» ниже, но **инварианты attach vs merge** остаются на duplicate-слое.

**Scanner:** роутер сканера в `main.py` отключён (`None`); отдельного пути создания `Candidate` из scanner в активном приложении не найдено.

---

## Рекомендация: первый PR (узкий)

Не переписывать все ingestion paths сразу.

**Статус (v1):** реализован модуль `backend/app/modules/leads/lead_candidate_conversion.py` — `create_candidate_from_lead_conversion` оборачивает вызов `create_candidate_full` из `service/_processing.py` и `service/_reroute.py`, пишет `activity_log` с `action=candidate_created` и payload (в т.ч. `conversion_contract_version=lead-conversion-contract@1`), идемпотентный short-circuit если у лида уже есть `candidate_id` на живой строке `candidates`.

**Статус (v1.1):** повторная доставка с тем же `tenant_id + source + external_id` — см. [lead-ingestion-external-id-idempotency.md](lead-ingestion-external-id-idempotency.md): lookup до INSERT, уникальный индекс, `begin_nested` + `IntegrityError` → повторный `get_lead_by_external_id` в `service/_processing.py`; тест `test_meta_webhook_redelivery_same_external_id_single_lead_and_candidate` в `tests/api/test_leads_meta.py`.

1. **Первый PR — семейство `process_normalized_lead` (одна точка):**  
   Ввести **conversion wrapper** (функция/сервис), который:
   - вызывается из `_processing.py` в единственном месте **перед** созданием нового dossier (там, где сегодня `create_candidate_full`);
   - проверяет предикаты контракта (минимум: `owner_company_id` / контекст компании, duplicate gate уже пройден);
   - вызывает существующий `create_candidate_full` как низкоуровневый writer **или** оставляет его внутри wrapper;
   - пишет **audit payload** с `conversion_contract_version=lead-conversion-contract@1` и полями из контракта `candidate_created` (хотя бы в существующий activity/лог-слой, без обязательного bus).

   Это автоматически покрывает **Meta webhook**, **POST /leads/meta**, **generic public webhook**, **import**, **bulk**, **retry**, **manual reprocess** — всё идёт в `process_normalized_lead`.

2. **Второй PR (по желанию в той же волне или сразу после):**  
   - **`_reroute.py`**: перевести вызов `create_candidate_full` на тот же wrapper (сейчас отдельный прямой вызов).  
   - **Тест:** повторная доставка с тем же `(source, external_id)` / повторный прогон **не создаёт второй** `Candidate` (идемпотентность на уровне лида + конверсии — уточнить текущее поведение `get_lead_by_external_id` и статусы лида).

3. **Отдельный PR:** **public intake** и **Telegram** — либо вызов общего wrapper с режимом `creation_kind=intake_draft`, либо явная спецификация в контракте, почему это не «conversion» (но тогда всё равно один writer для INSERT, чтобы не плодить drift).

---

## Финальный grep-audit (`backend/app/`) — boundary **PASS**

Проверка (ориентиры: `Candidate(`, `insert(Candidate`, `db.add(...candid`, `create_candidate_full(`), **без** `backend/tests/**`.

| Сигнатура | Находки в `app/` | Вердикт |
|-----------|------------------|---------|
| `create_candidate_full(` | `candidates/service.py` (определение), `router.py`, `lead_candidate_conversion.py`, `intake_channel_candidate.py` (×2) | Только канонические вызовы |
| `insert(Candidate` | `candidates/service.py` (одна строка внутри `create_candidate_full`) | Единственный SQL INSERT в проде |
| `Candidate(` (ORM конструктор) | `db/seeds/recruitment_team_flow_scenario.py`; `services/onboarding_demo_seed.py` | Только сиды/демо в `app/` |
| `db.add(candidate` / `session.add(Candidate` | `onboarding_demo_seed.py` (`db.add(c)`); `recruitment_team_flow_scenario.py` (`session.add(Candidate(...))`) | Только сиды/демо |
| Ложное срабатывание | `communications_allocator.AllocationCandidate(...)` — не модель `Candidate` | Игнорировать |

**Anti-regression:** мёртвый `candidates/repo.py::create_candidate` удалён — второй INSERT-path через repo больше не экспортируется.

---

## Связь с документом контракта

Матрица состояний и событие `candidate_created`: [lead-conversion-contract.md](lead-conversion-contract.md).
