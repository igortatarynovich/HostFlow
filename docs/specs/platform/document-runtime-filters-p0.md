# Document Runtime Filters — product track canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon + P1 complete (2026-06-24).  
**Hierarchy:** L3 product track — **consumer** of `document_runtime_v1`. Not foundation.  
**Owner:** Architecture canon + product team.

**Opened:** 2026-06-24 — after **Document UI Status Badges v1 closed** ([`document-ui-status-badges-p0.md`](document-ui-status-badges-p0.md) §20).

**Next implementation step:** Track D — Candidate Workspace runtime readiness surface ([`document-runtime-filters-p0.md`](document-runtime-filters-p0.md) P1 complete).

**Related canon:**

| Document | Relationship |
|----------|--------------|
| [`document-ui-status-badges-p0.md`](document-ui-status-badges-p0.md) | Badges = display projection; filters = selection predicate — same runtime source |
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | **Single upstream source** — `document_runtime_v1` |
| [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) | Notification events — separate from list filters |

---

## 1. Purpose

**Document Runtime Filters** answer:

> Given `document_runtime_v1`, does this document instance match a user-selected filter — without re-evaluating lifecycle or expiry?

Eliminates drift where badges show `expired` but filters use legacy `DocumentStatus` or date math.

---

## 2. Runtime Filter Vocabulary v1

| Filter | Runtime predicate |
|--------|-------------------|
| `expired` | `expiry_status === 'expired'` |
| `expiring_soon` | `expiry_status === 'expiring_soon'` |
| `missing` | `workflow_status === 'missing'` |
| `pending_review` | `runtime_signal === 'pending_verification'` |
| `rejected` | `workflow_status === 'rejected'` |
| `satisfied` | `satisfies_requirement === true` |

**Single matcher:** `runtimeMatchesFilter(runtime, filter)` — only predicate implementation.

---

## 3. Hard rules

**Forbidden as filter source:**

- `daysUntil()`, `Date.parse` for expiry filtering
- `isExpiringSoonDoc()`, `primaryStatus()` for filter matching
- Owner summary buckets (`ready_types`, `expiring_soon[]`, …)
- Checklist counters / readiness fragments
- Hub `DocumentStatus` enum comparison for filter match

**Allowed source:** `document_runtime_v1` only (on instance or via `document_runtime` on `DocumentOut`).

Workflow edit controls and sort keys may still read hub fields — that is not filtering.

---

## 4. P1 consumers

| Consumer | P1 |
|----------|-----|
| `CandidateDocuments` | ✅ |
| `CandidateDocsRailPanel` | ✅ |
| `DocumentsRegistryPage` | ✅ |

---

## 5. P1 acceptance

1. One runtime → same filter result everywhere (`runtimeMatchesFilter`).
2. No frontend date math in filter paths.
3. No duplicated predicates outside `runtimeDocumentFilters.ts`.
4. Unit tests cover full vocabulary v1.

---

## 6. Post-P1 (Track D preview)

Candidate Workspace readiness KPIs and blockers — runtime-driven surfaces; filters are prerequisite to remove legacy bucket drift in list + card views.

---

## 7. P1 implementation status (2026-06-24)

| Deliverable | Status | Location |
|-------------|--------|----------|
| `runtimeMatchesFilter` | ✅ | `runtimeDocumentFilters.ts` |
| `CandidateDocuments` | ✅ | Runtime dropdown; legacy status + expiring/missing checkboxes removed |
| `CandidateDocsRailPanel` | ✅ | Runtime filter on checklist rows |
| `DocumentsRegistryPage` | ✅ | Preset filters → runtime vocabulary (+ legacy URL compat) |
| Unit tests | ✅ | 9 tests |

---

## Changelog

- 2026-06-24: **P1 complete** — `runtimeMatchesFilter` + three consumers; no frontend date math in filter paths.
- 2026-06-24: P0 accepted — Document Runtime Filters Track A canon opened.
