# Employment start_allowed — runtime foundation (slice 1)

**Status:** **OPEN** — machine foundation only; not HR UI; not Full Spine  
**Phase class:** product  
**Opened:** 2026-09-13  
**Depends on:**  
- [`../architecture/employment-start-allowed.md`](../architecture/employment-start-allowed.md) (**Accepted**)  
- [`../../analysis/employment-start-allowed-adaptation-design.md`](../../analysis/employment-start-allowed-adaptation-design.md) (**Accepted**)  
- Inventory [`../../analysis/employment-start-allowed-runtime-inventory.md`](../../analysis/employment-start-allowed-runtime-inventory.md) @ `466016b6`  
**Named gate:** `employment-start-allowed-gate`  
**Does not amend:** L0 · ESO-4/5 PASS stamps · Full Spine Gate  

> **Slice 1 of 4.** Build the machine that derives `start_allowed` — no operator-set flag, no parallel evidence store, no mint cutover, no ESO-5 enforcement, no Full Spine.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Admit-to-work has no reproducible machine authority: evidence exists in Hub but no PEM-1 predicates, no typed exceptions, no gate that ESO-5 can later require.

**Completion proof (named consumer):**  
`employment_start_allowed.v1` reference + evaluate/apply (or equivalent) + `employment-start-allowed-gate` green against adaptation-design predicates (Contract normalized view, Medical vs `planned_start_date`, BHP + succession-proven exception). **No** HR host binding required for this slice PASS.

**False close (reject):** UI-only panel; `employee.start_allowed` PATCH; document-exists = satisfied; validity vs “today”; trusting `successive=true` alone; mint or ESO-5 cutover claimed as this slice.

---

## In scope

1. **Normalized evidence views** (read adapters) for Contract / Medical / BHP — Documents/HR remain write authorities.  
2. **Predicates** per Accepted adaptation design.  
3. **Typed exception authority** (narrow store + allowlist + succession proof for BHP).  
4. **Reference evaluator** `employment_start_allowed.v1` (LLM-OFF; derived decision).  
5. **Named CI gate** `employment-start-allowed-gate` (proofs from architecture Accept).  
6. Optional decision **snapshot** for audit — not source of truth.

## Out of scope (later slices)

| Slice | Deferred |
|-------|----------|
| **2** | ESO-4 → `handoff_from_candidate` mint timing cutover |
| **3** | HR host binding on `/app/hr/handoffs/:id` |
| **4** | ESO-5 requires `start_allowed`; remove PEM-1 mint-on-confirm |
| — | Full Spine Gate; ZUS/A1/delegation; expanding ESO-4 Formalize |

---

## Hard locks (inherit)

- Evaluator reads views; does not own Contract/Medical/BHP data.  
- `start_allowed` is **derived**, never operator-set authority.  
- `planned_start_date` required for date-bounded medical/BHP validity; unknown → `missing`.  
- Contract: `written_instrument_confirmed` from Documents view only.  
- No “Allow anyway”.  
- Non-PEM-1 → `unsupported_context`.

---

## Deliverables checklist

- [ ] Contract / Medical / BHP normalized read views (minimal fields)  
- [ ] Exception store + write/read for allowlisted codes only  
- [ ] `evaluate` / `apply` (apply = exception/evidence bind then re-eval; no force flag)  
- [ ] `employment-start-allowed-gate` green  
- [ ] Docs linkage: architecture + adaptation design + this brief  

---

## Non-goals

- Frontend Formalize/Started panels for start_allowed  
- Employee mint service or mint timing change  
- Full Spine  
- Płatnik / ePUAP / government API  

---

## Next after slice 1 PASS

Open **slice 2** (mint timing cutover) only when gate is green and foundation is on the Employment line. Full Spine stays closed.
