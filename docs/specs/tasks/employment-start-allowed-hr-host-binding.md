# Employment start_allowed — HR host binding (slice 3)

**Status:** **OPEN** — HR host binding only; not ESO-5 enforcement; not Full Spine  
**Phase class:** product  
**Opened:** 2026-09-13  
**Depends on:**  
- Slice 1 PASS: [`employment-start-allowed-runtime-foundation.md`](employment-start-allowed-runtime-foundation.md) @ `d5767488`  
- Slice 2 portable PASS + Formalize→ensure integration parity PASS: [`employment-start-allowed-mint-cutover.md`](employment-start-allowed-mint-cutover.md) (under test `322d0148`; parity gate **6 passed**)  
- Architecture: [`../architecture/employment-start-allowed.md`](../architecture/employment-start-allowed.md) (**Accepted**)  
- Adaptation design: [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted**)  
**Named gate (this slice):** `employment-start-allowed-hr-host-gate` (or equivalent single named gate — no duplicate SoT)  
**Does not amend:** L0 · evidence authorities (Contract/Medical/BHP) · Formalize thin table · Full Spine Gate · slice 4 scope  

> **Slice 3 of 4.** Bind `employment_start_allowed.v1` onto the **existing** HR handoff host `/app/hr/handoffs/:id`.  
> Operator clears one active missing via existing evidence supply/bind or allowlisted exception → automatic re-evaluate → `start_allowed=true`.  
> **Do not** enforce on ESO-5 Confirm. **Do not** delete mint-on-confirm. **Do not** open Full Spine.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Machine `start_allowed` exists and Employee can exist before Confirm, but the HR operator has no host-bound surface to see the one active missing item, supply/bind evidence or an allowlisted exception, and get an automatic re-evaluate to `start_allowed=true` on the existing handoff case.

**Proven chain already in place (prerequisite — not this slice’s work):**

```text
ESO-4 authoritative apply
  → ready_to_create_employee
  → ensure_employee_after_formalize_apply
  → canonical linked Employee
  → employment_start_allowed.v1 can evaluate on the correct employee_id
```

Read/evaluate Formalize remains without write-side effects; handoff linkage proven (integration parity gate **6 passed**).

**Completion proof (named consumer — this slice):**

```text
Employee exists (linked to this handoff)
  → evaluate start_allowed on /app/hr/handoffs/:id
  → one active missing
  → supply/bind evidence OR allowlisted exception
  → automatic re-evaluate
  → start_allowed=true
```

Machine + host proofs (named gate green) must show the bullets in § Proofs. **No** ESO-5 Confirm change required for this slice PASS.

**False close (reject):** new HR workflow/host; changing Contract/Medical/BHP evidence authorities; operator-set `start_allowed` PATCH as authority; ESO-5 requires `start_allowed`; deleting mint-on-confirm; physical start / Started; Full Spine claim; expanding Formalize.

---

## In scope

1. Bind `employment_start_allowed.v1` evaluate (and narrow apply for allowlisted exceptions / existing evidence bind) on **existing** `/app/hr/handoffs/:id`.  
2. Surface **one** active missing item (primary), not a universal checklist.  
3. Operator path: supply/bind evidence through **existing** Documents/evidence authorities **or** create/revoke an **allowlisted** typed exception → automatic re-evaluate.  
4. Show derived `start_allowed` / `missing` / `blocked` / `unsupported_context` honestly (no invent-via-UI).  
5. Named machine/host gate proofs for this binding.  

## Out of scope (hard)

| Item | Belongs to |
|------|------------|
| Changing Contract / Medical / BHP evidence authorities | **Forbidden** (Documents / existing SoT) |
| New HR workflow or new host route | **Forbidden** |
| ESO-5 Confirm requires `start_allowed=true` | **Slice 4** |
| Remove / forbid PEM-1 mint-on-confirm | **Slice 4** |
| Physical start / Started confirm | **ESO-5 / Slice 4** |
| Full Spine Gate | Later |
| Expanding ESO-4 Formalize thin table | **Forbidden** |
| New mint / Employee create path | **Forbidden** (ESA2 already owns mint timing) |

---

## Execution locks

1. **Host = existing handoff case only:** `/app/hr/handoffs/:id` (`HrHandoffDetailPage` / current HR handoff composition). No parallel admit-to-work workflow.  
2. **Authority = Employee:** evaluate against the Employee **linked** to this handoff (ESA2 linkage), not an arbitrary candidate Employee.  
3. **Derived state only:** UI must not PATCH `employee.start_allowed` / `force_start_allowed` / “Allow anyway”.  
4. **One active missing:** primary item from evaluator; no checklist dump.  
5. **Evidence:** read/bind existing Contract/Medical/BHP authorities only — no new evidence store; no parallel upload authority invented in Employment.  
6. **Exceptions:** allowlisted typed exceptions only (foundation / architecture); no invent-via-UI.  
7. **Do not** implement slice 4 in the same PR.  
8. **Do not** open Full Spine.  
9. **Do not** change Formalize mint semantics or ESO-5 Confirm semantics.

---

## Proofs (gate must show)

- [ ] On linked Employee for handoff, evaluate returns reproducible `start_allowed` / `missing` / `blocked` / `unsupported_context` on the host  
- [ ] When missing: UI/API exposes **one** primary active missing (not a universal list)  
- [ ] Supply/bind existing evidence → automatic re-evaluate can reach `start_allowed=true`  
- [ ] Allowlisted exception path → automatic re-evaluate can reach `start_allowed=true` (where policy allows)  
- [ ] No invent-via-UI / no operator-set `start_allowed` authority  
- [ ] No new HR host/workflow routes  
- [ ] No evidence-authority schema/ownership change in diff  
- [ ] ESO-5 Confirm still does **not** require `start_allowed`  
- [ ] Mint-on-confirm not deleted  
- [ ] Full Spine not claimed  

---

## Implementation sequence (slice 3)

```text
handoff host: resolve linked employee_id
  → evaluate employment_start_allowed.v1
  → bind primary missing + exception affordances on existing case
  → evidence bind / allowlisted exception → apply → re-eval
  → named hr-host gate proofs
  → PASS stamp
  → STOP (do not open slice 4 in the same change)
```

---

## Non-goals

- ESO-5 Confirm gating  
- Deleting legacy mint-on-confirm  
- Physical start / Started UI rewrite  
- New Documents types or parallel evidence tables  
- ZUS / A1 / delegation as Start blockers  
- Full Spine  

---

## Next after slice 3 PASS

**STOP.** Then open **slice 4** (ESO-5 enforcement + remove PEM-1 mint-on-confirm) as a separate brief/PR. Full Spine stays closed until slices prove PEM-1 admit-to-work end-to-end.
