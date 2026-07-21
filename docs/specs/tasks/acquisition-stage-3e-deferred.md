# Acquisition Stage 3E — Deferred Items

**Status:** Deferred (explicitly out of Stage 3E DONE)  
**Parent:** [Stage 3E — Activity Timeline](acquisition-stage-3e-activity-timeline.md) (**DONE** — PR #130–#133)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §10 · §14  
**Not Stage 4:** these are pipeline / instrumentation gaps; Flight Runtime is a separate epic — [stage-4](acquisition-stage-4-flight-runtime.md).

> Captured at Stage 3E close-out so they are **not** silently papered over inside Stage 4 UI/runtime work.

---

## Deferred backlog

| # | Item | Why deferred in 3E | Suggested home |
|---|------|--------------------|----------------|
| D1 | **Recruitment acquisition stamp + submission normalization** | Recruitment Lead→Application paths without Acquisition stamp / submission linkage cannot emit Timeline events without inventing a second pipeline | Intake / 3C normalization slice before more Recruitment emits |
| D2 | **Meta submission normalization** | Meta leads without a Submission row have no Timeline choke-point; do not emit from webhook adapters alone | Meta intake completeness + Submission always-on path |
| D3 | **Unified duplicate disposition → `DuplicateDetected`** | Catalog includes `DuplicateDetected`; no single final-disposition choke-point yet (`apply_blocked_duplicate_outcome` alone is insufficient) | Emit only at unified final disposition after pipeline normalization |
| D4 | **`create_candidate_full` transaction boundary** | Broader candidate create path vs Lead→Candidate conversion wrapper; Timeline emit must not invent ownership across txn boundaries | Candidate create contract audit; keep emit at conversion wrapper until boundary is explicit |
| D5 | **Catalog-only events for future stages** | Types reserved in catalog (e.g. `FlightFailed`, future runtime/ops events) without a real producer path | Emit when the owning runtime path exists (Stage 4+); do not fake emits |

---

## Rules

1. **Do not** open Stage 4 Launch/Pause/Resume work to “cover” these gaps.  
2. **Do not** emit Timeline events from random adapters to force coverage.  
3. New emits require an existing choke-point + `source_event_id` + catalog type (PR-1 append contract).  
4. Track progress by linking PRs back to this file (D1…D5).

---

## History

- 2026-07-21: Opened at Stage 3E DONE close-out (after PR #133).
