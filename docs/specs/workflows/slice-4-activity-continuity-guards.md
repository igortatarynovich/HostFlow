# Slice 4 — Activity Continuity Guards (spec skeleton)

**Status:** Guard 1 **Done (2026-07-02)** — UOS “Call candidate” suppression + continuity marker; lead note / activity / intake signals; conversion integration tests. Guard 2 **Done (2026-07-02)** — lead note + intake snapshot carried to candidate (`lead_continuity_v1`), audit marker, candidate card panel. Further guards (reminder SLA) incremental.  
**Depends on:** intake routing & decisions (Slice 2), qualification summary read-layer (Slice 3).  
**Intent:** tighten **Lead → Candidate** handoff so the system does not invent duplicate work or “day zero” contact semantics when the lead already has real activity.

**Related:** [Recruitment Application — lifecycle semantics](recruitment-application-lifecycle.md) (Application **intent** / status / idempotency on `lead_id` — **orthogonal** to this slice; see boundary note below).

---

## 1. Scope

- **In:** continuity at **conversion** from **Lead** to **Candidate** (process / attach / pool-adjacent paths that create or bind a candidate).
- **Out:** redesign of full CRM activity model, generic automation builder, or cross-entity scheduling unrelated to this handoff.

### 1.1 Boundary vs Recruitment Application lifecycle

[recruitment-application-lifecycle.md](recruitment-application-lifecycle.md) defines **Application** state (applied / in_review / …), transitions, and **idempotency** (e.g. one Application per `lead_id` on canonical conversion — §10). **Slice 4 continuity guards** operate on **Candidate-side operational work** (default UOS “Call candidate” reminder, future reminder/timeline hygiene) using **Lead** signals (`intake_resolution_v1`, CRM stage, `activity_log`).

**Do not conflate:**

- Suppressing or emitting a **first-contact task** does **not** change Application status and must **not** be inferred as `in_review` / `shortlisted` / etc.
- **Application lifecycle** must still be driven by explicit services/APIs per that doc — not by “contact happened” heuristics alone.

Conversely, **pool vs vacancy** and **one row per `lead_id`** rules remain the source of truth for **RecruitmentApplication** rows; continuity guards only avoid **duplicate candidate tasks** after the same conversion episode.

---

## 2. Problem

After conversion, operators still see:

- duplicate **first contact** tasks or playbooks as if no prior touch existed;
- extra **reminders** or SLA nudges triggered by candidate defaults while the **lead** already had contact attempts, notes, or explicit intake outcomes;
- **timeline noise** from overlapping or contradictory “first action” events;
- **lost context** when notes, intake flags, or lead-side signals are not carried in a predictable way.

This produces **fake work**, erodes trust in next-action UX, and wastes SLA capacity.

---

## 3. Guardrails (product)

- If a **meaningful contact or intake decision** already exists on the **Lead**, the **Candidate** must not be treated as a **greenfield** “first contact only” case without an explicit, auditable exception path.
- **No duplicate** default “first call / first contact” creation when equivalent work is already satisfied at lead scope (per rules in §5).
- **Reminders** must not be spawned for outcomes already achieved on the lead (e.g. contact completed, reject, pool handoff) unless a *new* obligation is defined — not a blind copy of generic candidate onboarding rules.
- Continuity must be **testable**: given lead state + conversion event, assert what tasks/reminders/timeline entries appear or do not appear.

---

## 4. Data sources (audit targets)

Use existing storage and events; no new “spine” required for this slice:

| Source | Use |
|--------|-----|
| Lead timeline / lead-scoped events | What happened before conversion |
| `normalized.intake_resolution_v1` | reject / request_info / pool / qualify signals |
| Lead notes (and any lead-scoped comments) | Context to **carry** or reference on candidate |
| Contact attempts / logged contact (lead or shared identifiers) | “Already contacted” |
| `ActivityLog` (or equivalent audit stream) | Prove idempotent / no duplicate side effects |
| Existing **tasks** & **reminders** tied to lead or pre-conversion | Avoid cloning or re-firing |

