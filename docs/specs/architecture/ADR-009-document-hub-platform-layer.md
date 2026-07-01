# ADR-009: Document Hub — общий платформенный слой документов

## Status

**Accepted (product & architecture direction).** Имплементация **поэтапная**. Текущий код (`Document`, типы, шаблоны, политики, dossier) уже развивается в домене документов — целевая модель ниже задаёт **единый registry**, **связи без копирования файлов** и **контексты проверки** по модулям без владения файлом конкретным модулем.

## Context

Документы используются в **Recruitment, HR, Fleet, Services, Finance** и не должны быть «файлом только внутри карточки кандидата» или только HR-dossier. Нужен **Document Hub** — **shared platform layer**: хранение, типы, шаблоны, наборы требований, сроки, статусы, связи с сущностями, передача **через links и права**, а не копированием.

**Document Hub** — **не** шестой продуктовый модуль ADR-004 (`recruitment` \| `hr` \| …). Это **platform capability** (как Forms и Integrations в §0 каталога): может быть **включён baseline** для модулей, **Advanced Document Management** — paid addon.

Связанные ADR:

- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) — `owner_company_id`, company scope, handoff.  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) — модули **потребляют** Document Hub, не владеют файлом как изолированным silo.  
- [`ADR-007`](ADR-007-forms-platform-capability.md) — загрузка файлов из форм может создавать **Document** в Hub.  
- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md) — handoff кандидата ↔ сотрудник с **тем же** документом через link.  
- [`ADR-014`](ADR-014-document-hub-access-model.md) — owner access vs document context vs workspace; `DocumentAccessResolver`; документ ≠ файл; **фазы 1–5 (§6)**; **policy-driven resolver (§7)**.

---

## Decision: назначение Document Hub

- **Хранить** документы как **отдельную сущность** (не только attachment в одной карточке).  
- **Определять** document types, **шаблоны**, **required document sets**, **чек-листы**.  
- **Отслеживать** статусы, **сроки действия**, **версии файлов**. *Reminders / задачи на проверку и продление документа создаются в Activity & Notification Operating Layer ([`ADR-012`](ADR-012-activity-notification-operating-layer.md)) — Document Hub публикует Activity, не владеет своей таблицей задач.*  
- **Связывать** с Candidate, Employee, Client, Company, Vehicle, Service Order, HR Case, Fleet Assignment, Invoice / Billing Profile и др.  
- **Передавать между модулями** через **Document Link** и **permissions / shared access**, **без копирования** бинарного файла.  
- **Управлять доступом**: кто видит, проверяет, скачивает; **handoff** к клиенту — явные правила (какие документы, поля, срок, download vs view-only, запрос исправления).

---

## Модель данных (целевая)

### Document

| Поле (концепт) | Назначение |
|----------------|------------|
| `tenant_id` | Workspace |
| `owner_company_id` | Владелец документа (ADR-003) |
| `document_type_id` | Тип в таксономии Hub |
| `file_id` / storage ref | Файл в хранилище |
| `status` | Жизненный цикл документа (агрегат) |
| `expires_at` | Срок действия |
| `verified_by` / `verified_at` | Базовая верификация (при необходимости) |
| `source_module` | Модуль-источник создания (`recruitment`, `hr`, …) |
| `source_entity_type` / `source_entity_id` | Откуда впервые привязан (например candidate) |
| `sensitivity_level` | Классификация чувствительности |
| `visibility_scope` | Базовые правила видимости |

### Document Link

Связь **одного** документа с **сущностью** в контексте модуля.

| Поле | Назначение |
|------|------------|
| `document_id` | Ссылка на Document |
| `linked_entity_type` / `linked_entity_id` | Candidate, Employee, Vehicle, … |
| `relation_type` | Семантика (например `reused_for_employment`) |
| `module_key` | `recruitment` \| `hr` \| `fleet` \| … |
| `access_scope` | Уточнение доступа в этом контексте |

**Пример (handoff кандидат → сотрудник):**  
Паспорт создан в Recruitment: `source_module=recruitment`, `source_entity_type=candidate`, `source_entity_id=…`. После найма **не копируем** файл; создаём **Document Link**: `linked_entity_type=employee`, `relation_type=reused_for_employment`, `module_key=hr`.

**Правило:** документы **не передаются копированием** между модулями; только **links + permissions + shared access**.

