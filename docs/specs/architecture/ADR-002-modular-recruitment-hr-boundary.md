# ADR-002: Recruitment vs HR boundary on candidate stages

## Status

Accepted — implemented incrementally starting 2026-05-06.

## Context

HostFlow mixed recruitment progress and post-hire HR work on a single candidate stage axis. Product-wise, **contract signing and ZUS are HR processes**; the recruiter’s job can end earlier. Selling **Recruitment**, **HR**, and **Fleet** as separate modules requires a clear handoff point from the candidate record to the **Workforce (Employee)** record.

## Decision

1. Introduce canonical candidate stages **`ready_for_hr`** and **`hired`** as **recruitment-closed** success codes (alongside legacy **`employed`**).
2. Treat **`PIPELINE_COMPLETED_STAGE_CODES`** as «операционная воронка кандидата закрыта» (no recruiter next-action / list noise), **not** «вся работа компании завершена». HR continues on `WorkforceEmployee` and related satellites.
3. Extend **`WORKFORCE_HANDOFF_STAGE_CODES`** so a **`WorkforceEmployee`** row is ensured when the case enters HR-owned stages, including `ready_for_hr`, `hired`, and `processing_by_hr`, not only `employment_pending` / `employed`.
4. Export **`RECRUITMENT_SUCCESS_STAGE_CODES`** for analytics and dashboards (hired-like counts without conflating with rejected/declined).
5. **Стадии и роли при включённом agency handoff:** **`ready_for_hr`** — финальное действие **Recruitment** (рекрутер может выставить). **`hired`** / **`employed`** (и прочий post-handoff lane) — зона **HR**; рекрутер не переводит на `hired` через PATCH кандидата. Константа **`RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES`** не включает `ready_for_hr`; включает `hired`, `employed`, клиентский/HR lane. Подробнее: [`invariants-recruitment-hr-document-hub.md`](invariants-recruitment-hr-document-hub.md).

## Consequences

- Документы кандидата при переходе в HR: **не копировать** файлы — связывать через **Document Hub** ([`ADR-009`](ADR-009-document-hub-platform-layer.md)) (`Document Link`, reuse / employment context).
- Tenants can move candidates to **`ready_for_hr` / `hired`** without implying that payroll or ZUS is finished.
- **Fleet** and full **HR pipeline templates** remain follow-up work; future ADRs can add explicit `hr_pipeline_instance` / `employment_template` tables.
- **Backward compatibility**: existing stages and funnels unchanged; new codes are additive. Funnel presets that already use system stage `hired` now resolve through the same operational-completion rules as backend constants.

## References

- [`handoff-contract.md`](handoff-contract.md) — продуктовый маппинг `ready_for_hr` / `ready_for_handoff` и типы handoff (internal vs client portal)
- [`operational-event-boundaries.md`](operational-event-boundaries.md) — границы операционных фактов: смена стадии vs создание handoff vs материализация HR
- `backend/app/constants/stages.py` — `PIPELINE_COMPLETED_STAGE_CODES`, `RECRUITMENT_SUCCESS_STAGE_CODES`
- `backend/app/services/workforce_employees.py` — `WORKFORCE_HANDOFF_STAGE_CODES`
- `docs/hr/module-scope.md` — HR module scope vs CRM
- `backend/app/auth/fleet_access.py` + `tenant.settings.modules.fleet` — отдельный продуктовый модуль Fleet на уровне тенанта
- `backend/app/auth/hr_workforce_access.py` + `tenant.settings.modules.hr` — API Workforce (HR) при выключенном модуле недоступен
- [`ADR-003-tenant-company-module-data-boundaries.md`](ADR-003-tenant-company-module-data-boundaries.md) — tenant-модули — только верхняя крышка; операционная граница и модули по **company** и назначениям пользователей
- [`ADR-004-five-product-modules-and-billing-events.md`](ADR-004-five-product-modules-and-billing-events.md) — пять независимых продуктовых модулей; Recruitment **не** главный; Billing Events → Finance
- [`ADR-009-document-hub-platform-layer.md`](ADR-009-document-hub-platform-layer.md) — общий слой документов при handoff Recruitment → HR
