# ADR-021 — Architecture Review Checklist

**ADR:** [ADR-021-unified-intake-resolution-model.md](ADR-021-unified-intake-resolution-model.md)  
**Status:** Accepted (Architecture 2026-07-24; Product / Engineering / Security countersignatures tracked on accepting PR)  
**Purpose:** Gate L1 approval before Phase 1A / 1B implementation contracts.  
**Out of scope for this review:** implementation detail, migrations, API field names, UI pixels.

---

## How to use

1. Reviewer reads ADR-021 revision 2 end-to-end.
2. For each section below: **Approve** | **Approve with note** | **Request change**.
3. All **Hard gate** items must be **Approve** (or Approve with note that does not weaken the rule).
4. When all hard gates pass → ADR status may move to **Accepted**.
5. Only after **Accepted** → author Phase 1A and Phase 1B contracts (separate L2 docs).

---

## Hard gates (must pass)

### 1. Unit of inbound work (ADR §2)

| # | Check | Pass? |
|---|-------|-------|
| 1.1 | Each **new external intake event** creates a **separate Application** (operational case) | Approve |
| 1.2 | **Clarification / re-submit** on same case **supplements** existing Application (new Submission) | Approve |
| 1.3 | Match with Candidate / ClientAccount **does not** auto-merge Applications or destroy history | Approve |
| 1.4 | One domain entity **may have many Applications** over time | Approve |

**Reviewer note:** Matching must not collapse inquiry history. Approve

---

### 2. Application / Submission / Intake event (ADR §3)

| # | Check | Pass? |
|---|-------|-------|
| 2.1 | Three concepts are **semantically distinct** in the contract | Approve |
| 2.2 | One Application may contain **multiple Submissions** | Approve |
| 2.3 | Submission list is **append-only** — not single mutable `Lead.normalized` | Approve |
| 2.4 | Intake event is **never** a product/UI object | Approve |

---

### 3. Lifecycle vs resolution (ADR §7)

| # | Check | Pass? |
|---|-------|-------|
| 3.1 | `lifecycle_status` and `resolution_code` are **separate fields** | Approve |
| 3.2 | `resolved` = process closed; **not** synonymous with `converted` | Approve |
| 3.3 | Terminal results use `resolution_code` enum only when `lifecycle_status=resolved` | Approve with note |
| 3.4 | Module stages remain **secondary** to `lifecycle_status` | Approve |

**Note (non-blocking):** `resolution_code=routed` is source-module closed perspective; same `application_id` continues in destination inbox — spell in Phase 1A.

---

### 4. Routing and ownership (ADR §6)

| # | Check | Pass? |
|---|-------|-------|
| 4.1 | Exactly **one `module_owner`** per Application at any time | Approve |
| 4.2 | Application **never** in two operational inboxes simultaneously | Approve |
| 4.3 | **Reroute** changes owner/intent; **same** `application_id` | Approve |
| 4.4 | `routing_history[]` is **append-only** audit | Approve |
| 4.5 | Unknown / ambiguous route → **Intake Review** inbox (Phase 3 path declared) | Approve with note |

**Note (non-blocking):** L0 INV-09 (IntakeRouter once at Lead create) is orthogonal to operator reroute §6.2 — clarified in ADR body.

---

### 5. Submitted data (ADR §5.1)

| # | Check | Pass? |
|---|-------|-------|
| 5.1 | Snapshot includes: schema/profile, presentation version, source, `submitted_at` | Approve |
| 5.2 | Snapshot includes: raw values, normalized values, attachments, consent metadata | Approve |
| 5.3 | Submissions are **immutable** after write | Approve |
| 5.4 | Contract **does not** rely on overwrite of current `Lead.normalized` alone | Approve |

---

### 6. Reviewed data (ADR §5.2)

| # | Check | Pass? |
|---|-------|-------|
| 6.1 | Field-level structure defined (original, reviewed, status, actor, timestamp, reason) | Approve |
| 6.2 | Phase 2 API is `reviewed-values`, **not** mutation of submitted snapshot | Approve |
| 6.3 | `needs_clarification` → new Submission, not in-place edit | Approve |

---

### 7. Decision idempotency (ADR §9)

| # | Check | Pass? |
|---|-------|-------|
| 7.1 | One decision must not create duplicate target entities | Approve |
| 7.2 | Executor replay returns same `target_entity_id` | Approve |
| 7.3 | `execution_status`: pending \| executing \| completed \| failed | Approve |
| 7.4 | Failed execution **retains** decision intent | Approve |
| 7.5 | Decision record is separate from executor side effects | Approve with note |

**Note (non-blocking):** Intent immutable; `execution_status` / `target_entity_id` may advance on retry — clarified in ADR §9.3.

---

### 8. Auto-processing policy (ADR §10)

| # | Check | Pass? |
|---|-------|-------|
| 8.1 | **Five policies** are distinct: routing, matching, link, create, reject | Approve |
| 8.2 | Single `auto_decision` flag is **rejected** as non-compliant | Approve |
| 8.3 | Default path: submit → inbox → review → decision | Approve |
| 8.4 | `auto-create` / `auto-link` require explicit policy + gates | Approve |
| 8.5 | ADR-013 P5C auto-create framed as **compatibility**, not default canon | Approve |

---

## Soft gates (recommended)

| # | Topic | Pass? |
|---|-------|-------|
| S.1 | Phase 1 feasible **without** `applications` table | Approve |
| S.2 | Lead remains transport-only; UI Constitution alignment | Approve |
| S.3 | Phase 1A / 1B split into **separate PRs** is acceptable to eng | Approve |
| S.4 | Tenant isolation sufficient on decision + submission audit (security) | Approve with note — enforce in Phase 1B/2 + RLS tests |
| S.5 | Product accepts removal of `/app/leads` from primary nav (Phase 1A) | Pending Product countersignature |

---

## Explicitly out of scope (do not block ADR on these)

- Exact JSON storage location on Lead vs side table
- Migration script for existing `Lead.normalized` overwrite behaviour
- Intake Review / Services inbox UI design (Phase 3)
- Telegram ingestion contract (Phase 4)
- Phase 1A / 1B task doc content (written **after** ADR Accepted)
- ADR-022 Accept (separate sign-off; not implied by ADR-021 Accept)

---

## Reviewer sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Architecture | Cursor agent (checklist walkthrough) | 2026-07-24 | Approved with notes |
| Product | | | ☐ Approved ☐ Changes requested |
| Engineering | | | ☐ Approved ☐ Changes requested |
| Security | | | ☐ Approved ☐ Changes requested |

**Changes requested — summary:**

```
(none blocking)

Non-blocking follow-ups:
- Phase 1A: routed vs same application_id for UI
- Phase 1B: execution_status transitions on retry
- Author phase-1a / phase-1b task docs
- ADR-022 remains Proposed — own sign-off required
```

---

## Post-approval sequence (do not start before Accepted)

1. `docs/specs/tasks/phase-1a-unified-intake-inbox-ownership-contract.md`
2. `docs/specs/tasks/phase-1b-unified-intake-review-surface-contract.md`

No implementation PRs until both contracts exist and Phase 1A is explicitly scheduled first.

**Do not** treat [ADR-022](ADR-022-intake-form-purpose-and-submission-policy-model.md) as settled canon until it has its own Accept pass.
