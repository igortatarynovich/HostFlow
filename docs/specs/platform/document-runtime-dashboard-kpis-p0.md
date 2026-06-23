# Document Runtime Dashboard KPIs — product track canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P1 complete (2026-06-24).  
**Hierarchy:** L3 product track — **read-only aggregates** over `document_runtime_v1`. Not foundation.  
**Owner:** Architecture canon + product team.

**Opened:** 2026-06-24 — after **Document Candidate Workspace Track D P1 complete** ([document-candidate-workspace-p0.md](document-candidate-workspace-p0.md)).

**Related canon:**

| Document | Relationship |
|----------|--------------|
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | Upstream runtime — dashboard does **not** re-evaluate lifecycle |
| [`document-runtime-filters-p0.md`](document-runtime-filters-p0.md) | Shared predicate vocabulary (Track A) |
| [`document-candidate-workspace-p0.md`](document-candidate-workspace-p0.md) | Per-candidate workspace surface |

---

## 1. Purpose

Dashboard KPI tiles show **tenant-level counts** aggregated from required-document `document_runtime_v1` checklist items.

Dashboard is **not** a second evaluator. It **projects** existing runtime state.

---

## 2. KPI vocabulary v1

| KPI | Runtime predicate |
|-----|-------------------|
| `expired` | `expiry_status === 'expired'` |
| `expiring_soon` | `expiry_status === 'expiring_soon'` |
| `expiring_7d` | `expiry_status === 'expiring_soon'` **and** `days_left <= 7` (from runtime metadata) |
| `pending_review` | `runtime_signal === 'pending_verification'` |
| `rejected` | `workflow_status === 'rejected'` |
| `missing_required` | `workflow_status === 'missing'` (required checklist item) |
| `ready_documents` | `satisfies_requirement === true` |

**Metadata:** `days_left` and `expires_on` attached at **delivery contract** enrich — not computed in UI.

---

## 3. Hard rules

**Forbidden:**

- New lifecycle/expiry evaluator
- Frontend date math (`daysUntil`, `Date.parse`)
- Owner summary buckets as SoT (`required.missing`, `expiring_soon[]`)
- Notification dispatch, cron, drilldown search, charts (out of P1)

**Allowed fallback:** legacy document-stats fields only when runtime checklist unavailable (strangler).

**Single backend aggregator:** `aggregate_document_runtime_kpis()` + shared `kpi_predicates.py`.

---

## 4. P1 deliverables

| Block | Scope |
|-------|--------|
| Backend projection | Aggregate `document_runtime.items` across candidates in tenant scope |
| Endpoint | `GET /analytics/document-runtime-kpis` |
| Frontend tiles | Dashboard documents widget — runtime KPI rows |
| Shared predicates | Track A vocabulary + dashboard extensions |
| Tests | expired, expiring_7d, pending, missing |

---

## 5. P1 acceptance

1. Dashboard KPI built from `document_runtime_v1` checklist items.
2. `expiring_7d` uses `days_left` from runtime metadata — no frontend date math.
3. `missing_required` from runtime checklist items.
4. Backend and frontend share Track A predicate vocabulary.
5. Legacy fallback only when runtime absent.

---

## 6. Post-P1

**Next track:** Notification Delivery (Track C) — channel layer over `notification_events`.

---

## 7. P1 implementation status (2026-06-24)

| Deliverable | Status | Location |
|-------------|--------|----------|
| Backend projection | ✅ | `dashboard_projection.py`, `kpi_predicates.py` |
| Endpoint | ✅ | `GET /analytics/document-runtime-kpis` |
| Expiry metadata | ✅ | `delivery_contract.py` (`days_left`, `expires_on`) |
| Frontend tiles | ✅ | `DashboardOpsOverviewPanels.tsx` |
| Shared predicates | ✅ | `runtimeDocumentFilters.ts` (Track A + dashboard KPIs) |
| Unit tests | ✅ | backend + frontend |
