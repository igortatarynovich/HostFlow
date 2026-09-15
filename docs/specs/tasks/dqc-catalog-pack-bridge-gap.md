# Gap-fix: DQC catalog ↔ recruitment pack

**Status:** **PASS**  
**Layer:** L3 proof / gap-fix — **not** a design rewrite · **not** Full Spine reopen  
**Phase class:** product  
**Opened:** 2026-09-15  
**Accepted:** 2026-09-15 — canon table locked (policy DQC ≡ Hub `code95`; second Hub type **forbidden**)  
**PASS stamp:** 2026-09-15 · named gate `dqc-catalog-pack-bridge-gate` · inbound `normalize_doc_type("driver_qualification_card")` → `code95` · delivery/Ready treats approved Hub `code95` as satisfying pack `driver_qualification_card`  
**Parent STOP:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) (**STOP** — Ready blocked; walk not resumed here)  
**Witness candidate (STOP):** `2f3c04fe-1312-444c-975a-4890007ff509`  
**Does not open:** Full Spine re-walk (separate next) · Hiring E2E · Formalize / start_allowed / ESO-5 · fixing `driver_license_with_code95` pending_verification

> **Narrow gap only.**  
> Canon: pack/R5 `driver_qualification_card` ≡ Hub storage `code95`.  
> **Do not** invent a second Hub type for the same physical Code 95 card.  
> Machine proof PASSed; **new** Full Spine walk is the next product step (new person).

---

## Original Goal → Completion Proof

**Problem this gap must permanently remove:**  
Recruitment Ready requires `driver_qualification_card`, but the ordinary Documents create path cannot store/recognize that requirement under one physical document — so a candidate cannot become Ready through normal UI/API.

**Completion proof (named consumer):**

```text
Operator Documents path creates/stores Code 95 evidence
  → transfer-readiness / Ready evaluator treats pack requirement
       driver_qualification_card as satisfied
  → no additional_document fallback for that requirement
  → machine gate green
  → only then: new person + new Full Spine walk from scratch
```

---

## STOP symptom (facts)

| Authority | Behavior on walk |
|-----------|------------------|
| Document pack / R5 | Requires `driver_qualification_card` (`recruitment.driver_ce_documents` / `r5_document_required`) |
| Documents Hub create | Input `driver_qualification_card` → catalog normalize → **`additional_document`** / `other` |
| Ready evaluator | `additional_document` ≠ fulfillment of `driver_qualification_card` |
| Same walk | Approved Hub row **`code95`** was present; transfer-readiness **still** reported DQC missing |

---

## Inventory — what already exists (do not duplicate)

### A. Platform / pack / R5 name = `driver_qualification_card`

| Surface | Evidence |
|---------|----------|
| Registry | [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json) code `driver_qualification_card` (“Driver qualification card (Code 95)”) |
| Legacy alias map | [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json): `code95` / `code_95` / `qualification_card` / `qualification_code95` → **`driver_qualification_card`** |
| Pack grouping | [`pack_definitions.py`](../../../backend/app/modules/documents/pack_definitions.py) `driver_pack.document_codes` includes `driver_qualification_card` |
| FE aliases | `hostflow-frontend/src/data/documentTypeAliases.ts` — same mapping |
| ADR language | ADR-018 lists `driver_qualification_card` among requirement document codes |

### B. Hub Documents storage type = `code95` (same physical card)

| Surface | Evidence |
|---------|----------|
| Module catalog definition | [`definitions.py`](../../../backend/app/document_types/definitions.py): **`code="code95"`**, name “Qualification card (Code 95)”, **`canonical_ref_code="driver_qualification_card"`**, aliases include inbound `driver_qualification_card` |
| Runtime Hub defaults | `DOCUMENT_TYPE_DEFAULTS` has **`code95`**, does **not** have `driver_qualification_card` as a primary Hub type |
| Owner-summary intent | [`owner_summary.py`](../../../backend/app/modules/documents/owner_summary.py): R5 uses `driver_qualification_card`; Hub persists `code95` |
| Pack projection test | `test_owner_summary_legacy_code95_satisfies_qualification_card` |

### C. What this is **not**

- Not “pack invented a fantasy name with no registry entry.”  
- Not “Documents has zero Code 95 type.”  
- Not a reason to mint a **second Hub type** named `driver_qualification_card` beside `code95`.

---

## Canon decision (**Accepted** 2026-09-15)

| Layer | Canonical identity |
|-------|-------------------|
| **Policy / pack / R5 / registry** | `driver_qualification_card` |
| **Hub Documents storage** | `code95` (existing) |
| **Physical document** | One: EU Code 95 / driver qualification card |
| **Link** | `driver_qualification_card` ≡ `code95` |
| **Rejected** | Adding Hub type `driver_qualification_card` as a parallel storage code |

### Decision checklist

- [x] Accept: one document, two codes (ref `driver_qualification_card` ≡ Hub `code95`)  
- [x] Reject: second Hub catalog type `driver_qualification_card`  
- [x] Reject: renaming pack away from registry canonical without Architecture/registry errata  
- [x] Scope stays DQC only — do **not** fold in `driver_license_with_code95` pending_verification  

---

## Implementation (PASS)

| Concern | Change |
|---------|--------|
| Inbound | `code95` aliases include `driver_qualification_card` → `normalize_doc_type("driver_qualification_card")` → **`code95`** (not `additional_document`) |
| Ready / delivery | `resolve_required_type_runtime_via_contract` resolves pack codes via Hub storage aliases (`legacy_codes_for_ref_canonical`) |
| Machine gate | `backend/tests/platform/test_dqc_catalog_pack_bridge_gate.py` · CI job `dqc-catalog-pack-bridge-gate` |

**False close avoided:** no second Hub type; pack still requires registry DQC; Full Spine not claimed; license pending not fixed here.

---

## Machine proof

**Gate id:** `dqc-catalog-pack-bridge-gate` — **PASS**

1. [x] `normalize_doc_type("driver_qualification_card")` → `code95` (never `additional_document`)  
2. [x] Approved Hub `code95` → delivery / hub bridge does **not** list `driver_qualification_card` missing  
3. [x] No Hub primary type `driver_qualification_card`  

---

## Explicitly out of this gap

| Out | Disposition |
|-----|-------------|
| `driver_license_with_code95` still `pending_verification` on STOP candidate | **Later** — only if next Full Spine walk stops there |
| Non-driver PEM-1 profile / new vacancy catalog | Not this hole |
| Full Spine composition walk | **Next** — new person from scratch |
| ZUS / start_allowed / Formalize | Untouched |

---

## Next

1. ~~Accept canon.~~ **Done.**  
2. ~~Narrow bridge + machine gate.~~ **PASS.**  
3. **New** Three-host Full Spine walk on a **new** person — do not resume STOP journal as PASS.
