# Workspace Capability Platform Completion

**Status:** **COMPLETE** (final G1–G5 2026-08-21) — [record](../gates/workspace-capability-platform-complete.md)  
**Phase class:** platform  
**Branch (docs):** `docs/shared-ui-capabilities-contract-seal` ✅ [#272](https://github.com/igortatarynovich/HostFlow/pull/272)  
**Branch (code):** `feat/workspace-capability-platform-completion` · [PR #273](https://github.com/igortatarynovich/HostFlow/pull/273)  
**Close-out:** [G1–G5 #273](../gates/workspace-capability-platform-g1-g5-closeout.md) · [COMPLETE](../gates/workspace-capability-platform-complete.md)  
**Equivalence slice:** [Host runtime-equivalence](workspace-capability-host-runtime-equivalence.md) ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274)  
**Parents:** [Goal Completion Gate](../gates/goal-completion-gate.md) · [Scope Completeness Audit](../gates/platform-scope-completeness-audit.md) · [UI constitution §3](../architecture/ui-constitution-v1.md) · [D1](entity-workspace-d1-contract-seal.md)…[D9](entity-workspace-d9-services-order-cutover.md) ✅ (brief-complete, **goal-incomplete**) · [D2](entity-workspace-d2-composition-contract.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [ADR-026](../architecture/ADR-026-capability-ownership.md) · [ADR-027](../architecture/ADR-027-capability-composition.md) · [ADR-036](../architecture/ADR-036-four-trust-roles-rbac.md) · [E2](documents-platform-e2-public-contract.md) (brief ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); **feat unlocked** after program COMPLETE)

> Previous same-day title **Entity Platform Completion** is **superseded in place** (this file).  
> The original goal still holds. The wrong next abstraction would have been: Entity Shell **owns** Notes/Consent/Tasks/Documents, and Application Workspace is just another Entity envelope.  
> This slice seals a **Capability Host Contract** on top of the **platform kit** (data types, fields, primitives, widgets, tables). Entity Workspace and Application Workspace stay **distinct** constitution types (§3.2 vs §3.3). Both **implement the same host contract**.  
> Not D10. Not a Recruitment rail patch. Not Documents E2. Not a Notes/Consent-only kit. Constitution §0: there are no screens; there are compositions of the kit.

**Naming (do not collapse):**

| Term | Meaning |
|------|---------|
| **Kit** | Data types, fields, UI primitives, widgets, tables. Screens are assembled **only** from this. **This** slice seals the typed catalogs as references to existing canons (Field Registry, PRIMITIVES_V1, TABLE_V1). |
| **Capability Host Contract** | Shared protocol: host → regions → contributions. **This** slice. |
| **Entity Workspace** | Constitution §3.3 host (converted object). Implements the contract. |
| **Application Workspace** | Constitution §3.2 host (inbound before conversion). Implements the contract. **Not** an Entity Workspace. |
| **D2 surfaces** | `overview` · `timeline` · `communication` · `forms` · `documents` · `context-rail` — catalog stays. |
| **Contribution** | Only legal add-path onto a host region. Same protocol for shell primitives, shared capabilities, platform surfaces, and module blocks. |

Do not invent a fifth shell. Do not collapse Shell `EntityWorkspaceSectionId` into D2 slot ids. Do not fold Application Workspace into Entity Shell.

---

## Why this slice

Original goal (pre-decomposition):

```text
Platform kit (defined first)
  data types → fields → primitives → widgets → tables
Then
  One envelope for the object
  + kit widgets placed by the host
Default and paid modules add blocks
  through one composition / contribution contract
The host does not know Recruitment or HR
  — it knows the kit + capability contract
Same object, same behaviour
  regardless of which modules are enabled
```

D substituted: Shell = geometry; inner functions stay module-owned.

A **second** substitution this brief must not make:

```text
Entity Shell owns Notes, Consent, Tasks, Documents semantics
Application Workspace = Entity Workspace with a different route
one flat "common entity capabilities" catalog
```

That would recreate a 3000-line `EntityWorkspace.tsx` monolith and erase constitution §3.

[Scope audit](../gates/platform-scope-completeness-audit.md): **STOP** vs original D goal. Do not multiply pages on the weak model.

---

## Original Goal → Completion Proof

This section is the acceptance of the program. Deliverables (typed ids, registry module, named CI) are evidence **for** this test, not a substitute for it.

**Problem this phase must permanently remove:**  
After this program, a new Entity **or** Application screen **cannot** be assembled by inventing a local data type, field, primitive, widget, table, rail, notes, consent, actions, or page-specific composition. The **kit** is the only legal substrate (Field Registry types/fields, PRIMITIVES_V1, TABLE_V1, widget classes). The **host** places regions; **capability owners** own semantics and state; modules add only through the Capability Host Contract. Default and paid modules use **the same** mechanism. Application Workspace stays Application Workspace. D1–D9 named cutovers do **not** count as this proof. A Notes/Consent/RODO widget kit is **not** this proof.

**Completion proof (named consumer):**  
**Recruitment Application** — Application Workspace host. Locked; feat does **not** choose Candidate instead.

```text
ApplicationWorkspace host
  assembled only from the platform kit
    (data types, Field Registry fields, PRIMITIVES_V1, widgets, TABLE_V1)
  + shell primitives (identity, status as owner projection, ownership region)
  + shared widgets (including Notes and Consent — not only those)
  + Recruitment contributions: stage / vacancy / assignee
  + one optional/paid contribution via the same contract
  + zero page-local types / fields / primitives / widgets / tables / rail stuffing
```

Candidate Entity Workspace is **not** the proof. It is closer to D4 and can yield a false PASS.

G4 bind is the Recruitment Application on Application Workspace (`ApplicationWorkspaceCapabilityHost` + `RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS`). Contract-only commits cannot claim G4; this feat did bind the proof screen. Goal Completion review (2026-08-21): **G4 PASS**. Intermediate G1–G5 of #273: **PASS_WITH_CONSTRAINTS** (second host runtime missing). Final review of [#274](https://github.com/igortatarynovich/HostFlow/pull/274): **PASS** — program **COMPLETE**. Documents E2 feat is unlocked. ListWorkspace is a separate previous slice and is not this close-out.

**False close (reject):** Entity Shell as semantic owner of Notes/Consent; Application folded into Entity; Notes/Consent/RODO **as the whole platform**; kit that modules still compose locally in parent JSX; stuffing JSX; Candidate-as-proof; D2 slot bind; treating D1–D9 ✅ as this program; minting a second Field Registry / primitives list / table standard.

---

## Capability-based acceptance (normative)

This program is **not** “ship Notes and Consent widgets” and **not** “Entity Shell owns everything common.” COMPLETE only if all of the following are true:

| # | Condition | Fail if |
|---|-----------|---------|
| 1 | **Capability Host Contract** is the only add-path onto Entity Workspace **and** Application Workspace | Page-local composition; Application treated as Entity |
| 2 | **Host owns placement/composition only.** Capability owner owns semantics/state | `EntityWorkspace.tsx` imports Notes/Consent/Tasks/Documents business logic |
| 3 | **Four classes** stay distinct (shell primitives / shared capabilities / platform surfaces / module contributions) under one placement protocol | One flat catalog; D2 surfaces renamed as “entity capabilities” |
| 4 | **Default and paid** modules use the same contribution mechanism | Paid module gets a special page or a second composition path |
| 5 | **permissions / actions / events / license** on a contribution are **references** to existing canons, not local vocabularies | Second RBAC, second Actions layer, second Event registry, new license SoT |
| 6 | **status** is a host region + **owner projection**. No global status enum | Candidate/Application/Employee/Vacancy/Company forced onto one enum |
| 7 | **Local analogues** of a kit piece are forbidden on new work | New data type / field / primitive / widget / table / Notes/Consent/rail forks remain legal |
| 8 | **Inventory of legacy implementations + migration map** exists | Forks unnamed; no map local widget → kit id / `capability_id` |
| 9 | **E2E proof** is Recruitment Application assembled from the kit | Proof is Candidate, a RODO widget, a slot bind, or a catalog freeze |

**Exit (Goal Completion Gate):** G1–G5 on **this** Original Goal section, not on “D10 consumer bound” and not on “we shipped cards.”

---

## Locked layer model

```text
Platform kit (this feat seals typed catalogs; SoT stays on existing canons)
  data types     → Field Registry §4
  fields         → Field Registry + Entity Profile (no copy)
  ui primitives  → PRIMITIVES_V1
  widgets        → compositions of primitives + fields
  tables         → TABLE_V1
Then
Capability Host Contract
  implemented by:
    EntityWorkspace     (constitution §3.3)
    ApplicationWorkspace (constitution §3.2)

Workspace Host
  → regions (header · summary · overview · rail · decision · platform_slot)
  → contributions (one protocol) that bind kit widgets, not ad-hoc JSX

Four classes (same protocol, different ownership / lifecycle):

  Shell primitives
    identity · status · ownership · common actions · audit
    Host places them. Owner supplies projection / fields.
    Host does not own domain meaning of status.

  Shared capabilities
    contacts · notes · consent · tasks/reminders · relations
    Host knows they may occupy overview/rail (etc.).
    Notes owns storage/state/actions.
    Consent owns policy/evidence/blocking (Compliance).
    Tasks own Activity (ADR-012).

  Platform capabilities / surfaces (D2 catalog — keep)
    timeline/activity · documents · communication · forms
    documents remains reserved until E2 after this program.

  Module contributions
    recruitment.stage · recruitment.vacancy · recruitment.assignee
    hr.employment · fleet.assignment · billing.*
    Paid module: same contract, not a special page.
```

**Rule:** Shell / host **must not** import Recruitment, HR, Notes storage, Consent policy, or Documents Hub internals. It resolves `capability_id` / `component_id` + placement + referenced permissions.

D2 slot ids **do not** grow `notes` / `consent` / `rodo`. Those are **shared capability widgets** placed into host regions (e.g. `overview` / `rail`), not new platform surfaces.

---

## Platform kit catalogs (normative — this feat)

Typed in `hostflow-frontend/src/platform/workspace-capability/kit.ts` and `backend/app/platform/workspace_capability/kit.py`. **References**, not second dictionaries.

**Summary:** 16 data types · 6 primitives · 78 fields · 16 widgets · 1 table frame · 2 hosts.

Gate counts Field Registry manifests (not prose): candidate = **18** (includes `operations.stage`); sales `single_select` / `multi_select` = **18** (must map to `code` / `reference_code[]`, not a 17th type).

| Layer | SoT | This feat |
|-------|-----|-----------|
| **Data types** | Field Registry [§4](../platform/field-registry-card-configuration.md#4-field-types) | Frozen `KIT_DATA_TYPE_IDS` must equal that table |
| **Fields** | [Field Registry](../platform/field-registry-card-configuration.md) + [Entity Profile](../platform/entity-profile-definition-registry.md) | Pointer only. Snapshot `KIT_REGISTERED_FIELD_COUNT = 78` asserted vs manifests |
| **UI primitives** | [PRIMITIVES_V1](../frontend/PRIMITIVES_V1.md) + [CHECKBOX_V1](../frontend/CHECKBOX_V1.md) | `status_badge` · `chip` · `select` · `button` · `input` · `checkbox` |
| **Widgets** | compositions of primitives + fields | `KIT_WIDGET_CLASS_IDS` (16). Notes/Consent are **two** widget classes, not the kit |
| **Tables** | [TABLE_V1](../frontend/TABLE_V1.md) + ListWorkspace | `table_v1_entity_list`. Filter/search/sort/pagination/bulk/saved views = **ListWorkspace zones**, not a `filter_bar` widget |
| **Host navigation** | Entity Workspace K3 · ListWorkspace status tabs · Application Workspace tabs | Tabs SoT = **host chrome**. Not a kit widget. Inventory `tabs_*` map here |
| **Proof-blocker primitive** | — | empty after `checkbox` lock. Do not use local `<input type="checkbox">` |
| **Hardening** | INPUT_V1 family locked CSS-only | `input_runtime` — extract a runtime component so pages cannot assemble ad-hoc `<input className="input">` |
| **Deferred gaps** | named, not invented locally | `modal` · `radio` · `toggle` |

**filter_bar is not a gap.** ListWorkspace already hosts `search` · `filters` · `sort` · `pagination` · `bulk` · `saved_views` (`KIT_LIST_WORKSPACE_ZONE_IDS`). A later `FILTER_BAR_V1` may only be **extraction** of zone `filters`, not a second filter layer.

**tabs is not a kit id.** There is no public `Tabs` primitive. `EntityWorkspaceNavTabs` / `ListWorkspaceStatusTabs` / `ApplicationWorkspace` tabs are host chrome. Do not treat inventory tabs as a platform dependency. Do not register a `tabs` widget while proofing a screen.

New work **must not** mint a local data type, field matrix, primitive, widget, or table when a kit id exists. If proof discovers a missing primitive/capability, **register it in the kit first**, then use it. Do not grow widget ids on the proof screen.

---

## Class catalogs (normative — this brief)

### Shell primitives

| id | Host role | Semantic owner | Notes |
|----|-----------|----------------|-------|
| `identity` | Places header | Entity/Application type owner supplies fields | Chrome, not a product |
| `status` | Places header/bucket | **Owner projection** | Not a HostFlow-wide enum. Constitution §4.4 is **UI display buckets** only. Candidate ≠ Application ≠ Employee ≠ Vacancy ≠ Company. This brief must not unify those enums. |
| `ownership` | Places header/rail | Host region for common assignee | Module-specific assignee (e.g. recruiter) is a **module contribution** |
| `actions` (common) | Places header/decision | Action Canon IDs (see references) | Host does not invent actions |
| `audit` | Places context | Activity / audit owner | Not a second history product |

### Shared capabilities

| id | Host role | Semantic owner | Notes |
|----|-----------|----------------|-------|
| `contacts` | Places content/rail | Contacts capability | Not Shell-owned |
| `notes` | Places overview/rail | Notes capability | One semantic Notes across Entity **and** Application hosts. Storage may stay split until a named later slice |
| `consent` | Places overview/rail | Compliance | **Not** named `rodo`. `lead_rodo_v1` is a **policy**. Forms keeps consent-at-capture (ADR-007) |
| `tasks` | Places rail | Activity (ADR-012) | Do not mint a second planner |
| `relations` | Places content | Relationship / entity-model owner | |

### Platform capabilities / surfaces

| id | Host role | Semantic owner | Notes |
|----|-----------|----------------|-------|
| `timeline` | D2 content slot | Activity (ADR-012) | Not a second Activity product |
| `documents` | D2 slot — **reserved until E2** | Documents platform (ADR-009) | Shell nav `documents` ≠ D2 enable (D4 rule stays) |
| `communication` | D2 slot | Communication | Already a D2 surface |
| `forms` | D2 slot | Forms (ADR-007) | Already a D2 surface |

### Module contributions (examples — not exhaustive)

| id | Contributor | Notes |
|----|-------------|-------|
| `recruitment.stage` | Recruitment | Decision/context contribution, not shared Notes |
| `recruitment.vacancy` | Recruitment | |
| `recruitment.assignee` | Recruitment | Module assignee ≠ shell `ownership` unless the owner projects it there |
| `hr.employment` | HR | |
| `fleet.assignment` | Fleet | |
| `billing.*` | Billing | Same contract; Billing Platform feat is **not** this slice |

---

## Capability Host Contract (normative fields)

A contribution is the only legal way to add a block to a **host** that implements this contract (Entity Workspace or Application Workspace). It is **not** “part of Entity Shell.” Application Workspace implements the **same** contract as an external host.

| Field | Meaning | Must reference (not a local vocabulary) |
|-------|---------|------------------------------------------|
| `capability_id` | Id from one of the four classes | This brief’s catalogs; module ids as `module.capability` |
| `class` | `shell_primitive` · `shared_capability` · `platform_surface` · `module_contribution` | This brief |
| `owner` | Semantic owner (P-02) | Catalog / ADR-026 owner — not the host |
| `contributor` | Module / paid add-on that registers it | ADR-004 module / entitlement |
| `host` | `entity_workspace` · `application_workspace` | Constitution §3. **Both legal.** Do not encode Application as Entity |
| `consumer` | Object type (`candidate` · `recruitment_application` · …) | Existing type ids |
| `component_id` | Registered renderer id | Static typed registry (this feat) |
| `placement` | Host region: `header` · `summary` · `overview` · `rail` · `decision` · D2 slot id | Host region catalog |
| `ordering` | Stable rank within region | This contract |
| `visibility` | When shown (state / module enabled / entitlement) | Owner state + license **reference** |
| `permissions` | Who may see / act | **ADR-036 / existing permission keys only.** No contribution-local RBAC |
| `state_owner` | Where state lives | Capability owner, never the host by default |
| `actions` | Canonical action ids | **Action Canon** when it exists; until then **only already-shipped named actions**. Do not mint a second Actions layer here ([ADR-019](../architecture/ADR-019-automation-capability-entitlement-control-plane.md) still names the hole) |
| `events` | Emit/consume | **Existing registered events only.** No new Event registry in this slice |
| `license` | Entitlement view: `default` · `optional` · `paid` | **ADR-004 / ADR-019 entitlement / module capability.** Not a new license SoT |
| `conflicts` | What it may not duplicate | `capability_id` uniqueness per `host`+`consumer`+region unless override policy |

**Conflict resolution (this brief):** one `capability_id` per host+consumer+region. A paid module **extends** via a new `capability_id` or an approved override record — it does not fork Notes/Consent.

**Registry:** `component_id` is part of the contract. Feat may land a **static typed registry** (id → renderer). A dynamic plugin loader is **not** required for the proof screen. Shipping the proof screen by stuffing JSX in the page **fails** this slice. Host files must not grow into the semantic owner of contributed capabilities.

---

## Proof consumer (locked)

**Recruitment Application** on **Application Workspace**. Goal Completion Gate G4. Not Candidate. Not Sales Inquiry (migrate-on-touch).

Must demonstrate, on one screen:

1. ApplicationWorkspace as Capability Host (not Entity Workspace reuse-by-rename).  
2. Shared `notes` and shared `consent` via contributions.  
3. Shell primitives: identity + status **as Recruitment Application owner projection** (not a global enum).  
4. Module contributions: `recruitment.stage` · `recruitment.vacancy` · `recruitment.assignee`.  
5. One `optional` or `paid` contribution registered the same way (fixture/stub allowed; **not** Billing Platform).  
6. No local ContextRail stuffing of those blocks.

Sales CallNotes/RODO remain inventory until migrate-on-touch. They are not the proof.

---

## Migration inventory (feat — required)

SoT: [workspace-capability-legacy-inventory.md](workspace-capability-legacy-inventory.md).

Feat lists current **local** blocks that violate the restored goal (non-exhaustive start):

| Local widget | Consumer | Host | Maps toward |
|--------------|----------|------|-------------|
| `SalesInquiryCallNotesSection` | Sales Inquiry | Application | shared `notes` |
| `SalesInquiryRodoSection` | Sales Inquiry | Application | shared `consent` + policy `lead_rodo_v1` |
| `CandidateRodoSection` | Candidate | Entity | shared `consent` (transport ≠ capability) |
| Recruitment comments / RODO | Recruitment Application | Application | shared `notes` / `consent` |
| ContextRail `vacancy` / `assignee` / stage | Recruitment Application | Application | `recruitment.vacancy` / `recruitment.assignee` / `recruitment.stage` |

Inventory ≠ migration of every row. Proof screen must not add a **new** row to this table.

---

## Locked principle

```text
Keep     D1 chrome, D2 surface catalog, D3–D9 as surface binds
Keep     Entity Workspace ≠ Application Workspace (constitution §3)
Seal     Capability Host Contract (placement only on the host)
Keep     capability owners (P-02) for semantics/state
Prove    Recruitment Application without local composition
Then     Documents E2 feat
Never    Shell-owns-Notes · Application-is-Entity · Candidate-as-proof
         D10-on-weak-model · second RBAC/Actions/Events inside this contract
```

This slice **must not**:

- start Documents E2 feat, OCR, D2 `documents` enable, Billing, AI  
- reopen D3–D9 as more surface cutovers  
- patch Recruitment/Sales rails as the definition of done  
- make Entity Shell the semantic owner of Notes/Consent/Tasks/Documents  
- fold Application Workspace into Entity Workspace  
- pick Candidate as G4 proof  
- merge Forms consent-at-capture into `consent`  
- name the capability `rodo`  
- mint a global status enum  
- mint a contribution-local permission / action / event / license vocabulary  
- mass-migrate every inventory row  
- rewrite Decision Model wholesale (decision zone may **host** contributed actions)  
- reopen P3–P5, R6, C2.4, Catalog Notifications RFC  
- reduce this program to Notes/Consent/RODO  
- mint a second Field Registry, primitives list, or table standard  
- multiply new entity/application screens before the E2E proof  

---

## Ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **Scope audit + Goal Completion Gate** | Classify closed phases | [audit](../gates/platform-scope-completeness-audit.md) ✅ |
| **Contract seal** | Host contract + four-class catalogs + reference fields | brief ✅ [#272](https://github.com/igortatarynovich/HostFlow/pull/272) |
| **Feat + G4 bind** | Typed registry + inventory + named gate + Recruitment Application host | ✅ [#273](https://github.com/igortatarynovich/HostFlow/pull/273) · G4 **PASS** |
| **G1–G5 close-out** | Goal Completion review of #273 | [close-out](../gates/workspace-capability-platform-g1-g5-closeout.md) **PASS_WITH_CONSTRAINTS** — program then **not COMPLETE** |
| **Host runtime-equivalence** | Second host + Notes/Consent owner boundaries | ✅ [#274](https://github.com/igortatarynovich/HostFlow/pull/274) @ `6f70a432` |
| **Final Goal Completion** | Program COMPLETE | [COMPLETE](../gates/workspace-capability-platform-complete.md) **PASS** |
| **Documents E2** | Public contract / D2 `documents` enable | brief ✅ [#271](https://github.com/igortatarynovich/HostFlow/pull/271); **feat unlocked** — G4 PASS did **not** unlock E2; COMPLETE does |

---

## Workspace Capability Platform Completion Gate (CI — this feat)

Named step: **Workspace Capability Platform Completion Gate**  
(`tests/platform/test_workspace_capability_platform_completion_gate.py`).

- Four-class catalogs frozen as in this brief  
- Platform kit catalogs frozen: data types = Field Registry §4; fields SoT = Field Registry (no copy); primitives = PRIMITIVES_V1; tables = TABLE_V1; widget classes include more than notes/consent  
- Contribution field set frozen, including `host` and `class`  
- `permissions` / `actions` / `events` / `license` documented as **references**, not new SoTs  
- No `rodo` capability_id  
- No global `status` enum introduced  
- Static registry module exists (or feat explicitly defers registry to proof slice **in the gate** — default: registry lands with feat)  
- D2 catalog unchanged; `documents` still reserved  
- Inventory file exists and lists kit forks (fields / primitives / tables / widgets) **and** Recruitment Application rail stuffing  
- D1–D9 / E1 gates stay green  
- E2 feat must not land  
- Goal Completion template filled in the feat PR description  
- Proof consumer id frozen as `recruitment_application` / Application Workspace  

Proof-screen slice adds G4 evidence; contract feat alone is **not** phase COMPLETE.

---

## In scope (docs PR — merged [#272](https://github.com/igortatarynovich/HostFlow/pull/272))

1. This brief (rename from Entity Platform Completion).  
2. Queue / roadmap / AGENTS / maturity / UI constitution / Architecture Review / E2 pointers.  
3. E2 feat stays locked.

## In scope (this feat PR)

1. Named Workspace Capability Platform Completion Gate.  
2. Typed host / capability / contribution contracts. Four classes as separate types, not one flat enum.  
3. Typed **platform kit** catalogs (data types, fields pointer, primitives, widgets, tables) as references to existing canons.  
4. Static renderer registry (`component_id` → module path only — not the platform).  
5. Migration inventory markdown (not RODO-only).  
6. Architecture Review 10 questions **and** Goal Completion G1–G5 in the PR body.  
7. **No** proof-screen rewrite. Next slice = Recruitment Application only.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Proof screen E2E (Recruitment Application) | Next slice after feat |
| Mass migration of inventory rows | After proof |
| D2 `documents` enable | E2 after this program |
| Action Canon runtime (if still missing) | Named later; this slice only **references** |
| Event registry | Named later; this slice only **references** existing events |
| FormTemplate SoT / P3–P5 | Forms |
| R6 table-cutover | Acquisition |
| C2.4 / SMTP allowlist burn-down | Communication |
| Catalog Communication RFC | A2-F1 |
| Fifth JWT role | ADR-036 RFC |

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Host owns placement only. Capability owners per catalogs (Compliance=`consent`, ADR-012=`tasks`/`timeline`, Documents=`documents`, Forms=`forms`, Notes capability=`notes`, modules=their contributions). P-02. |
| 2 Exists? | D1/D2 hosts/surfaces yes; Capability Host Contract **no** (audit STOP) |
| 3 Adapter | None new this docs PR. Consent/Forms boundary: capture vs post-intake notice |
| 4 Boundary | No E2 feat; no D10; no Application=Entity; no Shell-owns-semantics; no L0 Catalog rewrite |
| 5 Settings | No new Manifest keys. `license` **references** existing entitlement |
| 6 SoT | This brief = kit catalogs (references) + host contract + four-class catalogs. Field Registry / PRIMITIVES_V1 / TABLE_V1 remain SoT. D2 remains surface SoT. Permission/action/event SoTs stay on their canons |
| 7 Events | Contribution `events` = references to existing registered events only |
| 8 Requires | D1–D9 as surface binds · audit STOP · ADR-026/027 · ADR-036 · UI constitution §3 |
| 9 License | `default`/`optional`/`paid` is an entitlement **view**, not a new license capability |
| 10 Public contract | Additive L2 Capability Host Contract; D2 catalog not rewritten; no Catalog Passport |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog. P-02 is why the host must not own Notes/Consent. P-03 is why modules contribute instead of cloning them.

---

## Goal Completion Gate (this program — 2026-08-21 final)

Formal record: [COMPLETE](../gates/workspace-capability-platform-complete.md). Intermediate #273 review: [PASS_WITH_CONSTRAINTS](../gates/workspace-capability-platform-g1-g5-closeout.md).

| # | Verdict | This program |
|---|---------|--------------|
| **G1** | **PASS** | Kit first; host places; owners own semantics; one contribution contract for Entity **and** Application hosts without collapsing them. Runtime: `ApplicationWorkspaceCapabilityHost` **and** `EntityWorkspaceCapabilityHost`. Candidate Entity Workspace enters through the Entity host. Notes/Consent transport is behind owners. |
| **G2** | **PASS** | Forbidden: new local data types/fields/primitives/widgets/tables; new module Notes/Consent/rail products; page-local composition; Shell as semantic owner; Application-as-Entity; global status enum; contribution-local RBAC/Actions/Events; treating RODO as the platform; Candidate-as-G4. Named gate forbids `ApplicationCommentsSection` / `ApplicationRodoSection` on the proof surface. |
| **G3** | **PASS** | Next Application or Entity screen uses kit + host contract + catalogs only. Documents E2 uses the same contribution protocol. |
| **G4** | **PASS** | Recruitment Application assembled from the kit. Evidence: (1) `notes` and `consent` widget ids exist in kit; (2) semantic owner remains Notes / Compliance; (3) host only places; (4) Recruitment Application does **not** import local `ApplicationCommentsSection` / `ApplicationRodoSection` (or `SalesInquiryCallNotesSection` / `SalesInquiryRodoSection` / `CandidateRodoSection`); (5) a module contribution does not ship a copy of those shared widgets; (6) consent boolean uses `checkbox` primitive — not local `input type=checkbox`. Catalog rows alone are **not** G4. Contract-only commits cannot claim PASS on G4; this feat bound the screen. Candidate is **not** the proof. |
| **G5** | **PASS** (named leftovers) | D2 `documents` reserved until E2 feat; `checkbox` landed (`CHECKBOX_V1`) and G4 consent uses it; `input_runtime` is named hardening; `filter_bar` is **not** a second layer (ListWorkspace zones); tabs remain host chrome; Sales/HR inventory migrate-on-touch; Action Canon / Event registry remain referenced; Notes pre-convert stub when no candidate subject. |

Outcome: **PASS**. Program is **COMPLETE**. Documents E2 feat is unlocked. G4 PASS did not unlock E2. ListWorkspace is not this close-out.

---

## Acceptance

Capability-based (see table above). Checklist is **not** the proof:

- [x] Brief merged (this file + Original Goal → Completion Proof)  
- [x] Named Workspace Capability Platform Completion Gate (feat)  
- [x] Four-class catalogs + host contract frozen  
- [x] Host = placement only on the Application proof path; owners = semantics/state (transport behind Notes/Consent owners after #274)  
- [x] Entity Workspace ≠ Application Workspace  
- [x] permissions/actions/events/license are references  
- [x] status is owner projection, not a global enum  
- [x] Default and paid contributions share one mechanism  
- [x] Local analogues of shared capabilities forbidden on new work  
- [x] Legacy inventory + migration map  
- [x] Registry is the only legal add-path on the proof  
- [x] G4 = Recruitment Application bind (`ApplicationWorkspaceCapabilityHost`) — **PASS**  
- [x] Entity Workspace runtime host (`EntityWorkspaceCapabilityHost`) — G1 closed on [#274](https://github.com/igortatarynovich/HostFlow/pull/274)  
- [x] Notes/Consent owner facades hide transport — G5 residual closed  
- [x] Program COMPLETE after [host runtime-equivalence](workspace-capability-host-runtime-equivalence.md) + final Goal Completion  
- [x] E2 feat stays locked until that COMPLETE — now **unlocked**  

---

## DoD

- [ ] Capability Host Contract restored in writing (this file)  
- [ ] Queue + roadmap + AGENTS + constitution point here  
- [ ] D named “COMPLETE” qualified as brief-complete / goal-incomplete in audit  
- [ ] Feat + Recruitment Application proof locked in order  

---

## History

- 2026-08-20: Shared UI Capabilities Contract Seal drafted, then superseded (still accepted shell = geometry).  
- 2026-08-20: Product Track → Entity Platform Completion (flat common-capability catalog; Shell as owner of commons; proof Candidate **or** Recruitment).  
- 2026-08-20: **This revision:** rename to Workspace Capability Platform Completion. Capability Host Contract. Host ≠ semantic owner. Entity ≠ Application. Four-class catalogs. Canon references for permissions/actions/events/license. Status = owner projection. Proof locked to Recruitment Application.
- 2026-08-21: Brief merged [#272](https://github.com/igortatarynovich/HostFlow/pull/272). Feat: typed contracts, four-class catalogs, technical registry, inventory, named gate. Proof screen remains the next slice.
- 2026-08-21: Catalog inconsistencies closed: 78/18 counters vs manifests; filters = ListWorkspace zones (not `filter_bar` widget); tabs = host chrome (not kit id); `checkbox` = G4 proof blocker; `input_runtime` = named hardening.
- 2026-08-21: `CHECKBOX_V1` locked; `checkbox` registered in kit. Recruitment Application G4 bind via `ApplicationWorkspaceCapabilityHost` (Notes/Consent owned widgets; host places).
- 2026-08-21: Goal Completion G1–G5 of [#273](https://github.com/igortatarynovich/HostFlow/pull/273) → **PASS_WITH_CONSTRAINTS**. G2 PASS · G3 PASS (Application path) · G4 PASS · G5 PASS_WITH_CONSTRAINTS · G1 PASS_WITH_CONSTRAINTS (not full PASS). Program **not COMPLETE**. Documents E2 stays locked. Next: [host runtime-equivalence](workspace-capability-host-runtime-equivalence.md). ListWorkspace is a separate previous slice.
- 2026-08-21: Final Goal Completion of [#274](https://github.com/igortatarynovich/HostFlow/pull/274) → **PASS**. Program **COMPLETE**. G1 PASS (both hosts at runtime + Candidate bind). Documents E2 feat unlocked. Record: [workspace-capability-platform-complete.md](../gates/workspace-capability-platform-complete.md).
