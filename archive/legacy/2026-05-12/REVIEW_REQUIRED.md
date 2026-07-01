# Stage 3 — REVIEW_REQUIRED report

**Дата:** 2026-05-12  
**Контекст:** canonical baseline зафиксирован коммитом `9370fc4`; очевидный legacy перемещён в `archive/legacy/2026-05-12/` коммитом `f1b986e`. Этот отчёт перечисляет **неоднозначные** документы, по которым требуется ручное решение перед дальнейшим архивированием/удалением.

**Никаких действий по файлам из этого отчёта в этом коммите не выполняется.**

**Колонки:**
- **Path** — текущий путь
- **Содержимое** — кратко, что внутри
- **Почему REVIEW** — конкретная причина неопределённости
- **Связь с SSOT** — цитируется ли каноном / кодом
- **Рекомендация** — `KEEP` (оставить как актуальный канон), `MERGE_INTO_CANON` (полезный контент перенести в канон, файл архивировать), `ARCHIVE` (заархивировать без переноса), `DELETE` (удалить безвозвратно)

---

## A. Operational backlog (явно перечислен пользователем как «не трогать»)

Эти файлы оставлены без изменений по прямому указанию. Здесь они перечислены **только для прозрачности** — решение откладывается, рекомендация: **KEEP** до явного пересмотра командой.

### A.1 Seeds

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/seeds/additional_services_seed.md` | Семя данных для каталога Additional Services | Не цитируется кодом, но описан operational seed для модуля services | Не противоречит ADR-004 (services module) | **KEEP** |
| `docs/specs/seeds/candidate_portal_seed.md` | Seed для candidate portal | То же | Не противоречит модулю candidate_portal | **KEEP** |
| `docs/specs/seeds/invoicing_seed.md` | Seed для invoicing | То же | Не противоречит ADR-004 / Finance | **KEEP** |
| `docs/specs/seeds/templates_seed.md` | Seed для шаблонов документов | То же | Не противоречит ADR-009 (Document Hub) | **KEEP** |

### A.2 Tasks (operational backlog)

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/tasks/candidate_intake_and_docs.md` | Чек-лист задач по intake кандидата + документов | Дата ноябрь 2025; часть пунктов могла быть закрыта; проверка вручную | Operational backlog | **KEEP**, ревизия командой |
| `docs/specs/tasks/documents_dod.md` | Definition of Done модуля документов | Цитирует `reminders_matrix.md` (тоже REVIEW); ноябрь 2025 | Связан с Document Hub | **KEEP**, ревизия |
| `docs/specs/tasks/fix_companies_pg.md` | One-shot задача (Postgres-фикс для companies) | Цитируется только из `agent_prompt.md` (заархивирован); вероятно закрыта | Операционная одноразка | **KEEP** до подтверждения статуса (если выполнено — `ARCHIVE`) |
| `docs/specs/tasks/meta_leads_to_candidates.md` | Задача по интеграции Meta leads → candidates | Реализована (см. `backend/app/modules/leads/`); может быть устарела | Связана с активной интеграцией | **KEEP**, ревизия |
| `docs/specs/tasks/recruiter_auto_assignment.md` | Задача auto-assignment | Реализован `services/recruiter_assignment.py` | Связан с `manager-assignment.md` | **KEEP**, ревизия |
| `docs/specs/tasks/restructure_documents_module.md` | Реструктура documents module | Текущее состояние модуля документов — после ADR-009/014 | Может быть устаревшая | **KEEP**, ревизия |

