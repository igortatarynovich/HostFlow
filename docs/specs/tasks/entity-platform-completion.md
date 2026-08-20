# Entity Platform Completion

**Status:** **IN PROGRESS** (docs — this brief)  
**Phase class:** platform  
**Branch (docs):** `docs/shared-ui-capabilities-contract-seal` (this worktree; rename on PR to `docs/entity-platform-completion` if the remote branch is created fresh)  
**Branch (code):** `feat/entity-platform-completion` (locked until this brief merges)  
**Parents:** [Goal Completion Gate](../gates/goal-completion-gate.md) · [Scope Completeness Audit](../gates/platform-scope-completeness-audit.md) · [D1](entity-workspace-d1-contract-seal.md)…[D9](entity-workspace-d9-services-order-cutover.md) ✅ (brief-complete, **goal-incomplete**) · [D2](entity-workspace-d2-composition-contract.md) · [UI constitution](../architecture/ui-constitution-v1.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [ADR-026](../architecture/ADR-026-capability-ownership.md) · [ADR-027](../architecture/ADR-027-capability-composition.md) · [E2](documents-platform-e2-public-contract.md) (brief ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); **feat locked**)

> D1–D9 closed **their** briefs. They did **not** close the original Entity Platform goal.  
> This slice restores that goal. It is **not** D10 (another consumer on the weak model).  
> It is **not** a Recruitment rail patch. It is **not** Documents E2.  
> Same-day draft **Shared UI Capabilities Contract Seal** (Notes+Consent, no registry) is **superseded** — it still accepted “shell = geometry, inner functions = module-owned.”

**Naming (do not collapse):** **Entity Platform** = Entity Shell (common capabilities) + Module Contribution Contract. D2 **surfaces** stay (`overview` / `timeline` / `communication` / `forms` / `documents` / `context-rail`). This slice adds the missing layer **inside** those surfaces. Do not invent a fifth shell. Do not collapse Shell `EntityWorkspaceSectionId` into D2 slot ids.

---

## Why this slice

Original goal (pre-decomposition):

```text
Entity Shell
  = one envelope for the entity
  + all common information and functions
Module contributions
  = default modules and paid modules add blocks
  through one composition / contribution contract
Shell does not know Recruitment or HR
  — it knows the capability contract
Same entity, same behaviour
  regardless of which modules are enabled
```

D substituted:

```text
Shell = geometry (header / nav / content / rail)
D2  = platform surfaces
D3–D9 = named consumers bind surfaces
Inner notes / consent / actions / rail widgets = module-owned
```

After that substitution, D1–D9 were locally consistent. The error was **above** the first brief.

[Scope audit](../gates/platform-scope-completeness-audit.md): **STOP** vs original D goal. Do not multiply pages on the weak model.

---

## Original Goal → Completion Proof

This section is the acceptance of the program. Deliverables (typed ids, registry module, named CI) are evidence **for** this test, not a substitute for it.

**Problem this phase must permanently remove:**  
After Entity Platform, a new entity or application screen **cannot** be assembled by inventing a local rail, notes, consent, actions, widgets, or page-specific composition of shared capabilities. Shell already holds the common entity surface; modules add only through the contribution contract. Default and paid modules use **the same** mechanism. D1–D9 named cutovers do **not** count as this proof.

**Completion proof (named consumer):**  
One shipped screen (feat brief picks **one**: Candidate Entity Workspace **or** Recruitment Application) assembled as:

```text
Entity Shell
  + shared entity capabilities (at least identity, status, notes, consent where applicable)
  + default module contributions
  + one optional/paid contribution
  + zero page-local composition of those blocks
```

Until that screen exists, Entity Platform is **brief-complete at most**, never **COMPLETE** vs the original goal. Contract feat alone cannot claim G4. Multiplying further entity/application pages, D10-on-weak-D2, or Documents E2 feat is forbidden until this proof.

**False close (reject):** shipping a Notes/Consent **component kit** that modules still compose locally; stuffing JSX into a page; binding another consumer to D2 slots; grepping `data-entity-workspace-slot`; treating D1–D9 ✅ as this program.

---

## Capability-based acceptance (normative)

This program is **not** a UI-component slice. Acceptance is capability-based. All of the following must be true before Entity Platform may be marked COMPLETE:

