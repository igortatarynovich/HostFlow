# HostFlow — Security Operating Model

Этот каталог — **канонический security layer** в SDLC HostFlow. Документы здесь обязательны к соблюдению при изменениях, затрагивающих данные, доступ, документы, интеграции или публичные потоки.

## Иерархия

| Документ | Назначение |
|----------|------------|
| [security-ssot.md](./security-ssot.md) | Единый источник истины: классификация данных, изоляция, RBAC, handoff, auth, интеграции, тесты, KPI, IR. |
| [runtime-roadmap.md](./runtime-roadmap.md) | Фазовый backlog: runtime assertions, observability, telemetry, detection, AI/search isolation, scorecard; **канон полей security-событий**, security-owned pipeline. |
| [security-review-checklist.md](./security-review-checklist.md) | Обязательный чеклист для каждого PR, который трогает security perimeter. |
| [threat-models/](./threat-models/) | Узкоспециализированные threat models по поверхностям атаки. |
| [github-labels.md](./github-labels.md) | Имена GitHub labels + команды `gh` для первичной настройки. |

## Enforcement (CI + process)

- **PR template:** `.github/pull_request_template.md` (единый gate для всего репо).
- **CI:** `.github/workflows/security-gates.yml` — pip-audit, bandit, npm audit + sensitive-high gate, dependency-review, Trivy (CRITICAL), threat-model/docs gate, SQL f-string scan.
- **Авто-метки:** `.github/workflows/pull-request-labeler.yml` + `.github/labeler.yml`.

## Связь с остальной документацией

- Мультитенантность и RLS: `docs/specs/architecture/multi_tenant_model.md`
- RBAC и панели: `docs/specs/architecture/rbac_matrix.md`
- Handoff (контракт): `docs/specs/architecture/handoff-contract.md`
- Документы / storage: `docs/specs/architecture/object_storage.md`, `docs/specs/architecture/ADR-014-document-hub-access-model.md`
- Операционный бэклог продукта: `docs/SSOT.md` (не дублирует security SSOT)

## Правило приоритета

Если конфликт между «быстрой фичей» и требованиями из `security-ssot.md` — **сначала согласуется изменение SSOT или делается безопасная инкрементация**. Молчаливый security-долг запрещён.