---

## Document Requirement и Document Review (мульти-модульная проверка)

Один файл — **один** Document; **разные модули** могут требовать **разные проверки** в своём контексте.

### Document Requirement (в составе document set)

- `document_set_id`, `document_type_id`  
- `required`, `blocking`  
- `module_key`, `process_stage`  
- `verification_required`  

### Document Review

- `document_id`, `requirement_id`  
- `reviewed_by`, `status`, `comment`, `reviewed_at`  

**Пример:** prawo jazdy — *approved for qualification* в Recruitment, *approved for employment file* в HR, *approved for vehicle assignment* в Fleet: общий **файл**, разные **Document Review** по контексту.

---

## Required Document Sets и шаблоны

Модули **не хранят** собственный канонический список типов документов для процесса — они **запрашивают набор** из Hub (по `document_set_id` / ключу preset):

Примеры наборов: **Candidate Driver PL**, **Candidate Driver Foreigner**, **Employee Driver Foreigner**, **Warehouse Worker PL/Foreigner**, **Vehicle Handover**, **Client Billing**, **Work Permit Process**, **GITD Process**.

Один **document_type** (например driving license) может входить в **несколько** наборов; физически тот же **Document** может удовлетворять нескольким требованиям через статусы и reviews.

Документы **работают через шаблоны** (document templates) — согласование с существующим контуром `DocumentTemplate` в коде — эволюция, не дублирование конкурирующих систем.

---

## Использование по модулям (примеры типов)

**Recruitment:** CV, passport, driving license, Code 95, tachograph, residence card, preliminary consent.  
**HR:** questionnaire, ZUS, contract, PIT-2, payroll docs, work permit, HR consents (+ reuse из Recruitment).  
**Fleet:** license, Code 95, tachograph, medical, psychotests, handover protocol, vehicle docs, IMI/GITD confirmation.  
**Finance:** invoice attachments, billing details, payment confirmations, contracts, corrections.  
**Services:** service contracts, client docs, order docs, delivery confirmations.

---

## UX: Hub vs карточки

- **Document Hub** — отдельный экран / control center для ролей, которые **централизованно** работают с документами (комплаенс, back-office).  
- **Карточки** (Candidate, Employee, Vehicle, Assignment, HR Case, Service Order, Client) — **рабочие места**, где документы **отображаются и действуются** через те же ссылки и права.

**Итог:** Hub = registry + политики + поиск; модули = контекст использования.

---

## Handoff документов клиенту

При передаче кандидата/данных клиенту явно задавать: **какие документы**, **видимые поля**, **срок доступа**, **download / view-only**, **право запросить исправление**. Реализация через **access_scope**, share records, audit (детали — отдельная спека ACL для documents).

---

## Basic vs Advanced

| Tier | Содержание |
|------|------------|
| **Basic** | Upload, document type, link к сущности, статус, expiry |
| **Advanced** | Document sets, multi-module review, versioning, access logs, **Activity-driven document_check tasks** (через [`ADR-012`](ADR-012-activity-notification-operating-layer.md)), external sharing, e-signature, OCR, условные требования |

---

## Consequences

1. Новые фичи «документ для процесса» проектируются через **Hub + Link + Requirement/Review**, а не дублированием файлов в модуле.  
2. Миграция существующих связей документ↔кандидат — к явной модели **Document** + **Link**.  
3. Каталог и scope — [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0, [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md).

## References

- [`ADR-014`](ADR-014-document-hub-access-model.md)  
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md)  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)  
- [`ADR-007`](ADR-007-forms-platform-capability.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- [`../../document-hub/module-scope.md`](../../document-hub/module-scope.md)  
- [`../integration.md`](../integration.md) — операционные детали существующих потоков (по мере выравнивания)

## История

- 2026-05: первичная фиксация Document Hub как platform layer, сущности Document / Link / Requirement / Review, Basic/Advanced, запрет копирования между модулями.
- 2026-05-09: Phase 0 / [`ADR-012`](ADR-012-activity-notification-operating-layer.md) — уточнено, что reminders/задачи на проверку и продление документов **не** живут в Document Hub; Document Hub публикует Activity (`type='document_check'`, `source_module='documents'`) и Notification (`type='document_expiring'/'document_expired'`) в общий Activity & Notification Operating Layer.
