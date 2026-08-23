# Documents Platform E6 — Document Expiry / Validity (Phase E)

**Status:** **IN PROGRESS** (docs — this brief); feat locked until this brief merges  
**Phase class:** platform  
**Branch (docs):** `docs/documents-platform-e6-document-expiry`  
**Branch (code):** `feat/documents-platform-e6-document-expiry` (locked until this brief merges)  
**Parents:** [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · [E4](documents-platform-e4-candidate-document-link.md) ✅ · [E3](documents-platform-e3-first-consumer-bind.md) ✅ · [E2](documents-platform-e2-public-contract.md) ✅ · [E1](documents-platform-e1-contract-seal.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) ✅ · [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md) [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md) · [ADR-014](../architecture/ADR-014-document-hub-access-model.md) · [ADR-025](../architecture/ADR-025-standard-adapter-boundary.md) · [Capability Contract](../architecture/capability-contract.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [Document Hub scope](../../document-hub/module-scope.md) · [document expiry workflow](../workflows/document_expiry.md) · [A2-F8](../gates/platform-governance-review-a2.md)

> E5 dropped `documents.candidate_id`. Candidate relationship SoT is Hub `document_entity_links` (`candidate` / `primary`). D4 and D8 stay bound. Foundation stayed 🔄.  
> E6 seals **expiry / validity as a Hub document property** consumed through the public contract — not a Candidate-owned reminder silo, not mass D3–D9 bind, not OCR / packages / Foundation close.  
> E6 does **not** bind D3 / D5–D7 / D9, reopen G4, treat `next_action` or the reminder table as Documents SoT, open OCR / e-sign / packages, or mark Foundation ✅.

**Naming (do not collapse):** this **Documents Platform E6** is not E5 storage-bridge retirement, not E4 Candidate Document Link bind, not E3 first-consumer bind, not a D-series chrome cutover, not Shell `documents` nav, not Recruitment Application (G4), not OCR / e-sign product, not document packages, not document requests, not Billing Platform Phase F. Expiry seal ≠ Foundation ✅. Remaining Entity consumers stay unbound. Document Hub remains a **platform capability** (ADR-009), **not** a sixth product module.

---

## Why this slice

After [#282](https://github.com/igortatarynovich/HostFlow/pull/282) (`702b922c`) Document is no longer a Candidate child row. Phase E’s first horizon theme is still split:

| Layer | After E5 | Hole E6 closes |
|-------|----------|----------------|
| D4 / D8 consume | Hub links + `expires_at` on the Hub view | Leave bind as-is |
| `documents.expire_date` / `expires_at` | Present on the Document row | Must be the Hub validity SoT, not a Candidate field |
| `document_expiry_engine` | Evaluates a date | Keep as Documents evaluation helper — not a second SoT |
| `notification_events` (P2 table) | Already in schema | Must not become a parallel expiry product |
| [document_expiry.md](../workflows/document_expiry.md) | Still describes `candidate_id`, Candidate status flips, Hub-owned reminder table | Competing Candidate-lifecycle reading |
| `next_action.py` | Reasons `document_expired` / `document_expiring_soon` | Recruitment UOS consumer — not Documents SoT |
| Catalog `document.expired` | Already named | E6 does **not** mint a new event |
| D3 / D5–D7 / D9 | Omit `documents` | Stay omit — expiry ≠ mass bind |
| Foundation | 🔄 | Stays 🔄 — expiry ≠ packages / OCR / Foundation close |

Without E6, the next PR will either (a) bind every remaining consumer because “the FK is gone”, or (b) keep driving expiry from Candidate reminders / `next_action` and call lifecycle done, or (c) mark Foundation ✅ while validity is still a Candidate workflow.

E6 exists to prove **validity belongs to the Document**, not to decorate another Entity Workspace and not to finish Phase E.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E6, expiry / validity **cannot** be a Candidate-owned reminder pipeline that reads `documents.candidate_id` or treats the person as the document. Public consume of expiry is Hub `expires_at` (and Catalog `document.expired`) through `documents.public_contract.v1` / `documents.hub_adapter_v1`. D4 and D8 still place `documents`; they do not own evaluation. Activity / reminders stay in the Activity & Notification operating layer (ADR-012) — Document Hub **publishes**, it does not own a task table. D3 / D5–D7 / D9 stay unbound. Column-drop-plus-two-consumers is no longer a valid reading of “Documents lifecycle is done”.

**Completion proof (named consumer):**  
**Candidate Entity Workspace** — D4 `CandidateEntityWorkspacePanel` / `/app/candidates/:id`. Locked; feat does **not** choose Recruitment Application, a new Hub control-center, mass D3–D9 bind, or Foundation close instead.

```text
Candidate Entity Workspace (D4 host)
  + D2 documents surface still bound (E4)
  + documents.hub_adapter_v1 (same adapter — no second Adapter)
  + Hub view exposes expires_at from Document.expire_date
  + expiry evaluation is Documents-owned (document_expiry_engine / public contract)
  + no candidate_id in expiry workflow SoT
  + Activity layer may consume document.expired — Hub does not own reminders
  + D8 HR employee bind unchanged
  + D3 / D5–D7 / D9 still omit documents
```

Recruitment Application is **not** this proof (closed G4). HR employee is **not** this proof (closed E3). Client / Vacancy / Sales / Services are **not** this proof. OCR / packages / requests are **not** this proof.

**False close (reject):** Candidate status auto-flip as Documents SoT; reminder table inside Document Hub; `next_action` as the public contract; mass D3–D9 bind; Foundation ✅; OCR/e-sign/packages; G4 reused.

---

## Consumer decision (normative)

E5 left remaining Entity consumers unbound on purpose: they still need new `linked_entity_type` values. Binding them now would be the false close E5 named (“two hosts already work”).

Shipped after E5:

| Artifact | Owner | What it is today |
|----------|--------|------------------|
| D8 / D4 D2 bind | Document Hub + hosts | Live via `documents.hub_adapter_v1` |
| Candidate relationship | `document_entity_links` (`candidate` / `primary`) | Storage + consume |
| Validity field | `documents.expire_date` / Hub `expires_at` | Present; not sealed as public lifecycle |
| Expiry engine | `document_expiry_engine.py` | Date evaluation helper |
| Notification events table | Engineering P2 | Exists; not a Documents public op |
| Expiry workflow spec | [document_expiry.md](../workflows/document_expiry.md) | Still Candidate-FK / Candidate-status |
| UOS | `next_action.py` | Module consumer of expiry states |

**Decision: this slice = Document Expiry / Validity.** Proof consumer stays **Candidate (D4)** — the bound host that actually has expiring documents. E6 does not add a third D2 consumer.

| Remaining Entity consumers (D3 / D5–D7 / D9) | Later named slices — **not** this PR |
| Requests / packages / OCR / approvals / automation | Later E / Advanced — **not** this PR |
| Recruitment Application | Closed G4 — proves Workspace Capability, not Documents |

Feat **must** seal expiry on the public contract / adapter (read path + Catalog `document.expired` already named). It must retire Candidate-FK language from the expiry workflow SoT. It must **not** move reminder ownership into Document Hub.

---

## Goal

Prove three things on validity:

1. **Expiry is a Hub document property** — `expire_date` / public `expires_at`, not a Candidate column and not a person-status machine.  
2. **Same platform contract** — `documents.public_contract.v1` / `documents.hub_adapter_v1`; no second Adapter; no new public-contract id.  
3. **Activity stays downstream** — Document Hub publishes `document.expired` / expiring signals; ADR-012 owns reminders / tasks. D4 + D8 stay bound; D3 / D5–D7 / D9 still omit `documents`.

---

## Locked principle

```text
E1  → who owns Documents Platform + Hub ≠ dossier ≠ D2 enable
E2  → documents.public_contract.v1 + documents.hub_adapter_v1
    → D2 documents catalog unlock (reserved → enabled)
E3  → first consumer bind = HR employee (D8)
    → Document Link SoT for that consumer
E4  → Candidate Document Link bind (D4)
    → consume path = document_entity_links (candidate / primary)
E5  → drop documents.candidate_id
    → writers persist Hub links; no FK
E6 (this)
    → expiry / validity is Hub document property
    → public consume via same adapter; Catalog document.expired
    → Activity layer consumes; Hub does not own reminder table
    → D4 + D8 stay bound; D3 / D5–D7 / D9 stay unbound
    → same adapter; no second Adapter
E7+
    → remaining consumers / later lifecycle (locked until E6 feat)
```

E6 **must not**:

- bind `documents` on Sales Inquiry / Client / Sales Order / Vacancy / Services order  
- unbind or rewrite the D8 / D4 consume paths  
- reopen Recruitment Application as G4 or as the Documents proof  
- treat `next_action` / Candidate pipeline auto-flip as Documents SoT  
- put a reminder / task table inside Document Hub (ADR-012 owns that)  
- mint a second Adapter, a second public-contract id, or a local Candidate expiry table  
- open OCR, e-sign, packages, document requests, approvals automation, or Hub UI rebuild  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- mark Documents Foundation ✅ (stays 🔄)

---

## Validity SoT (this is the expiry seal)

| Layer | E5 | E6 (this) |
|-------|----|-----------|
| Relationship SoT | `document_entity_links` only | **Same** |
| Validity SoT | Unsealed date field + Candidate workflow leftover | Hub `expire_date` / public `expires_at` |
| Adapter | `documents.hub_adapter_v1` | **Same** — additive expiry read, no second Adapter |
| Catalog event | `document.expired` named | **Consumed**, not rewritten |
| Reminders | Candidate workflow leftover | Activity layer (ADR-012) |
| D4 / D8 | Bound | Bound (unchanged) |
| Other consumers | Unbound | Unbound |

**Invariants:**

1. One Document; many Links. Validity is on the Document, not on a Link.  
2. Modules consume only the public contract / adapter (Architecture Rule 2).  
3. No new local type / status dictionaries (Architecture Rule 1).  
4. D2 `documents` on D4 still renders via the adapter only.  
5. Hub does not own reminder rows.  

---

## D2 bind (unchanged — not mass bind)

E5 did not bind another consumer. **This slice does not either.**

| Layer | E5 | E6 (this) |
|-------|----|-----------|
| D8 / D4 slot lists | include `documents` | **still include** |
| D3 / D5–D7 / D9 slot lists | omit `documents` | **still omit** |
| Shell `EntityWorkspaceSectionId` `documents` | ≠ D2 slot | still ≠ D2 slot |

---

## Phase E ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **E1** | Contract seal (ownership / Hub ≠ dossier / D2 still reserved) | ✅ [#269](https://github.com/igortatarynovich/HostFlow/pull/269)/[#270](https://github.com/igortatarynovich/HostFlow/pull/270) · merge `f37deff1` |
| **E2** | Public contract / D2 `documents` catalog enable | ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271)/[#276](https://github.com/igortatarynovich/HostFlow/pull/276) · merge `826877b5` |
| **E3** | First consumer bind (HR employee) + Document Link SoT | ✅ [#277](https://github.com/igortatarynovich/HostFlow/pull/277)/[#278](https://github.com/igortatarynovich/HostFlow/pull/278) · merge `cc106a38` |
| **E4** | Candidate Document Link bind (D4) | ✅ [#279](https://github.com/igortatarynovich/HostFlow/pull/279)/[#280](https://github.com/igortatarynovich/HostFlow/pull/280) · merge `0af74913` |
| **E5** | Candidate storage-bridge retirement (`candidate_id` drop) | ✅ [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) · merge `702b922c` |
| **E6** | Document expiry / validity | ← **active** (brief; feat locked) |
| **E7+** | Remaining consumers / later lifecycle | locked until E6 feat |

Roadmap later themes (requests, packages, OCR, approvals, automation) stay **horizon**. Documents Foundation stays 🔄.

---

## In scope (this docs PR)

1. This brief — expiry decision + Original Goal → Completion Proof.  
2. Close **Documents Platform E5** as **COMPLETE** after [#281](https://github.com/igortatarynovich/HostFlow/pull/281)/[#282](https://github.com/igortatarynovich/HostFlow/pull/282) (`702b922c`).  
3. Point Product Track / queue / roadmap / AGENTS / maturity / Hub scope / D2 / D4 / D8 here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Public contract / adapter: expiry read is Hub `expires_at`; no Candidate FK.  
2. Retire Candidate-FK / Candidate-status-as-SoT language from [document_expiry.md](../workflows/document_expiry.md).  
3. Keep `document_expiry_engine` as Documents evaluation; do not mint a Hub reminder table.  
4. D4 + D8 still consume via `GET /api/v1/platform/documents/resolve`.  
5. Named **Documents Platform E6 Document Expiry Gate** — Hub validity SoT; D4/D8 still bound; D3 / D5–D7 / D9 unbound; adapter still `documents.hub_adapter_v1`; Foundation 🔄; G4 unchanged.  
6. E1–E5 / D1–D9 / WCP named gates stay green.  
7. Architecture Review Checklist (10 questions) + Goal Completion G1–G5 in the feat PR description.  
8. Pointers stay on E6 until E7 brief opens.

---

## Documents Platform E6 Document Expiry Gate (CI — mandatory)

Named step: **Documents Platform E6 Document Expiry Gate**  
(`tests/platform/test_documents_e6_document_expiry_gate.py`). Full-repo pytest red does not waive it. E1–E5 / D1–D9 / WCP gates stay green.

- Public consume of expiry goes through `documents.public_contract.v1` / `documents.hub_adapter_v1`  
- No `documents.candidate_id` in expiry SoT  
- D4 and D8 consumer slot lists still include `documents`  
- D3 / D5–D7 / D9 consumer slot lists still omit `documents`  
- No second Adapter; no new public-contract id  
- No Document Hub reminder / task table  
- Shell `documents` nav ≠ D2 slot  
- Recruitment Application G4 path unchanged  
- Documents Foundation maturity stays 🔄  
- No OCR / e-sign / packages product unlock; no Catalog shape rewrite  

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| D3 / D5 / D6 / D7 / D9 `documents` bind | Later named E slices — **not** this PR |
| Document requests / packages / OCR / e-sign / approvals automation | Later E / Advanced |
| Hub control-center UI rebuild | Later E Workspace |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |
| Documents Foundation ✅ | Later E close (requests / packages still open) |
| Reopen G4 Recruitment Application | Forbidden |
| Reopen E3 D8 / E4 D4 / E5 column drop | Forbidden |

Do **not** mix mass bind, OCR, Billing, AI, or Forms product unlocks into E6.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Documents platform (ADR-009); Activity layer (ADR-012) owns reminders. Candidate host **places** only |
| 2 Exists? | Public contract + adapter + D2 slot + D4/D8 binds + Hub table + `expire_date` + Catalog `document.expired` yes; expiry seal **new** (this); Foundation **no** |
| 3 Adapter | Same `documents.hub_adapter_v1`; no second Adapter |
| 4 Boundary | Expiry / validity only. D4/D8 stay. No D3 / D5–D7 / D9 bind. No OCR/e-sign/packages. No Billing/AI. No Forms P3–P5. No G4 reopen |
| 5 Settings | Existing Manifest IA only; no new keys in E6 |
| 6 SoT | Document Hub validity field; Activity layer for reminders |
| 7 Events | Catalog `document.expired` (already named) — no new Catalog events this slice |
| 8 Requires | E5 ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282) · E4 ✅ · E3 ✅ · E2 ✅ · E1 ✅ · D4 ✅ · D8 ✅ · WCP COMPLETE [#274](https://github.com/igortatarynovich/HostFlow/pull/274) · ADR-009 / ADR-012 / ADR-014 / ADR-025 |
| 9 License | None new (Basic = upload/link/status/expiry; Advanced = existing addon flags) |
| 10 Public contract | No id bump; additive expiry read; no Catalog shape change; no L0 P-rule change |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- Product Track = this brief; Documents Platform E5 is closed (#282 / `702b922c`).  
- Operators / agents cannot treat D4 bind, column drop, CandidateCard, Shell `documents` nav, `next_action`, or Recruitment Application as this proof.  
- Feat locked until this brief merges.  
- D3 / D5–D7 / D9 remain unbound on `documents`; D4 / D8 stay bound; Forms P3–P5, OCR, packages, and Billing stay out of Product Track.  
- Documents Foundation stays 🔄.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Public contract | `docs/specs/architecture/documents-public-contract.md` — expiry read |
| Workflow | `docs/specs/workflows/document_expiry.md` — drop Candidate-FK SoT |
| Adapter | `document_hub_delivery_contract.py` — Hub `expires_at` already projected; keep as public |
| Engine | `document_expiry_engine.py` — Documents evaluation; no Hub task table |
| Gate | `backend/tests/platform/test_documents_e6_document_expiry_gate.py` |
| Pointers | queue / roadmap / AGENTS / maturity stay on E6 until E7 |

---

## DoD

- [x] Brief sealed with expiry decision / Activity-layer boundary / in/out + Original Goal → Completion Proof  
- [x] Queue + roadmap + AGENTS + maturity pointed at this brief (this docs PR)  
- [x] E5 marked **COMPLETE** with #282 / `702b922c`  
- [ ] Feat PR — expiry public-contract seal (**after** this brief)

---

## History

- 2026-08-23: E6 brief opened — Document expiry / validity. Product Track → this brief (feat locked). E5 ✅ [#282](https://github.com/igortatarynovich/HostFlow/pull/282) (`702b922c`). D3 / D5–D7 / D9 stay unbound. Foundation stays 🔄.
