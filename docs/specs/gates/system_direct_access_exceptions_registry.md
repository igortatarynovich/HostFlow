# System Direct Access Exceptions Registry (pre REF-4 enforcement)

Status: draft-for-gate  
Target: mandatory enforcement companion for `system_layers_information_flow_audit.md`

Related:
- `docs/specs/gates/system_layers_information_flow_audit.md`
- `docs/specs/gates/ref4_core_catalog_completion_gate_plan.md`
- `docs/specs/reference_delivery_contract_standard.md`

## 1. Purpose

Перевести архитектурный аудит системных слоёв в enforcement-map: все временные direct-access исключения фиксируются, нормализуются, получают owner/milestone и формальные условия закрытия.

## 2. Violation Categories (normalized)

| Code | Meaning |
|---|---|
| `DIRECT_IMPORT` | direct Python import внутреннего системного слоя |
| `RAW_DB_ACCESS` | чтение reference/policy/config таблиц напрямую, мимо фасада |
| `LEGACY_WRAPPER` | использование deprecated/legacy wrapper вместо канонического контракта |
| `CONFIG_BYPASS` | чтение raw config (`tenant.settings` и аналоги) как runtime source-of-truth |
| `SCHEMA_COUPLING` | зависимость от внутренней структуры schema/table/model вместо DTO contract |
| `CROSS_DOMAIN_ACCESS` | чтение чужого domain layer напрямую (module-to-module coupling) |

## 3. Severity Model

| Severity | Значение |
|---|---|
| `CRITICAL` | ломает platform boundaries; блокирует gate progression |
| `HIGH` | создаёт устойчивый coupling и риск повторного монолита |
| `MEDIUM` | временно допустимо только как migration seam с removal plan |
| `LOW` | cleanup-класс, без изменения архитектурной семантики |

## 4. Canonical Exceptions Structure

Каждое исключение обязано содержать:

1. `ID`
2. `Consumer`
3. `Нарушение`
4. `Violation Code`
5. `Direct access path`
6. `Должно быть через`
7. `Owner`
8. `Severity`
9. `Removal milestone`
10. `Migration condition`
11. `PASS condition`
12. `STOP escalation condition`

## 5. Exceptions Registry

| ID | Consumer | Нарушение | Violation Code | Direct access path | Должно быть через | Owner | Severity | Removal milestone | Migration condition | PASS condition | STOP escalation condition |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `EXC-001` | HR Verification | import document_types directly | `DIRECT_IMPORT` | `reference_foundation.py` | `reference_facade.get_document_types()` | Platform | `HIGH` | `REF-4` | facade endpoint published + consumer switched behind feature flag | no direct import in runtime code; conformance scan green | if still present after REF-4 gate freeze -> `STOP` for HR-related REF-4 rollout |
| `EXC-002` | Recruitment Intake | raw country dictionary access | `CONFIG_BYPASS` | `countries.py` | `reference_facade.resolve_country()` | Recruitment | `MEDIUM` | `REF-4.2` | country resolver parity test passed for intake payloads | intake path uses facade-only country resolution | if unresolved by REF-4.2 -> escalate to `HIGH` + block new intake rule changes |
| `EXC-003` | HR Operational Risk | direct reference validator import in runtime risk builder | `DIRECT_IMPORT` | `backend/app/services/hr_operational_risk.py` (historical direct import removed on 2026-05-28; now `ReferenceServiceFacade.normalize_reference_code`) | `ReferenceServiceFacade` decision/profile codes projection | HR/Platform | `HIGH` | `REF-4` | completed in code: consumer switched to facade helper; keep guarded until full blocker cycle rerun | no `reference_foundation` import in HR runtime services; targeted test+scan green | unresolved at REF-4 freeze -> `STOP` for HR risk/alert rollout |
| `EXC-004` | Workforce Eligibility Resolver | direct reference validator import in blocker/impact mapping | `DIRECT_IMPORT` | `backend/app/services/workforce_eligibility_resolver.py` (historical direct import removed on 2026-05-28; now facade normalization only) | `ReferenceServiceFacade` canonical code mapping | HR/Platform | `HIGH` | `REF-4` | completed in code: resolver switched to `ReferenceServiceFacade.normalize_reference_code` for taxonomy normalization | resolver consumes facade-only code set; targeted test+scan green | unresolved by REF-4 -> `STOP` for eligibility runtime expansion |
| `EXC-005` | Legacy Documents Rules Runtime | raw JSON dictionaries + citizenship/doc rules from config files | `CONFIG_BYPASS` | `backend/app/services/documents.py` (`load_config('citizenship_rules.json'|...)`; `doc_types.json` local dictionary path removed on 2026-05-29 via canonical contract; raw citizenship/work_country normalization replaced by `ReferenceServiceFacade` contract on 2026-05-29) | reference/policy facade (`get_applicable_documents`, runtime policy DTO) | Documents/Platform | `HIGH` | `REF-4.1` | parity tests between legacy config and facade policy outputs | module no longer reads rule dictionaries from JSON at runtime | unresolved by REF-4.1 -> block new document policy logic |
| `EXC-006` | Handoff Snapshot | cross-domain direct import of documents CRUD | `CROSS_DOMAIN_ACCESS` | `backend/app/services/handoff_snapshot.py` (`from ...modules.documents.crud import list_candidate_documents`) | document read facade/service contract (Document Hub API/service) | Recruitment + Document Hub | `MEDIUM` | `REF-4.2` | Document Hub read contract for candidate docs exposed | handoff snapshot uses contract client, no module CRUD import | unresolved by REF-4.2 -> escalate to `HIGH` |
| `EXC-007` | HR Documents Queue | cross-domain direct import of documents CRUD | `CROSS_DOMAIN_ACCESS` | `backend/app/services/hr_documents_queue.py` (historical `modules.documents.crud` consumer import removed on 2026-05-28; now contract adapter path) | document read facade/service contract (Document Hub API/service) | HR + Document Hub | `HIGH` | `REF-4` | completed in scope: consumer switched to `document_hub_delivery_contract.list_candidate_documents_via_contract` | no direct `modules.documents.*` import in `hr_documents_queue.py`; targeted tests+scan green | unresolved by REF-4 -> `STOP` for HR doc queue changes |
| `EXC-008` | Candidate Work Panel | dependency on documents router helper (router-as-service) | `LEGACY_WRAPPER` | `backend/app/services/candidate_work_panel.py` (`from ...modules.documents.router import fetch_candidate_documents_summary_response`) | document summary facade/service DTO | Recruitment + Document Hub | `MEDIUM` | `REF-4.2` | dedicated service/facade summary endpoint exists | no import from `modules.documents.router` inside services | unresolved by REF-4.2 -> keep as temporary only with explicit waiver |
| `EXC-009` | Candidate Telegram Notifications | cross-domain direct imports of document rules/summary helpers | `CROSS_DOMAIN_ACCESS` | `backend/app/services/candidate_telegram_notifications.py` (historical `modules.documents.*` imports removed on 2026-05-28; now service-level contract adapter calls) | document facade APIs for checklist/summary and ruleset bootstrap | Recruitment + Document Hub | `HIGH` | `REF-4` | completed in scope: switched to `document_hub_delivery_contract` adapter functions | no direct `modules.documents.*` import in consumer; targeted tests+scan green | unresolved by REF-4 -> `STOP` for telegram doc-status automation changes |
| `EXC-010` | Document Type Runtime Resolver | direct DB reads of reference tables in consumer runtime | `RAW_DB_ACCESS` | `backend/app/services/document_type_runtime_resolver.py` (`RefDocumentType*` queries) | reference read facade/provider boundary | Platform | `MEDIUM` | `REF-5` | facade/provider path supports runtime profile lookup by doc/version | resolver no longer queries reference tables directly from consumer path | unresolved by REF-5 -> escalation to `HIGH` |

