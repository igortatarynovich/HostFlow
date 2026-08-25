# HostFlow Documentation Governance

**Цель:** не допустить распада canonical baseline после canonicalization (commit `9370fc4`+) обратно в хаос.

**Принцип:** документация — такой же контракт, как код. Любой новый документ обязан попасть **в правильный слой** (см. [`hierarchy-of-truth.md`](hierarchy-of-truth.md)) и **через правильный entry point** (см. [`documentation-rules.md`](documentation-rules.md)). За каждым каноническим слоем закреплён владелец-канон ([`ownership.md`](ownership.md)).

## Документы governance

| Файл | Назначение | Когда читать |
|---|---|---|
| [`hierarchy-of-truth.md`](hierarchy-of-truth.md) | **L1/L2/L3** — три уровня источников истины. Что важнее чего при конфликте. | Прежде чем ссылаться на `docs/...` как на «канон» |
| [`documentation-rules.md`](documentation-rules.md) | **Правила.** Куда класть новый ADR / workflow / module spec / runbook. Что запрещено. | Прежде чем создавать любой новый `.md` |
| [`ownership.md`](ownership.md) | **Владельцы канона.** Кто отвечает за security / architecture / modules / workflows / operational SSOT. | Прежде чем менять документ из чужого слоя |
| [`repository-operational-canon.md`](repository-operational-canon.md) | **L1 Engineering canon.** Trusted integration, worktree, health/import gates, PR split, recovery archive. | Перед любым Product PR / после recovery / при cleanup worktree |

## Enforcement

| Слой | Механизм |
|---|---|
| **Read-time** | `AGENTS.md` § «Documentation Governance» делает чтение этих файлов обязательным для AI-агентов и человеческих контрибьюторов перед изменением документации |
| **Write-time** | `make docs-lint` (Makefile target) — orphan + broken-link + forbidden-pattern + forbidden-path checks |
| **Merge-time** | CI job `docs-governance-gate` (см. `.github/workflows/security-gates.yml`) — те же проверки на PR блокируют merge при нарушениях |
| **Archive contract** | Любой архивированный документ обязан иметь явный canon replacement в `archive/legacy/YYYY-MM-DD/README.md` (см. [`documentation-rules.md`](documentation-rules.md) § «Archive») |

## Что governance НЕ делает

- Не диктует **содержимое** документов (это работа канон-владельцев).
- Не блокирует драфты на feature-ветке — проверки запускаются только на PR в защищённые ветки.
- Не запрещает черновики — но они должны жить в `docs/_drafts/<author>/` (вне canonical surface) или в feature-branch без cross-ref из канона.

## История

- **2026-05-12** — введено по итогам canonicalization pass (commits `9370fc4`…`b143e51`). Triggering risk: появление draft-v2/final-v2 параллельно канону, ad-hoc spec вне ADR, workflow без linkage в `workflows/index.md`.
- **2026-05-12** — Documentation governance package is already tracked and pushed as part of `b97ec8d` (`chore: commit remaining repo changes`). It is accepted as the factual introduction point. No history rewrite will be performed. Future governance changes must be committed separately.
- **2026-07-20** — [`repository-operational-canon.md`](repository-operational-canon.md): seal after missing-file / worktree / recovery crisis; Repository Health + Import Integrity gates mandatory before product work.
