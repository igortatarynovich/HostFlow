# ADR-022 Phase 2 — Sales-only Capability Flow (F3-B-10)

**Status:** **NORMATIVE (L2 — Product workflow canon)**  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `8224cc7a`  
**Product register:** F3-B-10  
**Owner:** Sales (commercial result) · Flights (destination / dispatch provenance) · Forms Platform (form surface only)  
**Parents:** [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) · [ADR-021](../architecture/ADR-021-unified-intake-resolution-model.md) · [ADR-023](../architecture/ADR-023-recruitment-sales-module-separation.md) · [ADR-020](../architecture/ADR-020-sales-to-engagement-commercial-model.md) · [Flights R3.5](../tasks/intake-r35-flights-dispatch-boundary.md) · [INV-16 Decision Priority](../architecture/decision-priority-rule.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)  
**Kickoff:** [`../tasks/adr022-phase2-kickoff.md`](../tasks/adr022-phase2-kickoff.md)  
**Requirements scrapbook (not implementation):** [`../tasks/adr022-product-b-local-commits-audit.md`](../tasks/adr022-product-b-local-commits-audit.md)

> This document is the **canonical docs-slice** for ADR-022 Phase 2 on the **current** architecture.  
> Historical commits on `feat/adr022-intake-policy-phase1-backend` are a **requirements source only** — never a port base.  
> **No** shared Sales/Recruitment Capability Wizard. **No** Lead as Sales SoT. **No** hidden fallback.

---

## 1. Purpose

Define the Sales-only product spine and the contracts between stages so implementation PRs (convert mapping first) cannot reintroduce:

- cross-module Capability catalogs;
- Lead-centric review / workspace SoT;
- convert that re-routes intake;
- silent attach / silent destination defaults.

---

## 2. Canonical spine

```text
SalesInquiry
  → Flights destination
  → Capability (Sales-owned)
  → Review (ambiguous / unresolved match)
  → Convert (Sales-owned result)
  → Traceability (immutable lineage)
```

| Stage | Meaning |
|-------|---------|
| **SalesInquiry** | Sole Sales-owned intake / commercial Application result after Flights handoff |
| **Flights destination** | Ownership of `route_intent`, destination contract, dispatch provenance |
| **Capability** | Sales commercial direction (e.g. targeted advertising) — evaluated only in Sales context |
| **Review** | SalesInquiry-owned signal when match is unresolved or ambiguous |
| **Convert** | Maps **confirmed** inquiry + decision → Sales-owned result (`ClientAccount` and related) |
| **Traceability** | Immutable lineage: SalesInquiry ↔ Flights dispatch refs ↔ result |

**Canonical chain for submit (platform):**

```text
Forms Platform → Flights (destination + dispatch) → Sales intake port → SalesInquiry
```

Not: Forms → Sales handler. Not: Forms → Recruitment. Not: Forms → shared wizard.

---

## 3. Normative product rules

1. **SalesInquiry** is the only Sales-owned ingress object for this flow.  
2. **Flights** owns destination resolution and dispatch provenance.  
3. **Capability** is determined only in **Sales** context for this spine.  
4. **Recruitment Capability does not participate.**  
5. **Lead is not SoT** — optional ADR-021 Phase 1 transport facade only; UI/API SoT paths use SalesInquiry.  
6. Ambiguous / unresolved match creates a **SalesInquiry-owned review signal** (not `Lead.stage` as long-term SoT).  
7. **Convert does not re-route intake** — no second Flights dispatch, no policy rematch as part of convert.  
8. Convert uses **already confirmed** destination / result context.  
9. Traceability links original SalesInquiry, Flights dispatch (opaque refs), and final Sales-owned result.  
10. No shared Sales/Recruitment wizard; no hidden fallback; unresolved and ambiguous states are **fail-closed**.

---

## 4. Contracts

### 4.1 Contract matrix

| Contract | Owner | Input | Output |
|----------|-------|-------|--------|
| **Destination resolution** | Flights | SalesInquiry intake context (form publication / invite attribution, Entity Profile, purpose, submission policy snapshot) | Destination contract (`route_intent=sales_inquiry`, dispatcher id, provenance handles) |
| **Capability evaluation** | Sales | SalesInquiry + destination context | Capability decision (allowed Sales capability codes only) |
| **Ambiguous review signal** | Sales | Unresolved / ambiguous match outcome | Review-required state on SalesInquiry |
| **Convert mapping** | Sales | Confirmed inquiry + operator/system decision + questionnaire field projections | Sales-owned result (`ClientAccount` + mapped commercial fields) |
| **Traceability** | Sales + opaque Flights reference | Source SalesInquiry id, Flights dispatch/provenance refs, result ids | Immutable lineage record (append-only; no rewrite of history) |

