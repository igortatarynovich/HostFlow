# Модуль Recruitment: цель и границы

Документ фиксирует **продуктовый модуль Recruitment** в смысле [`ADR-004`](../specs/architecture/ADR-004-five-product-modules-and-billing-events.md). Детальные фичи CRM (кандидаты, воронки, документы) распределены по существующим спекам в `docs/specs/modules/*`; здесь — **охват и anti-scope**.

## Суть

- **Входит:** лиды, кандидаты, вакансии, клиенты рекрутинга, пайплайн подбора, документы и правила стадий в контексте найма, handoff к HR/Fleet по продуктовым сценариям; **публикация вакансий и распространение** (Job Publishing) как capability модуля — см. [`ADR-008`](../specs/architecture/ADR-008-job-publishing-and-distribution.md).
- **Не входит:** каталог операционных заказов услуг как отдельный контур (→ **Services**), выставление счетов и агрегированный биллинг (→ **Finance** через **Billing Events**), кадровый жизненный цикл сотрудника (→ **HR**), операции автопарка (→ **Fleet**).

## Job Publishing / Job Distribution (ADR-008)

**Не** отдельный бизнес-модуль уровня HR/Fleet/Finance: слой **внутри Recruitment** (или addon к Recruitment) + marketplace-коннекторы порталов.

| Сущность | Роль |
|----------|------|
| **Vacancy** | Внутренняя потребность: кого ищем, для какой company, условия, headcount, `owner_company_id`, статус. **Не** кандидат и **не** pipeline кандидата. |
| **Job Post** | Публичная версия вакансии (title, description, язык, зарплата, локация, статус публикации, привязка к **application form**). Одна vacancy → **много** posts (языки, порталы, кампании). |
| **Publishing Channel** | Куда публикуем: career page, HostFlow job page, Pracuj, Indeed, Meta, LinkedIn, OLX и т.д. |
| **Application Form** | Контур [**Forms**](../forms/module-scope.md) / [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md): отклик, файлы, RODO, предквалификация. |

**Flow:** `Vacancy → Job Post → Publishing Channel → Application Form → Lead/Candidate` с атрибуцией **source / channel / campaign** и метриками конверсии **channel → candidate**.

**Зависимость:** при выключенном **Recruitment** Job Publishing **недоступен**. При включённом — basic в составе Recruitment, advanced — addon; интеграции отдельных порталов — через Marketplace ([`ADR-006`](../specs/architecture/ADR-006-marketplace-and-integration-platform.md)).

**Запреты:** не смешивать vacancy и candidate pipeline; публикация не живёт в Finance/Services.

Документы кандидата (CV, паспорт, права и т.д.) — в **Document Hub** как платформенные объекты, не «файлы только внутри Recruitment»; см. [`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md), [`../document-hub/module-scope.md`](../document-hub/module-scope.md).

## Лицензирование и флаги

- На тенанте: **triad** `candidates`, `leads`, `vacancies` + производное **`recruitment`** (см. [`module-catalog-and-routing-map.md`](../specs/architecture/module-catalog-and-routing-map.md)).
- На компании: подмножество через `enabled_modules` после внедрения HTTP enforcement (ADR-003).

## Интеграции с другими модулями

- **HR:** handoff кандидата на сотрудника — см. [`ADR-002`](../specs/architecture/ADR-002-modular-recruitment-hr-boundary.md).
- **Finance:** только **Billing Events** как возможный выход (ADR-004); прямых invoices из Recruitment не проектируем.

## Сопровождение

- Иерархия настроек (tenant / company / module settings per company): [`ADR-005`](../specs/architecture/ADR-005-three-level-settings-hierarchy.md). Схема JSON для компании: **`RecruitmentModuleSettingsV1`**; API `GET/PATCH .../module-settings/recruitment`. **Воронки и этапы подбора** — ownership модуля Recruitment, scope **company** (`company_id` + `module_key=recruitment`); gate и миграция — [`module-owned-pipelines-p0.md`](../specs/architecture/module-owned-pipelines-p0.md).  
- Публичные формы (анкета кандидата, отклик на вакансию, intake и т.д.) — **не** собственность только Recruitment: платформенный контур **Forms**, см. [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md) и [`../forms/module-scope.md`](../forms/module-scope.md). Связка **Job Post → Application Form** — [`ADR-008`](../specs/architecture/ADR-008-job-publishing-and-distribution.md).
- При смене границ обновляйте этот файл, **ADR-004** и каталог маршрутов.
- Матрица ролей: `docs/specs/architecture/rbac_matrix.md`.
