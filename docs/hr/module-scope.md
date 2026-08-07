# Модуль HR (Human Resources): цель и состав функций

Документ фиксирует **целевой охват** HR-модуля и границы с CRM. Оргструктура описана как **часть** этого модуля; реализация по пунктам ведётся постепенно — статус в коде см. раздел «Статус». При изменении продукта или API обновляйте этот файл в том же изменении, что и код.

## Суть HR-модуля: пять вопросов

HR-модуль в целом должен давать тенанту ответы на **пять операционных вопросов** по каждому нанятому человеку (и в агрегате по организации).

**Канонические формулировки (продукт):**

1. Может ли человек **легально** работать?
2. Все ли **документы действительны**?
3. **Кто и сколько** должен ему **заплатить**?
4. Есть ли **больничные, отпуска, отсутствия**?
5. **Переданы ли данные** в бухгалтерию / ZUS / TMS?

Таблица ниже раскладывает те же вопросы на требования к продукту и текущий код.

| № | Вопрос | Что должен обеспечивать продукт | Ориентир в продукте / коде | Зрелость |
|---|--------|---------------------------------|----------------------------|----------|
| **1** | **Может ли человек легально работать?** | Право на работу, основание занятости, статусы комплаенса (не путать с «просто документ в досье»). | Трудовые договоры / найм: `workforce_employments`; связка с кандидатом и этапами найма; в перспективе явный контур «right to work» и HR-документы. | Частично (MVP хранение контрактов/найма) |
| **2** | **Все ли документы действительны?** | Реестр сроков, просрочки, напоминания; разделение документов **кандидата клиента** и **кадровых** документов сотрудника. | Документы по связанному `candidate_id`: HR workspace → API документов кандидата; отдельный каталог HR-документов — по решению продукта. | Частично (через кандидата) |
| **3** | **Кто и сколько должен ему заплатить?** | Ставка, модель начисления, валюта, статус готовности к выплате; связь с занятостью. | `workforce_payroll_profiles`, поля ставки/валюты/`payroll_status`; договорённости в `workforce_employments` (`rate_model` и т.д.). | MVP данные (не расчёт зарплаты «до копейки» без отдельной спеки) |
| **4** | **Есть ли больничные, отпуска, отсутствия?** | Учёт периодов, статусы, влияние на расчёт (флагами), история. | `workforce_absences`, `workforce_leave_requests`; UI на карточке HR employee. | MVP хранение и CRUD |
| **5** | **Переданы ли данные в бухгалтерию / ZUS / TMS?** | Явные статусы handoff, ссылки на внешние системы, аудит «кто и когда отправил». | ZUS: `workforce_zus_profiles`; бухгалтерия: `payroll_status`, `external_refs` в payroll; TMS — интеграции вне текущего MVP или через Fleet/TMS модуль по решению. | Частично (поля и статусы, без полной интеграции всех систем) |

**Оргструктура и связка с учётной записью** (`org_units`, `linked_user_id`) отвечают не на эти пять вопросов напрямую, а на **«где человек в организации и под каким логином»** — это опора для доступов, отчётности и будущего headcount (см. блоки ниже).

Любая новая функция HR должна явно маппиться на один или несколько из вопросов 1–5 (или на явный вспомогательный слой: оргструктура, должности, аудит).

## Цель

Дать тенанту возможности для **управления людьми как сотрудниками организации** так, чтобы можно было последовательно закрывать вопросы **1–5** выше: от легальности и документов до выплат, отсутствий и передачи в учётные контуры. Дополнительно — формальная структура подразделений и связь с пользователями воркспейса. Контур **отделён** от операционного CRM-рекрутинга (вакансии клиентов, кандидаты, пайплайн), но может **наследовать** данные из найма (`candidate_id`, снимки).

### Разделение с CRM

| Область | CRM (рекрутинг / клиенты) | HR (внутренний контур) |
|--------|---------------------------|-------------------------|
| Основной объект | Кандидат, вакансия, клиент | Сотрудник (Workforce), ответы на вопросы **1–5**; оргструктура — вспомогательный справочник |
| Иерархия задач | Руководитель рекрутера в найме | Формальные подразделения и команды |
| Доступ к компаниям | Компании клиентов, ACL | Оргюниты и HR-сущности (по мере появления) |