### A.3 DB migration plans

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/db/migrations_plan_documents.md` | Plan миграций таблиц documents | Ноябрь 2025; реальные миграции в `backend/alembic/versions/` | Связан с Document Hub | **KEEP**, ревизия |
| `docs/specs/db/migrations_plan_invoicing.md` | Plan миграций invoicing | То же | Связан с Finance | **KEEP**, ревизия |

### A.4 Document expiry & i18n & telegram intake & comms research

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/workflows/document_expiry.md` | Workflow expiry документов | Ноябрь 2025; перекрывается reminders + ADR-012 | Связан с Document Hub workflow | **KEEP** (явно в «не трогать») |
| `docs/specs/i18n/index.md` | i18n index | Активный layout-доку | Связан с активной i18n инфраструктурой | **KEEP** |
| `docs/specs/i18n/candidate_intake_i18n_step1.md` | Step-1 черновик i18n для intake | Возможно одноразовый | Связан с intake | **KEEP** до подтверждения |
| `docs/specs/workflows/candidate-intake-via-telegram.md` | Telegram-канал intake | Март 2026; реальный канал | Описывает действующий канал | **KEEP** |
| `docs/specs/workflows/candidate-intake-via-telegram-execution-plan.md` | Execution plan того же | Март 2026 | Operational план | **KEEP** |
| `docs/specs/workflows/communications-workspace-research.md` | Research по communications workspace | Май 2026; явно research-черновик | Не цитируется кодом | **KEEP** (явно в «не трогать») |
| `docs/specs/workflows/email-client-outlook-style-research.md` | Research email client UI | Март 2026; research-черновик | Не цитируется кодом | **KEEP** (явно в «не трогать») |

---

## B. Прочие REVIEW_REQUIRED (не вошли в «не трогать»-список)

### B.1 LLM-min специальные версии

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/min/companies.min.md` | Сжатая версия companies spec для LLM-контекста | Стратегия `.min.md` упомянута только в архивированном `agent_tz.md`; LLM сейчас не использует | Дублирует `docs/specs/modules/companies.md` | **ARCHIVE** |
| `docs/specs/min/documents.min.md` | Min documents | То же | Дублирует `modules/documents.md` | **ARCHIVE** |
| `docs/specs/min/invoicing.min.md` | Min invoicing | То же | Дублирует `modules/invoicing.md` | **ARCHIVE** |
| `docs/specs/min/portals.min.md` | Min portals | То же | Дублирует `modules/{client,candidate}_portal.md` | **ARCHIVE** |
| `docs/specs/min/scheduler.min.md` | Min scheduler | Цитируется в `module-catalog-and-routing-map.md` как "путаемый с активной capability" | Дублирует `modules/scheduler.md`, но активно цитируется | **REVIEW** — обновить в module-catalog ссылку → archive, либо `KEEP` |

### B.2 LLM context infrastructure

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/_llm/context_map.yml` | LLM context map: anchors → spec paths | **Содержит stale пути**: `docs/specs/spec-documents.md` (правильно: `docs/spec-documents.md`); упоминает `db/schema_*.sql`, которые есть, но не покрывают новый канон. Не цитируется ни одним инструментом сейчас. | Не противоречит, но устарел | **MERGE_INTO_CANON** (если используется) или **ARCHIVE** |
| `docs/_llm/abbreviations.yml` | Список сокращений для LLM | Цитируется только в архивированном `agent_tz.md` | Не противоречит | **ARCHIVE** |
| `docs/_llm/edit_protocol.md` | Протокол редактирования delta-only для LLM | Цитируется в `architecture/multi_tenant_model.md` (упоминается?) — проверить | **ACTIVE** для LLM-агентов, но overlap с `AGENTS.md` | **REVIEW** — KEEP или MERGE_INTO_CANON |
| `docs/_llm/snippets/` | Папка со сниппетами (RLS, expiry, approvals) | Не цитируется напрямую | Не противоречит | **REVIEW** — содержимое неизвестно |

