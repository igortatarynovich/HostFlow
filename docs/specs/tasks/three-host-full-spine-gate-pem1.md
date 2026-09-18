# Three-host Full Spine Gate (kernel) — PEM-1 walks reclassified

**Status:** **HISTORICAL** (2026-09-18) — Walks 1–4 retained as evidence of kernel/policy conflation only. **Not** an open Full Spine gate. Kernel existence proved by [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md) **PASS**; first production composition by [`pem1-policy-composition.md`](pem1-policy-composition.md) **PASS**. Do **not** reopen this brief to “finish” Walks 1–4.  
**Layer:** L3 proof context — **not** L2 design/feature specification · **not** a release gate  
**Phase class:** product  
**Opened:** 2026-09-15  
**Closed as open gate:** 2026-09-18 (superseded by independent Kernel + PEM-1 proofs)  
**Walk attempted:** walk 1–3 STOP · walk 4 continuous under **policy-laden** PEM-1 config (reclassified — historical)  
**Architecture parent:** [`ADR-042-spine-policy-separation.md`](../architecture/ADR-042-spine-policy-separation.md) (**Accepted** 2026-09-15) — path → process → module → policy  
**Critical split (proved separately):** **Kernel ≠ PEM-1** — Kernel = каркас under empty Ready+Admit; PEM-1 = production composition on that каркас  
**Walks 1–4:** historical evidence only — **not** Spine existence criteria and **not** an unclosed Full Spine obligation  
**Map / I/O:** [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md) (six-field process cards)  
**Parents:**  
- [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md) (Spine / Policy Separation)  
- [`employment-spine-orchestrator-v1.md`](employment-spine-orchestrator-v1.md)  
- [`recruitment-spine-orchestrator-v1.md`](recruitment-spine-orchestrator-v1.md)  
- Slice 4 PASS: [`employment-start-allowed-eso5-enforcement.md`](employment-start-allowed-eso5-enforcement.md) @ `b8c9dd04`  
- Boundary E2E PASS: [`recruitment-employment-handoff-boundary-e2e-proof.md`](recruitment-employment-handoff-boundary-e2e-proof.md)  
- Gap PASSes (policy/evidence — **not** kernel proof): [`dqc-catalog-pack-bridge-gap.md`](dqc-catalog-pack-bridge-gap.md) · [`document-required-hub-alias-gap.md`](document-required-hub-alias-gap.md) · [`start-allowed-contract-bhp-hub-identity-gap.md`](start-allowed-contract-bhp-hub-identity-gap.md)  
**Does not amend:** L0 · ESO/ESA/RSO named gate PASS stamps · Hiring E2E · Formalize thin table · Release Readiness Gate  


> **Proof brief only — now historical.** Full Spine каркас = [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md). PEM-1 = [`pem1-policy-composition.md`](pem1-policy-composition.md).  
> **No code** from this brief. Do **not** continue Contract/BHP/Code95 fixes as “open Full Spine.”  
> Prerequisites (boundary E2E, Start Allowed 1–4, Confirm↔`start_allowed`, Hub identity) are **inputs**, not substitutes for the independent Kernel / PEM-1 stamps.

---

## Full Spine ≠ PEM-1

| Proof | Must prove | Must not prove |
|-------|------------|----------------|
| **Full Spine (kernel)** | Continuous каркас Lead/Apply → Recruitment → Handoff → Employment → Start → Workforce under **штатная** minimal/neutral policy | Driver packs, Contract/Medical/BHP, Code95, citizenship |
| **PEM-1 (policy composition)** | For PL domestic EU/EEA, correct policies wire (Recruitment quals + admit Contract/Medical/BHP) | That the каркас only exists when those documents are known |

**Neutral ≠ bypass (ADR-042 §4a):** kernel `allowed` must come from the **real policy contract** configured with **no additional requirements** — same evaluate path and verdict shape. Reject: `if test`, tenant disable-policy flags, internal API skips, operator-set `start_allowed`, seed Started.

