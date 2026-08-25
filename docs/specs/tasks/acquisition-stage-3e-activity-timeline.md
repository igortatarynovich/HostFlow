# Acquisition Stage 3E — Activity Timeline & Runtime Observability

**Status:** DONE (Product Track) — PR-1…PR-4 merged (#130–#133)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §10 · §14 slice **3E**  
**Parents:** Epic P / 3D ✅ · R3.5 Flights dispatch ✅ · Forms Sprint 1–6 ✅  
**PRs:** #130 Foundation · #131 Instrumentation · #132 Read API · #133 Thin UI  

> Stage 3E builds **observability infrastructure** only: a universal Activity Timeline.  
> It closes the V1 vertical’s history/audit slice (3A→3E).  
> **Not** Flight Runtime / operations. **Not** C2.4. **Not** multi-Flight UX / Template catalog (V2).  
> Model = **`AcquisitionActivityEvent`**.

**Maturity ladder (locked — ADR-024 §14.1):**

```text
3E Observability  — see          →  PR-1…PR-4  →  DONE ✅
4  Operations     — control      →  Flight Runtime (next Product)
5  Optimization   — improve      →  future horizon
6  Analytics      — decide       →  future horizon
```

Next Product epic: [`acquisition-stage-4-flight-runtime.md`](acquisition-stage-4-flight-runtime.md).  
Deferred instrumentation / pipeline items (not Stage 4): [`acquisition-stage-3e-deferred.md`](acquisition-stage-3e-deferred.md).

**Supersedes naming:** earlier draft `acquisition-stage-3e-flight-timeline.md` (Flight Timeline) — do not implement that framing.

---

## Why now

Communication foundation (C0–C2.2, C2.3 implemented) is mature enough for daily ops.  
**Product Track** delivered **Activity Timeline** — durable, typed history of the inbound demand flow.

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome
                 ↑
     Acquisition Activity Timeline (single store, many views)
```

---

## Product Track vs Engineering Track

| Track | Work | Blocks Product? |
|-------|------|-----------------|
| **Product** (this slice) | Activity Timeline foundation → instrumentation → read API → thin UI | — |
| **Engineering** | Full-repo pytest debt, #127 CI-unblock polish, C2.3 merge rebase | **No** — unless clean deploy / Alembic / new module bootstrap breaks |

C2.4 Scheduling remains **frozen**. C2.3 stays implementation-complete; merge when Engineering Track can land without stopping Product.

---

## Shipped (PR-1…PR-4)

### PR-1 — Foundation (#130)

- `acquisition_activity_events` + Alembic  
- Catalog + payload contracts  
- `append_activity_event()` single write path  
- Idempotency on `(tenant_id, source_event_id)`  
- Immutable (no update/delete API)

### PR-2 — Instrumentation (#131)

- Emit via `append_activity_event()` only at existing choke-points  
- Flight lifecycle, EndpointChanged, Submission/Routing, ResultAttributed, OutcomeChanged, LeadCreated, CandidateCreated  
- Explicit non-emits documented in [`acquisition-stage-3e-deferred.md`](acquisition-stage-3e-deferred.md)

### PR-3 — Timeline Read API (#132)

- `GET /api/v1/platform/acquisition-activity` (read-only)  
- Cursor pagination: `after_occurred_at` + `after_id` → `(occurred_at, id) >`  
- Filters + catalog `event_type` + exclusive time bounds + limit ≤ 200  
- Tenant + Acquisition read RBAC; no eager PII joins; GET/HEAD only

### PR-4 — Thin Operator UI (#133)

- `/app/acquisition/activity` — displays Read API only  
- Human labels, ref chips, payload expand (`<pre>` text)  
- Cursor Load more; filter Apply resets list/cursor  
- **No** Launch / Pause / Resume or write clients

```text
1. Foundation (model + append + catalog)     ← PR-1 (#130) ✅
2. Instrument existing 3C/3D paths          ← PR-2 (#131) ✅
3. Read API                                 ← PR-3 (#132) ✅
4. Thin UI last                             ← PR-4 (#133) ✅ → Stage 3E DONE
```

---

## Out of scope (all of 3E)

- **Flight Runtime / Stage 4** (Campaign/Flight CRUD, Endpoint Management, Launch/Pause/Resume, Live Intake Monitor, basic metrics, runtime actions)  
- Multi-Flight UX / wave compare (V2)  
- CampaignTemplate catalog  
- Forms Builder expansion  
- C2.4 Scheduling  
- Using Timeline as Automation Engine transport  
- Fixing the 657 base-known integration pytest failures (Engineering Track)  
- Weakening Acquisition product contract tests  
- Deferred pipeline items — [`acquisition-stage-3e-deferred.md`](acquisition-stage-3e-deferred.md)

---

## Definition of Done (Stage 3E)

Stage 3E is **complete** when Activity Timeline observability is shipped end-to-end (PR-1…PR-4). Flight Runtime is **not** required.

- [x] Single immutable Activity Timeline store (`acquisition_activity_events`)  
- [x] Events typed + versioned (`event_type` + `event_version` + payload contracts)  
- [x] Retry / redelivery does not duplicate (`source_event_id` idempotency)  
- [x] Tenant isolation enforced (app + tests)  
- [x] Flight and Campaign history from one store without row copies  
- [x] Existing 3C/3D chain instrumented without a second pipeline  
- [x] Timeline is **not** used as Automation Engine queue  
- [x] Read API available (PR-3)  
- [x] Operator can inspect history in minimal UI (PR-4) — observe only  
- [x] Clean PostgreSQL migration path  
- [x] Acquisition contract suites green; no new SPA `/app` literals; no cross-module ownership breaks  
- [x] Base-known 657 legacy failures are **not** a Product blocker  
- [x] ADR-024 3E marked DONE; V1 observability vertical closed  
- [x] Stage 4 Flight Runtime queued as next Product epic (not started inside 3E)  
- [x] Deferred items captured separately ([deferred](acquisition-stage-3e-deferred.md))

---

## History

- 2026-07-21: Opened as Product Track (Flight Timeline draft).  
- 2026-07-21: **Canon correction** — `AcquisitionActivityEvent`; Timeline ≠ event bus; PR 1–4; provider-agnostic; single store / many views. Filename → `acquisition-stage-3e-activity-timeline.md`.  
- 2026-07-21: **Boundary lock** — Stage 3E = observability only (ends at PR-4); Flight Runtime = Stage 4 (queued).  
- 2026-07-21: PR-3 Read API merged (#132); PR-4 Thin UI branch opened.  
- 2026-07-21: **DONE** — PR #133 merged; deferred backlog opened; Stage 4 becomes next Product epic.