| # | Condition | Fail if |
|---|-----------|---------|
| 1 | **Shell contains common entity capabilities** (identity, status, ownership, contacts, notes, consent, timeline, tasks, documents surface, relations, common actions, audit) | Shell is only geometry; inner functions stay module-owned |
| 2 | **Modules attach only through one contribution contract** | Page imports module sections; parent callbacks are the SoT |
| 3 | **Default and paid modules use the same mechanism** | A paid module gets a special page or a second composition path |
| 4 | **placement / ordering / visibility / permissions / actions / state ownership** are standardized on the contribution | Those concerns live in page JSX or ad-hoc props |
| 5 | **Local analogues of a shared capability are forbidden** on new work | New Notes/Consent/rail/widget forks remain legal |
| 6 | **Inventory of legacy implementations + migration map** exists | Forks are unnamed; no map from local widget → `capability_id` |
| 7 | **At least one E2E consumer** is Shell + shared capabilities + module contributions **without** page-local composition | Proof is a widget, a slot bind, or a catalog freeze |

**Exit (Goal Completion Gate):** G1–G5 on **this original Entity Shell goal**, not on “D10 consumer bound” and not on “we shipped cards.”

---

## Locked layer model (restored)

```text
Entity Shell (chrome — D1, keep)
  identity/header · status · regions
D2 platform surfaces (keep catalog)
  overview · timeline · communication · forms · documents · context-rail
Common Entity Capabilities (this — missing layer)
  contacts · notes · consent/compliance · activity/timeline
  tasks/reminders · documents surface · relations
  ownership/assignee (common) · common actions · audit/context
Module Contributions (this)
  Recruitment: applications · vacancy · recruitment stage · recruiter actions
  HR: employment · contracts · medical · onboarding
  Fleet: vehicle/driver · assignments · operational data
  Paid module: same contract, not a special page
```

Shell **must not** import Recruitment or HR types. It resolves contributions by `capability_id` / `component_id` + placement/permissions.

D2 slot ids **do not** grow `notes` / `consent` / `rodo` this slice. Those are **common capabilities** placed **into** `overview` or `context-rail` (or a named shell region), not new platform surfaces. `documents` as D2 platform slot stays reserved until E2 **after** this program’s exit.

---

## Common Entity Capabilities (normative catalog — this brief)

| capability_id | Semantic owner | Shell region (default) | Notes |
|---------------|----------------|------------------------|-------|
| `identity` | Entity Shell | header | Already D1-ish |
| `status` | Entity Shell | header | Process/stage projection — not module stage picker |
| `ownership` | Entity Shell | header / rail | Common assignee; module-specific assignee is a contribution |
| `contacts` | Entity Shell | content / rail | Shared contact surface |
| `notes` | Application when on Application Workspace; Entity Shell when on Entity | overview / rail | One semantic Notes; storage may stay split until a later slice |
| `consent` | Compliance | overview / rail | **Not** named RODO. `lead_rodo_v1` is a **policy**. Forms keeps consent-at-capture (ADR-007) |
| `timeline` | Platform (D2 content slot) | timeline | Not a second Activity product |
| `tasks` | Activity / Shell | rail | Align ADR-012; do not mint a second planner |
| `documents` | Documents platform | D2 slot — **reserved until E2** | Shell nav `documents` ≠ D2 enable (D4 rule stays) |
| `relations` | Entity Shell | content | |
| `actions` | Entity Shell (common) + module contributions | header / decision | Common vs module actions distinguished by owner |
| `audit` | Entity Shell / Activity | context | |

**Not** common capabilities (stay module contributions or decision context): recruitment stage, vacancy bind, HR employment, fleet assignment, billing tab.

---

## Module Contribution Contract (normative fields)

A contribution is the only legal way to add a block to Entity Shell / Application Workspace entity envelope.

| Field | Meaning |
|-------|---------|
| `capability_id` | Common capability **or** module capability id (`recruitment.vacancy`, …) |
| `owner` | Semantic owner (platform or module) |
| `contributor` | Module / paid add-on that registers it |
| `consumer` | Entity type (`candidate` · `recruitment_application` · …) |
| `component_id` | Registered renderer id |
| `placement` | Region: `header` · `summary` · `overview` · `rail` · `decision` · D2 slot id |
| `ordering` | Stable rank within region |
| `visibility` | When shown (state / license / module enabled) |
| `permissions` | Who may see / act |
| `state_owner` | Where state lives |
| `actions` | Canonical actions |
| `events` | What it may emit/consume (no ad-hoc parent callbacks as SoT) |
| `license` | `default` · `optional` · `paid` |
| `conflicts` | What it may not duplicate (`capability_id` uniqueness per consumer+region unless override policy) |

