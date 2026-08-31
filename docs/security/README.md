# HostFlow — Security Operating Model

Этот каталог — **канонический security layer** в SDLC HostFlow. Документы здесь обязательны к соблюдению при изменениях, затрагивающих данные, доступ, документы, интеграции или публичные потоки.

## Иерархия

| Документ | Назначение |
|----------|------------|
| [security-ssot.md](./security-ssot.md) | Единый источник истины: классификация данных, изоляция, RBAC, handoff, auth, интеграции, тесты, KPI, IR. |
| [runtime-roadmap.md](./runtime-roadmap.md) | Фазовый backlog: runtime assertions, observability, telemetry, detection, AI/search isolation, scorecard; **канон полей security-событий**, security-owned pipeline. |
| [detection-runbooks.md](./detection-runbooks.md) | Phase 7: triage runbooks для `detection.alert.raised` (export anomaly, retrieval/signed-URL bursts). |
| [security-scorecard.md](./security-scorecard.md) | Phase 8: living security scorecard (regen: `make security-scorecard`). |
| [security-events-governance.md](./security-events-governance.md) | Правила владения security events: canonical v1, taxonomy PR, запрет raw events, redaction, отделение transport от producers. |
| [security-review-checklist.md](./security-review-checklist.md) | Обязательный чеклист для каждого PR, который трогает security perimeter. |
| [threat-models/](./threat-models/) | Узкоспециализированные threat models по поверхностям атаки. |
| [credential-exposure-and-secrets-injection.md](./credential-exposure-and-secrets-injection.md) | **OPEN P0** — измеренные пути экспозиции секретов (образ, bind mount, права 644), классы credential-ов и последовательность ротации R-1…R-7. Значения секретов в документе отсутствуют по правилу. |
| [github-labels.md](./github-labels.md) | Имена GitHub labels + команды `gh` для первичной настройки. |
| [runtime-validation-report-hf-sec-stabilization-01.md](./runtime-validation-report-hf-sec-stabilization-01.md) | Отчёт спринта HF-Sec-Stabilization-01: legacy burn-down, runtime validation, telemetry quality (аудит репозитория + operational follow-ups). |
| [operations/security-runtime-cycle-checklists.md](./operations/security-runtime-cycle-checklists.md) | Практические процедуры цикла: staging log validation, volume snapshot, worker context audit (код), document flow manual, ссылка на mini-review / Search–AI merge gate. |

## Enforcement (CI + process)

- **PR template:** `.github/pull_request_template.md` (единый gate для всего репо).
- **CI:** `.github/workflows/security-gates.yml` — pip-audit, bandit, npm audit + sensitive-high gate, dependency-review, Trivy (CRITICAL), threat-model/docs gate, SQL f-string scan, **no raw `emit_security_event(`** (canonical security events).
- **Авто-метки:** `.github/workflows/pull-request-labeler.yml` + `.github/labeler.yml`.

## Связь с остальной документацией

- Мультитенантность и RLS: `docs/specs/architecture/multi_tenant_model.md`
- RBAC и панели: `docs/specs/architecture/rbac_matrix.md`
- Handoff (контракт): `docs/specs/architecture/handoff-contract.md`
- Документы / storage: `docs/specs/architecture/object_storage.md`, `docs/specs/architecture/ADR-014-document-hub-access-model.md`
- Операционный бэклог продукта: `docs/SSOT.md` (не дублирует security SSOT)

## Правило приоритета

Если конфликт между «быстрой фичей» и требованиями из `security-ssot.md` — **сначала согласуется изменение SSOT или делается безопасная инкрементация**. Молчаливый security-долг запрещён.