Exact field names and APIs are **implementation details**; this slice starts from inventory + rules, not a new schema layer.

---

## 5. Rules (to refine in implementation PR)

**Principle:** default candidate onboarding hooks consult **lead continuity signals** before creating “first contact” work.

| Situation | Direction |
|-----------|-----------|
| Lead has **no** logged contact and **no** blocking intake terminal state | Allow existing **first contact** (or equivalent) candidate defaults. |
| Lead has **completed** contact attempt(s) or equivalent “touched” signal | **Do not** create a second generic first-contact task; optionally create **follow-up** only if product rules say so. |
| `intake_resolution_v1.status` = **rejected** / terminal | No new candidate **first-contact** pressure from generic playbooks; align with existing conversion blockers. |
| **request_info** | No “first call” as if qualified; prefer **info follow-up** or suppress first-contact template until criteria met. |
| **pool** intent / handoff | Do not stack duplicate SLA **reminders** that assume cold outreach; carry context instead. |
| **Notes / summary** | When safe (PII, permissions), **copy or link** lead context to candidate (or first candidate activity) so recruiters do not re-discover. |
| **Duplicate attach** (existing candidate) | **Merge** continuity: never treat as brand-new lead; suppress duplicate first-contact if candidate already active. |

Edge cases (timezone, partial logging, multi-channel) are handled in implementation with **narrow** checks, not a global inference engine.

---

## 6. Non-goals

- **No** unified “Activities spine” or new canonical activity graph.
- **No** full **timeline engine** rewrite or cross-tenant analytics layer.
- **No** **automation overhaul** (rules marketplace, new trigger types) — only **guards** at defined handoff points.
- **No** ML or scoring for “contact likelihood.”

---

## 7. Acceptance (5–7 scenarios)

Automated or manual QA scripts; each scenario: **given** lead state **→** convert **→** **assert** tasks/reminders/timeline/notes behavior.

1. **Call done on lead** — contact logged (or equivalent) **before** process → candidate **does not** get default first-contact task; no duplicate reminder for “first touch.”
2. **request_info** — lead in info-requested intake → candidate path **does not** fire cold first-call playbook; follow-up aligns with spec (or nothing spurious).
3. **reject at intake** — conversion blocked or no spurious candidate tasks (align with current product); **no** reminders implying outreach.
4. **pool** — pool handoff → **no** duplicate SLA/reminder stack for the same obligation; context visible on candidate side as agreed.
5. **duplicate attach** — merge to existing candidate → **no** second “first contact”; continuity with existing candidate activity.
6. **no contact** — untouched lead, normal qualify path → **existing** first-contact behavior **unchanged** (baseline control).
7. **Note / context carry** — lead has note (or key intake fields) → after conversion, recruiter sees **carried** context (or explicit link), not an empty narrative.

---

## 8. Implementation order — Guard 1 first (narrow)

**Framing:** Slice 4 implementation is **operational behaviour alignment** at handoff points — not a new activities engine, not a timeline rewrite.

### 8.1 Why start with “no duplicate first-contact”

- Easy to **verify** (binary: task created or not).
- Easy to **explain** to recruiters (“you already contacted them on the lead”).
- Fast **trust** win; immediately cuts **fake work**.
- Good template for later guards (same pattern: read lead signals → gate candidate default).

### 8.2 Continuity Guard 1 — no duplicate first-contact task

**Goal:** On **Lead → Candidate** conversion, the system must **not** create the **default** “first contact” activity when the lead already reflects that the relationship is past day zero.

**Suppress** the default first-contact creation when **any** of the following is true (exact predicates and field mapping live in the implementation PR; align with existing intake + CRM models):

- A **successful contact attempt** (or product-equivalent “contact completed”) already exists on the **lead** scope.
- **`intake_resolution_v1`** is not in an implicit “no decision yet” state — i.e. any **recorded** intake outcome or action that is not “greenfield new” (reject, request_info, pool, qualify, etc., per current doctrine).
- A **note** and/or **call** (or equivalent logged touch) already exists on the lead.
- Recruiter has **explicitly qualified** the lead (per existing intake / confirm semantics) such that “first outreach” is not the right default.

