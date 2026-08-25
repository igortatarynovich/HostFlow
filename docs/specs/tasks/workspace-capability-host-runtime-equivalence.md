# Workspace Capability — Host runtime-equivalence

**Status:** **COMPLETE** (2026-08-21) — parent program **COMPLETE**  
**Phase class:** platform  
**Branch (docs):** lands with [#273](https://github.com/igortatarynovich/HostFlow/pull/273) close-out  
**Branch (code):** `feat/workspace-capability-host-runtime-equivalence`  
**Named gate:** Workspace Capability Host Runtime Equivalence Gate (`tests/platform/test_workspace_capability_host_runtime_equivalence_gate.py`)  
**Parents:** [G1–G5 close-out](../gates/workspace-capability-platform-g1-g5-closeout.md) **PASS_WITH_CONSTRAINTS** · [COMPLETE](../gates/workspace-capability-platform-complete.md) · [Workspace Capability Platform Completion](workspace-capability-platform-completion.md) · [Goal Completion Gate](../gates/goal-completion-gate.md) · [UI constitution §3](../architecture/ui-constitution-v1.md)

> Corrective slice **inside** Workspace Capability Platform Completion.  
> Not a new proof-screen. Not a new widget. Not D10. Not Documents E2. Not ListWorkspace.  
> G4 on Recruitment Application **stays**. This slice does not replace it with Candidate.

---

## Original Goal → Completion Proof

This slice does **not** invent a weaker goal. It closes the residuals named in the [G1–G5 close-out](../gates/workspace-capability-platform-g1-g5-closeout.md).

**Problem this phase must permanently remove:**  
After #273, a new **Entity** screen can still be assembled without a runtime Capability Host, and Notes/Consent capability UI still knows transport-specific APIs (candidate notes; Lead RODO). Dual-host sameness is typed, not implemented twice. Owner boundaries leak into the host/page layer. That is the original G1 gap, not a new product.

**Completion proof (named consumer):**  
**Entity Workspace runtime host** — `EntityWorkspaceCapabilityHost` implements the same Capability Host Contract as `ApplicationWorkspaceCapabilityHost` (placement only; same regions / contribution protocol). **Candidate Entity Workspace** is the host-equivalence bind (not a second G4). Shared `notes` / `consent` owners hide transport: host, page, and capability UI do not import Lead API or page-local candidate-notes wiring.

```text
EntityWorkspaceCapabilityHost
  same contract as ApplicationWorkspaceCapabilityHost
  + Candidate Entity Workspace enters through the host (Shell = chrome adapter)
  + D2 communication/forms placed via contribution contract (`platform_slot`)
  + Notes owner facade (no candidate-notes API in host/page/capability UI)
  + Consent owner facade (no Lead API in host/page/capability UI)
  + zero new proof-screen
  + zero new widget class
  + Recruitment Application G4 bind remains
```

False close (reject): wrapping Entity chrome without the contract; unused host + green file test; Candidate-as-replacement-G4; stuffing `EntityWorkspace.tsx` with Notes/Consent semantics; a second Application proof; unlocking E2 because G4 already passed.

---

## In scope (feat)

1. `EntityWorkspaceCapabilityHost` — placement-only runtime for `entity_workspace`. Same contribution protocol. Must not import Notes/Consent/Recruitment/HR internals.  
2. **Candidate Entity Workspace host-equivalence bind** — the real Entity screen enters through `EntityWorkspaceCapabilityHost`. `EntityWorkspaceShell` is chrome adapter. D2 `communication` / `forms` are host-placed contributions, not page-level `EntityWorkspaceCompositionHost`. Not a second G4.  
3. Notes owner boundary — capability UI talks to a Notes facade/API owned by Notes, not `/candidates/:id/notes` from the widget. Pre-convert Recruitment Application notes go through notesOwner application comments transport.  
4. Consent owner boundary — capability UI talks to Compliance (`consent` + policy `lead_rodo_v1`). No `getLead` / `sendLeadRodoCompliance` / `markLeadRodoSourceProvided` in `ConsentCapability`, host, or page.  
5. Named-gate extensions: both host implementations exist; a real Entity consumer uses the host; capability UI files do not import Lead client modules.  
6. Goal Completion template in the feat PR. Final G1–G5 review: [COMPLETE](../gates/workspace-capability-platform-complete.md).

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Documents E2 feat | Unlocked by program COMPLETE; not started in this slice |
| New proof-screen / second G4 consumer | G4 already PASS |
| New widget class / Notes-Consent kit | D-class false close |
| Mass migration of Sales/Candidate inventory | After COMPLETE |
| ListWorkspace / `collection_orchestration` | Separate previous slice |
| Local Recruitment rail patch (`ApplicationRodoSection`) | Forbidden |
| D2 `documents` enable | E2 after COMPLETE |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Host owns placement only. Notes owns notes state. Compliance owns consent. Unchanged from the parent program. |
| 2 Exists? | This feat lands `EntityWorkspaceCapabilityHost` plus Notes/Consent owner facades. Typed catalogs already exist on #273. |
| 3 Adapter | Consent/Lead transport adapter belongs to Compliance, not the page. Notes storage adapter belongs to Notes. |
| 4 Boundary | No E2; no new G4 screen; no Application=Entity; no Shell-owns-semantics; no ListWorkspace mix-in |
| 5 Settings | None |
| 6 SoT | Parent brief remains host-contract SoT. This slice is runtime-equivalence + owner facades. |
| 7 Events | Existing events only |
| 8 Requires | G4 PASS on Recruitment Application · G1–G5 PASS_WITH_CONSTRAINTS |
| 9 License | Unchanged entitlement view |
| 10 Public contract | No Catalog Passport; D2 unchanged |

Does **not** amend L0.

---

## Goal Completion Gate — filled (program COMPLETE)

Formal record: [Workspace Capability Platform COMPLETE](../gates/workspace-capability-platform-complete.md).

```text
Goal Completion Gate — Workspace Capability host runtime-equivalence
G1 Original problem: After #273 a new Entity screen can still assemble without a runtime Capability Host, and Notes/Consent UI still know transport APIs.
G2 Now forbidden local implementations: Lead/candidate-notes imports in ConsentCapability / NotesCapability / host / G4 panel; wrapping Entity chrome without EntityWorkspaceCapabilityHost; Candidate-as-G4; ApplicationRodoSection as WCP; new proof-screen.
G3 Next consumer without new primitive? Yes. Documents E2 and a second host consumer use the same contribution protocol. No new host primitive.
G4 End-to-end proof (path + what it does not fork): Recruitment Application G4 bind remains. Candidate Entity Workspace is the entity_workspace runtime-equivalence bind (host + contribution contract), not a second proof-screen.
G5 Remaining allowed workarounds (owner / until): mass Sales/Candidate inventory migrate-on-touch after COMPLETE; D2 documents reserved until E2 feat; ListWorkspace separate. Recruitment application notes before candidate conversion go through notesOwner application comments transport.
Outcome: PASS
```

---

## History

- 2026-08-21: Opened after G1–G5 close-out **PASS_WITH_CONSTRAINTS**. G4 remains PASS. E2 stays locked until program COMPLETE.
- 2026-08-21: Feat branch opened — Entity host runtime + Notes/Consent owner facades. Named gate added. Program still **not COMPLETE**.
- 2026-08-21: Candidate Entity Workspace bound as host-equivalence consumer (`CandidateEntityWorkspacePanel`). G4 stays Recruitment Application. Program still **not COMPLETE**.
- 2026-08-21: Final G1–G5 **PASS**. Program **COMPLETE**. Record: [workspace-capability-platform-complete.md](../gates/workspace-capability-platform-complete.md). Documents E2 feat unlocked. This slice does not start E2.
