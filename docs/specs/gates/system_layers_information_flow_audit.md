# System Layers Information Flow Audit (pre REF-4)

Status: draft-for-gate  
Target: mandatory gate before REF-4 implementation

Related:
- `docs/specs/gates/ref4_core_catalog_completion_gate_plan.md`
- `docs/specs/reference_delivery_contract_standard.md`
- `docs/specs/architecture/module-catalog-and-routing-map.md`
- `docs/recruitment/module-scope.md`
- `docs/hr/module-scope.md`
- `docs/fleet/module-scope.md`
- `docs/services/module-scope.md`
- `docs/finance/module-scope.md`
- `docs/forms/module-scope.md`
- `docs/document-hub/module-scope.md`

## 1. Цель аудита

Зафиксировать единую карту движения системных данных (System Information Flow Map) для всех shared/system layers HostFlow до REF-4, чтобы независимые модули получали данные только через стабильные contracts (facade/API/DTO/event), а не через прямой доступ к внутренним структурам.

## 2. Scope / Out of scope

In scope:
1. Reference Layer
2. Policy / Rules Layer
3. Identity / Tenant Layer
4. Config Layer
5. Facade / Delivery Layer
6. Audit / Event Layer
7. Validation Layer
8. Integration Intake Layer
9. Правила потребления этих слоёв независимыми модулями

Out of scope:
1. Детальная реализация UI/UX
2. Новые бизнес-правила модулей (Recruitment/HR/Fleet/Services/Finance)
3. Расширение runtime-оркестрации вне существующих контрактов

## 3. Список системных слоёв

1. Reference Layer
2. Policy / Rules Layer
3. Identity / Tenant Layer
4. Config Layer
5. Facade / Delivery Layer
6. Audit / Event Layer
7. Validation Layer
8. Integration Intake Layer

## 4. Таблица: слой → источник истины → что хранит → delivery contract

| Layer | Source of Truth | Что хранит | Owner | Delivery contract |
|---|---|---|---|---|
| Reference Layer | canonical catalogs + deterministic seed/migrations + reference storage behind facade (REF-2/REF-4) | countries, citizenship, ISO, document types, statuses, classifiers, metadata, versions | platform-reference / core | `ReferenceServiceFacade` canonical response (`module -> facade -> response`) |
| Policy / Rules Layer | versioned rule registry / applicability packs / policy-bound tenant overrides | applicability rules, required/optional/blocked logic, precedence, validity windows | platform/core (policy owner), tenant only in allowed override bounds | facade decision DTO (`required/optional/blocked/allowed` + reason/source) |
| Identity / Tenant Layer | tenant/user/role/permission model + RBAC matrix + tenant/company boundaries | tenant membership, role grants, permission scope, actor context | platform/core security + access owners | auth/permission services, scoped access context, guarded API endpoints |
| Config Layer | tenant settings + company settings + company_module_settings (ADR-005 hierarchy) | feature flags, module enablement, module settings JSON, UI behavior config | platform/core + module owners + tenant admin (bounded) | typed config DTO/API (`GET/PATCH module-settings`, snapshots through services) |
| Facade / Delivery Layer | explicit contract specs + stable DTO versioning | no new truth storage; contract projection of canonical layers | platform/core | stable facade/API DTO, contract version + reference version |
| Audit / Event Layer | audit/event persistence + event schema | action history, change events, triggers, actor/time trace | platform/core (observability/security) | audit query APIs + domain/system events |
| Validation Layer | canonical schemas + constraints + validator services | field schemas, constraints, validation rules, errors/warnings model | platform/core + schema owners | validation results DTO (`valid`, `errors`, `warnings`, codes) |
| Integration Intake Layer | normalized intake contracts + channel adapters + mapping rules | inbound payloads from Meta/WhatsApp/forms, normalized envelopes, intake metadata | platform/integrations owner | normalized payload DTO/events consumed by modules |

## 5. Таблица: модуль → какие системные данные получает → через какой facade/API

Независимые модули из `module-scope.md`: Recruitment, HR, Fleet, Services, Finance; платформенные capability-модули: Forms, Document Hub.

