# Document Candidate Workspace — product track canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon + P1 complete (2026-06-24).  
**Hierarchy:** L3 product track — **consumer** of `document_runtime_v1` on Candidate Card / work rail.  
**Owner:** Architecture canon + product team.

**Opened:** 2026-06-24 — after **Document Runtime Filters Track A P1 complete** ([`document-runtime-filters-p0.md`](document-runtime-filters-p0.md)).

**Related canon:**

| Document | Relationship |
|----------|--------------|
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | Upstream runtime + delivery contract |
| [`document-ui-status-badges-p0.md`](document-ui-status-badges-p0.md) | Badge projection per item |
| [`document-runtime-filters-p0.md`](document-runtime-filters-p0.md) | Filter predicates (list views) |

---

## 1. Purpose

**Candidate Workspace runtime surface** answers:

> Given hub checklist `document_runtime_v1` items, what readiness KPI, blockers, and warnings should the Candidate Card show?

Single read-only aggregation — no legacy owner-summary buckets as source of truth when runtime items are present.

---

## 2. Workspace vocabulary v1

| Surface | Runtime source |
|---------|----------------|
| **percent ready** | `satisfiedCount / totalRequired` from `satisfies_requirement` |
| **readiness key** | Derived from item badges (problem / ready / in_progress / …) |
| **blockers** | `document_runtime.blockers[]` per required type |
| **warnings** | `document_runtime.warnings[]` (e.g. expiring_soon) |
| **pipeline buckets** | Mapped from badges: missing → missing; rejected/expired → problematic; pending → in_progress |

---

## 3. Hard rules

**Forbidden when runtime items present:**

- `summary.required.missing` / `problematic` / `ready_types` as SoT
- `summary.expiring_soon[]` date lists
- `candidate.docs_progress` counters for KPI
- Frontend expiry date math

**Allowed fallback:** legacy summary/candidate fields only when `runtimeItems` absent (strangler).

**Single aggregator:** `buildRuntimeWorkspaceFromSummary()` in `runtimeWorkspacePresentation.ts`.

---

## 4. P1 consumers

| Consumer | P1 |
|----------|-----|
| `CandidateDocsRailPanel` | ✅ KPI + blockers + `onLoadedBlockers` |
| `CandidateDocsChecklistMiniPanel` | ✅ percent + blockers/warnings |
| `CandidateDocsPanel` | ✅ header KPI when summary loaded |

---

## 5. P1 acceptance

1. Runtime items → same KPI/blockers on rail and panel.
2. `onLoadedBlockers` fed from runtime pipeline buckets, not legacy arrays.
3. No owner-summary bucket SoT when runtime checklist available.
4. Unit tests on workspace aggregator.

---

## 6. Post-P1

**Next track:** Dashboard KPIs (Track B) — tenant-level aggregates from same runtime predicates.

---

## 7. P1 implementation status (2026-06-24)

| Deliverable | Status | Location |
|-------------|--------|----------|
| `buildRuntimeWorkspaceFromSummary` | ✅ | `runtimeWorkspacePresentation.ts` |
| `useCandidateRuntimeWorkspace` | ✅ | `hooks/useCandidateRuntimeWorkspace.ts` |
| `CandidateDocsRailPanel` | ✅ | KPI + runtime blockers/warnings |
| `CandidateDocsChecklistMiniPanel` | ✅ | Runtime percent + blockers/warnings |
| `CandidateDocsPanel` / `ReadinessPanel` | ✅ | Runtime KPI header |
| Unit tests | ✅ | 3 tests |

---

## Changelog

- 2026-06-24: **P1 complete** — Candidate Workspace runtime surface on rail + panels.
- 2026-06-24: P0 accepted — Track D canon opened.
