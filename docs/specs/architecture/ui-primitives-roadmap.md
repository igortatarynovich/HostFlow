# UI Primitives Roadmap — Build Order

**Status:** canonical (L1 — development strategy).  
**Owner:** Product + Platform UX + Architecture.  
**Catalog (start here):** [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md)  
**Constitution (frozen):** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)

---

## §0. The one principle

> **We design Flows — continuous user movement — not screens, modules, or isolated components.**

Phase 1 is validated by **Decision Flow** working end-to-end, not by primitive checklists.

> **Entity Model is the source of truth for all surfaces.** See Catalog §0.A — build order: Model → Workspace → Rail → Table.

---

## §0.1 Filters (every task)

1. **Which Flow does this improve?** If unclear → defer.  
2. **Does this eliminate a logged Flow Break?** If not → defer (Phase 1 = audit only).  
3. **Does this belong in Entity Model** (field + projection flags) **instead of a one-off adapter?** If yes → extend model first.

---

## §1. Phases

| Phase | What | Status |
|-------|------|--------|
| **0** | Platform Canon | **COMPLETE** |
| **1** | Decision Flow audit (layout baseline) | **Paused** — no new Rail work |
| **2.1** | **Entity Model Canon** — [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md) | **Keep** — L1 passport |
| **2.2** | **Universal Entity Schema** — [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md) §2 | **ACTIVE — sole feature work** |
| **2.3** | Entity Workspace Shell (schema executor) | **Scaffold** |
| **2.4** | Projections — Table, Rail, Search ← Model + Schema | **Blocked** until 2.2–2.3 |
| **3** | Universal Application Workspace | After Phase 2 |

Phase 2 is **Entity Model + Universal Entity Workspace Canon** — not Rail, not «карточка кандидата». See Workspace Canon §9 freeze.

---

## §2. Phase 0 — Platform Canon ✓

Frozen. See Catalog §0 intro.

---

## §3. Phase 1 — Decision Flow Audit (ACTIVE)

> **Next step is not development. Next step is operational audit.**

**Instruction:** «Пройди Decision Flow» — not «сделай DataTable».

### Audit sequence

| Step | Action | Exit |
|------|--------|------|
| 1 | Recruiter walks full **Decision Flow** on Candidates | Log every **Flow Break** |
| 2 | Fix platform until **zero open breaks** on Candidates | See break log |
| 3 | Same audit on **Sales** (Обращения) | New breaks → platform, not Sales fork |
| 4 | **Phase 1 complete** | ≥2 roles, zero open breaks, zero role-specific behavior |

**Break log:** [`decision-flow-breaks-log.md`](decision-flow-breaks-log.md)  
**Break taxonomy:** Catalog §0 — FB-1 … FB-6

### What counts as a bug

> **Any Flow Break is a platform bug** — not only code errors.

### Allowed work in Phase 1

| Allowed | Forbidden |
|---------|-----------|
| Fix breaks after **UI verification** fails | New features |
| Re-verify #1–#6 before any #7+ | Assuming code merge = break closed |
| Platform fix for highest **P0** | Fixing by discovery order (#7 because #7) |

### Verification gate

1. Manual Decision Flow on Candidates (user behavior only).  
2. Break reproduces → **open** regardless of PR.  
3. #1–#6 must be **UI-verified** before remaining P0 work.  
4. Re-rank open breaks P0 → P1 → P2; fix highest P0 first (#9 may beat #7).

**Log:** [`decision-flow-breaks-log.md`](decision-flow-breaks-log.md)

### Reference reminder (why we audit)

**Decision Workspace** = first **Reference Scenario**. **Decision Flow:**

```text
List → Select → Rail → Action → Next object
```

Composes: Data Table + Selection Model + Detail Rail.  
Same Flow for every role — different data only.

### What Reference means

Reference = **continuous flow without context loss** — not component completeness, not business KPIs (no object counts, no time targets).

```text
Object selected → decision → action → next object immediately
  → list context preserved
  → no manual return to list
  → no re-finding the same object
  → Entity Workspace only when Decision Flow cannot complete the action
```

**Boundary test:** *Can this action be done in Decision Flow?* Yes → Rail. No → Entity Flow.

### Product DoD (Phase 1 exit)

| # | Criterion |
|---|-----------|
| D1 | **Continuous flow:** select → act → next without manual list recovery |
| D2 | Actions that fit Decision Flow **must** stay in Rail |
| D3 | Entity Workspace **only** when Decision Workspace is **exhausted** |
| D4 | After action → rail updates / next object; no row hunting |
| D5 | **List is the workspace** |
| D6 | Filters, sort, selection, rail persist correctly |
| D7 | Interaction Rules enforced |

Full checklist: Catalog §0.

### Multi-role validation

After **zero open Flow Breaks** on Candidates:

| Role | Pilot | Pass = |
|------|-------|--------|
| **Recruiter** | Candidates | Zero open breaks; module = config + adapters |
| **Sales** | Обращения | Same Decision Flow; new breaks → platform only |

**Phase 1 complete:** ≥2 roles, zero open breaks, zero role-specific table/rail forks.

---

## §4. Phase 2 — Primitives + Compositions

Start after Decision Workspace Reference.

Primitive queue (Button → Form Field → Badge → Status → …) — see Catalog §3.

Compositions assemble only from Reference primitives. Composition rule unchanged.

---

## §5. Phase 3 — Workspaces

Entity / Application Workspace fold together when compositions exist.  
Geometry reference (read-only): [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md).

---

## §6. Freeze map

| Surface | Until | Action |
|---------|-------|--------|
| Platform Canon docs | Phase 0 | Gap only |
| **Everything in Phase 1** | Zero open Flow Breaks on Candidates + Sales | Audit + break fixes only |
| Candidate entity page | Phase 3 | Bugfix only |
| Search Home | Phase 3+ | Bugfix only |
| New architecture docs | — | Forbidden — Catalog row only |

---

## §7. PR gate

1. **Which Flow Break** does this close? No logged FB → defer.  
2. **Which Flow** does this improve? Unclear → defer.  
3. Role-specific table/rail behavior? → reject.  
4. Module-only UI? → reject.  
5. New markdown spec? → reject (break log row OK).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v7 — Phase 1 = operational audit; Flow Break as work unit |
| 2026-07-09 | v6 — Flow filter; continuous flow DoD |
| 2026-07-09 | v1 — initial |