### 4.2 Destination resolution (Flights)

| Field | Rule |
|-------|------|
| Owner | Acquisition / Flights |
| Input | Intake context from Forms (publication or invite) + Entity Profile axes from ADR-022 |
| Output | Destination contract consumed by Sales intake port |
| Forbidden | Sales inventing `route_intent`; Recruitment destination on Sales form; silent default to another module |

### 4.3 Capability evaluation (Sales)

| Field | Rule |
|-------|------|
| Owner | Sales |
| Input | SalesInquiry + confirmed destination context |
| Output | Capability decision within Sales catalog only (Phase 2: Product B / targeted-advertising class) |
| Forbidden | Mixing Recruitment Capability codes; platform Entity Profile knobs as the manager’s primary “direction” UI; cross-module Capability menu |

### 4.4 Ambiguous review signal (Sales)

| Field | Rule |
|-------|------|
| Owner | Sales (projected onto SalesInquiry) |
| Input | Match outcomes: `possible` / `conflict` / `multiple` / unresolved destination or identity |
| Output | Explicit **review-required** state; no auto-attach; no auto-convert |
| Forbidden | Treating `Lead.stage = review_required` as long-term SoT; auto-picking among candidates; silent drop of ambiguity |

### 4.5 Convert mapping (Sales)

| Field | Rule |
|-------|------|
| Owner | Sales |
| Input | Confirmed SalesInquiry + confirmed destination/result context + questionnaire projections (industry, budget, notes, …) |
| Output | Sales-owned result (`ClientAccount` per ADR-020 / Stage 1A contract) with mapped fields |
| Forbidden | Re-running Flights dispatch; rematching ClientAccount/Candidate at convert; converting while review-required unresolved |

### 4.6 Traceability (Sales + Flights refs)

| Field | Rule |
|-------|------|
| Owner | Sales owns the lineage view; Flights refs remain opaque tokens / provenance ids |
| Input | `sales_inquiry_id`, Flights dispatch/provenance refs, form/publication/invite ids, `client_account_id` (result) |
| Output | Immutable lineage usable from SalesInquiry and ClientAccount surfaces |
| Forbidden | Rewriting lineage; Lead CRM detail as primary SoT path; inventing Recruitment links |

---

## 5. Ownership

| Object / decision | Owner | Non-owner |
|-------------------|-------|-----------|
| Form Definition / presentation / publication surface | Forms Platform | Sales, Recruitment |
| Destination, `route_intent`, dispatch, unresolved disposition at transport | Flights | Sales, Recruitment |
| SalesInquiry lifecycle & inbox | Sales | Flights (after handoff), Recruitment |
| Sales Capability decision | Sales | Recruitment, Forms |
| Review-required signal | Sales (on SalesInquiry) | Lead transport as SoT |
| Convert → ClientAccount | Sales | Flights, Recruitment |
| Recruitment Application / Candidate Capability | Recruitment | **Out of this spine** |
| Lead row | Transport facade (ADR-021 Phase 1) | Must not be product SoT |

---

## 6. Invariants

1. **INV-SI-01** — One Sales form publication / invite path resolves to **exactly one** Flights destination for Sales (`sales_inquiry`). Missing destination → fail-closed.  
2. **INV-SI-02** — SalesInquiry is created/attached only via Sales intake port after Flights handoff.  
3. **INV-SI-03** — Capability codes in this flow ⊆ Sales Capability set; Recruitment codes are invalid input.  
4. **INV-SI-04** — Match never targets ClientAccount or Candidate directly at submit (ADR-022 / ADR-021).  
5. **INV-SI-05** — Ambiguous / unresolved match ⇒ review-required; convert blocked.  
6. **INV-SI-06** — Convert does not call destination resolution or intake policy again.  
7. **INV-SI-07** — Traceability entries are append-only; source/result refs never silently swapped.  
8. **INV-SI-08** — No hidden fallback to Recruitment, Lead CRM SoT, or “best guess” attach.  
9. **INV-SI-09** — Personal invite uses forced `attach` to known SalesInquiry; public uses `match_or_create` with fail-closed ambiguity.  
10. **INV-SI-10** — Module independence (L0 / INV-16): Sales ↛ Recruitment internals; Flights ↛ Sales ORM.

