# ADR-021 — Architecture Review Checklist

**ADR:** [ADR-021-unified-intake-resolution-model.md](ADR-021-unified-intake-resolution-model.md)  
**Status:** Proposed (revision 2)  
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
| 1.1 | Each **new external intake event** creates a **separate Application** (operational case) | ☐ |
| 1.2 | **Clarification / re-submit** on same case **supplements** existing Application (new Submission) | ☐ |
| 1.3 | Match with Candidate / ClientAccount **does not** auto-merge Applications or destroy history | ☐ |
| 1.4 | One domain entity **may have many Applications** over time | ☐ |

**Reviewer note:** Matching must not collapse inquiry history. ☐ Agree

---

### 2. Application / Submission / Intake event (ADR §3)

| # | Check | Pass? |
|---|-------|-------|
| 2.1 | Three concepts are **semantically distinct** in the contract | ☐ |
| 2.2 | One Application may contain **multiple Submissions** | ☐ |
| 2.3 | Submission list is **append-only** — not single mutable `Lead.normalized` | ☐ |
| 2.4 | Intake event is **never** a product/UI object | ☐ |

---

### 3. Lifecycle vs resolution (ADR §7)

| # | Check | Pass? |
|---|-------|-------|
| 3.1 | `lifecycle_status` and `resolution_code` are **separate fields** | ☐ |
| 3.2 | `resolved` = process closed; **not** synonymous with `converted` | ☐ |
| 3.3 | Terminal results use `resolution_code` enum only when `lifecycle_status=resolved` | ☐ |
| 3.4 | Module stages remain **secondary** to `lifecycle_status` | ☐ |

---

### 4. Routing and ownership (ADR §6)

| # | Check | Pass? |
|---|-------|-------|
| 4.1 | Exactly **one `module_owner`** per Application at any time | ☐ |
| 4.2 | Application **never** in two operational inboxes simultaneously | ☐ |
| 4.3 | **Reroute** changes owner/intent; **same** `application_id` | ☐ |
| 4.4 | `routing_history[]` is **append-only** audit | ☐ |
| 4.5 | Unknown / ambiguous route → **Intake Review** inbox (Phase 3 path declared) | ☐ |

---

### 5. Submitted data (ADR §5.1)

| # | Check | Pass? |
|---|-------|-------|
| 5.1 | Snapshot includes: schema/profile, presentation version, source, `submitted_at` | ☐ |
| 5.2 | Snapshot includes: raw values, normalized values, attachments, consent metadata | ☐ |
| 5.3 | Submissions are **immutable** after write | ☐ |
| 5.4 | Contract **does not** rely on overwrite of current `Lead.normalized` alone | ☐ |

---

### 6. Reviewed data (ADR §5.2)

| # | Check | Pass? |
|---|-------|-------|
| 6.1 | Field-level structure defined (original, reviewed, status, actor, timestamp, reason) | ☐ |
| 6.2 | Phase 2 API is `reviewed-values`, **not** mutation of submitted snapshot | ☐ |
| 6.3 | `needs_clarification` → new Submission, not in-place edit | ☐ |

---

### 7. Decision idempotency (ADR §9)

| # | Check | Pass? |
|---|-------|-------|
| 7.1 | One decision must not create duplicate target entities | ☐ |
| 7.2 | Executor replay returns same `target_entity_id` | ☐ |
| 7.3 | `execution_status`: pending \| executing \| completed \| failed | ☐ |
| 7.4 | Failed execution **retains** decision intent | ☐ |
| 7.5 | Decision record is separate from executor side effects | ☐ |

---

### 8. Auto-processing policy (ADR §10)

| # | Check | Pass? |
|---|-------|-------|
| 8.1 | **Five policies** are distinct: routing, matching, link, create, reject | ☐ |
| 8.2 | Single `auto_decision` flag is **rejected** as non-compliant | ☐ |
| 8.3 | Default path: submit → inbox → review → decision | ☐ |
| 8.4 | `auto-create` / `auto-link` require explicit policy + gates | ☐ |
| 8.5 | ADR-013 P5C auto-create framed as **compatibility**, not default canon | ☐ |

---

## Soft gates (recommended)

| # | Topic | Pass? |
|---|-------|-------|
| S.1 | Phase 1 feasible **without** `applications` table | ☐ |
| S.2 | Lead remains transport-only; UI Constitution alignment | ☐ |
| S.3 | Phase 1A / 1B split into **separate PRs** is acceptable to eng | ☐ |
| S.4 | Tenant isolation sufficient on decision + submission audit (security) | ☐ |
| S.5 | Product accepts removal of `/app/leads` from primary nav (Phase 1A) | ☐ |

---

## Explicitly out of scope (do not block ADR on these)

- Exact JSON storage location on Lead vs side table
- Migration script for existing `Lead.normalized` overwrite behaviour
- Intake Review / Services inbox UI design (Phase 3)
- Telegram ingestion contract (Phase 4)
- Phase 1A / 1B task doc content (written **after** ADR Accepted)

---

## Reviewer sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Architecture | | | ☐ Approved ☐ Changes requested |
| Product | | | ☐ Approved ☐ Changes requested |
| Engineering | | | ☐ Approved ☐ Changes requested |
| Security | | | ☐ Approved ☐ Changes requested |

**Changes requested — summary:**

```
(leave blank or list blockers)
```

---

## Post-approval sequence (do not start before Accepted)

1. `docs/specs/tasks/phase-1a-unified-intake-inbox-ownership-contract.md`
2. `docs/specs/tasks/phase-1b-unified-intake-review-surface-contract.md`

No implementation PRs until both contracts exist and Phase 1A is explicitly scheduled first.
