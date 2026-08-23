# Documents Platform E4 — Candidate Document Link (Phase E)

**Status:** **COMPLETE** ([#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913`)  
**Next:** [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) ✅ → [Documents Platform E6](documents-platform-e6-document-expiry.md) ✅ → [Documents Platform E7 — Document Requests](documents-platform-e7-document-requests.md) (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/documents-platform-e4-candidate-document-link` ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)  
**Branch (code):** `feat/documents-platform-e4-candidate-document-link` ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280)  
**Parents:** [Documents Platform E3](documents-platform-e3-first-consumer-bind.md) [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · [E2](documents-platform-e2-public-contract.md) ✅ · [E1](documents-platform-e1-contract-seal.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [Document Hub scope](../../document-hub/module-scope.md) · [A2-F8](../gates/platform-governance-review-a2.md)

> E3 bound D2 `documents` on HR employee through Capability Host + Document Link ([#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38`). Candidate still consumes via `documents.candidate_id` / synthesized dataclass links. Foundation stayed 🔄.  
> E4 replaces that Candidate **consume path** with Hub `document_entity_links`. Same adapter. One more named consumer — not mass D3–D9 bind.  
> E4 does **not** drop `documents.candidate_id`, bind D3 / D5–D7 / D9, treat Shell `documents` nav as the D2 slot, open OCR / e-sign / packages, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E4** is not E3 first-consumer bind, not E2 catalog unlock, not E1 contract seal, not D4 chrome cutover, not Shell `documents` nav, not CandidateCard documents panel, not Recruitment Application (G4), not OCR / e-sign product, not document packages, not Billing Platform Phase F. Candidate Document Link ≠ mass D3–D9 bind. First consumer (D8) stays bound. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

After [#276](https://github.com/igortatarynovich/HostFlow/pull/276)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) Documents is consumable on one host and still split on Candidate:

| Layer | After E3 | Hole E4 closes |
|-------|----------|----------------|
| D8 HR employee | D2 `documents` live via `document_entity_links` (`workforce_employee` / `reused_for_hr`) | Leave as-is |
| Candidate consume | `list_candidate_documents_via_contract` + required `documents.candidate_id` | Competing FK is still the Candidate path — false Document Link SoT |
| Synthesized links | `document_data_contract.DocumentEntityLink` dataclass (`relation_type=primary`) | Projection, not Hub table — must not become a third model |
| D4 Candidate host | Places `communication` / `forms` only | D2 `documents` still unbound on the entity that **owns** most documents |
| D3 / D5–D7 / D9 | Omit `documents` | Stay omit — this slice is not mass bind |
| Foundation | 🔄 | Stays 🔄 — Candidate Link ≠ lifecycle close |

Without E4, the next PR will either (a) bind every remaining consumer because “E3 proved documents work”, or (b) keep listing Candidate documents by `candidate_id` and call that Document Link, or (c) drop the column before the consume path is Hub links.

E4 exists to prove **Candidate on Document Link**, not to decorate the Candidate card and not to finish Phase E.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E4, Candidate **cannot** obtain documents for the D2 `documents` surface by querying `documents.candidate_id`, a synthesized dataclass “link”, or a page-local Candidate documents panel. The consume path is Hub `document_entity_links`. `documents.public_contract.v1` / `documents.hub_adapter_v1` remain the only legal consume path. HR employee bind stays. Catalog-enabled-plus-one-consumer is no longer a valid reading of “Candidate documents work”.

**Completion proof (named consumer):**  
**Candidate Entity Workspace** — D4 `CandidateEntityWorkspacePanel` / `/app/candidates/:id`. Locked; feat does **not** choose Recruitment Application, a new screen, or mass D3–D9 bind instead.

```text
Candidate Entity Workspace (D4 host)
  + D2 documents surface bound (not Shell documents nav)
  + Workspace Capability contribution / slot contract (host places only)
  + documents.hub_adapter_v1 (same adapter as E2/E3 — no second Adapter)
  + Document Link SoT: document_entity_links
      linked_entity_type=candidate
      relation_type=primary
  + zero page-local fetch (CandidateCard documents panel / Shell documents section)
  + D8 HR employee bind unchanged
  + documents.candidate_id column still present (storage bridge, not consume path)
```

Recruitment Application is **not** this proof (closed G4). HR employee is **not** this proof (closed E3). Client / Vacancy / Sales / Services are **not** this proof.

**False close (reject):** Candidate docs visible via `candidate_id` list; Shell `documents` nav as the slot; synthesized dataclass as SoT; mass D3–D9 bind; column drop; Foundation ✅; OCR/e-sign/packages; G4 reused.

---

## Consumer decision (normative)

E3 left Candidate on the legacy bridge on purpose: HR already had operational Hub rows; minting `linked_entity_type=candidate` in that slice would have been a second cutover.

Shipped after E3:

| Artifact | Owner | What it is today |
|----------|--------|------------------|
| `document_entity_links` for HR | Document Hub | Real rows (`workforce_employee` / `reused_for_hr`) |
| Candidate relationship | `documents.candidate_id` (required FK) | Storage + consume path |
| Synthesized links | `document_data_contract.DocumentEntityLink` dataclass | Projection from `candidate_id` (`relation_type=primary`) — **not** the Hub table |
| Adapter Candidate op | `list_candidate_documents_via_contract` | Legacy bridge |
| Adapter Link op | `list_entity_link_documents_via_contract` | E3 D8 path only (`workforce_employee` / `reused_for_hr`) |
| D4 host contributions | `candidateEntity.ts` | `communication` + `forms` — no `documents` |
| Local Candidate UI | CandidateCard / Shell `documents` nav | Module chrome — not the D2 slot |

**Decision: this consumer = Candidate (D4).**

| HR employee (D8) | Already bound (E3) — do not reopen |
|------------------|-------------------------------------|
| Client / Vacancy / Sales / Services | No operational Candidate-origin rows; would mint new `linked_entity_type` values — later named slices |
| Recruitment Application | Closed G4 — proves Workspace Capability, not Documents |

`linked_entity_type=candidate` / `relation_type=primary` is the Hub type this slice may persist. It is **not** a new domain: E3 already named it as the deferred Candidate Link. Synthesized dataclass `owner_type="candidate"` is **not** the table.

Dropping `documents.candidate_id` is a **later named E slice**. E4 replaces the **consume path**. Feat may ensure / backfill primary Hub rows from the FK and dual-write on create. It must **not** delete the column.

---

## Goal

Prove three things on Candidate:

1. **D2 `documents` is live on D4** — bound through the slot/contribution contract, not Shell nav and not CandidateCard.  
2. **Document Link is the Candidate consume path** — Hub `document_entity_links`, not `candidate_id` SELECT and not the dataclass projection.  
3. **Same platform contract** — `documents.public_contract.v1` / `documents.hub_adapter_v1`; no second Adapter; D8 bind unchanged; D3 / D5–D7 / D9 still omit `documents`.

---

## Locked principle

```text
E1  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2  → documents.public_contract.v1 + documents.hub_adapter_v1
    → D2 documents catalog unlock (reserved → enabled)
E3  → first consumer bind = HR employee (D8)
    → Document Link SoT for that consumer
E4 (this)
    → Candidate Document Link bind (D4)
    → consume path = document_entity_links (candidate / primary)
    → same adapter; no second Adapter
    → candidate_id remains storage bridge (not dropped)
    → D3 / D5–D7 / D9 stay unbound
    → D8 stays bound
E5
    → Candidate storage-bridge retirement (`candidate_id` drop) — [brief](documents-platform-e5-candidate-storage-bridge.md) ✅
E6
    → Document expiry / validity — [brief](documents-platform-e6-document-expiry.md) ✅
E7
    → Document requests — [brief](documents-platform-e7-document-requests.md)
E8+
    → remaining consumers / later lifecycle (locked until E7 feat)
```

E4 **must not**:

- bind `documents` on Sales Inquiry / Client / Sales Order / Vacancy / Services order  
- unbind or rewrite the D8 HR employee consume path  
- reopen Recruitment Application as G4 or as the Documents proof  
- collapse Shell `EntityWorkspaceSectionId` `documents` into `compositionSlots.ts`  
- treat CandidateCard documents panel / `#documents` Shell nav as the D2 slot  
- drop `documents.candidate_id`  
- treat `document_data_contract.DocumentEntityLink` dataclass as the Hub table  
- mint a second Adapter, a second public-contract id, or a local Candidate document table  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mark Documents Foundation ✅ (stays 🔄)

---

## Document Link SoT (Candidate — not a global column drop)

| Layer | E3 | E4 (this) |
|-------|----|-----------|
| Relationship SoT for Candidate | Not claimed (`candidate_id` consume) | `document_entity_links` (`candidate` / `primary`) |
| Adapter resolve for Candidate | `list_candidate_documents_via_contract` | **Same** `documents.hub_adapter_v1` — entity-link resolve |
| `documents.candidate_id` | Legacy bridge + Candidate consume | **Still** storage bridge; **not** the D2 consume path |
| Synthesized dataclass links | Not SoT | Still not SoT |
| D8 HR employee | Bound | Bound (unchanged) |
| Other consumers | Unbound | Unbound |

**Invariants:**

1. One Document; many Links. Handoff remains links + permissions, never copy (ADR-009).  
2. Modules consume only the public contract / adapter (Architecture Rule 2).  
3. No new local type / status dictionaries (Architecture Rule 1).  
4. D2 `documents` on D4 renders via the adapter only.  
5. `candidate_id` on `documents` may still be written; it is not how D4 reads.

Feat may dual-write / backfill Hub primary links. It must **not** add a second Candidate FK, mint `document_links_v2`, or keep `list_candidate_documents_via_contract` as the proof consume path.

---

## D2 bind (Candidate — not mass bind)

E3 bound D8. **This slice binds D4.** It does not bind the rest.

| Layer | E3 | E4 (this) |
|-------|----|-----------|
| `ENTITY_WORKSPACE_ENABLED_SLOT_IDS` | includes `documents` | unchanged |
| D8 `hrEmployeeConsumer` slot list | includes `documents` | **still includes** |
| D4 `candidateConsumer` slot list | omits `documents` | **includes** `documents` |
| D4 host contributions | communication + forms | **adds** `workspace.surface.documents` |
| D3 / D5–D7 / D9 slot lists | omit `documents` | **still omit** |
| Shell `EntityWorkspaceSectionId` `documents` | ≠ D2 slot | still ≠ D2 slot |

CandidateCard / Shell documents **must not** remain the consume path for the bound surface. Feat retires that local fetch on the proof screen (module nav may remain labelled as not-the-slot until migrate-on-touch).

---

## Phase E ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1` |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c` |
| **E6** | Document expiry / validity | ✅ [#284](https://github.com/igortatarynovich/HostFlow/pull/284)/[#285](https://github.com/igortatarynovich/HostFlow/pull/285) · merge `79e638c3` |
| **E7** | Document requests | [brief](documents-platform-e7-document-requests.md) (brief; feat locked) |

Roadmap lifecycle themes (expiry, requests, packages, OCR, approvals, automation) stay **horizon**. Documents Foundation stays 🔄.

---

## In scope (this docs PR)

1. This brief — consumer decision + Original Goal → Completion Proof.  
2. Close **Documents Platform E3** as **COMPLETE** after [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope / D2 / D4 / D8 here.  
4. Brief merged ([#279](https://github.com/igortatarynovich/HostFlow/pull/279) · `dbeb7822`).

## In scope (feat PR — after this brief)

1. Bind D4 `documents` through the Capability Host contribution / D2 slot contract.  
2. Extend `documents.hub_adapter_v1` entity-link resolve for `candidate` / `primary` — **no second Adapter**, no contract id bump. D8 resolve stays.  
3. Ensure / backfill Hub primary links so D4 does not read via `candidate_id`. Column stays.  
4. Retire page-local Candidate documents fetch on the proof surface (CandidateCard / Shell nav must not be the D2 consume path).  
5. Named **Documents Platform E4 Candidate Document Link Gate** — D4 bound; D8 still bound; D3 / D5–D7 / D9 unbound; adapter still `documents.hub_adapter_v1`; consume path = Document Link; `candidate_id` still present; Shell nav ≠ D2; Foundation 🔄; G4 unchanged.  
6. E1 / E2 / E3 / D1–D9 / WCP named gates stay green (amend only assertions that froze “Candidate must not bind documents”).  
7. Architecture Review Checklist (10 questions) + Goal Completion G1–G5 in the feat PR description.  
8. Pointers moved to [E5](documents-platform-e5-candidate-storage-bridge.md) after this feat merged.

---

## Documents Platform E4 Candidate Document Link Gate (CI — mandatory)

Named step: **Documents Platform E4 Candidate Document Link Gate**  
(`tests/platform/test_documents_e4_candidate_document_link_gate.py`). Full-repo pytest red does not waive it. E1 / E2 / E3 / D1–D9 / WCP gates stay green.

- D4 consumer slot list includes `documents`  
- D8 consumer slot list still includes `documents`  
- D3 / D5–D7 / D9 consumer slot lists still omit `documents`  
- Proof surface consumes via `documents.public_contract.v1` / `documents.hub_adapter_v1`  
- Adapter resolve for D4 goes through `document_entity_links` (`candidate` / `primary`)  
- No second Adapter; no new public-contract id  
- `documents.candidate_id` column still present (storage bridge)  
- Shell `documents` nav ≠ D2 slot  
- Recruitment Application G4 path unchanged  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Drop `documents.candidate_id` | Later named E slice |
| D3 / D5 / D6 / D7 / D9 `documents` bind | Later named E slices — **not** this PR |
| OCR / e-sign / packages / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Entity Catalog Passport | Unchanged |
| Documents Foundation ✅ | Later E close (lifecycle still open) |
| Reopen G4 Recruitment Application | Forbidden |
| Reopen E3 D8 bind | Forbidden |

Do **not** mix mass bind, column drop, OCR, Billing, AI, or Forms product unlocks into E4.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); Candidate host **places** only. Not Recruitment / a sixth product module |
| 2 Exists? | Public contract + adapter + D2 catalog slot + D8 bind + Hub table yes; Candidate Link consume **new** (this); Foundation **no** |
| 3 Adapter | Same `documents.hub_adapter_v1`; entity-link resolve additive (`candidate` / `primary`); no second Adapter |
| 4 Boundary | One added consumer (D4); D8 stays; no D3 / D5–D7 / D9 bind; no `candidate_id` drop; no dossier-as-slot; no OCR/e-sign product; no Billing/AI; no Forms P3–P5; no G4 reopen |
| 5 Settings | Existing Manifest IA only; no new keys in E4 |
| 6 SoT | Document Hub + Document Link table for Candidate consume; `candidate_id` remains storage bridge |
| 7 Events | Catalog `document.created` / `linked` / `verified` / `expired` — no new events this slice |
| 8 Requires | E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) · E2 ✅ · E1 ✅ · D4 ✅ · WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · ADR-009 / ADR-014 / ADR-025 |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | No id bump; additive Candidate entity-link resolve under `documents.public_contract.v1`; no Catalog shape change; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track → [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md); this slice is closed (#280 / `0af74913`).  
- Operators / agents cannot treat HR bind, CandidateCard, Shell `documents` nav, `candidate_id` list, or Recruitment Application as this proof.  
- Feat ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) (brief ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)).  
- D3 / D5–D7 / D9 remain unbound on `documents`; D8 stays bound; Forms P3–P5, OCR, and Billing stay out of Product Track.  
- Documents Foundation stays 🔄.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| D4 bind | `hostflow-frontend/src/platform/entity-workspace/candidateConsumer.ts` |
| Host / contribution | `hostflow-frontend/src/platform/workspace-capability/candidateEntity.ts` — place D2 `documents` |
| Proof surface | `CandidateEntityWorkspacePanel` / `CandidateDetailRoute` — host places; no local composition |
| Retire local fetch | CandidateCard documents panel / Shell `documents` nav must not be the D2 path |
| Adapter | `backend/app/services/document_hub_delivery_contract.py` — entity-link resolve for `candidate` / `primary` |
| Link SoT | `backend/app/models/document_entity_link.py` — persist Hub rows; dataclass is not SoT |
| Public contract note | `docs/specs/architecture/documents-public-contract.md` — E4 Candidate Link resolve; still not column drop |
| Gate | `backend/tests/platform/test_documents_e4_candidate_document_link_gate.py` |
| Prior gates | E3 / D4 / D2 assertions that froze “Candidate must not bind documents” |
| Pointers | queue / roadmap / AGENTS / maturity → [E5](documents-platform-e5-candidate-storage-bridge.md) |

---

## DoD

- [x] Brief sealed with consumer decision / Document Link ownership / D2 live vs enabled / in/out + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E3 marked **COMPLETE** with #278 / `cc106a38`  
- [x] Feat PR — D4 bind + Candidate Document Link resolve ([#280](https://github.com/igortatarynovich/HostFlow/pull/280) · `0af74913`)

---

## History

- 2026-08-22: E4 feat ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280) (`0af74913`). Next = [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) (feat locked).
- 2026-08-22: E4 feat opened — D4 bind + Candidate Document Link resolve; named Candidate Document Link Gate. Brief ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279) (`dbeb7822`). D3 / D5–D7 / D9 stay unbound. `candidate_id` stays. Foundation stays 🔄.
- 2026-08-22: E4 brief opened — Candidate Document Link bind (D4). Product Track → this brief (feat locked). E3 ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`). D3 / D5–D7 / D9 stay unbound. `candidate_id` stays. Foundation stays 🔄.
