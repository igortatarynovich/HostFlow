# RSO-2C — Employment auto-init after Transfer

**Status:** **OPEN** — implementation landed; machine gate green; PASS-stamp pending  
**Phase class:** product  
**Opened:** 2026-09-13  
**Parent:** [`recruitment-employment-handoff-rso2-cutover.md`](recruitment-employment-handoff-rso2-cutover.md)  
**Depends on:**  
- RSO-1 PASS: [`../architecture/ready-for-employment-contract.md`](../architecture/ready-for-employment-contract.md)  
- Boundary ownership **Accepted:** [`../architecture/recruitment-employment-boundary-ownership.md`](../architecture/recruitment-employment-boundary-ownership.md)  
- ESO-1 Accepted: [`../architecture/employment-accept-policy.md`](../architecture/employment-accept-policy.md)  
- **RSO-2A CLOSED** + **RSO-2B PASS** ([`recruitment-employment-handoff-rso2b-emit.md`](recruitment-employment-handoff-rso2b-emit.md) @ `ab864e86`)  
**Named gate (this slice):** `rso2-auto-init-gate`  
**Does not open:** RSO-2D · RSO-2E · Slice 4 · Full Spine · new ACL product · Formalize  

> **Init only.** After Transfer emits a validated `ready_for_employment.v1` and leaves a pending `CandidateHandoff`, Employment-owned `apply_employment_accept_policy` decides and, on `auto_accept`, runs the Employment initializer (`accept_handoff` side effects).  
> Drop ritual Accept **button** as the default happy path.  
> Do **not** inline Accept inside `create_handoff`. Do **not** cut over HR live read-model (2D) or delete the compat shim (2E).

---

## Original Goal → Completion Proof

**Problem this slice must permanently remove:**  
After Transfer, HR still services the boundary with ritual **Take into HR review** (`POST …/accept`) even when `employment_accept_policy.v1` would `auto_accept`. Employment init exists but is not the default post-Transfer path.

**Completion proof (named consumer):**

```text
create_handoff (internal_hr)  → pending + RFE manifest (RSO-2B; unchanged)
  → Employment-owned apply_employment_accept_policy (post-Transfer; not inside create_handoff)
  → on auto_accept: accept_handoff side effects + employment_started audit
  → HR host opens accepted/in-review surface (no Take into HR review chore)
  → on review_required: concrete blockers (not blank Accept ritual)
  → named gate green
```

**False close (reject):** Accept/mint inlined in Recruitment `create_handoff`; ritual Accept remains default when policy says auto; claiming 2D live cutover or 2E shim delete; Slice 4 / Full Spine; new ACL.

---

## Scope (in)

1. **Post-Transfer Employment step** for `destination=internal_hr`: after successful Transfer emit/persist, call Employment-owned `apply_employment_accept_policy` (idempotent initializer path).  
2. **Ownership split:** `create_handoff` remains emit + pending transport only — **never** imports/calls `accept_handoff` / `apply_employment_accept_policy`.  
3. **Keep Employment initializer:** all accept side effects stay on `accept_handoff` / `hr_acceptance_orchestrator` (delayed-workforce preserved as Employment policy).  
4. **Drop ritual Accept as default UX** when policy auto-accepts (detail pickup CTA + inbox pickup CTA for that path).  
5. When decision ≠ `auto_accept`, surface **concrete blockers** (existing policy payload); do not invent a new Accept chore.  
6. Named machine gate `rso2-auto-init-gate` proving the split + auto path.  
7. Regression: RSO-2B emit locks still hold; shim untouched as SoT.

---

## Scope (out)

| Out | Owner later |
|-----|-------------|
| HR host live Person/Documents read-model cutover | **RSO-2D** |
| Delete `handoff_manifest_compat` | **RSO-2E** |
| Slice 4 / Full Spine / new ACL | **Closed** |
| Client-portal Accept ritual | **Out** (not internal_hr boundary) |
| Inline Accept inside `create_handoff` | **Forbidden** |
| New architecture L1 / dual-write / permanent shim | **Forbidden** |

---

## Execution locks

1. **Transfer emit ≠ Accept execute** — lock 8 of parent cutover.  
2. **Employment owns** `apply_employment_accept_policy` and initializer side effects.  
3. **Composition may sit after Transfer** (API/composition layer), but **must not** live inside Recruitment `create_handoff` service body.  
4. **Ritual `POST /handoffs/{id}/accept` may remain** as a non-default escape / legacy trigger into the same initializer — not the happy path when `auto_accept`.  
5. **Preserve delayed-workforce** behavior (`delayed_hr_workforce_creation`) as Employment init, not Transfer.  
6. **No RSO-2D/2E** work in this PR.  
7. **STOP after PASS** — do not auto-open 2D.

---

## Composition (locked target)

```text
Recruitment create_handoff(internal_hr)
  → emit+validate RFE → persist snapshot → pending CandidateHandoff
  → return (no Accept)

Employment apply_employment_accept_policy (post-Transfer step)
  → resolve package from snapshot (RSO-2B)
  → evaluate employment_accept_policy.v1
  → auto_accept → accept_handoff (+ employment_started)
  → else → blockers / review_required (no blank ritual)
```

Actor for auto-init: Transfer actor is acceptable as `reviewed_by` / policy actor when Employment applies immediately after Transfer; assignment rules of `accept_handoff` unchanged.

---

## PASS criteria (machine)

- [x] Post-Transfer Employment path calls `apply_employment_accept_policy` for `internal_hr` after successful create  
- [x] `create_handoff` source does **not** call `accept_handoff` / `apply_employment_accept_policy`  
- [x] On `auto_accept`: handoff reaches `accepted`; Employment initializer side effects run; `employment_started` audit present on policy path  
- [x] Ritual Accept button is **not** the default happy path when policy auto-accepts (detail + inbox pickup CTAs)  
- [x] On non-auto: blockers returned; no silent Accept  
- [x] Delayed-workforce flag behavior unchanged (Employment-owned)  
- [x] RSO-2D / RSO-2E / Slice 4 / Full Spine untouched  
- [x] Named gate `rso2-auto-init-gate` green (**7 passed**)  

---

## After machine PASS

1. **PASS stamped** on this brief.  
2. **STOP.** Do not open RSO-2D in the same change.  
3. Next separate: RSO-2D → RSO-2E delete shim.

---

## Implementation map

| Concern | Location |
|---------|----------|
| Employment apply (existing) | `backend/app/services/employment_accept_orchestrator.py` |
| Post-Transfer helper | `apply_employment_accept_after_transfer` (same module) |
| Employment initializer (existing) | `backend/app/services/handoff.py` → `accept_handoff` + `hr_acceptance_orchestrator` |
| Post-Transfer composition | `backend/app/api/v1/handoffs.py` → `create_handoff_route` after successful `internal_hr` create |
| Drop ritual CTA default | `HrHandoffDetailPage.tsx`, `HrInboxPage.tsx` |
| Policy API (existing) | `POST /handoffs/{id}/employment-accept-policy` |
| Named gate | `backend/tests/platform/test_rso2_auto_init_gate.py` |
| CI wire | `.github/workflows/backend-ci.yml` → `rso2-auto-init-gate` |