Walks 1–4 in this file are **PEM-1-laden** artifacts. Walk 4 Started ≠ Full Spine PASS.

---

## Original Goal → Completion Proof

**Problem this gate must permanently remove:**  
Named RSO/ESO/ESA and boundary proofs are green in pieces, but HostFlow still cannot claim a **policy-independent** continuous каркас across three hosts — so “Full Spine” was wrongly equated with PEM-1 document walks.

**Completion proof (named consumer) — kernel:**  
One continuous composition witness for **one** person through Lead → Recruitment → Handoff → Employment → Start → Workforce on the three hosts, under **minimal/neutral** policy, with invariants held — without stitching prior gate PASSes and without requiring PEM-1 document sets.

**Separate proof (not this stamp):** PEM-1 policy composition may reuse Walk 4 as a composition artifact after kernel exists.

---

## 1. Kernel witness (locked target — not yet run)

```text
Lead / Apply
  → Recruitment Ready (штатная Ready policy with zero extra requirements)
  → Transfer / RFE (ready_for_employment.v1)
  → Employment auto-init
  → Employee (Formalize→ensure; not Confirm-mint)
  → start_allowed via штатная admit policy (zero extra requirements → allowed on evaluate)
  → human Confirm physical start
  → Started
  → Workforce handoff identity recoverable
```

Same product hosts and policy engines as production. Empty/zero-requirement **ruleset** ≠ engine bypass.

**Historical PEM-1 walk (policy composition — not kernel):**

```text
… → Contract + Medical + BHP evidence / exception → start_allowed=true → Confirm → Started
```

ZUS / Insurance may appear **after** Started as lifecycle — not part of kernel or PEM-1 pre-Start path.

---

## 2. Three hosts (locked)

| # | Host | Role in walk |
|---|------|----------------|
| 1 | **Recruitment / Application** | Ready → Transfer / RFE emit |
| 2 | **Boundary / handoff** | Package + Employment auto-init (no ritual Accept happy path) |
| 3 | **HR Employment** | Employee → admit-to-work → Confirm → Started |

**Traceability:** the same `candidate` / `application` / `handoff` / `employee` identifiers must be recoverable across the whole walk. Fragmented persons or re-seeded dossiers are invalid.

---

## 3. Invariants (must hold on the witness)

| Invariant | Meaning |
|-----------|---------|
| Ownership | Recruitment does not employ; Employment does not re-own Recruitment qualification |
| No re-ask | Recruitment-known package facts are not required re-entry chores |
| Admit ≠ start | `start_allowed=true` does **not** auto-Started; human Confirm remains |
| Post-Start only | ZUS / Insurance are **not** pre-Start blockers for PEM-1 |
| PEM-1 out | A1 / delegacja / work-permit legalization **absent** from this walk |
| No bypass | Confirm impossible when `start_allowed != true`; no mint-on-confirm; no operator-set `start_allowed` |

---

## 4. False close (reject)

| Reject | Why |
|--------|-----|
| Sum of RSO / ESO / ESA named gate PASSes | Piecewise machine green ≠ composition |
| Boundary E2E witness alone | Stops before Employee → `start_allowed` → Started |
| Slice 1–4 / Confirm enforcement alone | Does not prove Recruitment → Transfer → HR continuity |
| CI-only / seeded shortcut walk | Not a product composition witness |
| Claiming Hiring E2E / RS-7 | Different program; remains closed |
| Any new feature work “to enable” Full Spine inside this brief | This brief **forbids** code |
| PEM-1 document walk as kernel PASS | Full Spine ≠ PEM-1 |
| `if test` / tenant disable-policy / internal API skip of evaluate | Neutral-as-bypass |
| Operator-set `start_allowed` / forged Ready / seed Started | Not process contract |

**Hard rule:** Full Spine PASS is **not** arithmetic and **not** a policy bypass. It requires **one** composition witness on real hosts through the real policy engine.

---

## Execution lock