**Conflict resolution (this brief):** one `capability_id` per consumer+region. A paid module **extends** via a new `capability_id` or an approved override record — it does not fork Notes/Consent.

**Registry:** `component_id` is part of the contract. Feat may land a **static typed registry** (id → renderer). A dynamic plugin loader is **not** required for the proof screen. Shipping the proof screen by stuffing JSX in the page **fails** this slice.

---

## Proof consumer (after contract feat)

One screen, Goal Completion Gate G4:

```text
Entity Shell
  + common capabilities (at least identity, status, notes, consent where applicable)
  + default module contributions
  + one optional/paid contribution
  and zero page-local composition of those blocks
```

Preferred proof: **Candidate Entity Workspace** (already D1 Shell + D4 D2 bind) **or** **Recruitment Application** if Application Workspace is the envelope that must share Notes/Consent with Sales. Feat brief will pick **one** — not both. Sales existing CallNotes/RODO = migrate-on-touch, not the proof’s blocking rewrite.

---

## Migration inventory (feat — required)

Feat lists current **local** blocks that violate the restored goal (non-exhaustive start):

| Local widget | Consumer | Maps toward |
|--------------|----------|-------------|
| `SalesInquiryCallNotesSection` | Sales Inquiry | `notes` |
| `SalesInquiryRodoSection` | Sales Inquiry | `consent` + policy `lead_rodo_v1` |
| `CandidateRodoSection` | Candidate | `consent` (transport ≠ capability) |
| Recruitment comments/RODO/stage (if present) | Recruitment Application | `notes` / `consent` / module `recruitment.stage` |
| ContextRail `vacancy` / `assignee` | Recruitment Application | module contributions, not common Notes |

Inventory ≠ migration of every row. Proof screen must not add a **new** row to this table.

---

## Locked principle

```text
Keep     D1 chrome, D2 surface catalog, D3–D9 consumer bindings as surface binds
Restore  common capabilities + contribution contract (this)
Prove    one screen without local composition
Then     Documents E2 feat
Never    D10-on-weak-model · ApplicationRodoSection-as-platform · registry-without-proof
```

This slice **must not**:

- start Documents E2 feat, OCR, D2 `documents` enable, Billing, AI  
- reopen D3–D9 as more surface cutovers  
- patch Recruitment/Sales rails as the definition of done  
- merge Forms consent-at-capture into `consent`  
- name the capability `rodo`  
- mass-migrate every inventory row  
- rewrite Decision Model wholesale (decision zone may **host** contributed actions)  
- reopen P3–P5, R6, C2.4, Catalog Notifications RFC  
- treat Shared UI Capabilities (superseded) as still Product Track  
- reduce this program to a Notes/Consent **component kit** or other UI widgets as definition of done  
- multiply new entity/application screens, rails, or D10 cutovers before the E2E proof  

---

## Ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **Scope audit + Goal Completion Gate** | Classify closed phases | [audit](../gates/platform-scope-completeness-audit.md) ✅ this PR |
| **Contract seal** | Common catalog + contribution fields | **this brief** (feat locked) |
| **Feat** | Typed registry + inventory + named gate | after brief |
| **Proof screen** | One E2E consumer; Goal Completion Gate G4 | locked until feat |
| **Documents E2** | Public contract / D2 `documents` enable | brief ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); feat after proof + G4 PASS or PASS_WITH_CONSTRAINTS that does **not** include “inner capabilities still module-owned” |

---

## Entity Platform Completion Gate (CI — after feat)

Named step: **Entity Platform Completion Gate**  
(`tests/platform/test_entity_platform_completion_gate.py`).

- Common capability ids frozen as in this brief  
- Contribution field set frozen  
- No `rodo` capability_id  
- Static registry module exists (or feat explicitly defers registry to proof slice **in the gate** — default: registry lands with feat)  
- D2 catalog unchanged; `documents` still reserved  
- Inventory file exists and lists Notes/Consent forks  
- D1–D9 / E1 gates stay green  
- E2 feat must not land  
- Goal Completion template filled in the feat PR description  

Proof-screen slice adds G4 evidence; contract feat alone is **not** phase COMPLETE.

---

## In scope (this docs PR)