---

## 7. State transitions

```text
[Forms submit]
    → Flights destination resolution
         ├─ FAIL (missing / invalid destination) → rejected / held (fail-closed; no SalesInquiry create)
         └─ OK → Sales intake port
              → match_or_create | attach
                   ├─ strong_single / known attach → SalesInquiry active (open)
                   ├─ zero match → SalesInquiry created (open)
                   └─ ambiguous | unresolved → SalesInquiry + review-required
                                              (no auto-attach; convert blocked)

[SalesInquiry open, not review-required]
    → Capability evaluation (Sales)
         ├─ valid Sales capability → capability decided
         └─ invalid / Recruitment / unknown → fail-closed

[capability decided + inquiry confirmed]
    → Convert mapping
         ├─ success → ClientAccount (Sales result) + lineage append
         └─ missing confirmed context / still review-required → refuse convert

[any terminal Sales result]
    → Traceability lineage complete (inquiry ↔ flights refs ↔ result)
```

| From | Event | To | Guard |
|------|-------|----|-------|
| (none) | Flights destination OK + create | SalesInquiry `open` | Destination = Sales |
| (none) | Flights destination OK + strong attach | Existing SalesInquiry `open` | Match matrix satisfied |
| SalesInquiry `open` | Ambiguous match recorded | `review-required` | Fail-closed; no attach |
| `review-required` | Manager resolves match | `open` (confirmed) | Explicit decision |
| `open` + capability decided | Convert | Result linked | Not review-required; destination confirmed |
| Any | Convert without confirmed context | **No transition** | Refuse |

Lead lifecycle fields, if present, are **projections/facade**, not authoritative for these transitions.

---

## 8. Fail-closed cases

| Case | Required behaviour |
|------|--------------------|
| Destination missing / not Sales | Do not create SalesInquiry; do not invent Recruitment path |
| Recruitment Capability code on Sales create | Reject |
| Ambiguous public match | Review-required; no auto-attach; no convert |
| Partial identifiers (email-only / phone-only) where matrix requires both | No strong attach |
| Convert while review-required | Refuse |
| Convert that would re-dispatch Flights or rematch intake | Refuse |
| Traceability write without source or result ref | Refuse |
| Shared Sales+Recruitment wizard entry | Forbidden (process + product fail) |
| Silent fallback to Lead CRM as SoT UI | Forbidden |
| Matching ClientAccount / Candidate at submit | Forbidden |

---

## 9. Idempotency

| Operation | Key / rule |
|-----------|------------|
| Public submit | Submission idempotency key (ADR-022 Phase 1); append-only submissions |
| Invite attach | Forced attach to known `application_id` / SalesInquiry; re-submit appends |
| Flights dispatch | Dispatch / provenance idempotency per R3.5 / R5 ledger |
| Convert | Idempotent on confirmed SalesInquiry → existing ClientAccount link (Stage 1A unique guard on source) |
| Traceability append | Same logical event does not duplicate contradictory lineage edges |

Replaying a successful convert must return the same Sales-owned result identity, not create a second ClientAccount for the same confirmed inquiry.

---

## 10. Audit / traceability

Minimum lineage fields (logical; storage is implementation):

| Ref | Required |
|-----|----------|
| `tenant_id` | ✓ |
| `sales_inquiry_id` | ✓ |
| Flights dispatch / provenance opaque refs | ✓ after handoff |
| `form_id` + publication or invite id | ✓ |
| `effective_submission_policy` snapshot | ✓ at submit |
| `match_result` (when matching ran) | ✓ |
| `capability_code` (when decided) | ✓ |
| `client_account_id` (after convert) | ✓ |
| Actor / decision timestamps for review & convert | ✓ |

Audit must answer: *which SalesInquiry, which Flights dispatch, which Capability, which result — without reading Recruitment objects.*

---

## 11. Out of scope (this docs-slice and Phase 2 Sales spine)

