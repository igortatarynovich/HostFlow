# Workspace Capability Platform — Goal Completion G1–G5 close-out

**Status:** **PASS_WITH_CONSTRAINTS** (2026-08-21) — historical review of #273; program status **superseded** by [COMPLETE](workspace-capability-platform-complete.md)  
**Decision ID:** `WCP_G1_G5_PASS_WITH_CONSTRAINTS`  
**Type:** Goal Completion Gate application (not a product feature)  
**Parents:** [Goal Completion Gate](goal-completion-gate.md) · [Workspace Capability Platform Completion](../tasks/workspace-capability-platform-completion.md) · [Host runtime-equivalence slice](../tasks/workspace-capability-host-runtime-equivalence.md) · [Scope Completeness Audit](platform-scope-completeness-audit.md)  
**Evidence branch:** `feat/workspace-capability-platform-completion` @ `18f2a7aa` · [PR #273](https://github.com/igortatarynovich/HostFlow/pull/273)

> This is the Goal Completion review of [#273](https://github.com/igortatarynovich/HostFlow/pull/273).  
> It is **not** program COMPLETE. It does **not** unlock Documents E2 feat.  
> ListWorkspace Orchestration is a **separate** previous slice and is not this close-out.  
> **2026-08-21:** program status superseded by [final PASS / COMPLETE](workspace-capability-platform-complete.md) on [#274](https://github.com/igortatarynovich/HostFlow/pull/274). Keep this file as the #273 G1 residual record.

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `PASS_WITH_CONSTRAINTS` |
| **Date** | 2026-08-21 |
| **Program status** | **not COMPLETE** |
| **Next Product Track** | [Host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md) — second host + owner boundaries |
| **Not outcome** | Clean `PASS` / program COMPLETE · Documents E2 feat · a new proof-screen · a new widget kit · mixing ListWorkspace or a local Recruitment rail |

**Rationale:** G4 is proven structurally on Recruitment Application. Named CI **Workspace Capability Platform Completion Gate** is green (D1–D9 / E1 / Forms gates also green on that head). Remaining incompleteness is original-goal residue on **G1** (two hosts in runtime, not only in types) plus owner-boundary constraints named under G5. Those residuals **are** the original dual-host / owner-hides-transport problem — they do not silently swap the goal, and they **block** the next platform expansion that would multiply forks (Documents E2).

---

## Goal Completion Gate — Workspace Capability Platform Completion

G1 Original problem: After D, a new Entity **or** Application screen cannot be assembled by inventing a local rail, notes, consent, actions, widgets, or page-specific composition. The host places; capability owners own semantics/state; both constitution hosts implement the same Capability Host Contract without collapsing §3.2 / §3.3.

G2 Now forbidden local implementations: new local Notes/Consent/rail products; `ApplicationCommentsSection` / `ApplicationRodoSection` / `ApplicationStageSection` on the proof surface; parent JSX composing vacancy/assignee/notes/consent/stage; Shell as semantic owner; Application-as-Entity; RODO as the platform; treating ListWorkspace as this close-out.

G3 Next consumer without new primitive? **Yes for a new Application proof path** — kit + `ApplicationWorkspaceCapabilityHost` + contribution contract. **No for Entity Workspace** until the second host has a runtime implementation.

G4 End-to-end proof (path + what it does not fork): Recruitment Application — `ApplicationRecruitmentDetailPanel` → `ApplicationWorkspaceCapabilityHost` + `RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS`. Parent JSX does not own vacancy/assignee/notes/consent/stage composition. Named gate forbids return of local Notes/Consent/rail blocks. Candidate is not the proof.

G5 Remaining allowed workarounds (owner / until): dual-host typed-only until [host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md); Notes pre-convert stub + candidate notes storage until Notes owner boundary; Consent Lead API transport leakage until Compliance owner hides transport; D2 `documents` reserved; Sales/Candidate inventory migrate-on-touch; Action Canon / Event registry remain referenced.

Outcome: **PASS_WITH_CONSTRAINTS**

---

## Per-question verdict

| # | Verdict | Evidence | Residual |
|---|---------|----------|----------|
| **G1** | **PASS_WITH_CONSTRAINTS** | Typed contract declares `entity_workspace` and `application_workspace`. Application host runtime exists. | No `EntityWorkspaceCapabilityHost` in the #273 diff. Dual-host contract is proven as types, not as two host implementations. **Not full PASS.** |
| **G2** | **PASS** | Named gate forbids local Notes/Consent/rail imports on the proof surface. Panel no longer stuffs those blocks. | — |
| **G3** | **PASS** for a new Application proof path | New Application screen can assemble via host + contributions without a new primitive for that path. | Entity path still needs the second host runtime (G1). |
| **G4** | **PASS** | Structural bind on Recruitment Application. Named WCP gate SUCCESS on `18f2a7aa`. | Catalog rows / `data-` attributes alone were rejected; this is the shipped panel. |
| **G5** | **PASS_WITH_CONSTRAINTS** | Residuals named with owner and next slice. | Notes ownership transitional; Consent transport leakage; Entity host missing. |

Red `backend-ci` **Tests with coverage** on that head is **base-known** pytest debt (documents `status`, etc.). It is **not** a G4 fail. The named Workspace Capability Platform Completion Gate is green.

---

## Named constraints (G1 / G5)

These are original-goal leftovers. They are **not** a silent goal swap. The next layer may proceed **only** for work that closes them. It may **not** proceed for Documents E2.

1. **Second host runtime.** `entity_workspace` must implement the same Capability Host Contract in code (`EntityWorkspaceCapabilityHost`), not only in `WORKSPACE_CAPABILITY_HOST_IDS`.  
2. **Notes owner boundary.** Shared `notes` must not depend on the page knowing candidate-notes transport. Pre-convert stub is an allowed transitional constraint until the next slice, not proof of a fully independent Notes owner.  
3. **Consent owner boundary.** `capability_id` is `consent`, owner is Compliance, policy remains `lead_rodo_v1`. The capability UI must stop knowing Lead API (`getLead` / `sendLeadRodoCompliance` / `markLeadRodoSourceProvided`). Transport stays behind the Compliance owner.

---

## What this close-out does not do

| Forbidden reading | Why |
|-------------------|-----|
| Program **COMPLETE** | G1 is not full PASS |
| Unlock Documents E2 feat | G1 residual is the original dual-host gap; E2 would multiply screens on a still-weak host model |
| Start a new proof-screen | G4 already passed on Recruitment Application |
| Start a new widget / Notes-Consent kit | That was the D-class false close |
| Patch Recruitment rail on another branch as WCP | Local `ApplicationRodoSection` stuffing fails G2/G4 |
| Fold ListWorkspace into this close-out | Separate previous slice (`collection_orchestration`) |
| Treat Candidate Entity Workspace as G4 | False PASS; locked against |

---

## Next slice (locked)

[Host runtime-equivalence](../tasks/workspace-capability-host-runtime-equivalence.md):

- Entity Workspace implements the same Capability Host Contract at runtime.  
- Notes / Consent stop leaking transport-specific API into host / page / capability UI.  
- Then a **final** Goal Completion Gate can claim COMPLETE.  
- **Then** Documents E2 feat.

Not a new proof-screen. Not a new widget. Not ListWorkspace.

---

## History

- 2026-08-21: Goal Completion review of [#273](https://github.com/igortatarynovich/HostFlow/pull/273) @ `18f2a7aa`. Outcome **PASS_WITH_CONSTRAINTS**. G4 PASS. G1 not full PASS. E2 remains locked.
- 2026-08-21: Program status superseded by [COMPLETE](workspace-capability-platform-complete.md) after host runtime-equivalence on [#274](https://github.com/igortatarynovich/HostFlow/pull/274). This file stays the #273 review.