### B.3 Documents module spec dual-track

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/spec-documents.md` | «Живой спек v0.1 модуля Документы» (DocumentType, Document, Ruleset, статусы, чеклист, валидации) | Ноябрь 2025. Параллельно существуют `docs/specs/modules/documents.md`, `documents_workflow_contract.md`, `ADR-009-document-hub-platform-layer.md`, `ADR-014-document-hub-access-model.md`. Цитируется только из `docs/specs/core.md` | Конкурирует с актуальной модульной + ADR парой | **MERGE_INTO_CANON**: полезные части (ruleset JSON, валидации, regex per-type) — в `modules/documents.md`; затем **ARCHIVE** |

### B.4 Pipe / pipedesign — продуктовый blueprint и design tokens

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/pipe.md` | 800-строчный «HostFlow Product Blueprint» на основе анализа Pipedrive: продуктовая философия, UX-паттерны, IA, automation logic, pipeline design | Цитируется из `SSOT.md`, `HOSTFLOW_AUDIT_AND_PLAN.md`, `plans-matrix.md`, `operations-loop.md`. Часть data-model замещена `hostflow-core-domain-map-v1.md`, но UX/IA части уникальны | Активный канон по UX/IA, частично legacy по data model | **KEEP** + добавить header «Data model сменён на `hostflow-core-domain-map-v1.md`; здесь — UX/IA blueprint» |
| `docs/pipedesign.md` | Лендинг + дизайн-система + токены (~5KB) | **Цитируется напрямую из кода**: `hostflow-frontend/tailwind.config.cjs` ("Brand tokens aligned to docs/pipedesign.md") | Single source of truth для design tokens | **KEEP** (актуальный канон) |

### B.5 Operational runbook-style docs (одноразовые how-to)

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/META_GRAPH_190_FIX.md` | Как починить ошибку GRAPH_190 в Meta Leads (получение нового Page Access Token и т.д.) | Не one-shot — это **процедура**, повторно используется при истечении токена. Цитируется только из `HOSTFLOW_AUDIT_AND_PLAN.md` (история) | Не противоречит | **KEEP** или **MERGE_INTO_CANON**: `docs/runbooks/meta-graph-190.md` (отложить до Stage реструктуризации папок) |
| `docs/VAPID_KEYS.md` | Setup VAPID keys для Web Push | Активная процедура (генерация, ENV, деплой) | Не противоречит | **KEEP** или **MERGE_INTO_CANON**: `docs/runbooks/vapid-keys.md` |
| `docs/FRONTEND_DEPLOY.md` | Deploy frontend через Caddy | Активная процедура | Не противоречит | **KEEP** или **MERGE_INTO_CANON**: `docs/runbooks/frontend-deploy.md` |
| `deploy/TROUBLESHOOTING.md` | Deploy troubleshooting | Активная процедура | Не противоречит | **KEEP** или **MERGE_INTO_CANON**: `docs/runbooks/deploy-troubleshooting.md` |

### B.6 SEO / UX

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/seo/content-page-template.md` | SEO-шаблон content-страницы (H1/H2/CTA структура для feature/use-case/comparison страниц F10) | Март 2026; не цитируется кодом, но активная content-конвенция | Не противоречит | **KEEP** (контент-операционка) |
| `docs/ux/business-terminology-map.md` | Словарь терминов agency/employer/services (Client/Company/Vacancy/Order) | Март 2026, **Status: ACTIVE** (внутри). Частично перекрывается `docs/specs/glossary.md`, но содержит уникальный business-type mapping | Перекрытие с glossary | **MERGE_INTO_CANON**: содержимое в `glossary.md`, затем **ARCHIVE**, **или KEEP** как UX-канон |

