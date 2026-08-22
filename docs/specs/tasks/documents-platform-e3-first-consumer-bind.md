# Documents Platform E3 — First Consumer Bind + Document Link SoT (Phase E)

**Status:** **COMPLETE** ([#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38`)  
**Next:** [Documents Platform E4 — Candidate Document Link](documents-platform-e4-candidate-document-link.md) ✅ → [Documents Platform E5 — Candidate Storage Bridge Retirement](documents-platform-e5-candidate-storage-bridge.md) (brief; feat locked)  
**Phase class:** platform  
**Branch (docs):** `docs/documents-platform-e3-first-consumer-bind` ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)  
**Branch (code):** `feat/documents-platform-e3-first-consumer-bind` ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278)  
**Parents:** [Documents Platform E2](documents-platform-e2-public-contract.md) [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · [E1](documents-platform-e1-contract-seal.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) ✅ · [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [Document Hub scope](../../document-hub/module-scope.md) · [A2-F8](../gates/platform-governance-review-a2.md)

> E2 sealed `documents.public_contract.v1` / `documents.hub_adapter_v1` and enabled the D2 `documents` **catalog** slot ([#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5`). D3–D9 stayed unbound. Foundation stayed 🔄.  
> E3 proves that contract is **consumable** through Workspace Capability Platform: one named consumer, D2 `documents` surface live, Hub adapter, Document Link SoT.  
> E3 does **not** show documents via a page-local widget, bind D3–D7/D9, drop `documents.candidate_id`, open OCR / e-sign / packages, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E3** is not E2 catalog unlock, not E1 contract seal, not a D-series chrome cutover, not Shell `documents` nav, not Candidate / HR dossier, not Recruitment Application (G4 — already closed), not OCR / e-sign product, not document packages, not Billing Platform Phase F. Catalog unlock ≠ consumer bind. First consumer bind ≠ mass D3–D9 bind. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

After [#273](https://github.com/igortatarynovich/HostFlow/pull/273)/[#274](https://github.com/igortatarynovich/HostFlow/pull/274)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) the stack is consistent and still incomplete:

| Layer | After E2 / WCP | Hole E3 closes |
|-------|----------------|----------------|
| Workspace Capability Platform | COMPLETE — host places, owners own semantics; G4 = Recruitment Application | Must not be reopened as the E3 proof |
| Public contract / adapter | `documents.public_contract.v1` / `documents.hub_adapter_v1` on the Hub façade | Still candidate-centric; not Document Link SoT |
| D2 `documents` | Catalog **enabled**; reserved list empty | No consumer slot list includes it — enabled id, not a live surface |
| Consumers | D3–D9 omit `documents` | Zero binds |
| Relationship | `documents.candidate_id` (legacy bridge) + Hub table `document_entity_links` (HR reuse MVP) | Two models; Link is not SoT |
| Foundation | 🔄 | Stays 🔄 after E3 — one bind ≠ lifecycle close |

Without E3, the next PR will either (a) paste a local documents section onto an Entity screen and call it “D2 documents”, or (b) flip every D3–D9 consumer onto the slot because “the catalog is enabled”, or (c) treat Recruitment Application as the Documents proof.

E3 exists to prove **Documents on the Capability Host**, not to decorate one card.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E3, a workspace consumer **cannot** obtain documents by inventing a page-local documents widget, a second relationship model, or a module-owned fetch/composition path. Documents remain a **platform capability**: the host **places** the D2 `documents` surface; **Documents** owns semantics, adapter, and relationship SoT. `documents.public_contract.v1` / `documents.hub_adapter_v1` are the only legal consume path. Catalog-enabled-but-unbound is no longer a valid reading of “documents work”.

**Completion proof (named consumer):**  
**HR employee Entity Workspace** — D8 `HrEmployeeDetailPage` / `/app/hr/employees/:employeeId`. Locked; feat does **not** choose Candidate, Recruitment Application, or a new screen instead.

```text
HR employee Entity Workspace (D8 host)
  + D2 documents surface bound (not merely catalog-enabled)
  + Workspace Capability contribution / slot contract (host places only)
  + documents.hub_adapter_v1 (same adapter as E2 — no second Adapter)
  + Document Link SoT: document_entity_links
      linked_entity_type=workforce_employee
      relation_type=reused_for_hr
  + zero page-local fetch (HrEmployeeDocumentsSection / dossier / #hr-employee-linked-documents)
  + zero second relationship model (no employee_id on documents, no local join table)
```

Recruitment Application is **not** this proof. It is the closed Workspace Capability G4. Candidate is **not** this proof (see consumer decision below).

**False close (reject):** documents visible on an HR card via local section; D2 id enabled with no bind; Candidate bind via `candidate_id`; G4 reused; Foundation ✅; mass D3–D9 bind; OCR/e-sign/packages as this slice.

---

## Consumer decision (normative — existing Document Link ownership)

E3 does **not** pick the consumer by UI convenience. It picks the entity that already has an operational Document Link, so the slice does not invent a new domain model.

Shipped Document Link ownership after E2:

| Artifact | Owner | What it is today |
|----------|--------|------------------|
| `document_entity_links` (`DocumentEntityLink` ORM) | Document Hub (ADR-009 MVP) | Real link rows |
| Operational writer | HR handoff (`ensure_hr_document_links`) | `linked_entity_type=workforce_employee`, `relation_type=reused_for_hr` (+ `workforce_hr_review` in acceptance) |
| Candidate relationship | `documents.candidate_id` (required FK) | Legacy bridge — E1/E2: **not** Hub SoT |
| Synthesized links | `document_data_contract.DocumentEntityLink` dataclass | Projection from `candidate_id` (`relation_type=primary`) — **not** the Hub table |
| Adapter | `documents.hub_adapter_v1` | Candidate-centric (`list_candidate_documents_via_contract`) |
| Local HR UI | `HrEmployeeDocumentsSection` | Page-local `document_links` fetch — the anti-pattern |

**Decision: first consumer = HR employee (D8).**

| Candidate | Rejected as E3 proof |
|-----------|----------------------|
| Consuming Candidate via `candidate_id` | Keeps the competing FK as the consume path — false Document Link SoT |
| Minting `linked_entity_type=candidate` primary links in the same slice | Invents a second cutover while HR already has real Hub links |
| Operational need | Real, but owned by the legacy bridge, not by Document Link |

| Client / Vacancy / Sales / Services | Rejected |
|-------------------------------------|----------|
| No operational `document_entity_links` rows | Would mint new `linked_entity_type` values and a new domain relationship |

| Recruitment Application | Rejected |
|-------------------------|----------|
| Closed G4 | Proves Workspace Capability Platform, not Documents capability |

HR employee already needs the relationship operationally (handoff reuse **without** file copy, ADR-009 / ADR-002). The domain model already exists. E3 binds that existing Link through D2 + adapter.

Candidate bind via Document Link (replace `candidate_id` as consume path) is a **later named E slice**. E3 does **not** drop the column.

---

## Goal

Prove three things on one named consumer:

1. **D2 `documents` is live** — bound on D8, rendered through the slot/contribution contract, not an enabled id sitting unused.  
2. **Documents platform remains semantic owner** — consume only `documents.public_contract.v1` / `documents.hub_adapter_v1`; no `modules.documents.crud` from HR; no local type dictionary.  
3. **Workspace consumer only places** — HR employee host does not own documents fetch, composition, or relationship.

And seal **Document Link SoT for that consumer**: Hub table `document_entity_links` is the relationship. `documents.candidate_id` stays a **legacy bridge** for Candidate-origin storage until a later named slice.

This slice does **not** rebuild Hub UI, cut over Candidate, or treat dossier / Shell nav as the D2 slot.

---

## Locked principle

```text
E1  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2  → documents.public_contract.v1 + documents.hub_adapter_v1
    → D2 documents catalog unlock (reserved → enabled)
    → D3–D9 still omit documents
E3 (this)
    → first consumer bind = HR employee (D8)
    → Document Link SoT for that consumer (document_entity_links)
    → same adapter; entity-link resolve; no second Adapter
    → D3–D7 / D9 stay unbound
E4
    → Candidate Document Link bind (D4) — [brief](documents-platform-e4-candidate-document-link.md) ✅
E5
    → Candidate storage-bridge retirement (`candidate_id` drop) — [brief](documents-platform-e5-candidate-storage-bridge.md)
E6+
    → remaining consumers / lifecycle (locked until E5 feat)
```

E3 **must not**:

- bind `documents` on Sales Inquiry / Candidate / Client / Sales Order / Vacancy / Services order  
- reopen Recruitment Application as G4 or as the Documents proof  
- collapse Shell `EntityWorkspaceSectionId` `documents` into `compositionSlots.ts`  
- treat `#hr-employee-linked-documents` / `HrEmployeeDocumentsSection` / Employee dossier / Candidate docs panel as the D2 slot  
- drop `documents.candidate_id` or backfill all Candidate primary links  
- mint a second Adapter, a second public-contract id, or a local HR document table  
- copy files across Recruitment ↔ HR  
- open OCR, e-sign, packages, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- cut over `HrHandoffDetailPage`  
- invent a new `linked_entity_type` (client, vacancy, …)  
- mark Documents Foundation ✅ (stays 🔄)

---

## Document Link SoT (this slice — not a global table cutover)

| Layer | E2 | E3 (this) |
|-------|----|-----------|
| Relationship SoT for the named consumer | Not claimed | `document_entity_links` |
| Adapter resolve for that consumer | Candidate-centric façade | **Same** `documents.hub_adapter_v1` — entity-link resolve (`workforce_employee` / `reused_for_hr`) |
| `documents.candidate_id` | Legacy bridge | **Still** legacy bridge for Candidate-origin rows |
| Synthesized dataclass links | Not SoT | Still not SoT; must not become a third model |
| Other consumers | Unbound | Unbound |

**Invariants:**

1. One Document; many Links. Handoff is links + permissions, never copy (ADR-009).  
2. Modules consume only the public contract / adapter (Architecture Rule 2).  
3. No new local type / status dictionaries (Architecture Rule 1).  
4. D2 `documents` on D8 renders via the adapter only.  
5. `candidate_id` on `documents` is storage bridge, not the HR consume path.

Feat may dual-read Hub links for D8. It must **not** add `employee_id` to `documents`, mint `document_links_v2`, or treat the dataclass in `document_data_contract.py` as the table.

---

## D2 bind (one consumer — not catalog work)

E2 already enabled the catalog slot. **This slice binds it once.**

| Layer | E2 | E3 (this) |
|-------|----|-----------|
| `ENTITY_WORKSPACE_ENABLED_SLOT_IDS` | includes `documents` | unchanged |
| D8 `hrEmployeeConsumer` slot list | omits `documents` | **includes** `documents` |
| D3–D7 / D9 slot lists | omit `documents` | **still omit** |
| Shell `EntityWorkspaceSectionId` `documents` | ≠ D2 slot | still ≠ D2 slot |
| Host | Capability Host places the surface | HR employee host places; Documents owns semantics |

`HrEmployeeDocumentsSection` / dossier linked-documents **must not** remain the consume path for the bound surface. Feat retires that local fetch on the proof screen (module nav may remain labelled as not-the-slot until migrate-on-touch, but the D2 surface cannot call it).

---

## Phase E ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1` |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | [brief](documents-platform-e5-candidate-storage-bridge.md) (feat locked) |
| **E6+** | Remaining consumers / lifecycle | locked until E5 feat |

Roadmap lifecycle themes (expiry, requests, packages, OCR, approvals, automation) stay **horizon**. Documents Foundation stays 🔄.

---

## In scope (this docs PR)

1. This brief — consumer decision + Original Goal → Completion Proof.  
2. Close **Documents Platform E2** as **COMPLETE** after [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) (`826877b5`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope / D2 / D8 here.  
4. Feat follows this brief.

## In scope (feat PR — this)

1. Bind D8 `documents` through the Capability Host contribution / D2 slot contract.  
2. Extend `documents.hub_adapter_v1` with entity-link resolve for `workforce_employee` / `reused_for_hr` — **no second Adapter**, no contract id bump.  
3. Retire page-local documents fetch on the proof surface (`HrEmployeeDocumentsSection` must not be the D2 consume path).  
4. Named **Documents Platform E3 First Consumer Bind Gate** — D8 bound; D3–D7/D9 unbound; adapter still `documents.hub_adapter_v1`; consume path = Document Link; `candidate_id` still bridge; Shell nav ≠ D2; Foundation 🔄; G4 unchanged.  
5. E1 / E2 / D1–D9 / WCP named gates stay green (amend only assertions that froze “no consumer bind”).  
6. Architecture Review Checklist (10 questions) + Goal Completion G1–G5 in the feat PR description.  
7. Pointers moved to [E4](documents-platform-e4-candidate-document-link.md) after this feat merged; now [E5](documents-platform-e5-candidate-storage-bridge.md).

---

## Documents Platform E3 First Consumer Bind Gate (CI — mandatory)

Named step: **Documents Platform E3 First Consumer Bind Gate**  
(`tests/platform/test_documents_e3_first_consumer_bind_gate.py`). Full-repo pytest red does not waive it. E1 / E2 / D1–D9 / WCP gates stay green.

- D8 consumer slot list includes `documents`  
- D3–D7 / D9 consumer slot lists still omit `documents`  
- Proof surface consumes via `documents.public_contract.v1` / `documents.hub_adapter_v1`  
- Adapter resolve for D8 goes through `document_entity_links` (`workforce_employee` / `reused_for_hr`)  
- No second Adapter; no new public-contract id  
- `documents.candidate_id` column still present (legacy bridge)  
- Shell `documents` nav ≠ D2 slot  
- Recruitment Application G4 path unchanged  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Candidate bind via Document Link (replace `candidate_id` consume path) | Later named E slice |
| Drop / backfill `documents.candidate_id` | Later named E slice |
| D3 / D5 / D6 / D7 / D9 `documents` bind | Later named E slices |
| OCR / e-sign / packages / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| `HrHandoffDetailPage` cutover | Out (not E3) |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Entity Catalog Passport | Unchanged |
| Documents Foundation ✅ | Later E close (lifecycle still open) |
| Reopen G4 Recruitment Application | Forbidden |

Do **not** mix Candidate cutover, mass bind, OCR, Billing, AI, or Forms product unlocks into E3.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); HR employee host **places** only. Not Recruitment / a sixth product module |
| 2 Exists? | Public contract + adapter + D2 catalog slot + Hub `document_entity_links` yes; first consumer bind **new** (this); Foundation **no** |
| 3 Adapter | Same `documents.hub_adapter_v1`; entity-link resolve additive; no second Adapter |
| 4 Boundary | One consumer (D8); no D3–D7/D9 bind; no Candidate `candidate_id` drop; no dossier-as-slot; no OCR/e-sign product; no Billing/AI; no Forms P3–P5; no file-copy handoff; no G4 reopen |
| 5 Settings | Existing Manifest IA only; no new keys in E3 |
| 6 SoT | Document Hub + Document Link table for the named consumer; `candidate_id` remains legacy bridge |
| 7 Events | Catalog `document.created` / `linked` / `verified` / `expired` — no new events this slice |
| 8 Requires | E2 ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) · E1 ✅ · D8 ✅ · WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · ADR-009 / ADR-014 / ADR-025 |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | No id bump; additive entity-link resolve under `documents.public_contract.v1`; no Catalog shape change; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track → [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md); this slice is closed (#278 / `cc106a38`). E4 ✅ (#280 / `0af74913`).  
- Operators / agents cannot treat catalog enable, HR dossier, Shell `documents` nav, Candidate `candidate_id`, or Recruitment Application as this proof.  
- Feat ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (brief ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)).  
- D3–D7 / D9 remain unbound on `documents`; Forms P3–P5, OCR, and Billing stay out of Product Track.  
- Documents Foundation stays 🔄.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| D8 bind | `hostflow-frontend/src/platform/entity-workspace/hrEmployeeConsumer.ts` |
| Host / contribution | HR employee Entity host — place D2 `documents`; no local composition |
| Retire local fetch | `hostflow-frontend/src/pages/hr/HrEmployeeDocumentsSection.tsx` (must not be the D2 path) |
| Adapter | `backend/app/services/document_hub_delivery_contract.py` — entity-link resolve on existing ids |
| Link SoT | `backend/app/models/document_entity_link.py` / `workforce_hr_operational_context.py` — consume Hub table; no second model |
| Public contract note | `docs/specs/architecture/documents-public-contract.md` — E3 entity-link resolve; still not Candidate column drop |
| Gate | `backend/tests/platform/test_documents_e3_first_consumer_bind_gate.py` |
| Prior gates | E2 / D8 assertions that froze “no documents bind” |
| Pointers | queue / roadmap / AGENTS / maturity → [E5](documents-platform-e5-candidate-storage-bridge.md) |

---

## DoD

- [x] Brief sealed with consumer decision / Document Link ownership / D2 live vs enabled / in/out + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E2 marked **COMPLETE** with #276 / `826877b5`  
- [x] Feat PR — D8 bind + adapter entity-link resolve ([#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38`)

---

## History

- 2026-08-22: E5 brief opened — Product Track → [E5](documents-platform-e5-candidate-storage-bridge.md) (feat locked). E4 ✅ [#280](https://github.com/igortatarynovich/HostFlow/pull/280). This slice ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`).
- 2026-08-22: E3 feat ✅ [#278](https://github.com/igortatarynovich/HostFlow/pull/278) (`cc106a38`) — D8 bind + entity-link resolve; named First Consumer Bind Gate. Product Track → [E4](documents-platform-e4-candidate-document-link.md). Foundation stays 🔄.
- 2026-08-22: E3 feat opened — D8 bind + entity-link resolve on `documents.hub_adapter_v1`; named First Consumer Bind Gate. Brief ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277). Foundation stays 🔄.
- 2026-08-22: E3 brief opened — first consumer bind = HR employee (D8) + Document Link SoT. Product Track → this brief (feat locked). E2 ✅ [#276](https://github.com/igortatarynovich/HostFlow/pull/276) (`826877b5`). WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274). G4 stays Recruitment Application. Foundation stays 🔄.
