# Repository Operational Canon

**Status:** **NORMATIVE (L1 — Engineering canon)**  
**Date:** 2026-07-20  
**Stable base:** `integration/release-product-a-b` @ `d7c8fd25` (and successors only via fast-forward)  
**Owner:** Engineering lead ([`ownership.md`](ownership.md) · Engineering canon)  
**Parents:** [`AGENTS.md`](../../AGENTS.md) · [`hierarchy-of-truth.md`](hierarchy-of-truth.md) · INV-16 Decision Priority  
**Related gates:** [`../specs/gates/git-import-integrity-and-repo-health.md`](../specs/gates/git-import-integrity-and-repo-health.md)

> Канон **разработки репозитория**, не продуктовой архитектуры HostFlow.  
> После инцидентов July 2026 (missing files, смешанные PR, потеря worktree, `/tmp` как SoT) этот документ — **обязательный** контракт для людей и AI-агентов.

---

## 1. Trusted base

| Rule | Detail |
|------|--------|
| **Единственный trusted base** | `integration/release-product-a-b` |
| **Синхронизация** | Только **fast-forward** с `origin/integration/release-product-a-b` |
| **Запрещено** | `git reset --hard` / `git clean -fd` до документирования уникальных изменений |
| **Запрещено** | Считать `main`, feature tip или `/tmp` копию источником истины для merge |

Любая продуктовая ветка создаётся **от актуального tip integration**, не от устаревшего локального snapshot.

---

## 2. Worktree discipline

| Rule | Detail |
|------|--------|
| **Работа через worktree** | Параллельные ветки — отдельные worktree; не checkout чужой ветки в занятый worktree |
| **Основной checkout** (`/opt/HostFlow` или эквивалент) | Держать на `integration/release-product-a-b`, **clean** |
| **Один branch ↔ один worktree** | Не пытаться checkout ветки, уже привязанной к другому worktree |
| **Активный worktree** | Не удалять и не переключать, пока сессия не завершена и status не clean |

### Удаление worktree (после merge / завершения сессии)

1. `git status` в worktree — **clean**  
2. `git worktree remove <path>`  
3. `git worktree prune`  
4. Удалить **локальную** merged-ветку (`git branch -d`)  
5. **Remote branch не удалять** автоматически  

### Stale worktree

Запись в `git worktree list` при отсутствии каталога → после проверки: `git worktree prune`.

---

## 3. Mandatory gates before product work

Перед **любым** новым Product PR:

```bash
python3 scripts/repo_health_gate.py --strict-worktrees
# или
make repo-health
```

Gate обязан подтвердить:

1. Clean working tree  
2. Допустимая ветка (integration или явно разрешённая)  
3. Fast-forward с `origin/integration` (на integration)  
4. Ровно **один** Alembic head + валидный revision graph  
5. Нет stale worktree  
6. Нет untracked файлов в `backend/alembic/versions/`  
7. **GIT-IMPORT-INTEGRITY** (локальные TS/TSX imports резолвятся)

| Gate | Script | CI |
|------|--------|-----|
| Repository Health | `scripts/repo_health_gate.py` | Локально / pre-product (обязательно) |
| GIT-IMPORT-INTEGRITY | `hostflow-frontend/scripts/check_ts_import_integrity.py` | `frontend-static-qa` (до `npm ci`) |

Если хотя бы один пункт FAIL — **новая продуктовая разработка не начинается**. Сначала integrity / cleanup.

---

## 4. Pull request discipline

| Rule | Detail |
|------|--------|
| **Один concern — один PR** | Не смешивать restore platform integrity, Product feature и docs/CI-health |
| **Правильная base** | Product / fix на текущий line → `integration/release-product-a-b` (не `main`, если цель — integration line) |
| **Тонкий diff** | После retarget проверить реальный scope (`git diff integration...HEAD`) |
| **Pre-existing CI** | Не чинить чужие gate failures внутри product PR, если они уже на integration tip |
| **Integrity restore** | Missing imported files (класс `deployHosts` / `csrf`) — **отдельный** PR, приоритетнее feature |

### Запрет смешанных PR

Недопустимо в одном PR одновременно, например:

- questionnaire → Communication Pipeline **и** duplicates/rematch **и** CORS/deployHosts  
- product UX **и** starlette/docs SPA-literal cleanup  
- recovery dump **и** live Alembic chain  

Split → отдельные PR с независимым review.

---

## 5. Recovery & archive branches

| Rule | Detail |
|------|--------|
| **`/tmp` plain copies** | Не SoT. Уникальное → ветка `recovery/*` + README provenance, затем review |
| **Recovery branch** | **Архив**, не продуктовая ветка. **Не merge wholesale** в integration |
| **После review** | Полезное — thin PR от свежей integration; устаревшее — документированно discard |
| **Удаление `/tmp`** | Только после подтверждения, что уникальное уже в `recovery/*` и классифицировано |
| **Удаление recovery worktree** | После стабильного релизного среза; **remote `recovery/*` оставить** как архив |

Канон классификации recovery July 2026:  
[`../specs/gates/recovery-tmp-unique-20260720-review.md`](../specs/gates/recovery-tmp-unique-20260720-review.md)

---

## 6. Historical feature branches as requirements source

| Rule | Detail |
|------|--------|
| **Не rebase** длинных устаревших веток на integration целиком | |
| **Не cherry-pick UI/wizard «как было»** без ownership review | |
| **Старые коммиты** | Источник **требований / идей**, не источник реализации |
| **Новая реализация** | Всегда от текущего integration tip, в архитектуре текущего L0 |

Пример: ADR-022 Product B local commits —  
[`../specs/tasks/adr022-product-b-local-commits-audit.md`](../specs/tasks/adr022-product-b-local-commits-audit.md) → Phase 2 kickoff  
[`../specs/tasks/adr022-phase2-kickoff.md`](../specs/tasks/adr022-phase2-kickoff.md)

---

## 7. Alembic & migrations

| Rule | Detail |
|------|--------|
| Один head | Обязателен (graph gate / health gate) |
| Новые ревизии | Только на актуальном head integration line |
| Stash / recovery drafts | Не копировать в `backend/alembic/versions/` без rewrite parents |
| Untracked `versions/*.py` | Блокируют Repository Health |

---

## 8. Stable development baseline (seal)

С **2026-07-20** считается закрытым операционный кризис:

- Integration — единственный trusted tip  
- Missing-import класс устранён системно (gate + restores)  
- Worktree / recovery / PR scope — дисциплинированы  
- Product work возобновляется только при green Repository Health  

Нарушение этого канона = **process fail**, даже если код «работает локально».

---

## 9. Quick checklist (copy into agent / human start-of-day)

- [ ] `git fetch origin && git status` на integration — clean, FF  
- [ ] `make repo-health` (или `python3 scripts/repo_health_gate.py --strict-worktrees`)  
- [ ] Новая работа — новый worktree от integration tip  
- [ ] PR: один concern, base = integration  
- [ ] Нет checkout веток из чужих активных worktree  
- [ ] `/tmp` не используется как SoT  