**Важно:** оргструктура **не заменяет** поле руководителя (supervisor) у пользователя — это **линия отчётности в приложении** для операционных сценариев; дерево оргюнитов — **справочник подразделений и членства**.

## Порядок внедрения и пул настроек

**Employee pipeline (P0, shipped):** company-scoped воронки `module_key=hr`, `type=employee` — bootstrap, `resolve_hr_employee_funnel`, runtime binding на `WorkforceEmployee.meta.employee_pipeline`, `/meta/stages?pipeline_type=employee`. Gate: [`hr-employee-pipeline-p0.md`](../specs/architecture/hr-employee-pipeline-p0.md) (**CLOSED**). Recruitment не обязателен для HR-only tenant.

**ADR-035:** HR pipelines are **object-typed** (`WorkforceEmployee`), built from **operational stages** + platform **system transitions** (e.g. `handoff_to_fleet`, close). Templates → company instances. Exit to Fleet creates Fleet assignment linked to Employee — not a renamed Employee. See [`ADR-035-module-object-pipeline-settings.md`](../specs/architecture/ADR-035-module-object-pipeline-settings.md).

Публичный сбор данных (анкеты сотрудника, ZUS, согласия и т.д.) — контур **Forms** как платформенной capability, см. [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md) и [`../forms/module-scope.md`](../forms/module-scope.md). Кадровые документы и reuse файлов из Recruitment — **Document Hub** ([`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md), [`../document-hub/module-scope.md`](../document-hub/module-scope.md)).

**Настройки (канон):** три уровня — **Tenant → Company → Company Module Settings**; см. [`ADR-005`](../specs/architecture/ADR-005-three-level-settings-hierarchy.md). Кратко:

| Уровень | Что хранит для HR |
|--------|-------------------|
| **Tenant** | Лицензия: модуль `hr` включён на workspace, матрица ролей, security, audit, **только presets по умолчанию** — не операционные шаблоны конкретной компании |
| **Company** | `enabled_modules`, юрданные, роли/пользователи company, visibility, оргструктура и т.д. |
| **Module Settings (per company)** | Employee pipeline (`employee_pipeline_funnel_id`), employment/contract templates, HR document templates, ZUS checklist, work permit rules, HR assignment rules — `(company_id, module_key=hr, settings_json)`; **`HrModuleSettingsV1`**; bootstrap + resolver + CMS PATCH validation (gate H1–H6). |

Рекрутинг не обязан существовать: HR-only company конфигурируется независимо. Текущий код может ещё опираться на `tenant.settings`; новые фичи — с **company scope** по ADR-005.

## Функциональные блоки (логические подсистемы)

Сопоставление с вопросами **1–5**: в скобках — номера.

| Блок | Назначение |
|------|------------|
| **Каталог сотрудников (Workforce)** | Единая запись сотрудника, статусы жизненного цикла, связь с кандидатом и опционально с `User` (`linked_user_id`). Якорь для **1–5**. |
| **Труд / договоры (Employments)** | Контракты, ставки, график в модели данных — вопрос **1**, база для **3**. |
| **Зарплатный профиль (Payroll)** | Кто платит, сколько, статус готовности — вопрос **3**; handoff — **5** (бухгалтерия). |
| **ZUS** | Регистрации и формы — вопрос **5** (PL). |
| **Отсутствия и отпуска** | Больничные, отпуска, прочие отсутствия — вопрос **4**. |
| **Документы** | Действительность и сроки — вопрос **2** (сейчас частично через досье кандидата). |
| **Оргструктура** | Подразделения и членство пользователей; инвайты с `org_unit_id` — вспомогательный слой (не 1–5). |
| **Должности и грейды** | Справочник позиций — усиливает **1** и **3** по политике продукта — *(развитие)*. |
| **Аналитика HR** | Своды по headcount, отсутствиям, затратам — *(развитие)*. |

Оргструктура — **базовый справочник** для «где сидит человек в организации»; вопросы **1–5** закрываются прежде всего **каталогом сотрудника и спутниками** (payroll, ZUS, absences, leave, employments, документы).

### Подблок «Оргструктура» (детализация)

- Единый источник правды по формальным единицам: division, department, team, cost_center и расширения по политике продукта.
- CRUD узлов; защита от циклов при смене родителя (сервисный слой).
- Участники узла: добавление и исключение пользователя тенанта.
- Назначение набора оргюнитов с карточки пользователя (атомарная замена членств по API).
- Поле оргюнита в инвайте; применение членства при принятии инвайта.

**Вне оргструктуры:** роли приложения, ACL компаний, бизнес-правила рекрутерского supervisor.

## Статус реализации

| Подсистема | Статус | Ориентир в коде |
|------------|--------|------------------|
| Оргструктура (дерево, CRUD, members) | Реализовано | таблицы `org_*`, сервис оргструктуры, `api/v1/admin/org_units.py` |
| Инвайт с `org_unit_id` | Реализовано | модель инвайта, `services/users.py` при accept |
| Карточка пользователя + PATCH org-units | Реализовано | admin users API, фронт (UsersPage, OrganizationPanel, настройки) |
| Права: `administrator` и `supervisor` на орг-API; для supervisor — GET users, GET user, PATCH org-units | Реализовано | `require_roles` на роутерах; фронт: `admin.users` vs `users.manage` |
| Workforce employee + спутники (payroll, ZUS, employments, absences, leave, onboarding tasks) | MVP данные + API + HR UI | `workforce_*` таблицы, `api/v1/workforce/router.py`, `HrEmployee*` |
| Связка Workforce ↔ User (`linked_user_id`) + оргюниты на карточке | MVP | миграция `202604302490_*`, PATCH employee, `link-user-options` |
| Вопросы **1–5** как сквозной продуктовый контроль (алерты сроков, расчёт выплат, экспорт в бухгалтерию/ZUS/TMS) | Не завершено | углубление спеки по каждому вопросу и интеграции |

## Дорожная карта HR vNext (по порядку)

Приоритеты ниже — порядок продуктовой разработки; статус «✓» = основная часть в прод-коде.

| Фаза | Содержание | Статус |
|------|------------|--------|
| **P0** | Оргструктура: дерево, CRUD, членство пользователей, инвайт с `org_unit_id`, права admin/supervisor, аудит изменений, экспорт/импорт JSON (`merge_by_code`). | ✓ |
| **P1** | Связка **WorkforceEmployee ↔ User** (`linked_user_id`) и отображение оргюнитов связанного пользователя на HR-карточке; опции выбора — `GET /workforce/employees/link-user-options`. | ✓ (MVP) |
| **P2** | Должности и грейды (справочник + назначение). | Запланировано |
| **P3** | Отсутствия / календарь HR: расширение вопроса **4** (правила, календарь, связь с Fleet/TMS — только по явному решению). | Частично (модели + UI карточки) |
| **P4** | Аналитика HR (headcount по узлам и др.). | Запланировано |

Нормативная модель «сотрудник vs пользователь»: [`ADR-001-workforce-employee-vs-app-user.md`](ADR-001-workforce-employee-vs-app-user.md).  
Граница «рекрутинг закрыт → кадры»: [`ADR-002-modular-recruitment-hr-boundary.md`](../specs/architecture/ADR-002-modular-recruitment-hr-boundary.md).  
Двухуровневые модули (tenant + company), владение данными по **Company**: [`ADR-003`](../specs/architecture/ADR-003-tenant-company-module-data-boundaries.md). Каталог из **пяти** продуктовых модулей (HR — один из них) и правило **Billing Events**: [`ADR-004`](../specs/architecture/ADR-004-five-product-modules-and-billing-events.md). Карта ключей и API: [`module-catalog-and-routing-map.md`](../specs/architecture/module-catalog-and-routing-map.md).  
Тест-план оргструктуры: [`test-plan-org-structure.md`](test-plan-org-structure.md).

## Контракт API (оргструктура)

Префикс тенанта: `X-Tenant-Id`. Базовый путь: `/api/v1/admin`.

- `GET /org-units/tree`
- `GET /org-units/export` — снимок `{ version, tenant_id, units[] }` для бэкапа / HRIS.
- `POST /org-units/import` — тело `{ "version": 1, "units": [...] }`, слияние по уникальному **`code`** (см. тест-план).
- `POST /org-units`
- `PATCH /org-units/{unit_id}`
- `DELETE /org-units/{unit_id}`
- `GET` / `POST` / `DELETE` для участников узла (`.../org-units/{unit_id}/members...`)
- `PATCH /users/{user_id}/org-units` — тело `{ "org_unit_ids": ["..."] }`

Детали схем: `backend/app/schemas/org_structure.py`, ответы пользователя — `UserDetailOut`.

## Права

- **Администратор:** полная админка пользователей и оргструктура.
- **Супервайзер:** оргструктура + чтение списка и карточки пользователя + PATCH org-units; прочие write-операции админки пользователей — только там, где явно разрешено эндпоинтом.
- **Фронт:** сценарий оргструктуры для роли с `users.manage` без `admin.users` (вкладка organization, пункт настроек).
- **HR workspace (workforce):** API `/api/v1/workforce/*` для ролей `hr_officer`, `administrator`, `supervisor`, **`recruiter`** и др. по `HANDOFF_ROLES` (единый операционный контур найма → сотрудник). При **`tenant.settings.modules.hr = false`** все маршруты `/workforce/*` возвращают **403** (см. `auth/hr_workforce_access.py`). На фронте — права `workforce.view` / `workforce.manage` и модуль тенанта **`hr`** (матрица ролей); для тенанта типа «компания» пользователь с ролью рекрутёра в UI может отображаться как `client_processor`, но с тем же доступом к workforce при включённом модуле.

Расширение ролей — обновлять этот документ и матрицу RBAC (`docs/specs/architecture/rbac_matrix.md`).

## Критерии готовности по вопросам 1–5 (черновик v0)

Цель раздела — зафиксировать **наблюдаемые** критерии «ответ получен / нет» для продукта, QA и будущих алертов. Это не полная спека интеграций; детали handoff в внешние системы — в отдельных ADR по мере появления.

| № | Вопрос | «Ответ получен» (MVP / текущий задел) | Пробелы (следующие итерации) | Ориентир аудита / данных |
|---|--------|----------------------------------------|------------------------------|---------------------------|
| **1** | Легально работать? | Есть запись сотрудника и хотя бы один `workforce_employment` с типом договора / датами; статус сотрудника не противоречит найму. | Явный контур «right to work», сроки разрешений, блокирующие статусы для выпуска в смену. | `workforce.employment_create` / `employment_patch`; снимок кандидата при handoff. |
| **2** | Документы действительны? | Документы по связанному `candidate_id` доступны из HR (`GET .../workforce/employees/{id}/documents`); типы и сроки — в модели досье. | Реестр сроков по сотруднику, просрочки, отдельный каталог «кадровых» документов без кандидата. | Действия в документном контуре кандидата; в перспективе — события по срокам. |
| **3** | Кто и сколько платит? | Заполнен `workforce_payroll_profiles` (ставка, валюта, `payroll_status`); согласованности с employment — на усмотрение процесса. | Расчётные листы, правила надбавок, связь с выплатами. | `workforce.payroll_profile_patch`. |
| **4** | Больничные / отпуска / отсутствия? | Есть строки `workforce_absences`, `workforce_leave_requests` и UI на карточке. | Календарь, правила пересечений, уведомления. | `workforce.absence_*`, `workforce.leave_request_*`. |
| **5** | Передано в бухгалтерию / ZUS / TMS? | ZUS: профиль `workforce_zus_profiles` со статусами; бухгалтерия: `payroll_status`, `external_refs`; TMS — через Fleet/TMS по решению продукта. | Подтверждённые события «отправлено в систему X», повторная отправка, ошибки интеграции. | `workforce.zus_profile_patch`; расширение payload в `activity_log` при появлении интеграций. |

При введении алертов и отчётов **явно ссылаться на строку таблицы** (номер вопроса и критерий).

Регресс v0 после handoff (bundle, документы по кандидату, идемпотентность): `backend/tests/api/test_workforce_hr_readiness_v0.py`.

## Бэклог спецификации

1. ~~Дорожная карта HR vNext~~ — см. раздел «Дорожная карта HR vNext» выше.
2. ~~ADR «Сотрудник vs User»~~ — [`ADR-001-workforce-employee-vs-app-user.md`](ADR-001-workforce-employee-vs-app-user.md); связь `linked_user_id` (P1) реализована.
3. ~~Аудит оргструктуры~~ — `user_audit_log` + `activity_log`; импорт пакета: `org_unit.import`.
4. ~~Импорт/экспорт дерева (v1 JSON)~~ — `GET/POST .../org-units/export|import`; расширения CSV/XLSX — позже.
5. ~~Подсказки в UI~~ — блок оргструктуры и карточка пользователя (супервайзер vs подразделения).
6. Контрактные тесты и CI — см. [`test-plan-org-structure.md`](test-plan-org-structure.md); требуется стабильный `alembic upgrade head` в пайплайне. Интеграционный контракт workforce + рекрутёр: `backend/tests/api/test_workforce_recruiter_contract.py` (ловит отсутствие роутера `workforce` и регресс RBAC). Сид тестовой БД в `conftest._init_data` поднимает квоты мест в `tenant_licenses`, чтобы на общей БД не падали инвайты и смена роли (`seat_limit_reached`).
7. Углубление по каждому из вопросов **1–5**: ~~черновик критериев v0~~ — см. раздел «Критерии готовности по вопросам 1–5»; далее — алерты (сроки документов, пробелы в payroll), события аудита handoff в бухгалтерию/ZUS/TMS, мини-спеки или ADR по интеграциям.

## Process Engine — HR stages (P0 manifest)

HR owns **`hr.*` system stages** in Process Engine (not recruitment funnel stages or legacy four-bucket `system_stage`). Registration: [`hr-process-manifest-p0.md`](../specs/architecture/hr-process-manifest-p0.md).

## Employee pipeline ownership (P0 — shipped)

| Owns | Does not own |
|------|----------------|
| `module_key=hr`, `type=employee` company-scoped funnels and stages | Recruitment candidate/lead funnels (`module_key=recruitment`) |
| `resolve_hr_employee_funnel`, `bootstrap_hr_employee_funnel_for_company` | `resolve_recruitment_funnel` in HR paths |
| `WorkforceEmployee.meta.employee_pipeline` on create (when `company_id` set) | Recruitment → HR handoff runtime (separate gate) |
| `/meta/stages?pipeline_type=employee&company_id=` — stages with `pe_maps_to_module=hr` | HR analytics dashboard widgets (post-gate) |

Spec + gate closure: [`hr-employee-pipeline-p0.md`](../specs/architecture/hr-employee-pipeline-p0.md). Acceptance: `backend/tests/integration/test_hr_only_employee_pipeline_h6.py`.

## Сопровождение

- При изменении охвата обновляйте этот файл и задачи в бэклоге.
- Детали моделей и миграций — в Alembic и `backend/app`.

## История

- Зафиксировано: рекрутер тенанта включён в роли HR workforce API и фронтовые права `workforce.*` при активном модуле `hr` (совместно с `hr_officer` / руководством).
- Зафиксировано: границы HR vs CRM, состав подсистем, оргструктура как реализованный подмодуль, API и права.
- Добавлены: дорожная карта P0–P4, ADR-001 (WorkforceEmployee vs User), тест-план оргструктуры, экспорт/импорт JSON v1, подсказки UI (оргструктура vs супервайзер).
- Зафиксирована **суть HR** как пять вопросов (легальность, документы, выплаты, отсутствия, передача в бухгалтерию / ZUS / TMS) с каноническим нумерованным списком и бэклогом на углубление критериев.
- Добавлен черновик **критериев готовности v0** по вопросам 1–5 (таблица для QA/продукта и будущих алертов).
- Зафиксирован порядок: **сначала модуль кадров** без раздельных HR-воронок; целевой **пул настроек HR** — Company Module Settings (`module_key=hr`), см. ADR-005.
