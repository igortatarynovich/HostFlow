# Employment start_allowed — runtime foundation (slice 1)

**Status:** **PASS** — machine foundation (slice 1) @ `d5767488`  
**Phase class:** product  
**Opened:** 2026-09-13  
**PASS stamp:** local gate `employment-start-allowed-gate` **17 passed** (derived-state replay included); no mint / UI / ESO-5 changes  
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
`employment_start_allowed.v1` reference + evaluate/apply + `employment-start-allowed-gate` green against adaptation-design predicates. Machine reproducibly returns `start_allowed` / `missing` / `blocked` / `unsupported_context`. **No** HR host binding, mint change, or ESO-5 semantic change required for this slice PASS.

**False close (reject):** UI-only panel; `employee.start_allowed` PATCH; document-exists = satisfied; validity vs “today”; trusting `successive=true` alone; mint or ESO-5 cutover claimed as this slice; new Contract/Medical/BHP persistence tables.

---

## Execution locks (slice 1)

### 1. Normalized views = read-only adapters

- Contract / Medical / BHP views are **DTO / projection / service reads** over existing data.  
- **Forbidden:** new Employment evidence persistence models for those domains.  
- If medical/BHP need new meta fields → **Documents schema** errata on existing types — not a new Employment evidence table.  
- Slice 1 may project optional meta when present; absence → `missing`, not invent a write path.

### 2. `apply` write scope (narrow)

`apply` may **only**:

- create / revoke a **typed exception** resolution (allowlisted);  
- attach an **already existing** evidence reference to an exception **if** that bind mechanic already exists in-product.

`apply` must **not**:

- become a universal write command;  
- invent Contract / Medical / BHP upload or meta-write paths;  
- set `start_allowed` as stored authority.

If evidence is missing: evaluator returns `missing`; UI/write adaptation = **slice 3** or Documents-owned errata — **not** slice 1.

### 3. Gate must prove derived-state replay

In addition to architecture gate proofs, CI must include:

1. Evidence satisfies → decision `start_allowed`.  
2. Authority evidence changes / becomes invalid → next `evaluate` no longer returns `start_allowed`.  
3. A prior **snapshot** must **not** keep permission after evidence invalidation.

```text
snapshot = audit
evaluator = authority
```

### 4. Do not touch mint

**Forbidden in slice 1:** any change to `handoff_from_candidate` / Employee create timing — even if convenient. That is **slice 2**.

### 5. No frontend / no ESO-5 semantics

No HR UI. No ESO-5 confirm gating. No Formalize thin-table expansion.

---

## Implementation sequence (slice 1)

```text
normalized read views
  → typed exception store / allowlist
  → pure reference evaluator
  → apply resolution semantics (exceptions only)
  → employment-start-allowed-gate
  → regression proofs (incl. derived-state replay)
  → PASS stamp
```

---

## In scope

1. Read-only normalized evidence views (Contract / Medical / BHP).  
2. Predicates per Accepted adaptation design.  
3. Typed exception authority (narrow store + allowlist + succession proof).  
4. Reference evaluator `employment_start_allowed.v1` (LLM-OFF; **derived** decision).  
5. `apply` limited to exception create/revoke (+ existing-ref bind only if already available).  
6. Named CI gate `employment-start-allowed-gate` including derived-state replay.  
7. Optional decision snapshot for audit — not source of truth.

## Out of scope

| Slice | Deferred |
|-------|----------|
| **2** | ESO-4 → `handoff_from_candidate` mint timing cutover (**do not touch mint here**) |
| **3** | HR host binding / evidence write UX |
| **4** | ESO-5 requires `start_allowed`; remove PEM-1 mint-on-confirm |
| — | Full Spine; ZUS/A1/delegation; expanding ESO-4 Formalize |

---

## Hard locks (inherit)

- Evaluator reads views; does not own Contract/Medical/BHP data.  
- `start_allowed` is **derived**, never operator-set authority.  
- `planned_start_date` required for date-bounded medical/BHP validity; unknown → `missing`.  
- Contract: `written_instrument_confirmed` from Documents-normalized view only.  
- No “Allow anyway”.  
- Non-PEM-1 → `unsupported_context`.

---

## Deliverables checklist

- [x] Contract / Medical / BHP normalized **read** views (no new evidence tables)  
- [x] Exception store + allowlist + succession proof  
- [x] `evaluate` / narrow `apply`  
- [x] `employment-start-allowed-gate` green (incl. derived-state replay)  
- [x] Docs linkage + CI job + PASS stamp  
- [x] Proof: slice-1 modules do not import/call `handoff_from_candidate`  

---

## PASS criterion

Machine authority reproducibly answers `start_allowed` / `missing` / `blocked` / `unsupported_context`; gate green; **Employee mint, HR UI, and ESO-5 semantics unchanged**.

**PASS (slice 1 machine):** reference `employment_start_allowed.v1` + evidence projections + typed exception model/service + named CI gate (17 proofs).

---

## Next after slice 1 PASS

Open **slice 2** (mint timing cutover) only when this PASS is committed. Full Spine stays closed.