| Module | Какие системные данные получает | Через какой facade/API |
|---|---|---|
| Recruitment | reference catalogs, applicability decisions, identity scope, module config, validation output, intake normalized payloads, audit signals | `ReferenceServiceFacade`, auth/permission APIs, `company_module_settings` API, validation services, integration intake contracts, audit/event APIs |
| HR | reference catalogs, policy decisions (work eligibility/doc requirements), identity scope, HR module config, validation, audit trail | `ReferenceServiceFacade`, RBAC/auth services, `module-settings/hr`, validation services, audit APIs/events |
| Fleet | country/document classifiers, rule decisions, fleet scope permissions, fleet config, validation, intake payloads | `ReferenceServiceFacade`, auth/fleet access guards, `module-settings/fleet`, validation contracts, intake normalization APIs/events |
| Services | classifiers/statuses/rules, access scope, services config, validation, intake payloads | `ReferenceServiceFacade`, auth/permission services, `module-settings/services`, validation services, integration intake contracts |
| Finance | reference classifiers, policy decisions, finance scope and enablement, finance config, validation, audit/events | `ReferenceServiceFacade`, auth/permission services, `module-settings/finance`, validation contracts, audit/event APIs |
| Forms (platform capability) | identity/tenant scope, config, validation schema, reference dictionaries for form fields | auth/context services, config APIs, validation layer, reference facade for canonical dictionaries |
| Document Hub (platform capability) | canonical doc types/classifiers, policy decisions, scope permissions, validation schema, audit/events | `ReferenceServiceFacade`, policy/permission services, validation layer, audit/event layer APIs |

## 6. Запрещённые direct access paths

Запрещено для модулей Recruitment/HR/Fleet/Services/Finance/Forms/Document Hub:

1. direct reads внутренних reference tables как runtime source-of-truth;
2. direct import внутренних registry/helper для принятия бизнес-решений в модуле;
3. чтение raw `tenant.settings`/seed-структур как конечного контракта поведения;
4. обход facade через legacy wrappers/resolvers без contract DTO;
5. прямое использование чужих domain helpers между модулями для policy/reference решений;
6. запись/чтение module runtime logic из migration seed напрямую;
7. прямое решение required/blocked логики через module-local `if/else` матрицы.

## 7. Допустимые временные исключения

Исключения допустимы только как migration seam и только с явным owner + removal milestone:

1. compatibility fallback в facade/resolver path, если покрыт тестами и gate-учётом;
2. sync/backfill jobs, где прямой доступ нужен для миграции данных, но не для module runtime;
3. legacy adapters, помеченные как transitional, с датой удаления до/в рамках REF-5.

Для каждого исключения обязательно:
1. ticket/owner;
2. срок удаления;
3. guard-scan allowlist запись;
4. тест, подтверждающий основной путь через facade/API.

## 8. STOP-criteria

Gate = `STOP`, если выполняется хотя бы одно:

1. для любого системного слоя не определён source of truth;
2. нет owner-а данных для слоя или домена;
3. модуль читает системные данные напрямую, минуя facade/API contract;
4. delivery contract нестабилен или не версионирован;
5. есть несколько активных источников истины для одного и того же системного домена;
6. tenant override policy не ограничена и не валидируется;
7. нет явного списка временных исключений с датой удаления;
8. guard/conformance scan не подтверждает boundary discipline.

## 9. Что должно быть готово до REF-4 implementation

Обязательный минимум до старта REF-4:

1. утверждён этот audit-doc как gate-артефакт;
2. зафиксирован System Information Flow Map по всем 8 системным слоям;
3. для каждого слоя заполнены: source of truth, owner, storage model, delivery contract;
4. матрица module consumption (таблица из раздела 5) согласована с module owners;
5. опубликован список запрещённых direct access paths и включён в проверки;
6. зафиксирован реестр временных исключений с удалением;
7. подтверждён путь `module -> facade/API -> canonical response` для системных данных;
8. получено gate-решение: `PASS` или `PASS_WITH_CONSTRAINTS` (без `STOP`) перед расширением REF-4 каталогов.

