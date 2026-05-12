# Current Separation Status — Recruitment, Document Hub, HR

Инвентаризационный снимок после **operational verification** (журнал §6.3 в [`implementation-roadmap-single-tenant-hr-handoff.md`](implementation-roadmap-single-tenant-hr-handoff.md)).  
Цель: **не новая архитектура**, а ясность — что отделено, что частично, где legacy, что тестировать дальше.

---

## Уже подтверждено (сводка)

| Область | Статус |
|--------|--------|
| Recruitment → HR handoff | работает |
| Candidate → WorkforceEmployee | работает |
| HR Case / operational context | работает |
| Документы из Recruitment видны в HR | работает |
| Документы не копируются | подтверждено |
| HR review документов | работает |
| Открытие файлов из HR через Document Hub | исправлено и работает; видимость **Open** — по **`document.id`** (Hub); **`GET /workforce/employees/{id}/documents`** не отдаёт recruitment URL `.../candidates/.../documents/.../file` (`cand_doc_for_workforce_hr_response`) + тесты |
| Повторный handoff | без дублей |
| Return to recruitment | работает |
| Recruitment write lock после HR materialization | работает |
| Admin override | работает |
| Bulk paths под lock | проверены |
| Fleet boundary | не связан скрыто с Candidate / HR context |

---

## Сводная таблица: домены

| Domain | Owns (operational) | Confirmed routes (примеры) | Confirmed contracts | Legacy coupling | Next validation |
|--------|-------------------|----------------------------|---------------------|-----------------|-----------------|
| **Recruitment** | Lead, Candidate, Vacancy, pipeline/stages, сбор документов как UX flow, **handoff trigger** | `GET/PATCH /api/v1/candidates/{id}`, stage-history, notes, pipeline-overrides, next-action | После HR materialization **обычный recruiter `PATCH` → 403**; read остаётся | Часть document flows всё ещё candidate-facing | Не лезть в HR case / не создавать employee в обход handoff; audit UI на `can_edit` |
| **HR / Workforce** | WorkforceEmployee, HR case / operational context, HR document review, **ownership после materialization**, return to recruitment | `GET /workforce/employees`, `GET …/{id}`, `…/documents`, `…/hr-bundle`, `…/hr-operational-context`, `POST …/hr-review`, `GET …/return-to-recruitment/eligibility` | Один employee на контур reuse; HR review **не копирует** файлы; return **снимает** recruitment lock | Полный HR module (контракты, ZUS, termination и т.д.) вне текущего контура | Contracts, permits, onboarding lifecycle, termination — отдельные прогоны |
| **Document Hub** | Файл по `document_id`, reuse между Candidate и Employee, checks/reviews, **нет копирования blob** | `GET /api/v1/db/documents/{document_id}/file`, `GET …/checks` | HR preview **только** через Hub (authenticated client), не через `…/candidates/…/documents/…/file` в новой вкладке | Candidate summary / legacy candidate file route всё ещё существуют | **Приоритет:** инвентаризация + ownership legacy routes; запрет случайного reuse candidate file URL в HR/Fleet/Services UI |
| **Handoff** | Контракт передачи edit responsibility; stage-driven и row-driven сценарии | `GET /handoffs/pending-with-candidates`, `CandidateHandoff` API, stage → materialization | `ready_for_hr` — internal HR route; `ready_for_handoff` + флаг `workforce_handoff_on_ready_for_handoff_stage`; **WorkforceEmployee existence = operational ownership transfer** | Нет единой таблицы «handoff events» (MVP: несколько механизмов) | При contradiction — фиксировать, какой путь source of truth; не унифицировать «в теории» без стенда |
| **Fleet** | Транспортный домен изолированно | `/api/v1/fleet/*` | Нет прямого Candidate / CandDoc / HR operational context; связь с HR только **`workforce_employee_id`** | — | HR → Fleet lifecycle как **отдельный** operational flow (не смешивать с текущим contour) |

---

## Recruitment — что отделено

**Отвечает за:** Lead, Candidate, Vacancy, pipeline/stages, candidate documents collection как пользовательский flow, **handoff trigger**.

**Не должен после handoff:** редактировать candidate dossier (для обычного рекрутёра); создавать employee «в обход» канона; управлять HR case; копировать документы.

**Сейчас:** граница **частично enforced** (write lock + bulk + return semantics на стенде подтверждены).

---

## HR / Workforce — что отделено

**Отвечает за:** WorkforceEmployee, HR case / operational context, HR document review, ownership после materialization, return to recruitment.

**Сейчас:** первый HR contour работает как **отдельный** измеримый цикл (см. §6.3 журнала).

---

## Document Hub — что отделено

