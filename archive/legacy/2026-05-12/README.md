# Legacy documentation archive — 2026-05-12

Файлы этой директории были перемещены сюда в рамках canonicalization пройденной 2026-05-12 (см. commit `9370fc4` для предшествующего baseline нового канона).

**Эти документы не удалены, но больше не являются источником истины.** При расхождении приоритет у канонических документов, перечисленных в столбце «Canon replacement» ниже.

| Заархивированный файл | Прежний путь | Почему legacy | Canon replacement |
|---|---|---|---|
| `agent_tz.md` | `docs/specs/agent_tz.md` | Старое ТЗ для LLM-агента (опирается на `.min.md` / `snippets` / `context_map.yml` стратегию). Полностью замещено каноническим engineering-гайдом. | `AGENTS.md` |
| `agent_prompt.md` | `docs/specs/agent_prompt.md` | Старый prompt-генератор для LLM. Замещён актуальным AGENTS.md и edit-protocol. | `AGENTS.md`, `docs/_llm/edit_protocol.md` |
| `hostflow-ecosystem.md` | `docs/specs/hostflow-ecosystem.md` | Старая модель «5 подбрендов» (HostFlow CRM / LeadHub / Docs / HR / Connect) **конфликтует** с новой моделью пяти продуктовых модулей (recruitment / hr / fleet / services / finance). | `docs/specs/architecture/ADR-004-five-product-modules-and-billing-events.md`, `docs/specs/architecture/platform-architecture-principles.md`, `docs/specs/architecture/module-catalog-and-routing-map.md` |
| `architecture-client_and_subscription_model.md` | `docs/specs/architecture/client_and_subscription_model.md` | Описывает legacy-модель «клиент с тенантом / без тенанта» через таблицу `tenant_links`. Замещено каноном «Company = data boundary» с явным cross-company доступом через handoff. | `docs/specs/architecture/hostflow-core-domain-map-v1.md`, `docs/specs/architecture/ADR-003-tenant-company-module-data-boundaries.md`, `docs/specs/architecture/handoff-contract.md` |
| `client-profile-and-vacancy-redesign.md` | `docs/specs/client-profile-and-vacancy-redesign.md` | Redesign-черновик от 2026-03-12. Не цитируется кодом. Канон по vacancy/recruitment вынесен в актуальные ADR и module-spec. | `docs/specs/architecture/recruitment-domain-model.md`, `docs/specs/modules/vacancies.md`, `docs/specs/modules/companies.md` |
| `public_intake_new_specification.md` | `docs/specs/public_intake_new_specification.md` | Спецификация publication-intake от 2025-12-04. Замещена каноническим ADR. | `docs/specs/architecture/ADR-013-public-intake-strategy.md` |
| `analysis-candidate_intake_improvement_plan.md` | `docs/analysis/candidate_intake_improvement_plan.md` | Improvement plan от 2025-12-04. Реальные decisions перенесены в новый workflow-канон. | `docs/specs/workflows/lead-intake-resolution-and-activity-continuity.md`, `docs/specs/workflows/lead-intake-conversion-flow-audit.md`, `docs/specs/workflows/candidate-creation-entrypoints-audit.md` |
| `workflows-lead_to_candidate.md` | `docs/specs/workflows/lead_to_candidate.md` | Дубликат / устаревшая версия. Конверсия Lead → Candidate описана новым контрактом и операционной моделью. | `docs/specs/workflows/lead-conversion-contract.md`, `docs/specs/workflows/lead-to-candidate-operating-model.md` |
| `workflows-candidate_pipeline.md` | `docs/specs/workflows/candidate_pipeline.md` | Старая «pipeline-кандидата» спецификация. Замещена доменной моделью + ADR-002 (граница Recruitment ↔ HR). | `docs/specs/architecture/recruitment-domain-model.md`, `docs/specs/architecture/ADR-002-modular-recruitment-hr-boundary.md` |
| `workflows-reminders_rework.md` | `docs/specs/workflows/reminders_rework.md` | Rework-черновик подсистемы напоминаний. Канон зафиксирован в ADR-012 + Activity & Notification Operating Layer. | `docs/specs/architecture/ADR-012-activity-notification-operating-layer.md`, `docs/specs/architecture/activity-notification-operating-layer.md` |
| `min-companies.min.md` | `docs/specs/min/companies.min.md` | LLM-min копия (стратегия `.min.md`). Ноль inbound references в active surface. Стратегия `.min.md` ушла вместе с архивированным `agent_tz.md`. Дублирует canon. | `docs/specs/modules/companies.md` |
| `min-documents.min.md` | `docs/specs/min/documents.min.md` | LLM-min копия. Orphan + duplicate. | `docs/specs/modules/documents.md` |
| `min-invoicing.min.md` | `docs/specs/min/invoicing.min.md` | LLM-min копия. Orphan + duplicate. | `docs/specs/modules/invoicing.md` |
| `min-portals.min.md` | `docs/specs/min/portals.min.md` | LLM-min копия (объединённый client_portal + candidate_portal). Orphan + duplicate. | `docs/specs/modules/client_portal.md`, `docs/specs/modules/candidate_portal.md` |

**Замечание:** `docs/specs/min/scheduler.min.md` оставлен в active surface — он явно цитируется из `docs/specs/architecture/ADR-012-activity-notification-operating-layer.md` как пример отдельного booking/services-домена, который команда часто путает с «планировщиком работы рекрутёра».

## Inbound-ссылки, обновлённые в этом коммите

- `docs/specs/rules.md` — ссылка на `workflows/candidate_pipeline.md` заменена на canonical replacement (`recruitment-domain-model.md` + ADR-002).
- `docs/specs/workflows/index.md` — удалены строки таблицы для `candidate_pipeline.md` и `lead_to_candidate.md`; обновлено упоминание в §«Взаимосвязь Workflow».
- `docs/specs/workflows/activities.md` — ссылка на `reminders_rework.md` помечена как **archived** + указан canon.
- `docs/specs/architecture/ADR-012-activity-notification-operating-layer.md` — ссылка на `reminders_rework.md` помечена как заархивированная.

## Что НЕ было заархивировано (требует отдельного review)

Список файлов с REVIEW_REQUIRED см. в Stage 3 отчёте (`/tmp/stage3_review_required.md` после генерации). В текущем cleanup намеренно не тронуты:

- `docs/specs/seeds/`, `docs/specs/tasks/`, `docs/specs/min/`, `docs/specs/i18n/`, `docs/specs/db/migrations_plan_*.md`
- `docs/specs/workflows/document_expiry.md`, `candidate-intake-via-telegram*.md`, `communications-workspace-research.md`, `email-client-outlook-style-research.md`
- `docs/META_GRAPH_190_FIX.md`, `docs/VAPID_KEYS.md`, `docs/FRONTEND_DEPLOY.md`, `deploy/TROUBLESHOOTING.md`
- `docs/seo/`, `docs/ux/`, `docs/_llm/context_map.yml`
- `docs/spec-documents.md`, `docs/pipe.md`, `docs/pipedesign.md`

## Восстановление

Любой файл из этой директории может быть возвращён в актуальный канон:

```bash
git mv archive/legacy/2026-05-12/<file> docs/<original-path>
git commit -m "docs: restore <file> from archive"
```

При восстановлении — обязательно сверить с текущим каноном (см. колонку «Canon replacement» выше), чтобы не вернуть противоречие.