**Always:** Persist a **continuity marker** (event, log line, or structured flag) when first-contact is **skipped** so behaviour is **auditable** — not a silent no-op.

**Explicitly out of scope for Guard 1:** new reminder rules, full timeline deduplication, or follow-up task templates — those are **later guards** once Guard 1 is covered by tests (see scenario **1** and **6** in §7).

### 8.3 Later increments

After Guard 1: reminder / SLA duplication (§7.1, §7.4), `request_info` playbook alignment (§7.2), richer context carry (§7.7) — **one pressure point per PR** where possible.

### 8.4 Guard 1 — implementation checklist (first PR)

Operational slice: **one guard**, **one contradiction resolved** — no jump into a giant Activities system.

1. **Locate** the code path that creates the **default first-contact** task (or equivalent) on **Candidate** creation / bind from **Lead** process.
2. **Extract** a small **continuity suppression helper** (pure or thin I/O): input = lead + conversion context → output = `suppress_first_contact: bool` + optional reason codes for the marker.
3. **Inputs to evaluate** (any hit → suppress default first-contact):
   - successful **contact attempt** on lead;
   - **`intake_resolution_v1`** with a recorded non-greenfield outcome;
   - existing **note** / **call** (or equivalent touch) on lead;
   - **explicit qualify** (and related confirm semantics) where product says first outreach is already satisfied.
4. **On suppression:** do **not** create the default first-contact task; **do** write the **continuity marker** (observable / auditable — not silent omission).
5. **Acceptance tests** (minimal set for this PR):
   - **call done** on lead → **no** duplicate first-contact on candidate;
   - **no contact** greenfield path → default task **still created** (baseline);
   - **duplicate attach** to existing candidate → **no** fake first-contact;
   - **request_info** (or other non-greenfield intake) → suppression + **continuity preserved** (marker + no wrong “cold first call” default).

### 8.5 Guard 2 — context carry (note + intake snapshot) — **Done (2026-07-02)**

**Goal:** After Lead → Candidate conversion, recruiter sees **carried** lead context (note, intake decision), not an empty narrative.

**Implementation:**

- `backend/app/services/lead_context_carry.py` — `carry_lead_context_on_conversion`, `build_lead_continuity_snapshot`
- Hook in `create_candidate_full(..., source_lead=...)` before UOS auto-activity
- Candidate `extra.lead_continuity_v1` + `extra.source_lead_id`; lead note copied to `candidate.note` when empty
- ActivityLog action `lead_to_candidate.context_carried`
- FE: `CandidateLeadOriginPanel` on candidate card
- Tests: `backend/tests/modules/leads/test_lead_context_carry_guard.py`

**Done when:** scenario 7 (§7) — lead note visible on candidate + link to source lead. ✅

---

## References

- **Recruitment Application lifecycle (intent / enum / idempotency):** `docs/specs/workflows/recruitment-application-lifecycle.md`
- **Application lifecycle reconciliation / conflicts (C1–C4, C2b, I1):** `docs/specs/workflows/recruitment-application-lifecycle-sync-note.md`
- Slice 3 (read-only qualification context): `docs/specs/workflows/slice-3-qualification-summary-data-audit.md`
- Intake / routing: `docs/specs/workflows/lead-intake-resolution-and-activity-continuity.md`
- **Guard 1 code:** `backend/app/services/lead_first_contact_continuity.py`, gate in `backend/app/services/uos_auto_activities.py` (`ensure_candidate_created_call_task`, optional `source_lead`). Lead conversion passes `source_lead` via `create_candidate_full(..., source_lead=lead)` from `lead_candidate_conversion.py`, `service/_processing.py`, `service/_reroute.py`.
- **Guard 2 code:** `backend/app/services/lead_context_carry.py`, hook in `create_candidate_full`; FE `CandidateLeadOriginPanel.tsx`
- **Tests:** `backend/tests/modules/leads/test_first_contact_continuity_guard.py`, `backend/tests/modules/leads/test_lead_context_carry_guard.py`
