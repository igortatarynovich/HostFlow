# Модуль Recruitment: цель и границы

Документ фиксирует **продуктовый модуль Recruitment** в смысле [`ADR-004`](../specs/architecture/ADR-004-five-product-modules-and-billing-events.md).  
**Capability Boundary / passport:** [`platform-capability-catalog.md`](../specs/architecture/platform-capability-catalog.md#recruitment).  
Детальные фичи CRM (кандидаты, воронки, документы) распределены по существующим спекам в `docs/specs/modules/*`; здесь — **охват и anti-scope**.

## Суть

- **Входит:** Applications (отклики), кандидаты, **вакансии** (потребность + прогресс закрытия), пайплайн отбора, интервью/документы/решение в контексте найма, handoff к HR/Fleet; **Job Post / vacancy-facing publishing** — см. [`ADR-008`](../specs/architecture/ADR-008-job-publishing-and-distribution.md).
- **Не входит (оператор привлечения):** создание набора / выбор формы / Meta / launch-pause / счётчики притока / timeline кампании — SoT UI = **Marketing Workspace** `/app/marketing` ([`../acquisition/module-scope.md`](../acquisition/module-scope.md), [`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)).
- **Не входит:** Sales Inquiry / ClientAccount (→ **Sales**); Service Order (→ **Services**); Invoice / Payment (→ **Finance**); **Employee Workspace** и кадровый lifecycle (→ **HR** — Recruitment только handoff + ссылка); операции автопарка (→ **Fleet**); владение Campaign/Ad как SoT (→ **Acquisition**). См. [`ADR-023`](../specs/architecture/ADR-023-recruitment-sales-module-separation.md).
- **`Lead`** — только внутренний transport intake; в UI модуля — **Отклик (Application)** / **Кандидат**, никогда «лид» как рабочий объект ([`ui-constitution-v1.md`](../specs/architecture/ui-constitution-v1.md)).
- **Nav:** Employees **не** живут в секции Recruitment. Пункт **«Подборы»** (`/app/recruitment/searches`) — **deprecated**; rail = Вакансии / Отклики / Кандидаты. VacancyDetail → CTA «Кампании / привлечение» ведёт в Marketing.
- **Stage 2A product API:** `/api/v1/recruitment/applications/*`, `/api/v1/recruitment/candidates/*` (legacy `/api/v1/candidates` remains compat).

## Job Publishing / Job Distribution (ADR-008)

**Не** отдельный бизнес-модуль уровня HR/Fleet/Finance: слой **внутри Recruitment** (или addon к Recruitment) + marketplace-коннекторы порталов.

| Сущность | Роль |
|----------|------|
| **Vacancy** | Внутренняя потребность: кого ищем, для какой company, условия, headcount, `owner_company_id`, статус. **Не** кандидат и **не** pipeline кандидата. |
| **Job Post** | Публичная версия вакансии (title, description, язык, зарплата, локация, статус публикации, привязка к **application form**). Одна vacancy → **много** posts (языки, порталы, кампании). |
| **Publishing Channel** | Куда публикуем: career page, HostFlow job page, Pracuj, Indeed, Meta, LinkedIn, OLX и т.д. |
| **Application Form** | Контур [**Forms**](../forms/module-scope.md) / [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md): отклик, файлы, RODO, предквалификация. |

**Flow:** `Vacancy → Job Post → Publishing Channel → Application Form → Application → Candidate` с атрибуцией **source / channel / campaign**. Долгосрочно **Campaign / ads / multi-module placement** живут в Shared **Acquisition** ([`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)); Job Post не становится владельцем Sales Inquiry.

**Vacancy ≠ Campaign:** Vacancy = внутренняя потребность Recruitment (закрытие позиций); Campaign/Flight = объект Acquisition / Marketing Workspace. Один Vacancy → много кампаний. Operator UI «Подборы» как второй acquisition console **запрещён**.

**Зависимость:** при выключенном **Recruitment** Job Publishing **недоступен**. При включённом — basic в составе Recruitment, advanced — addon; интеграции отдельных порталов — через Marketplace ([`ADR-006`](../specs/architecture/ADR-006-marketplace-and-integration-platform.md)).

**Запреты:** не смешивать vacancy и candidate pipeline; публикация не живёт в Finance/Services.

Документы кандидата (CV, паспорт, права и т.д.) — в **Document Hub** как платформенные объекты, не «файлы только внутри Recruitment»; см. [`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md), [`../document-hub/module-scope.md`](../document-hub/module-scope.md).

## Лицензирование и флаги

- На тенанте: **triad** `candidates`, `leads`, `vacancies` + производное **`recruitment`** (см. [`module-catalog-and-routing-map.md`](../specs/architecture/module-catalog-and-routing-map.md)).
- На компании: подмножество через `enabled_modules` после внедрения HTTP enforcement (ADR-003).

## Интеграции с другими модулями

- **HR:** handoff кандидата на сотрудника — см. [`ADR-002`](../specs/architecture/ADR-002-modular-recruitment-hr-boundary.md).
- **Finance:** только **Billing Events** как возможный выход (ADR-004); прямых invoices из Recruitment не проектируем.

## Pipeline ownership (module-owned pipelines P0 — gate closed 2026-06-30)

Recruitment **owns** candidate and lead pipeline definitions. Canonical scope:

| Dimension | Value |
|-----------|--------|
| `module_key` | `recruitment` |
| `funnel.type` | `candidate` \| `lead` (`deal` — legacy CRM, not Recruitment P0) |
| `company_id` | **Required** for all new operational funnels |
| Default pointer | `RecruitmentModuleSettingsV1.default_candidate_funnel_id` (company CMS); resolver step 2 |
| Resolution | Single chain — [`module-owned-pipelines-p0.md`](../specs/architecture/module-owned-pipelines-p0.md) §5 |

**Runtime entry points** use `recruitment_funnel_assignment` helpers → `resolve_recruitment_funnel`. **Forbidden after P0 gate:** new tenant-wide operational funnels; cross-module funnel rows; gates on legacy `system_stage` alone.

**Temporary strangler:** pre-migration tenant funnels (`company_id IS NULL`) remain readable via resolver step 4 and analytics `legacy_tenant=true` until backfill + dashboard migration. See spec §7.3.

## Сопровождение

- Иерархия настроек (tenant / company / module settings per company): [`ADR-005`](../specs/architecture/ADR-005-three-level-settings-hierarchy.md). Схема JSON для компании: **`RecruitmentModuleSettingsV1`**; API `GET/PATCH .../module-settings/recruitment`. **Воронки и этапы подбора** — ownership модуля Recruitment, scope **company** (`company_id` + `module_key=recruitment`); gate и миграция — [`module-owned-pipelines-p0.md`](../specs/architecture/module-owned-pipelines-p0.md).  
- Публичные формы (анкета кандидата, отклик на вакансию, intake и т.д.) — **не** собственность только Recruitment: платформенный контур **Forms**, см. [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md) и [`../forms/module-scope.md`](../forms/module-scope.md). Связка **Job Post → Application Form** — [`ADR-008`](../specs/architecture/ADR-008-job-publishing-and-distribution.md).
- При смене границ обновляйте этот файл, **ADR-004** и каталог маршрутов.
- Матрица ролей: `docs/specs/architecture/rbac_matrix.md`.
