# Lifecycle Identity L0 — Contract Seal

**Status:** **PARTIAL** — **LI-1 ✅ PASS** [#300](https://github.com/igortatarynovich/HostFlow/pull/300) (existence guard shipped after CL1 Gate); **LI-2…LI-4 QUEUED** and not scheduled. Recorded as a declared residual in the [unowned work register](../gates/v1-unowned-work-register.md). Consumed by [Hiring E2E](hiring-workflow-e2e.md) HE-2 (LI-1 only)  
**Phase class:** platform  
**Branch (docs):** this slice — ADR + L2 + queue linkage  
**Branch (code):** none until **CL1 Gate**; then `feat/lifecycle-identity-li1-…` for LI-1 only. LI-2+ stay in the Lifecycle ladder  
**Parents:** [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md) · [Lifecycle Identity Canon](../architecture/lifecycle-identity-canon.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Process Engine](../platform/process-engine.md) · [Module-owned pipelines P0](../architecture/module-owned-pipelines-p0.md) · [CL0](entity-field-composition-cl0-contract-seal.md)

> ADR-037 seals **stage existence vs company funnel vs Process Engine vs Handoff**. Funnel tables are configuration, not a catalog.  
> This brief does **not** become Product Track **now**. **Active Product Track remains CL0.** **LI-1** (existence/identity guard only) is the only Lifecycle slice between CL1 and CL2. Do not start LI-1 while CL0 holds Product Track. LI-2+ do **not** block CL2+.  
> This brief does **not** ship registry loader, funnel FK, Candidate UI cutover, Sales namespaces, HR handoff runtime, Documents E8, Forms P3–P5, or custom stages.

**Naming (do not collapse):** Lifecycle Identity is not Funnel Engine v2, not PE P7, not Country Registry, not Documents E8, not Entity D10, not a Recruitment rail patch. Registry ≠ funnel row. PE ≠ existence. Handoff ≠ FunnelTransition.

---

## Why this slice

Candidate, Lead, and Client stage lists are independent catalogs. Making `funnels` the SoT would copy the Country mistake: company rows would mint identities. PE `system_stages` almost look like a registry but lack `entity_kind` and still hold HR/client codes on Recruitment.

Without a sealed identity contract, the next pipeline PR will either (a) universalize FunnelStage.code, (b) union `stages.py` + Lead literals + FE client codes into a new stub canon, or (c) cut over UI onto the same forks.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After the **program** (not this docs PR alone), the question “does stage X exist for this module + entity kind?” has **one** producer — the Module Stage Registry. Company funnels only reference registered keys. Process Engine does not own existence. Cross-module moves are Handoff/Conversion. UI cannot mint identity. `FunnelStage.code`, `constants/stages.py`, `LeadStage`, Sales 3-stage UI, and `client_stage` literals cannot independently create a new identity.

**Completion proof (named consumer):**  
**Recruitment Candidate pipeline resolution** — `resolve_recruitment_funnel` + `GET /meta/stages` for `pipeline_type=candidate` (company-scoped). Proof is that every stage shown/assigned is a registered `recruitment.candidate.*` key (or a declared alias **to** that key). This brief does **not** choose Sales Inquiry, Client card, HR employee kanban, or Recruitment Application G4 as the first proof. Later Sales/HR slices have their own proofs.

```text
Module Stage Registry (existence)
  → Company Funnel Instance (subset + order + overlay)
  → Process Engine (transition / handoff rules on registry ids)
  → UI /meta/stages (projection)
```

**False close (reject):** funnel table as SoT; PE `module.code` as SoT without `entity_kind`; union of legacy lists as canon; Candidate UI cutover before existence test; custom `FunnelStage.code`; starting LI-1 as Product Track while CL0 is active; E8 / Forms P3; minting `sales.*` keys from Recruitment Lead codes.

---

## Queue placement (mandatory)

| Track | Role |
|-------|------|
| **Product (now)** | [RPM-1](requirement-policy-management.md) — the CL0…CL7 / LI-1 / DR1 / Overlay / E8 chain is **done**; see [queue locked sequence](sales-to-comms-sequential-queue.md) |
| **This program** | LI-1 shipped as the existence/identity guard ([#300](https://github.com/igortatarynovich/HostFlow/pull/300)). **LI-2…LI-4 remain queued**, are not scheduled, and do not block any v1 blocker. Hiring E2E consumes LI-1 only. |

Do not parallelize LI-1 with CL0. Do not expand LI-1 into Funnel/UI cutover. Do not let LI-2+ stall Field Composition CL2+.

---

## Sealed now (docs)

1. Identity = `{module_key}.{entity_kind}.{stage_key}`.  
2. Registry owns existence; Funnel owns company use; PE owns allow/happen; Handoff joins lifecycles.  
3. Custom stages **out** of first runtime.  
4. Namespaces declared: `recruitment.lead/candidate`, `sales.application/client`, `hr.employee`.  
5. ADR-002 HR-on-Candidate-axis = strangler encoding, not target.  
6. No new L0 invariant (no INV-18 without Architecture RFC).

---

## Queued runtime slices (LI-1 after CL1; LI-2+ later; one-at-a-time)

Order is locked. Do not skip to UI.

| # | Slice | In | Out |
|---|--------|----|-----|
| **LI-0** | Contract seal | This brief + ADR-037 + L2 | Runtime |
| **LI-1** | Existence guard | Architectural test: one producer for “is X registered?”; forbid new literals outside registry path | Funnel schema change, UI |
| **LI-2** | Registry contract for Recruitment Candidate (+ Lead namespace) | Manifest/loader; `entity_kind`; aliases point at keys; PE templates keyed by registry id | Sales/HR full catalogs; Candidate kanban rewrite |
| **LI-3** | `funnel_stages` → reference | Company overlay; validation entity funnel ⊇ only own keys | Cutover of all consumers |
| **LI-4** | Candidate consumer cutover | `/meta/stages` + create/PATCH use registry keys; `stages.py` becomes projection | Sales/Client/HR |
| **LI-5+** | Sales application/client; HR employee bind; drop Lead/Company projections | Separate briefs | Fleet unless declared |

LI-1 may be a **test-only / docs-enforced** slice (repo guard) before schema. That is still feat-queue work, not this PR.

---

## Locked: not in this program’s first feats

- Documents E8+ / Foundation close  
- Forms P3–P5  
- Entity D10 / ListWorkspace  
- Funnel as universal status for Fleet  
- Tenant custom stage registry  
- Rewriting L0 P-rules or adding INV-18  
- Handoff **runtime** gate (still [`hr-handoff-runtime-p0.md`](../architecture/hr-handoff-runtime-p0.md))

---

## Architecture review (brief)

Owner = module (identities) + platform Funnel primitive (shape) + PE (evaluation). Not a new sold capability. SoT = registry existence. Public contract later (LI-2). Checklist: [architecture-review-checklist.md](../architecture/architecture-review-checklist.md) answered on [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md).

---

## History

- 2026-08-23: Feat placement sealed — **LI-1 after CL1**, not after CL7 / not full Lifecycle. LI-2+ do not block CL2+.
- 2026-08-23: Brief opened. Canon sealed in ADR-037 + L2. Product Track stays CL0. No feat.