**Отвечает за:** открытие файла через `GET /api/v1/db/documents/{document_id}/file`, reuse документа между Candidate и Employee, checks/reviews, отсутствие копирования.

**Сейчас:** Hub ведёт себя как **shared layer**; часть **старых** candidate document endpoints всё ещё живёт (не обязательно ошибка MVP, но **риск повторного coupling** в UI/модулях).

---

## Handoff — что подтверждено

**Контракты:** `ready_for_hr`; `ready_for_handoff`; `workforce_handoff_on_ready_for_handoff_stage`; handoff передаёт **edit responsibility**; **`WorkforceEmployee` = ownership marker**.

**Сейчас:** контракт подтверждён **execution**; единая event-модель handoff **не** требуется для MVP, но это осознанный технический долг.

---

## Fleet

**Сейчас:** отдельный домен; boundary **PASS** по коду; **HR → Fleet lifecycle** как operational flow **ещё не** был целью текущего контура.

---

## Что ещё не полностью ясно

1. **Document Hub vs legacy** — static inventory зафиксирована в § «Document Hub vs legacy — инвентаризация по коду»; риск остаётся **процессный**: новые экраны или интеграции могут снова привязаться к `file_url` / candidate `/file` без ревью.
2. **Handoff events** — несколько механизмов (stage-driven, `CandidateHandoff`, workforce row); контракт есть, унифицированной event-таблицы нет.
3. **HR module** — вне текущего контура: contracts, permits, ZUS, onboarding checklist, termination и т.д.
4. **Communications / Activity / Notifications** — в логах участвуют; отдельно не проверялись на hidden orchestration, мутацию чужого state, Telegram bypass.

---

## Позиция по roadmap

Завершён первый **измеримый** contour: **Recruitment → Document Hub → HR** — задеплоено, протестировано, contradiction найден и закрыт, повторно подтверждено (§6.3).

---

## Рекомендуемый следующий validation-контур

**Статус контура «Document Hub vs legacy candidate document routes» (2026-05-06):** в **хорошем состоянии** до следующего contradiction или нового evidence — static audit, запись в §6.3, preventive cleanup HR (**Open** только от Hub-идентичности `document.id`), регрессионные тесты. Ниже — **чеклист для повторного** прогона при регрессии или расширении scope.

**Document Hub vs legacy candidate document routes** — **practical engineering contour** (инвентаризация + стенд + при необходимости минимальные фиксы). **Не новая спека** — только исполнимые артефакты ниже.

### Фокус (конкретно)

1. **Кто ещё использует candidate document endpoints** — backend callers, frontend `api/*`, прямые `fetch`/`<a href>`.
2. **Какие UI-компоненты считают Candidate владельцем документов** — не только Recruitment; HR/Fleet/Services/admin при необходимости.
3. **Где `file_url` всё ещё recruitment-oriented** — ответы API, нормализаторы, копипаста в новых экранах.
4. **Где есть прямые CandDoc assumptions вне Recruitment** — типы, хелперы, скрытый reuse recruitment DTO.
5. **Кто может мутировать document state напрямую** — обход Hub/политики владения; кто вызывает write из чужого домена.
6. **Где Hub пока только facade над старой моделью** — честная фиксация (корректный внешний контракт при внутреннем legacy-пути — ок до contradiction).
7. **Read/write policy** — кто может **читать**, кто **менять**, кто только **линкует / review’ит**; регрессия: не-recruitment UI **не** открывает candidate `/file` без `Authorization`.

### Допустимый результат прогона (ровно один или несколько)

* **Список** найденных legacy uses (маршруты + вызывающие стороны).
* **Подтверждение**, что конкретный route/component **безопасен** (краткая запись + при необходимости стенд).
* **Contradiction** (нарушение политики / ownership).
* **Минимальный fix** + **regression test** при contradiction.
* **Запись evidence** в **§6.3** журнала [`implementation-roadmap-single-tenant-hr-handoff.md`](implementation-roadmap-single-tenant-hr-handoff.md) — строка или отдельная строка таблицы, без раздувания канона.

Рабочая цепочка: **facts → таблица маршрутов/components → contradiction (если есть) → минимальный фикс → §6.3**.

---

## Document Hub vs legacy — инвентаризация по коду (static audit)

**Дата:** 2026-05-06. **Метод:** ripgrep по `HostFlow/backend` и `HostFlow/hostflow-frontend` (маршруты `candidates/.../documents`, `CandDoc`, `file_url`, вызовы `docsApi`).

**Вывод:** новой **contradiction** относительно политики «HR не открывает candidate `/file` в новой вкладке без авторизации» **не обнаружено** — поведение HR уже приведено к Hub (`downloadDocumentFile`). Ниже — фиксация **кто что вызывает**, чтобы не плодить скрытый reuse.