| Rule | Lock |
|------|------|
| Code / migrations / UI / new APIs from this brief | **Forbidden** |
| New Formalize / evidence / ACL / Hiring E2E scope | **Forbidden** |
| Neutral implemented as policy bypass | **Forbidden** |
| Kernel walk succeeds with invariants + ADR-042 §4a | **PASS** — stamp kernel; record witness ids |
| Walk fails | **STOP** — classify defect (kernel / policy-rule / evidence-authority / integration); only then open a **separate** gap-fix brief |

Do **not** invent functionality from a STOP. The gap-fix is a later, explicit open.

---

## PASS / STOP outcomes

| Outcome | When |
|---------|------|
| **PASS (kernel)** | One continuous каркас witness across three hosts under штатная minimal policy (neutral ≠ bypass); invariants held; ids traced |
| **STOP** | Witness breaks — record hole + **defect class**; Full Spine remains **NOT PASS** |
| PEM-1 composition | Separate proof after kernel; not this stamp |

**Full Spine Gate (this brief) = HISTORICAL.** Walks 1–3 remain STOP witnesses (evidence/authority holes mistaken for route infrastructure). Walk 4 is retained as a **policy-laden composition artifact** only — **not** kernel PASS. Kernel каркас PASS = [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md). PEM-1 PASS = [`pem1-policy-composition.md`](pem1-policy-composition.md). See [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md).

---

## Architectural hold (2026-09-15)

Walks 1–3 showed the same failure mode: a **document / pack / Hub identity** condition stopped the walk as if the **life path** did not exist. Construction order was inverted (bottom-up from documents). Correct order per ADR-042:

```text
Life path → Processes → Modules → Boundaries/I/O → Policies/rules inside modules → Evidence
```

| Layer | Correct role |
|-------|----------------|
| Life path / каркас | Отклик → Отбор → Передача → Трудоустройство → Выход → Работа |
| Process / module | Recruitment · Handoff · Employment · Admit · Start · Workforce |
| Policy | May this action run **now**? (`allowed` / `blocked` / `missing` / … + `next_action`) |
| Evidence | Inputs to rules (Code95, Contract, Medical, BHP, …) — never create a new route |

**Do not** open further Contract/BHP/Code95 gap-fixes **as Full Spine topology**. Close six-field I/O: [`spine-policy-separation-inventory.md`](spine-policy-separation-inventory.md). Then baseline **kernel** proof → PEM-1 composition. Walks 1–4 retained as conflation evidence only.

---

## Walk journal 4 (2026-09-15) — RECLASSIFIED (not Full Spine PASS)

**Person:** new (not walk-1/2/3, not boundary witnesses).  
**Ops:** `docker compose restart backend` after identity gate PASS; verified `normalize_doc_type("employment_contract"|"bhp")` keep Hub codes.

| ID | Value |
|----|--------|
| `candidate_id` | `26722244-2e29-4e1d-903e-fa3b70cae1f9` |
| `handoff_id` | `becd1ceb-0b6c-4701-a422-3ba3b5c32036` |
| `employee_id` | `a2ba795f-82a4-4b37-9cd2-5a414706169b` |

| Checkpoint | Result |
|------------|--------|
| Ready | **PASS** — `transfer_allowed=true` (DQC←`code95` alias holds) |
| Transfer / RFE + auto-init | **PASS** — `status=accepted`; snapshot `contract_id=ready_for_employment.v1` |
| Formalize → Employee | **PASS** — `formalization_complete`; `employee_ensure_wrote=true` |
| Contract + Medical + BHP → `start_allowed` | **PASS** — Hub stored `employment_contract` + `bhp`; `start_allowed=true`; `started=false` until Confirm |
| Confirm → Started | **PASS** — `decision=started`, `started=true`, `mint_employee=false`, `start_event_emitted=true` |

**Invariants observed on this person (still useful):** Admit ≠ start (`start_allowed=true` with `started=false` before Confirm); no mint-on-confirm; continuous IDs; product Hub APIs only.

**Reclassification:** Continuous Started under PEM-1 document/policy load proves **policy composition can complete**, not that HostFlow has a **policy-independent lifecycle kernel**. Per ADR-042 this journal does **not** stamp Full Spine PASS.