Note: `EXC-001/EXC-002` — seed entries для формата реестра. Фактический inventory дополняется по guard-scan/code-audit.

## 6. Removal Policy (mandatory)

Для каждого exception запись считается валидной только если есть:

1. `owner` (персональный, не абстрактный “team”);
2. `milestone` (например `REF-4`, `REF-4.1`, `REF-4.2`, `REF-5`);
3. явный `target facade/contract`;
4. `migration condition` (что должно быть готово до переключения);
5. `PASS condition` (как проверяем закрытие);
6. `STOP escalation condition` (когда исключение блокирует следующий слой).

Правило:
- исключение без этих полей считается неоформленным и трактуется как violation (`HIGH` минимум).

## 7. Allowed Platform Access Matrix (architectural firewall)

| Consumer Module | Allowed System Layers |
|---|---|
| Recruitment | Reference Facade, Policy Facade, Identity Context, Config API, Validation Facade, Audit/Event API, Integration Intake Contract |
| HR | Reference Facade, Policy Facade, Identity Context, Config API, Validation Facade, Audit/Event API |
| Fleet | Reference Facade, Policy Facade, Identity Context, Config API, Validation Facade, Audit/Event API, Integration Intake Contract |
| Services | Reference Facade, Policy Facade, Identity Context, Config API, Validation Facade, Audit/Event API, Integration Intake Contract |
| Finance | Reference Facade, Policy Facade, Identity Context, Config API, Validation Facade, Audit/Event API |
| Forms (platform capability) | Identity Context, Config API, Validation Facade, Reference Facade |
| Document Hub (platform capability) | Reference Facade, Policy Facade, Identity Context, Validation Facade, Audit/Event API |

Hard rule:
- доступ к системным данным вне разрешённого набора для модуля = direct-access violation.

## 8. Delivery-Type Matrix

| Layer | Delivery Type |
|---|---|
| Reference | facade/read API |
| Policy | decision engine facade (`required/optional/blocked/allowed`) |
| Identity / Tenant | auth context + permission service |
| Config | tenant/company-scoped config API (typed DTO) |
| Facade / Delivery | versioned stable DTO contract |
| Audit / Event | event stream + audit read API |
| Validation | schema validator facade |
| Integration Intake | normalized intake contract (API/event envelope) |

Hard rule:
- новый способ передачи данных между слоем и модулем не допускается без обновления этой матрицы и gate-аппрува.

## 9. Governance and Update Rules

1. Обновление реестра обязательно в том же PR, где появляется новое временное исключение.
2. Закрытие исключения обязательно в том же PR, где убран direct-access path.
3. Любой `CRITICAL` exception блокирует переход к следующему implementation layer.
4. Любой `HIGH` exception без milestone -> автоматический `STOP` до нормализации записи.
5. Перед REF-4 implementation требуется актуальный snapshot реестра с owner-signoff.

## 10. REF-4 Entry Gate Checklist (enforcement)

REF-4 implementation разрешён только если одновременно выполнено:

1. `system_layers_information_flow_audit.md` утверждён;
2. этот реестр создан и заполнен (минимум seed + фактические активные исключения);
3. Allowed Platform Access Matrix согласована module owners;
4. Delivery-Type Matrix согласована platform/core owners;
5. нет `CRITICAL` исключений;
6. все `HIGH` исключения имеют принятый removal milestone и PASS/STOP conditions.