### B.7 Architecture docs (старые, но цитируемые из security/code)

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/architecture/multi_tenant_model.md` | Multi-tenant модель + `tenant_links` | Март 2026; **Цитируется из**: `docs/security/security-ssot.md`, `docs/security/README.md`, `docs/security/threat-models/handoff.md`, `.github/labeler.yml`. Но **частично перекрыта** `hostflow-core-domain-map-v1.md` (Company = data boundary) | Активный security canon, конфликт с domain map | **MERGE_INTO_CANON**: обновить под новую модель и оставить, **или KEEP** + добавить header «Часть содержимого мигрирует в `hostflow-core-domain-map-v1.md`» |
| `docs/specs/architecture/rbac_matrix.md` | RBAC матрица ролей и permissions | Ноябрь 2025; **Цитируется из**: `docs/security/security-ssot.md`, `security-review-checklist.md`, `threat-models/exports.md`, `threat-models/client-portal.md`, `backend/app/auth/hiring_workspace_roles.py` | Активный canon | **KEEP** |
| `docs/specs/architecture/object_storage.md` | Object storage модель | Апрель 2026; **Цитируется из**: `docs/security/security-ssot.md`, `threat-models/document-uploads.md`, `security/README.md` | Активный canon | **KEEP** |
| `docs/specs/architecture/job_queue.md` | Job queue модель | Апрель 2026; цитируется из `HOSTFLOW_AUDIT_AND_PLAN.md` Phase 0 #5 | Активный canon | **KEEP** |

### B.8 Большие исторические SSOT-файлы

| Path | Размер | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|---|
| `docs/SSOT.md` | 83 KB | Главный operational SSOT: правила разработки, открытый бэклог, плановые тарифы (§2.16), биллинг-операционка (§2.17) | **Heavy code refs**: `i18n/{en,pl,ru}.json`, `main.py`, `spa_paths.py`, `stripe_price_catalog.py`, `featureFlags.ts`, `bundle-budget.json`, scripts | Главный operational canon | **KEEP** (без перемещения; реструктуризация в `/docs/ssot/` — отдельным этапом после cleanup) |
| `docs/HOSTFLOW_AUDIT_AND_PLAN.md` | 137 KB | Архитектурный аудит + дорожная карта (Phase 0..8) | **Heavy refs** в коде и в десятках specs | Активный roadmap | **KEEP** (без перемещения) |

### B.9 Phase / roadmap files

| Path | Содержимое | Почему REVIEW | Связь с SSOT | Рекомендация |
|---|---|---|---|---|
| `docs/specs/roadmap.md` | Старый roadmap | Достижим из `_llm/context_map.yml`; перекрыт `phase-8-roadmap.md` + `phases-2-8-engineering-closure.md` | Возможно устарел | **REVIEW** — KEEP/ARCHIVE по решению |
| `docs/specs/phase-8-roadmap.md` | Phase 8 roadmap | Цитирует `HOSTFLOW_AUDIT_AND_PLAN.md` Phase 8; читает `phases-2-8-engineering-closure.md` | Активный | **KEEP** |
| `docs/specs/phases-2-8-engineering-closure.md` | Свод по фазам 2-8 | Активный | Активный | **KEEP** |

---

## Сводная таблица рекомендаций

| Рекомендация | Кол-во | Действие |
|---|---|---|
| **KEEP** | ~28 | Оставить без изменений |
| **MERGE_INTO_CANON** | ~5 | Перенести содержимое в канон, затем archive |
| **ARCHIVE** | ~5 | Переместить в `archive/legacy/2026-05-12/` (или новую дату) после подтверждения |
| **DELETE** | 0 | Ничего не подходит под безусловное удаление на этом этапе |

---

## Что произошло и что предстоит

**Уже сделано:**
- Stage 0 (commit `9370fc4`): canonical baseline зафиксирован — 78 .md файлов
- Stage 2 (commit `f1b986e`): 10 явно устаревших / duplicate перемещены в `archive/legacy/2026-05-12/`

**Осталось:**
- Решения по B.1 (5 min-файлов), B.2 (LLM context), B.3 (`spec-documents.md`), B.4 (pipe.md header note), B.5 (4 runbook-style — нужны ли в `docs/runbooks/`), B.6 (`business-terminology-map.md` mergе в glossary), B.7 (`multi_tenant_model.md` обновление под domain map v1), B.9 (`roadmap.md` статус)
- A.1-A.4 — отложено по прямому указанию пользователя (operational backlog)

Реструктуризация папок (`docs/runbooks/`, `docs/ssot/`, перемещение SSOT.md и HOSTFLOW_AUDIT_AND_PLAN.md) — **отдельным этапом** после cleanup.
