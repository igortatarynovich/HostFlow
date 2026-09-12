# Vacancy Recruitment Requirements SoT

**Status:** **Accepted** (L2 contract). Runtime **not this slice**.  
**Phase class:** product  
**Module owner:** **Recruitment**  
**Date:** 2026-09-11  
**Trusted base:** `feat/eso4-formalize`  
**Parents:** [ADR-042](../architecture/ADR-042-operator-host-boundary.md) · [RSO v1](recruitment-spine-orchestrator-v1.md) · [RPM-1](../architecture/requirement-policy-authority.md) · [Vacancy Overlay](entity-profile-vacancy-overlay-contract.md) · [Mapping Authority](mapping-authority.md) · [ADR-016](../architecture/ADR-016-requirement-evidence-document-separation.md)  
**Research (L3, not SoT):** [HRappka audit](../../analysis/hrappka-live-session-audit-brief.md) · [Inventory](../../analysis/vacancy-requirements-facts-inventory.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02**, **INV-01** (one SoT for vacancy recruitment requirements), **INV-16**. Does not open a tenth write of “must provide document type X?”. Does not merge Overlay into RPM. Does not schedule this as sequential-queue Active Product (unlock ≠ schedule). Does not wait on HR UI. Does not claim Full Spine PASS.

> Vacancy states what must be true of a person. The **system** answers fit / missing / not_fit. The operator gets **one** next action.  
> That answer is **not** three buttons. It does **not** replace **Подходит**. It does **not** rename «Создать кандидата».

---

## Operator question (one)

For this vacancy, **what must be true** of a person for Recruitment to treat them as a fit — and given **canonical facts**, is the current person **fit**, **missing**, or **not_fit** (with an explanation)?

No second question is this contract. Not “must they provide document type X?” (RPM-1). Not “source answer → field?” (Mapping Authority). Not Ready for employment / Transfer. Not Employment pathway.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
The operator either manufactures a Candidate (`Создать кандидата`) or builds a second **Profiling / matching parameters** layer (`lead_criteria_v1` / Candidate Requirements tab) to answer “does this driver fit the vacancy?” while requirements also live in rich text, packs, Overlay (no UI), and slots. Relabeling Create to Fits / Not fits / Missing would leave that problem in place.

**Completion proof (named consumer):**  
On an Application bound to a vacancy: the system shows **fit / missing / not_fit + explanation** from Vacancy Requirements × canonical facts. Exactly **one** next action: **Подходит** (existing Fits verb → Candidate) when fit; collect the named missing fact when missing; **Не подходит** / close when not_fit. Operator does not create matching parameters and does not get three outcome buttons.

**False close (reject):** renaming «Создать кандидата» to Fits / Not fits / Missing; three buttons for the three outcomes; growing `lead_criteria_v1` / Candidate Requirements tab; a new matching-parameters table; vacancy UI that writes RPM `tenant_delta`; evaluator that reads `field_answers` / Meta payload / `lead.normalized` as SoT; auto-Transfer from fit; auto Employment case from **Подходит**; treating Overlay Gate “not vacancy UI” as a forever ban on *any* Overlay producer; folding rates / contract subtype / permits into vacancy create; claiming Full Spine PASS; waiting on HR UI.

---

## Decision

### 1. Result ≠ verb

| | Role |
|--|------|
| **fit / missing / not_fit + explanation** | System result. Zero-choice input. |
| **Подходит** | Human boundary into Candidates ([ADR-042](../architecture/ADR-042-operator-host-boundary.md)). Allowed next action when result is **fit**. Side effect: create/find Candidate. Not Ready. Not Transfer. |
| **Не подходит** | Human close when result is **not_fit** (or operator override of an inbound we will not recruit). |
| Collect named fact | Only next action when result is **missing**. |
| «Создать кандидата» | Ritual. Stays **DELETE_UI** on the happy path (RSO). Not renamed. |

### 2. One write of vacancy recruitment requirements

Operator at vacancy create/edit states **role classification** (Entity Profile) and **what must be true** (short guided steps: required documents from catalog + fact predicates such as years CE / geo). That write persists as:

- profile bind on the vacancy (already exists), and  
- **Vacancy Overlay** delta (`entity_profile_vacancy_overlay.v1`) — tighten/add over Profile / Screening Pack  

Overlay Gate forbade vacancy UI **as that slice’s producer**. This brief is the **later Overlay operator write**. It does not mint a second overlay store.

| May write | Must not write |
|-----------|----------------|
| Overlay `delta[]` + `Vacancy.candidate_profile_id` | `lead_criteria_v1` / `lead_fit_evaluation_enabled_v1` as SoT |
| | RPM `tenant_delta` (that is “must provide type X?”) |
| | A new matching-parameters table |
| | Vacancy `description` as the requirements SoT |
| | `field_answers` as facts |

**RPM-1** remains the SoT for “must this candidate provide document type X?”. Vacancy Overlay may **tighten or add** document predicates for **this vacancy**; it must not fork pack identity and must not become a second pack catalog.

### 3. One evaluator, canonical facts only

```text
resolve_overlay(profile, vacancy) → merge(profile, screening_pack, overlay)
  × canonical facts (field registry / Mapping Authority)
  → { status: fit | missing | not_fit, explanation[], next_action }
```

Documents are **evidence** (ADR-016), not a second fact bag. Missing Hub evidence for a required overlay/pack document is **missing**, not `not_fit` by empty `normalized.documents[]`.

`lead_criteria_v1` is **leftover**. Do not extend `CandidateRequirementsTab`. Runtime fold/retire is a feat after this contract — not a parallel product.

Canonical **occupancy** is the sibling contract [`canonical-facts-completeness.md`](canonical-facts-completeness.md) (consumers-first matrix; one read path). This evaluator must not ship on `lead.normalized` as SoT. If occupancy cutover for the facts it evaluates is not ready, the evaluator slice **STOP** — it does not invent a fourth bag.

### 4. Application chrome

Show the result. Offer the one `next_action`. Do not host Transfer / Formalize / Started on the Application.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Recruitment writes vacancy requirements (profile + Overlay). Platform Overlay/RPM/Mapping stay their contracts. Employment does not write this. |
| 2 | Not a new Catalog capability. Overlay + field registry already exist. |
| 3 | No new adapter. Evaluator consumes Overlay merge + canonical facts. Shared Intake still the Mapping runtime caller. |
| 4 | Overlay remains Overlay. RPM remains RPM. No Hub packages table. No CL8. |
| 5 | Vacancy create steps are **this** operator write, not a Settings JSON page and not RPM-2. |
| 6 | SoT for the operator question = this file. Inventory is L3 context. |
| 7 | No new event family in this docs slice. |
| 8 | **Requires:** Overlay contract, RPM-1, Mapping consumers-read-facts-only. **Optional later:** facts completeness runtime. |
| 9 | No new licence. |
| 10 | Public contract additive. Does not rewrite L0. |

---

## Non-goals

- HR operator host / Full Spine operator PASS  
- Canonical facts occupancy cutover (sibling: [`canonical-facts-completeness.md`](canonical-facts-completeness.md) — contract sealed; runtime separate)  
- Growing A3 Candidate Requirements Workspace as vacancy policy  
- Mapping Authority UX  
- Employment missing / legalization / rates / contracts  

---

## Next

1. **This contract** — sealed here. Runtime not started.  
2. **Canonical Facts Completeness** — sealed: [`canonical-facts-completeness.md`](canonical-facts-completeness.md). Then **minimal runtime occupancy cutover** (decision-critical Driver CE set). Evaluator must not precede that cutover onto `lead.normalized`.  
3. Runtime feat: Overlay operator write at vacancy create + evaluator on Application + leftover `lead_criteria_v1` classified — **after** occupancy cutover. Not auto-scheduled here.