---

## Walk journal 1 (2026-09-15) — STOP

**Person:** new (not boundary `e9ef16f2-…` / `c0832430-…`).

| ID | Value |
|----|--------|
| `candidate_id` | `2f3c04fe-1312-444c-975a-4890007ff509` |
| `application_id` | *not reached* (no Recruitment Application created before Ready) |
| `handoff_id` | *not reached* |
| `employee_id` | *not reached* |

| Checkpoint | Result |
|------------|--------|
| Ready | **STOP** — `transfer_allowed=false` |
| RFE emitted | not reached |
| auto-init | not reached |
| Employee exists | not reached |
| Contract/Medical/BHP satisfied | not reached |
| `start_allowed=true` | not reached |
| human Confirm | not reached |
| Started | not reached |

**Host / context at stop:** Recruitment / Application — vacancy `9088b484-dc44-4f75-9913-1e2999cb1ef2` (`Vacancy conversion idemp`, company Test Logistics) · entity profile `recruitment.candidate.driver_ce` · tenant only exposes candidate profile `driver_ce_default`.

**Product path used (no DB / no seed helpers):** create candidate → PATCH identity/dossier confirmations → activities + `first_contact_completed` → Hub `POST /db/candidate/.../documents` + presign + mock-upload (env S3 stand-in) → requirements `select-evidence` / link / approve. Backend restarted once so Slice 4 code was loaded (ops, not a product fix).

**Concrete hole (STOP):**

1. Transfer readiness requires document type **`driver_qualification_card`** (`document_pack` / `recruitment.driver_ce_documents` / `r5_document_required:driver_qualification_card`).
2. Documents catalog **does not** register that type: create remaps to `additional_document` / `other` (`custom_name` / `user_comment` required). Hub runtime lists the file as `additional_document`, **not** as `driver_qualification_card`.
3. Therefore the operator cannot satisfy the Ready gate for this default driver_ce vacancy through the normal Documents product path. Walk stops **before** Transfer/RFE — composition across three hosts cannot start.

**Secondary observation (not the STOP stamp):** at stop, checklist still had `driver_license_with_code95` in `pending_verification` after meta fix; sole `transfer-readiness` blocker reported was DQC. Boundary handoff person was **not** reused; that prior witness also shows an `additional_document` row and is not a Ready substitute for Full Spine.

**False-close avoided:** did not declare PASS from Slice 4 / boundary E2E; did not SQL-patch types; did not call `seed_documents_for_ready_for_handoff`.

---

## Walk journal 2 (2026-09-15) — STOP (post DQC catalog bridge)

**Person:** new (not walk-1 `2f3c04fe-…`, not boundary `e9ef16f2-…` / `c0832430-…`).  
**Ops:** `docker compose restart backend` before walk; verified `normalize_doc_type("driver_qualification_card")` → `code95`.

| ID | Value |
|----|--------|
| `candidate_id` | `f5841c06-f2ff-4b3c-a376-6a7c4834e6f3` |
| `application_id` | *not reached* (no Recruitment Application before Ready) |
| `handoff_id` | *not reached* |
| `employee_id` | *not reached* |

| Checkpoint | Result |
|------------|--------|
| Ready | **STOP** — `transfer_allowed=false` |
| RFE emitted … Started | not reached |

**Proven on this walk (not enough for Ready):**

- Inbound create `doc_type=driver_qualification_card` → Hub stored **`code95`** (catalog bridge works).  
- Checklist slots fulfilled (`all_fulfilled=true` on requirements workspace) including `driver_license_with_code95` **approved**.  
- Hub holds approved `code95` with files.

**Concrete hole (STOP) — distinct from walk-1 catalog miss:**