### Таблица: legacy candidate document surface (backend)

| Маршрут / артефакт | Назначение | Риск coupling | Примечание |
|--------------------|------------|---------------|------------|
| `backend/app/api/v1/candidate_documents.py` (`/api/v1/candidates/.../documents`, `.../file`) | REST v1 под префиксом candidates | Средний для внешних клиентов; SPA не ходит сюда за основным UX | Остаётся совместимостью и тестами; мутации и ACL — в этом роутере |
| `CandDoc.from_document` → `file_url` = `/api/v1/candidates/{cid}/documents/{did}/file` | DTO для списков | Низкий, если UI **не** навигирует по строке | Presigned/`path` в `file_url` **перезаписываются** этим URL при наличии `candidate_id` + `id` |
| `GET /workforce/employees/{id}/documents` → `List[CandDoc]` | HR-доступ к досьме без прямого вызова candidates API | Низкий | **Sanitized:** `cand_doc_for_workforce_hr_response` — `file_url` = `null`, вложенные `url` с candidate `/file` убраны; клиент открывает файл через Hub по `id` |
| `backend/app/api/public/intake.py` — ссылки на `.../candidates/.../file` | Публичный кабинет / intake | Ожидаемо recruitment-facing | Не HR workspace |
| `vacancies/router.py` → `apply_template_to_candidate_impl` | Автоподстановка шаблонов | К домену Recruitment | Имплементация рядом с legacy candidate documents |
| `scripts/seed.ts` — `POST /candidates/{id}/documents` | Сиды | Dev-only | Не production UI |

### Таблица: Document Hub (frontend recruitment + общие модули)

| Клиент | Вызовы | Заметка |
|--------|--------|---------|
| `hostflow-frontend/src/api/client.ts` — `listCandidateDocuments`, `createCandidateDocument`, summary, export | `docsApi` → `/candidate/{id}/documents`, `/documents/...` | База **не** `/api/v1/candidates/.../documents` для основного SPA |
| `modules/documents/CandidateDocuments.tsx`, превью | `getDocumentFileUrl` / `downloadDocumentFile` → Hub | Recruitment UX на Hub |
| `pages/hr/HrEmployeeDocumentsSection.tsx` | Список: `GET .../workforce/employees/{id}/documents`; открытие: `downloadDocumentFile(documentId)` | Кнопка **Open** по **`document.id`**; байт — Hub (`hostflow-frontend/src/pages/hr/__tests__/HrEmployeeDocumentsSection.test.tsx`) |
| `api/workforce.ts` — `listWorkforceEmployeeDocuments` | Нормализация CandDoc → `Document` | Поле **`downloadUrl` удалено** — сервер не подставляет recruitment URLs в HR-ответ |

### Итог по чеклисту контура

1. **Кто использует candidate document endpoints:** в основном **backend** (роутер, публичный intake, тесты, seed); **hostflow-frontend** не дергает `/api/v1/candidates/{id}/documents` для карточки кандидата — использует Hub.
2. **UI «владелец — Candidate»:** документный UX рекрутинга завязан на **candidate id как owner** в Hub (`/candidate/{id}/...`), что корректно для Recruitment; HR не дублирует редактор, только список + review + Hub file.
3. **`file_url`:** в **recruitment** `CandDoc` по-прежнему может указывать на candidate `/file`; в **workforce HR list** это поле **не отдаётся** (и вложенные legacy URLs вычищаются). Канон для HR UI: Hub-идентичность `document.id`.
4. **CandDoc вне Recruitment:** workforce list — sanitized `CandDoc`; фронт не выводит отдельный download URL из этого ответа.
5. **Мутации state:** HR — `POST .../hr-review` (отдельный контракт); recruitment — Hub `patch`/`check` из `CandidateDocuments`.
6. **Hub vs facade:** workforce documents — **facade** над тем же документным рядом + **sanitized** `CandDoc`; файловый байт — только Hub.
7. **Read/write:** соответствует ранее зафиксированной политике; **новых** нарушений в статике нет.

**Follow-up / статус:** *выполнено (frontend + backend).* HR UI: **Open** только от **`document.id`** + Hub. Backend: **`GET /workforce/employees/{id}/documents`** не содержит recruitment `.../candidates/.../documents/.../file` в JSON. **Legacy** candidate file route остаётся там, где оправдано (recruitment API, public intake и т.д.), не в HR workforce list. Регрессия: `test_workforce_employee_documents.py::test_workforce_employee_documents_omit_legacy_candidate_file_url`, `test_single_tenant_recruitment_hr_handoff_flow.py` (assert по телу ответа).
