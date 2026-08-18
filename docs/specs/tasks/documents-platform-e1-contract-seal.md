# Documents Platform E1 — Foundation contract seal (Phase E)

**Status:** **COMPLETE** ([#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1`)  
**Next:** [Documents Platform E2 — Public contract & D2 slot enable](documents-platform-e2-public-contract.md) ([#271](https://github.com/igortatarynovich/HostFlow/pull/271); feat locked)  
**Branch (docs):** `docs/documents-platform-e1-contract-seal` ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)  
**Branch (code):** `feat/documents-platform-e1-contract-seal` ✅ [#270](https://github.com/igortatarynovich/HostFlow/pull/270)  
**Parents:** [Entity Workspace D9](entity-workspace-d9-services-order-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [Document Hub scope](../../document-hub/module-scope.md) · [Catalog Documents](../architecture/platform-capability-catalog.md#documents) · [A2-F8](../gates/platform-governance-review-a2.md)

> Phase D last named consumer closed via D9 ([#268](https://github.com/igortatarynovich/HostFlow/pull/268) · `28978a1f`).  
> Phase E starts here: seal what **Documents Platform** owns — before D2 `documents` enable, OCR, packages, or Hub UI rebuild.  
> E1 does **not** enable D2 `documents`, rewrite L0 Catalog, or open Billing / AI.

**Naming (do not collapse):** this **Documents Platform E1** is not Entity Workspace D9, not D2 slot enable, not Shell `documents` nav, not Candidate / HR dossier, not Recruitment document slots, not OCR / e-sign product, not document packages, not Billing Platform Phase F. Document Hub is a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

[A2-F8](../gates/platform-governance-review-a2.md): Documents Foundation is still consolidating. ADR-009 / Catalog passport already exist, but maturity cannot mark Foundation ✅ while Hub vs candidate-owned `documents`, public contract ids, and the D2 slot remain unsealed.

Shipped runtime vs canon:

| Artifact | Shipped | Drift |
|----------|---------|--------|
| Passport | Catalog [Documents](../architecture/platform-capability-catalog.md#documents) | Exists; Foundation not ✅ |
| Manifest | [`capability-settings-manifest.md`](../architecture/capability-settings-manifest.md#documents) | Illustrative keys only (OCR / e-sign / retention) |
| Public Contract | Catalog Exposes: Document Adapter / Verification Adapter / document set resolution (**Stable**) | No sealed `documents.public_contract.v1` id (unlike Forms C1) |
| Adapter | `document_hub_delivery_contract.py` | Candidate-centric façade over `modules.documents.crud` — not ADR-009 Document Link SoT |
| Runtime | `Document` + `candidate_id`, templates, dossier, expiry | Dual model: legacy candidate-owned row vs Hub links / requirement / review |
| D2 slot | `compositionSlots.ts` `documents` **reserved** | Opening Phase E ≠ enable; E1 **must keep reserved** |

Without an explicit E1 seal, the next PR will either treat Candidate/HR dossier as Documents Platform done, or flip D2 `documents` on because “Phase E started”.

---

## Goal

Seal Documents as a **platform capability** (ownership → Hub vs module file silo → adapter boundary → D2 slot still reserved) so later Phase E slices have one SoT. Align Product Track pointers. Do not invent a second document store.

This slice does **not** enable the Entity Workspace documents slot, accept OCR / e-sign as Product Track, or replace `candidate_id` with Document Link in one PR.

---

## Ownership card (required before domain promotion)

| Field | Value |
|-------|--------|
| **Domain name** | Documents Platform / Document Hub (Phase E) |
| **Owner** | Documents platform ([ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · Catalog [Documents](../architecture/platform-capability-catalog.md#documents)) |
| **Source of truth** | ADR-009 Document + Document Link + Requirement + Review. Module cards **display** via links. Legacy `documents.candidate_id` is **not** Hub SoT |
| **Consumers** | Recruitment, HR, Fleet, Finance, Services, Entity Workspace D2 `documents` slot (later E slice) |
| **Delivery contract** | Today: `document_hub_delivery_contract.py`. Sealed public-contract id = later E slice (not E1) |
| **Versioning** | No silent second registry; types/sets from Hub (Architecture Rule 1 — no new local dictionaries) |
| **Override policy** | Modules **must not** ship a parallel file table as document SoT; handoff **must not** copy blobs |
| **Enforcement** | Named E1 gate (feat); D1–D9 gates stay green; D2 `documents` remains un-enableable |

---

## Locked principle

```text
ADR-009 Document Hub (platform)
  → Document is a business object; file is a version
  → links + permissions, never copy between modules
PX / D1 chrome + D2 slot catalog
  → documents named as reserved until a later E slice unlocks
E1 (this)
  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2
  → public contract / D2 catalog enable ([documents-platform-e2-public-contract.md](documents-platform-e2-public-contract.md))
E3+
  → first consumer bind / Document Link SoT / lifecycle
```

E1 **must not**:

- enable D2 `documents` or treat Phase E open as that unlock  
- collapse Shell `EntityWorkspaceSectionId` `documents` into `compositionSlots.ts`  
- treat Candidate docs panel / HR dossier / Vacancy docs / Services billing as D2 enable  
- mint new Catalog Passport keys or rewrite L0 Catalog  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild as this slice  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- cut over `HrHandoffDetailPage` or re-bind D3–D9 consumers  
- invent a second document store or local type dictionary  
- copy files across Recruitment ↔ HR as the handoff path  
- mark Documents Foundation ✅ (stays 🔄 until a later E close)

---

## Phase E ladder (locked start)

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) |
| **E2** | Public contract / D2 `documents` catalog enable | [brief](documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271) (feat locked) |
| **E3+** | First consumer bind / Document Link SoT / lifecycle | locked until E2 feat |

Roadmap lifecycle themes (expiry, requests, packages, OCR, approvals, automation) are **horizon**, not this slice.

---

## In scope (this docs PR)

1. This brief.  
2. Close **Entity Workspace D9** as **COMPLETE** after [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) (`28978a1f`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity here.  
4. Clarify D2: Phase E open ≠ `documents` enable. Feat locked until this brief merges. ← done [#269](https://github.com/igortatarynovich/HostFlow/pull/269)

## In scope (feat PR — after this brief)

1. Named **Documents Platform E1 Contract Seal Gate** — Hub ownership sealed; D2 `documents` still cannot be enabled; Shell nav ≠ D2 slot; no Catalog rewrite; D1–D9 gates still green; Documents Foundation stays 🔄.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Pointers stay on E1 until E2 brief opens. ← done [E2 brief](documents-platform-e2-public-contract.md)  
4. **No** D2 slot enable, OCR/e-sign product, or Document Link table cutover unless a later named slice.

---

## Documents Platform E1 Contract Seal Gate (CI — mandatory)

Named step: **Documents Platform E1 Contract Seal Gate**  
(`tests/platform/test_documents_e1_contract_seal_gate.py`). Full-repo pytest red does not waive it. D1–D9 gates stay green.

**CI (#270):** named gate **11 passed**. Full-repo `Tests with coverage` **484 failed / 2740 passed** — Engineering Track, same baseline as D9; does not waive this gate.

- Ownership / Hub ≠ dossier / D2 still reserved locked in brief  
- Documents Foundation maturity stays 🔄 (not ✅)  
- Entity Foundation stays 🔄  
- Delivery façade `document_hub_delivery_contract.py` exists and is not `documents.public_contract.v1`  
- D2 `documents` still cannot be enabled; Shell `documents` nav ≠ D2 slot  
- No Catalog rewrite / no Entity Catalog Passport mint  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| D2 `documents` enable on Entity Workspace | [E2](documents-platform-e2-public-contract.md) |
| Sealed `documents.public_contract.v1` + Adapter id gates | [E2](documents-platform-e2-public-contract.md) |
| Document Link SoT (replace `candidate_id` row ownership) | Later E slice |
| OCR / e-sign / packages / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| `HrHandoffDetailPage` cutover | Out (not E1) |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Entity Catalog Passport | Unchanged (D-series residual) |

Do **not** mix D2 enable, OCR, Billing, AI, or Forms product unlocks into E1.

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); not Recruitment / HR / a sixth product module |
| 2 Exists? | Hub + Catalog passport + delivery façade yes; Foundation **no** — that is Phase E |
| 3 Adapter | `document_hub_delivery_contract.py` today; public-contract id later; no second Adapter in E1 |
| 4 Boundary | No D2 enable; no dossier-as-platform; no OCR/e-sign product; no Billing/AI; no Forms P3–P5; no file-copy handoff |
| 5 Settings | Existing Manifest IA only; no new keys in E1 |
| 6 SoT | Document Hub (ADR-009); candidate-owned `documents` is legacy bridge, not Hub SoT |
| 7 Events | Catalog `document.created` / `linked` / `verified` / `expired` — no new events this slice |
| 8 Requires | D9 ✅ · D2 reserved slot named · ADR-009 / ADR-014 · Forms Foundation ✅ (compose later) |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | Additive enforcement gate only; no DTO bump; no `documents.public_contract.v1`; no Catalog shape change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#269](https://github.com/igortatarynovich/HostFlow/pull/269))  
- [x] Named Documents Platform E1 Contract Seal Gate  
- [x] D9 remains closed (#268 / `28978a1f`)  
- [x] D2 `documents` cannot be enabled; Shell nav ≠ D2 slot  
- [x] No Catalog rewrite; Documents Foundation remains 🔄  
- [x] Forms P3–P5 and Billing stay out of Product Track  

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Gate | `backend/tests/platform/test_documents_e1_contract_seal_gate.py` |
| Slot freeze | D2 `compositionSlots.ts` — `documents` still reserved (assert, do not enable) |
| Pointers | queue / roadmap / AGENTS / maturity stay on E1 until E2 |
| Hub notes | `docs/document-hub/module-scope.md` Product Track pointer only — not ADR rewrite |

---

## DoD

- [x] Brief sealed with ownership card + in/out + acceptance  
- [x] Queue + roadmap + AGENTS + maturity point at this brief  
- [x] D9 marked **COMPLETE** with #268 / `28978a1f`  
- [x] Feat PR — boundary gates (named Contract Seal Gate)

---

## History

- 2026-08-18: E2 brief opened — public contract / D2 catalog enable; Product Track → [E2](documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271) (feat locked). E1 ✅ [#270](https://github.com/igortatarynovich/HostFlow/pull/270) (`f37deff1`). CI: named Contract Seal Gate 11 passed; full Tests with coverage 484 failed / 2740 passed (Engineering Track, same as D9).
- 2026-08-18: E1 feat — named **Documents Platform E1 Contract Seal Gate**; D2 `documents` still reserved; no public-contract id; Foundation 🔄. Pointers stay on E1 until E2 brief.
- 2026-08-18: E1 brief ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269) (`17bd3dd3`).
- 2026-08-18: D9 ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) (`28978a1f`). Product Track → Documents Platform E1 contract seal (this brief). Feat locked. Not D2 `documents` enable / not OCR / not Forms P3–P5 / not Billing.