1. Transfer-readiness sole document blocker remains `document_missing: driver_qualification_card` (`source_layer=requirement_engine`).  
2. Root cause in product path: `evaluate_requirement_rules` **DOCUMENT_REQUIRED** resolves via `doc_index.get(doc_code)` on the **exact** pack code (`driver_qualification_card`) and does **not** expand Hub storage aliases (`code95`). Approved `code95` therefore still yields a missing-document blocker.  
3. Delivery-contract / hub-bridge alias resolve (DQC gap machine gate) is **not** the path that clears this transfer-readiness blocker.

**Not this STOP:** `driver_license_with_code95` was **approved** on walk 2 (not the halt).

**False-close avoided:** no seed/DB patch; no reuse of prior witnesses; no Full Spine PASS; no mid-walk code fix.

---

## Walk journal 3 (2026-09-15) — STOP (post DOCUMENT_REQUIRED Hub alias)

**Person:** new (not walk-1 `2f3c04fe-…`, not walk-2 `f5841c06-…`, not boundary `e9ef16f2-…` / `c0832430-…`).  
**Ops:** `docker compose restart backend` before walk; verified `hub_storage_keys_for_requirement_code("driver_qualification_card")` includes `code95`.

| ID | Value |
|----|--------|
| `candidate_id` | `86d19b53-123c-40d9-96e3-ff43641232f1` |
| `handoff_id` | `30fc19fa-78b8-4426-84f5-28329d9538a0` |
| `employee_id` | `22666d06-25de-46f1-bb73-8222eb81fc78` |
| `application_id` | *not separately minted* (handoff from candidate) |

| Checkpoint | Result |
|------------|--------|
| Ready | **PASS** — `transfer_allowed=true`; `missing_documents=[]` (approved Hub `code95` from inbound DQC satisfies DOCUMENT_REQUIRED) |
| Transfer / RFE + auto-init | **PASS** — handoff `status=accepted`, `accepted_at` set; snapshot path live |
| Formalize → Employee | **PASS** — `formalization_complete` / `ready_to_create_employee=true`; `employee_ensure_wrote=true` |
| Contract + Medical + BHP → `start_allowed` | **STOP** |
| Confirm → Started | not reached |

**Proven on this walk (not enough for Full Spine):**

- DOCUMENT_REQUIRED alias gap holds on product Ready path (no `document_missing: driver_qualification_card` with approved `code95`).  
- Continuous Ready → Transfer → Formalize → Employee for one person.

**Concrete hole (STOP) — distinct from walk-1/2 Ready holes:**

1. `employment-start-allowed` evaluate stays `decision=missing` with active_missing `written_employment_contract_or_confirmation` + `introductory_bhp_before_admit`.  
2. Product Hub create of `contract` / `employment_contract` / `bhp` / `szkolenia_bhp` **normalizes to `additional_document`** (types absent from Hub catalog defaults).  
3. `employment_start_allowed_orchestrator._doc_mapping` / `_pick_doc` read collapsed `doc_type=additional_document` and **do not** resolve `meta.type` when primary type is set — so signed-contract / introductory-BHP meta on those rows never satisfy start_allowed. Medical (`medical_certificate`) is found; Contract/BHP are not.  
4. No mid-walk code fix; no seed/DB shortcut; Confirm not attempted.

**False-close avoided:** Walk 3 remains a STOP witness; Ready alias success is not Full Spine PASS.

---

## Out of scope

- Hiring workflow E2E / RS-7  
- ZUS/Insurance product depth beyond “post-Start lifecycle exists as non-blocker”  
- PEM-N (third-country, posting, A1)  
- Expanding ESO-4 Formalize thin table  
- Release Readiness Gate / “готовы к запуску”

---

## Next

1. **Kernel PASS 2026-09-18** — [`baseline-full-spine-kernel-proof.md`](baseline-full-spine-kernel-proof.md).  
2. **Active PEM-1 composition proof** — [`pem1-policy-composition.md`](pem1-policy-composition.md) (**OPEN**). This file’s Walks 1–4 remain **historical evidence only** — do **not** continue them.  
3. Do **not** reopen Kernel “for confidence.” Classified STOP items only via the PEM-1 brief.  
4. Full Spine **kernel** claim is met by the baseline proof; PEM-1 is a separate composition stamp.