- Recruitment Capability create / wizard / catalog UI  
- Shared Sales+Recruitment Capability Wizard (any form)  
- Lead CRM as long-term Sales workspace SoT  
- Re-implementing ADR-022 Phase 1 `match_or_create` / `attach` (already on integration)  
- Convert implementation code (next PR: convert mapping only)  
- Create-card UI / post-save card (later thin PR)  
- Traceability UI panel (later thin PR)  
- Quote / ServiceOrder / billing (ADR-020 later stages)  
- Intake Review Queue UI as a separate platform product (ADR-021 Phase 3)  
- Cherry-pick / rebase of `feat/adr022-intake-policy-phase1-backend`

---

## 12. Acceptance criteria (docs-slice)

- [x] Spine documented without references to an old shared wizard as implementation base  
- [x] Contract matrix filled for Destination, Capability, Review, Convert, Traceability  
- [x] Ownership, invariants, state transitions, fail-closed, idempotency, audit sections present  
- [x] Lead explicitly non-SoT; Recruitment Capability excluded  
- [x] Convert explicitly non-routing  
- [x] Historical ADR022 commits mapped to requirements without porting code  
- [x] Workflow registered in [`index.md`](index.md)  
- [x] Next implementation PR = **Convert mapping only** (no wizard, no UI shell) → [`../tasks/sales-questionnaire-convert-mapping.md`](../tasks/sales-questionnaire-convert-mapping.md)
- [x] After Convert: **Review implementation** → [`../tasks/sales-ambiguous-match-review.md`](../tasks/sales-ambiguous-match-review.md)
- [ ] After Review: **Traceability implementation** (no UI)

---

## 13. Migration path from Phase 1

| Phase 1 (on integration) | Phase 2 stance |
|--------------------------|----------------|
| ADR-022 purpose / policy / `match_or_create` / `attach` + tests | **Keep** — foundation; do not re-open |
| Flights R3.5 dispatch + Sales intake port | **Keep** — destination ownership |
| Sales questionnaire invite + Communication Pipeline binder | **Keep** — send path |
| Lead transport facade | **Keep as facade only**; product SoT → SalesInquiry |
| Missing F3-B-10 Flow Spec | **This document** |
| Missing convert field mapping from questionnaire | **Next PR** (`feat/sales-questionnaire-convert-mapping`) |
| Ambiguous match → Lead.stage style signal | **Redesign** → SalesInquiry review signal |
| Capability-first create UI | **Later** Sales-only create card (not shared wizard) |
| Traceability panel on Lead paths | **Later** SalesInquiry / ClientAccount paths |

Order after this docs PR:

1. Convert mapping implementation  
2. Ambiguous-match review on SalesInquiry  
3. Traceability implementation (**no UI**)  
4. Sales-only Capability create card (UI last)  

---

## 14. Mapping of historical ADR022 commits → requirements (no implementation port)

Source: [`adr022-product-b-local-commits-audit.md`](../tasks/adr022-product-b-local-commits-audit.md).  
Branch `feat/adr022-intake-policy-phase1-backend` must **not** be checked out as a base.

| Commit | Class | Requirement absorbed here | Must not port |
|--------|-------|---------------------------|---------------|
| `d7c41aef` | Discard | None (obsolete G-B-05 doc path) | File revival |
| `b34aaa4a` | Redesign → docs | Capability-first mental model; answers land in Sales inquiries | TenantLeadForm-as-product-SoT wording as canon |
| `fc15643c` | Redesign → docs | Create flow ends at a working tool (send/copy/preview) — **later UI PR** | Platform jargon / Lead-forms SoT |
| `7dac9ada` | Redesign | Sales-only Capability create (intent only) | Shared Sales+Recruitment catalog wizard code |
| `08a766ea` | Redesign → docs | Usage modes (invite vs public); convert mapping table; destination/compatibility | Any path that skips Flights |
| `21ab01c1` | Port selective + redesign | Convert field mapping + review + traceability **as requirements** | Lead.stage SoT; Lead CRM primary traceability routes; wholesale cherry-pick |

---

## 15. Next implementation step

**Immediately after merge of this docs-slice:**

```text
feat/sales-questionnaire-convert-mapping
```

Scope: Convert mapping only — see [`../tasks/sales-questionnaire-convert-mapping.md`](../tasks/sales-questionnaire-convert-mapping.md).

**Then:** Review implementation → Traceability → Capability UI (last).

**Not in Convert PR:** wizard, Capability create UI, Recruitment anything, Flights changes, mixed integrity fixes.

Start gate: `make repo-health` on integration tip (Repository Operational Canon).
