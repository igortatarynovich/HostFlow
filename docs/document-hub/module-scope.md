# Document Hub: охват платформенного слоя документов

**Document Hub** — общий слой для HostFlow: документ как **самостоятельная сущность**, а не только вложение в одной карточке. Нормативное решение — **[`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md)**.  
**Capability Boundary / passport:** [`platform-capability-catalog.md`](../specs/architecture/platform-capability-catalog.md#documents).  
**Product Track (live):** [Documents Platform E2](../specs/tasks/documents-platform-e2-public-contract.md) (feat; named Public Contract Gate). Public contract: [`documents-public-contract.md`](../specs/architecture/documents-public-contract.md). WCP [COMPLETE](../specs/gates/workspace-capability-platform-complete.md); intermediate [PASS_WITH_CONSTRAINTS](../specs/gates/workspace-capability-platform-g1-g5-closeout.md) on #273. E2 brief ✅ ([#271](https://github.com/igortatarynovich/HostFlow/pull/271)). E1 ✅. D2 `documents` catalog unlock is E2; D3–D9 stay unbound.  
В **§0** каталога модулей Hub стоит в **Core / Platform** рядом с Companies, Users/Roles, Forms, Integrations.

## Назначение

- Хранение и **registry** документов  
- **Document types** и **document templates**  
- **Required document sets** и чек-листы требований  
- Статусы, **сроки действия**, напоминания  
- Связь с **множеством сущностей** через **links**  
- Передача между модулями **без копирования файла** — links, permissions, shared access  
- Централизованное управление доступом и аудит (в Advanced)

## Ключевое правило

**Documents are shared platform objects, not module-owned files.**

- **Ownership:** `owner_company_id` задаёт владельца.  
- **Использование:** `Document Link` + `module_key` + `access_scope` — где документ фигурирует.  
- **Права:** кто видит / проверяет / меняет / скачивает.  
- **Handoff между компаниями:** явная политика (какие документы, поля, срок, download vs просмотр, запрос исправления).

## Сущности (целевая модель)

См. детали в **ADR-009**. Кратко:

- **Document** — tenant, owner, type, file, status, expires_at, verification, source_module / source_entity, sensitivity, visibility.  
- **Document Link** — привязка к Candidate, Employee, Client, Company, Vehicle, Service Order, HR Case, Fleet Assignment, Invoice/Billing Profile и т.д.  
- **Document Requirement** — элемент набора: тип, обязательность, blocking, module_key, stage, нужна ли верификация.  
- **Document Review** — статус проверки **в контексте требования** (один файл — несколько reviews в Recruitment / HR / Fleet).

## Пример reuse

Документ «паспорт» создан при сборе в **Recruitment** (`source_* = candidate`). После найма файл **не дублируется**; добавляется **Link** на `employee` с `relation_type=reused_for_employment`, `module_key=hr`.

## Required Document Sets (примеры)

Пресеты наборов (ключи продуктовые, расширяемые):

- Candidate Driver PL / **Candidate Driver Foreigner**  
- Employee Driver Foreigner  
- Warehouse Worker PL / Foreigner  
- Vehicle Handover  
- Client Billing  
- Work Permit Process  
- GITD Process  

Модуль **не дублирует** канонический список типов для процесса — **запрашивает набор** у Hub (по set id / ключу). Один и тот же **document_type** (например driving license) может входить в наборы Recruitment, HR и Fleet; **файл один**, **reviews** могут различаться.

## Использование по модулям (ориентир типов)

| Модуль | Примеры документов / процессов |
|--------|--------------------------------|
| Recruitment | CV, passport, licenses, Code 95, tachograph, residence, preliminary consent |
| HR | questionnaire, ZUS, contract, PIT-2, payroll, work permit, consents; reuse из Recruitment |
| Fleet | license, Code 95, tachograph, medical, psychotests, handover, vehicle docs, GITD/IMI |
| Finance | invoice attachments, billing details, payment confirmations, contracts, corrections |
| Services | service contracts, client docs, order docs, delivery confirmations |

## UX

- **Document Hub** — экран для ролей «документный» контур (комплаенс, централизованный контроль).  
- **Карточки** (Candidate, Employee, Vehicle, Assignment, HR Case, Service Order, Client) — встроенная работа с теми же документами через links.

## Basic vs Advanced

| Basic | Advanced |
|-------|----------|
| Upload, type, link, status, expiry | Document sets, multi-module review, versioning, access logs, reminders, external sharing, e-signature, OCR, условные требования |

## Текущий код

Существующий контур `Document`, `DocumentType`, `DocumentTemplate`, политики, dossier — **эволюционирует** к модели ADR-009 (явные links, requirement/review, наборы из Hub). Точечные пути API см. код в `backend/app` и [`../specs/integration.md`](../specs/integration.md) по мере обновления.

## Сопровождение

Менять этот файл и **ADR-009** совместно с продуктом при смене модели доступа или новых presets наборов.

## История

- 2026-08-20: Product Track → [Entity Platform Completion](../specs/tasks/workspace-capability-platform-completion.md); E2 brief ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271) (feat locked).  
- 2026-08-18: Product Track → Documents Platform E1 ([brief](../specs/tasks/documents-platform-e1-contract-seal.md)); D9 ✅ [#268](https://github.com/igortatarynovich/HostFlow/pull/268). D2 slot not enabled.
- 2026-05: первичная фиксация scope Document Hub и таблица примеров по модулям.