1. This brief.  
2. [Goal Completion Gate](../gates/goal-completion-gate.md).  
3. [Scope Completeness Audit](../gates/platform-scope-completeness-audit.md).  
4. Queue / roadmap / AGENTS / maturity / UI constitution / Architecture Review Checklist point here.  
5. Lock E2 feat. Supersede Shared UI Capabilities draft.  
6. Feat locked until this brief merges.

## In scope (feat PR)

1. Named Entity Platform Completion Gate.  
2. Typed common capability ids + contribution fields + static `component_id` registry.  
3. Migration inventory markdown.  
4. Architecture Review 10 questions **and** Goal Completion G1–G5 in the PR body.  
5. **No** proof-screen rewrite unless the same PR can still stay one concern — default: proof is the **next** slice.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Proof screen E2E | Next slice after feat |
| Mass migration of inventory rows | After proof |
| D2 `documents` enable | E2 after this program |
| FormTemplate SoT / P3–P5 | Forms |
| R6 table-cutover | Acquisition |
| C2.4 / SMTP allowlist burn-down | Communication |
| Catalog Communication RFC | A2-F1 |
| Fifth JWT role | ADR-036 RFC |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI owns Shell + embedding; Compliance owns `consent` semantics; Application/Entity owns `notes` per consumer kind; modules own their contribution semantics |
| 2 Exists? | D1/D2 yes; common inner capabilities **no** (audit STOP) |
| 3 Adapter | None new this docs PR. Consent/Forms boundary: capture vs post-intake notice |
| 4 Boundary | No E2 feat; no D10; no Recruitment patch as done; no L0 Catalog rewrite |
| 5 Settings | No new Manifest keys this brief; `license` on contributions uses existing entitlement later |
| 6 SoT | This brief = common catalog + contribution fields; D2 remains surface SoT |
| 7 Events | Contribution `events` field reserved; no new Catalog events |
| 8 Requires | D1–D9 ✅ (as surface binds) · audit STOP · ADR-026/027 · UI constitution |
| 9 License | Paid contribution flag is contract-only this slice |
| 10 Public contract | Additive L2 Entity Platform contract; D2 catalog not rewritten; no Catalog Passport |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog. P-03 is the reason modules must contribute instead of cloning Notes/Consent.

---

## Goal Completion Gate (this program — preview)

| # | This program |
|---|--------------|
| **G1** | Entity Shell + common functions + one contribution contract; modules do not invent rails/notes/consent/widgets |
| **G2** | Forbidden: new module Notes/Consent/rail products; page-local composition of common capabilities |
| **G3** | Next entity/application screen uses registry + catalog only |
| **G4** | Proof screen (later slice) |
| **G5** | D2 `documents` still reserved; storage split for Notes allowed until named slice; D3–D9 surface binds may remain until migrate-on-touch |

Contract-seal feat **cannot** claim PASS on G4. It may claim brief-complete for the contract only.

---

## Acceptance

Capability-based (see table above). Checklist is **not** the proof:

- [ ] Brief merged (this file + Original Goal → Completion Proof)  
- [ ] Audit + Goal Completion Gate merged (same PR ok)  
- [ ] Named Entity Platform Completion Gate (feat)  
- [ ] Common catalog + contribution fields frozen  
- [ ] placement / ordering / visibility / permissions / actions / state ownership on the contract  
- [ ] Default and paid contributions share one mechanism  
- [ ] Local analogues of shared capabilities forbidden on new work  
- [ ] Legacy inventory + migration map  
- [ ] Registry is the only legal add-path for new common/module blocks on the proof (proof slice)  
- [ ] E2E proof consumer shipped (later slice) — **required for COMPLETE**  
- [ ] E2 feat stays locked until that COMPLETE  
- [ ] Shared UI Capabilities is not Product Track  

---

## DoD

- [ ] Original Entity Shell goal restored in writing (this file)  
- [ ] Queue + roadmap + AGENTS + constitution point here  
- [ ] D named “COMPLETE” qualified as brief-complete / goal-incomplete in audit  
- [ ] Feat + proof slices locked in order  

---

## History

- 2026-08-20: Shared UI Capabilities Contract Seal drafted (Notes+Consent, no registry), then **superseded** the same day — still accepted the weak D model.  
- 2026-08-20: Product Track → Entity Platform Completion (this). D1–D9 remain brief-complete. E2 feat locked. Audit STOP on original D goal.  
- 2026-08-20: Acceptance locked **capability-based** (not a UI kit). Mandatory brief section Original Goal → Completion Proof. E2E consumer required before COMPLETE; no further entity/application page multiplication until then.
