# Acquisition UI Cutover C-7 — Подборы decommission + cutover PASS

**Status:** READY TO IMPLEMENT — **ACTIVE Product Track** (after C-6 Form Builder DONE)  
**Date:** 2026-07-26  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) (C-7 row + acceptance gate)  
**Parents:** ADR-024 · C-2 create-stop (#158) · [C-6 Forms](acquisition-ui-cutover-c6-form-builder.md) · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)  
**Next:** Cutover PASS → Source Diagnostics (first post-cutover Product Epic); Stage 5 PR-2 may resume  
**Blocks:** Stage 5 PR-2 remains paused until this gate PASS

> C-7 closes the **Stage 4 product/UI cutover**: retire Подборы as an advertising launch surface, finish reconciliation inventory, and prove the Marketing onboarding path end-to-end.  
> **Not** Source Diagnostics ops console. **Not** Stage 5 Optimization. **Not** deleting historical activity JSON before reconciliation is documented.

---

## 1. Why now

C-1…C-6 delivered Marketing IA, Sources, Test lead, Mapping, and Forms. Legacy Подборы launch UI still exists (create/duplicate already **410** from C-2). Leaving it visible keeps dual-path confusion and blocks Stage 5 PR-2.

```text
Connect → Source → Test Lead → Mapping → Form → Campaign → Flight → Lead
```

C-7 makes that path the **only** operator launch story.

---

## 2. Product job (one sentence)

An operator cannot start a **new ad launch** from Подборы; legacy acquisition URLs are redirect or strictly read-only; reconciliation inventory is documented; production Marketing nav smoke passes — **cutover PASS**.

---

## 3. Locked boundary

| Concern | C-2 | C-7 | OUT |
|---------|-----|-----|-----|
| New launch via `searchAcquisition` create/duplicate | ✅ stopped (410) | keep enforcement | — |
| Подборы list / nav as launch surface | still visible | retire / redirect / read-only | ❌ wipe activity history |
| Audience / bindings writes on legacy rows | still live (constraint) | gate or remove | ❌ silent data loss |
| Reconciliation inventory | snapshot `linked`/`unresolved` | counts documented | ❌ force-migrate all rows |
| Source Diagnostics | — | — | ❌ post–C-7 epic |
| Stage 5 PR-2 | paused | unpause only after PASS | ❌ sneak Optimization into C-7 |

---

## 4. Donor / reuse

| Need | Donor |
|------|--------|
| Create-stop / 410 | C-2 `LegacyLaunchDisabledError` + FE helpers / scan tests |
| Snapshot reconciliation | Campaign/Flight acquisition snapshot `reconciliation` |
| Marketing setup deep-link | `/app/marketing/new` prefill from vacancy when unambiguous |
| Nav / IA tables | [acquisition-ui-cutover.md](acquisition-ui-cutover.md) Sales / Recruitment / Marketing |

**Forbidden:** new Marketing host module; Stage 5 explainability; Diagnostics timeline epic.

---

## 5. UX sketch (minimum)

1. Подборы acquisition launch CTAs removed or redirected to Marketing setup.  
2. Legacy `/app/recruitment/searches/:id/acquisition/*` → read-only banner + link to Campaign when linked, else reconciliation note.  
3. Remaining writable legacy surfaces from C-2 constraint (audience PUT / bindings) gated or removed.  
4. Document migrated / unresolved counts.  
5. Production nav smoke of Marketing (Campaigns / Sources / Forms / Activity) + Recruitment without launch.

---

## 6. OUT

- Source Diagnostics epic (post–C-7 Product)  
- Stage 5 PR-2 implementation (only **unpause** after PASS)  
- Stage 6 Analytics  
- Hard-delete of legacy search acquisition rows without inventory  

---

## 7. Acceptance (cutover PASS)

- [ ] New ad launch cannot start from Подборы; legacy URLs redirect or read-only  
- [ ] C-2 leftover writable surfaces (audience/bindings) gated or retired  
- [ ] Reconciliation inventory: migrated / unresolved counts documented  
- [ ] Sales / Recruitment / Marketing IA match cutover tables  
- [ ] End-to-end path (Connect → … → First processed lead) executable without a developer  
- [ ] Deploy smoke of full production Marketing nav  
- [ ] Cutover docs: C-7 PASS; Stage 5 PR-2 may resume; Product Track → Source Diagnostics  
- [ ] Tests: launch-stop scans + redirect/nav scans; `make docs-lint`  

---

## 8. Implementation order (suggested PR split)

1. **Docs / brief** (this file) + queue linkage  
2. **UI retire / redirects** for Подборы launch surfaces  
3. **Legacy write gates** (audience/bindings) + reconciliation inventory note  
4. Close-out + production smoke → cutover PASS  

---

## 9. STOP conditions

- Deleting activity/JSON history without reconciliation inventory  
- Opening Stage 5 PR-2 before C-7 PASS  
- Absorbing Source Diagnostics into this slice  
- Re-enabling `searchAcquisition` create/duplicate  
