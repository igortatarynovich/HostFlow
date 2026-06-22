# Requirement Rules Engine — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon only — **no runtime code in this slice**.  
**Hierarchy:** L2 operating canon — platform layer. **Evaluation layer** between Entity Profile composition and Documents / Process Engine / Readiness runtime.  
**Owner:** Architecture canon + platform core team.

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) | Entity Profile defines *which* fields/documents/process profile apply; Requirement Engine evaluates *what is still required* |
| [`field-registry-card-configuration.md`](field-registry-card-configuration.md) | Canonical field codes; requirement rules reference `qualified_code` only |
| [`process-engine.md`](process-engine.md) | Transition / handoff evaluation consumes requirement results; Field & Document Requirement Registries migrate here |
| P10A Presentation Rules | **Separate layer** — UI visibility only; see §9 |

---

## 1. Purpose

The **Requirement Rules Engine** answers:

> What must be true about this entity — data, documents, eligibility — before the platform can treat it as complete, ready, or allowed to move to the next process stage?

It is a **platform evaluation layer**, not a form or UI feature.

| Responsibility | Detail |
|----------------|--------|
| **Data requirements** | Which canonical fields must be populated (by context: intake, card save, transition, handoff) |
| **Document requirements** | Which document types / packs must be present, verified, or unexpired |
| **Readiness** | Aggregated completeness for modules (dossier ready, package ready, transfer ready) |
| **Gates** | Blocking reasons that prevent stage transition or outcome execution |
| **Eligibility** | Conditional requirements derived from entity state (citizenship, role, vacancy category) |
| **Stage transition blocking** | Normalized blockers returned to Process Engine transition evaluator |

**Main canon (non-negotiable):**

| Layer | Question |
|-------|----------|
| **Presentation Rules (P10A)** | What should we **show** the user on a form right now? |
| **Requirement Rules (this engine)** | What does the **system require** for process movement and readiness? |

Presentation Rules optimize UX inside a form session. Requirement Rules define platform truth for Documents, Process Engine, Readiness, Outcome Rules, and Intake validation.

---

## 2. Non-goals

The Requirement Rules Engine is **not**:

| Non-goal | Where it belongs instead |
|----------|--------------------------|
| Form Builder / Intake Source admin | Intake Source + Presentation write APIs |
| UI field visibility (show/hide, required-if on form) | **P10A** — `presentation_rules` on `ep_intake_presentations` |
| Card layout, section order, label overrides | Field Registry **Card Layout** + Entity Profile **presentation** |
| Drag-and-drop form designer | Future Forms platform (ADR-007) — display only |
| Storing entity field values | Entity records + normalized payload / `presentation_values_v1` |
| Document file upload UX | Document Hub upload surfaces |
| Process stage picker UI | CRM funnel / PE admin UI — **consumes** blockers, does not define rules |
| A second Process Engine | Process Engine **orchestrates** transitions; Requirement Engine **evaluates** requirement satisfaction |
| CandidateProfile.config JSON blob | Legacy — **migrate out**, do not extend |

**P0 rule:** If a rule affects whether a document must exist, a stage can advance, or readiness is green — it belongs here (or a registered rule source feeding here). If it only affects what the applicant sees on the public form — it belongs in P10A.

---

## 3. Position in architecture

### 3.1 Platform stack

```
Field Registry (canonical semantics)
        ↓
Entity Profile (composition: fields, document_pack_code, process_profile_code)
        ↓
Requirement Rules Engine (evaluate: what is required / blocking)
        ↓
┌───────────────┬────────────────┬──────────────┬─────────────────┐
│ Document Hub  │ Process Engine │ Readiness    │ Outcome Rules   │
│ (presence/    │ (transition    │ (aggregated  │ (create_entity  │
│  verification)│  orchestration)│  completeness│  gates)         │
└───────────────┴────────────────┴──────────────┴─────────────────┘
        ↓
Intake validation (post-normalize checks on Lead / draft)
```

### 3.2 End-to-end chain (current HostFlow milestone)

After P5A–P10A, the **Forms / Intake chain** is:

```
Field Registry → Entity Profile → Presentation → Mapping → Public Runtime → Lead Draft → Decision → Outcome
```

The **Requirement chain** (this document) attaches **after Entity Profile** and **parallel to Presentation**:

```
Field Registry → Entity Profile → Requirement Rules → Documents / PE / Readiness / Outcome / Intake
                      ↓
                 Presentation (P10A — display only)
                      ↓
                 Mapping → Public Runtime → Lead Draft
```

Presentation and Requirement share the same Field Registry codes but **must not share rule storage or evaluators**.

### 3.3 Evaluation flow (conceptual)

```
1. Resolve entity_profile_code (+ tenant overrides)
2. Load registered rule sets from rule sources (§5)
3. Build EvaluationInput from entity snapshot (§7)
4. Evaluate conditions → RequirementEvaluationResult (§8)
5. Consumers apply result (block transition, show readiness panel, reject intake, etc.)
```

Requirement Engine **evaluates**; it does **not** mutate entities or advance process stages.

---

## 4. Rule sources

Rules are **declared** in registered sources and **evaluated** by the Requirement Engine. No ad-hoc rule JSON in UI layers.

| Source | Owns | Examples |
|--------|------|----------|
| **Entity Profile** | Baseline field/document composition for an entity type | `recruitment.candidate.driver_ce` → default required fields, `document_pack_code`, `process_profile_code` |
| **Document Pack** | Pack-level required / optional document types | `recruitment.driver_ce_documents` → passport, driver_license, code95 |
| **Process Profile** | Stage / transition requirements | `recruitment.default` → requirements to enter `questionnaire_submitted`, `ready_for_handoff` |
| **Tenant override** | Approved tenant-specific relaxations or additions | Supervisor-approved work_permit waiver; extra client pack |

### 4.1 Source precedence (effective rules)

When sources overlap, effective requirements merge with this precedence (highest wins for **relaxation**; **additions** accumulate):

1. Platform seed (Entity Profile + pack + process profile manifests)
2. Tenant override (explicit relax/add — audited)
3. Runtime context modifiers (stage, route_intent, vacancy binding) — **not** stored in Form Presentation

**Hard rule:** Form Presentation (`ep_intake_presentations`) is **never** a rule source for requirements.

### 4.2 Registration model (P1 target)

| Concept | Description |
|---------|-------------|
| `requirement_rule_set` | Versioned bundle keyed by `(tenant_id, source_type, source_code, context)` |
| `requirement_rule` | Typed rule row with condition AST + target references |
| `rule_source_ref` | Pointer: `entity_profile:recruitment.candidate.driver_ce`, `document_pack:…`, `process_profile:…` |

P1 implements read + evaluate against seeded `driver_ce` rules; write/admin API is a later slice.

---

## 5. Consumers

Consumers **read** evaluation results; they do **not** embed requirement logic.

| Consumer | Uses result for |
|----------|-----------------|
| **Document Hub** | Required types from packs + eligibility rules; presence/verification checks feed back into evaluation |
| **Process Engine** | `evaluate_transition()` — aggregate blockers before stage PATCH / handoff |
| **Readiness** | `transfer-readiness`, `recruitment_package_readiness`, dossier completeness — migrate from tactical validators |
| **Outcome Rules** | Decision Layer — block `create_candidate` when hard requirements fail (optional soft warnings) |
| **Intake validation** | Post-normalize validation on Lead draft / public submit (distinct from P10A form required-if) |

### 5.1 Consumer anti-patterns (forbidden)

| Anti-pattern | Why forbidden |
|--------------|---------------|
| Frontend computes “needs work permit” from citizenship | Business rule in UI — must call evaluation API |
| Document upload page hardcodes required doc list | Must come from evaluation result |
| `CandidateProfile.config.document_configs` checked in router | Legacy — migrate to engine |
| P10A `required_if` on citizenship → work_permit field | Business requirement disguised as presentation rule |

---

## 6. Rule types

Canonical rule types for P0/P1 schema design:

| Type | Code | Meaning | Example |
|------|------|---------|---------|
| Field required | `field_required` | Canonical field must be populated | `platform.identity.citizenship` required before handoff |
| Document required | `document_required` | Document type or pack item must be present / verified | `passport` blocking for `driver_ce` pack |
| Eligibility | `eligibility` | Conditional requirement based on entity attributes | citizenship ∉ EU → `work_permit` document required |
| Gate blocked | `gate_blocked` | Hard stop with reason code | duplicate active candidate → block create |
| Stage requirement | `stage_requirement` | Requirements to enter or leave a PE system stage | cannot enter `ready_for_handoff` without phone + code95 |

### 6.1 Condition model (sketch for P1)

Conditions reference **evaluation input** only — not form presentation state:

```yaml
condition:
  field: platform.identity.citizenship
  operator: not_in
  value: [PL, DE, FR, ...]   # or reference group: eu_citizenship
then:
  require_documents: [work_permit]
  level: blocking
```

**Not in P1:** arbitrary JavaScript, frontend expressions, presentation `show_if` reuse.

### 6.2 Mapping to Process Engine registries

| Requirement type | Process Engine canon (existing) |
|------------------|----------------------------------|
| `field_required` | Field Requirement Registry (`process-engine.md` §3.6) |
| `document_required` | Document Requirement Registry (§3.7) |
| `stage_requirement` | Transition Rule Registry (§3.3) |
| `eligibility` | Module hook + requirement rules (new unified evaluator) |
| `gate_blocked` | Outcome / Decision Layer + PE override registry |

P1 unifies **read/evaluate** behind one facade; PE internal registries may remain as storage backends during migration.

---

## 7. Evaluation input

Single evaluation request contract (P1 API target):

| Field | Type | Purpose |
|-------|------|---------|
| `entity_type` | string | `candidate`, `client`, `lead`, … |
| `entity_id` | uuid \| null | Persisted entity when exists |
| `entity_profile_code` | string | Resolved Entity Profile (required) |
| `tenant_id` | uuid | Tenant scope |
| `stage` | string \| null | Current PE system stage / funnel stage |
| `route_intent` | string \| null | Intake routing context |
| `normalized_payload` | object | Canonical field values keyed by `qualified_code` and/or legacy normalized paths |
| `documents` | array | Document Hub snapshot: type, status, verification, expiry |
| `context` | enum | `intake`, `card_save`, `transition`, `handoff`, `readiness` — which requirement set applies |
| `target_stage` | string \| null | For transition evaluation |
| `vacancy_id` | uuid \| null | Optional vacancy-scoped modifiers |
| `process_profile_code` | string \| null | Override / confirm from Entity Profile |

**Input sources:**

| Input | Provider |
|-------|----------|
| `normalized_payload` | Lead/Candidate record, `ingest_envelope_v1`, public intake state |
| `documents` | Document Hub list API / readiness adapter |
| `entity_profile_code` | Entity Profile resolver, Intake Source, Vacancy bridge |
| `stage` | Process Engine instance / legacy funnel |

Presentation `presentation_values_v1` may **feed** normalized_payload for intake context but is not the authority for business requirements.

---

## 8. Evaluation output

Single evaluation result contract:

| Field | Type | Purpose |
|-------|------|---------|
| `entity_profile_code` | string | Echo resolved profile |
| `context` | string | Echo evaluation context |
| `required_fields` | array | `{ qualified_code, level: blocking \| warning, reason_code }` |
| `required_documents` | array | `{ document_type_code, pack_code?, level, verification, reason_code }` |
| `blockers` | array | Hard stops: `{ code, message, source_rule_id, layer }` |
| `warnings` | array | Non-blocking gaps |
| `satisfied` | bool | No blocking items for this context |
| `evaluation_version` | string | `requirement_evaluation_v1` |
| `rule_sources_applied` | array | Audit: which sources contributed |
| `evaluated_at` | datetime | Server timestamp |

Consumers map output to UX:

| Consumer | Primary fields |
|----------|----------------|
| Process Engine | `blockers`, `required_fields`, `required_documents` |
| Readiness API | `satisfied`, `warnings`, aggregated percentages |
| Intake | `blockers` on submit (optional P2); warnings on draft |
| Outcome Rules | `blockers` with disposition hints |

---

## 9. Ownership

| Artifact | Owner (write) | Readers |
|----------|---------------|---------|
| Entity Profile field composition | Platform registry + tenant EP admin (future) | Requirement Engine, Presentation runtime, Card layout |
| Document pack definitions | Platform / module manifests | Requirement Engine, Document Hub |
| Process profile + transition rules | Process Engine registry | Requirement Engine, PE transition evaluator |
| Tenant requirement overrides | Tenant admin (audited) | Requirement Engine only |
| **Requirement rule sets** | Platform seeds + module manifests | Requirement Engine evaluator |
| **Evaluation results** | Requirement Engine (computed) | PE, Hub, Readiness, Outcome, Intake — read-only |
| Presentation rules (P10A) | Form admin / `ep_intake_presentations` | Public form UI only |

**Ownership rule:** Only registered rule sources and the Requirement Engine may **define** requirements. Consumers may **display** results and **enforce** blockers — never duplicate rule definitions.

---

## 10. Boundary with P10A (Presentation Rules)

| Dimension | P10A Presentation Rules | Requirement Rules Engine |
|-----------|-------------------------|---------------------------|
| **Question** | What to show on the form? | What does the system require? |
| **Storage** | `ep_intake_presentations.presentation_overrides.presentation_rules` | Registered rule sources (§4) — **not** in presentation |
| **Scope** | Fields in presentation subset | Entity Profile + packs + process context |
| **Evaluated against** | Current form session values | Entity snapshot + documents + stage |
| **Affects** | Public/settings form render | Documents, PE, Readiness, Outcome, Intake |
| **Example (safe for P10A)** | If `has_whatsapp=true` → show `whatsapp_phone` | — |
| **Example (forbidden in P10A)** | If citizenship ≠ EU → require work_permit field | citizenship ∉ EU → `document_required: work_permit` |

**Enforcement:**

- P10A write validation rejects business-pattern rules in presentation editor (future guard).
- Requirement Engine rejects reading from `presentation_rules`.
- Code review gate: no `citizenship` / `work_permit` / `visa` logic in `presentation_rules.py` or public form components.

See [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) §P10 scope split.

---

## 11. Migration — exiting `CandidateProfile.config`

**Strategy:** strangler fig — same pattern as Field Registry and Entity Profile.

| Legacy fragment | Target owner | Requirement Engine role |
|-----------------|--------------|-------------------------|
| `field_configs[].required` (business) | Entity Profile + `field_required` rules | Evaluate for card_save / transition |
| `document_configs[]` | `document_pack_code` + `document_required` rules | Evaluate via Hub snapshot |
| gates / funnel fragments | Process Profile + `stage_requirement` | Feed PE transition evaluator |
| Tactical validators (`recruitment_package_readiness`, `TransferPolicyResolver` field checks) | Requirement Engine facade | Single evaluate API |

### 11.1 Migration phases

| Phase | Deliverable | Legacy shim |
|-------|-------------|-------------|
| **P0 — Canon** | This document + cross-links | All legacy paths unchanged |
| **P1 — Schema + read/evaluate + seed** | `requirement_evaluation_v1` API; `driver_ce` from Entity Profile + Document Pack **only** | Legacy validators still run; dual-read compare in tests |
| **P2 — Process Profile hooks** | `stage_requirement` + PE transition consumer wiring | Legacy validators deprecated |
| **P3 — Tenant overrides** | Audited relax/add registry + admin write | — |
| **Closure** | No requirement logic outside engine + sources | Remove `CandidateProfile.config` requirement fragments |

**Do not migrate:** layout-only `field_configs` (visible, order, labels) — those stay in Card Layout / Entity Profile presentation.

---

## 12. Hard rules (P0 gate)

Requirement logic **must not** be stored or evaluated in:

| Forbidden location | Reason |
|--------------------|--------|
| Form Presentation (`ep_intake_presentations`, P10A rules) | UI layer only |
| Frontend (React components, `presentationRules.ts`) | Client display; P10A evaluator is UX-only |
| `CandidateProfile.config` (new writes) | Legacy blob — migrate out |
| Document upload UI | Consumer of required list |
| Process stage UI / funnel PATCH handlers | Consumer of blockers |
| Meta mapping / intake mapping | Normalization only — not business gates |
| Ad-hoc API router validators | Tactical duplication |

**Allowed:** registered rule sources (§4) + Requirement Engine evaluator + audited tenant overrides.

---

## 13. P1 scope (after P0 gate)

**P1 — Requirement Rules Engine foundation** (implementation **blocked until P0 accepted**):

**P1 hard rule (source checkpoint):**

> **Requirement Rules Engine P1 = deterministic requirements from Entity Profile + Document Pack only.**

P1 must not implement Process Profile or Tenant Override resolution. Those sources are canon for the full engine (§4) but deferred to keep the first evaluator small and foundation-first — same pattern as Field Registry P1 and Entity Profile P1.

| Rule source | P1 | Later |
|-------------|:--:|-------|
| **Entity Profile** | ✅ | — |
| **Document Pack** | ✅ | — |
| **Process Profile** | ❌ | **P2** — stage/transition hooks |
| **Tenant Override** | ❌ | **P3** — audited relax/add |

**P1 proof case:** `recruitment.candidate.driver_ce` → required fields (from Entity Profile composition) + required documents (from `document_pack_code` / pack manifest). No stage-aware rules, no tenant-specific waivers.

| Deliverable | Description |
|-------------|-------------|
| Schema | `requirement_rule_sets` / `requirement_rules` tables or manifest-backed registry |
| Rule types (minimal) | `field_required`, `document_required` only (`eligibility` stub optional — must not pull Process Profile) |
| Read API | `GET /api/v1/platform/requirement-rules/{entity_profile_code}` |
| Evaluate API | `POST /api/v1/platform/requirement-rules/evaluate` → `requirement_evaluation_v1` |
| Evaluator | Pure function + loader from Entity Profile + Document Pack manifests only; no PE side effects |
| Seed | `recruitment.candidate.driver_ce` — baseline fields + driver document pack |
| Tests | Unit evaluator + API; compare sample output to legacy readiness where applicable |

**Explicitly out of P1:**

- Process Profile / `stage_requirement` evaluation
- Tenant override read or write
- Form Builder / presentation UI for requirements
- Full PE transition rewiring (P2)
- Automatic removal of `CandidateProfile.config`
- Outcome Rules automatic blocking (optional P2)
- Conditional eligibility chains that require process context (P2+)

---

## 14. P0 deliverables (this document)

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Purpose and non-goals | **Done** (this doc) |
| 2 | Architecture position vs Field Registry / Entity Profile / PE | **Done** (§3) |
| 3 | Rule sources and ownership | **Done** (§4, §9) |
| 4 | Consumers | **Done** (§5) |
| 5 | Rule types + evaluation I/O contracts | **Done** (§6–§8) |
| 6 | P10A boundary | **Done** (§10) |
| 7 | Migration from CandidateProfile.config | **Done** (§11) |
| 8 | Hard rules + P1 scope gate | **Done** (§12–§13) |
| 9 | Cross-links from sibling canon docs | **Done** (header + §10) |

**Next implementation step (after P0 acceptance):** **P1 — Requirement Rules Engine** — schema + evaluator + `driver_ce` seed + read/evaluate API.

**Do not start P10B implementation or Form Builder requirement UI until P1 schema is accepted.**

---

## 15. Code anchors (future P1)

| Area | Target location (P1) |
|------|----------------------|
| Evaluator | `backend/app/requirement_rules/evaluator.py` |
| Registry / loader | `backend/app/requirement_rules/registry.py` |
| Manifest seeds | `backend/app/requirement_rules/manifests/recruitment.py` |
| Read/evaluate API | `backend/app/api/v1/platform/requirement_rules.py` |
| Facade for consumers | `backend/app/requirement_rules/facade.py` |
| Tests | `backend/tests/requirement_rules/` |

**Legacy to migrate (consumers today):**

| Legacy | Location |
|--------|----------|
| `recruitment_package_readiness` | `backend/app/services/recruitment_package_readiness.py` |
| `TransferPolicyResolver` | `backend/app/services/transfer_policy_resolver.py` |
| `CandidateProfile.config` document/field gates | `backend/app/models/candidate_profile.py` |
| PE Field/Document Requirement Registry | `process-engine.md` §3.6–§3.7 |

---

## Changelog

- 2026-06-22: P0 accepted — Requirement Rules Engine canon; P10A/P10B boundary; P1 scope gate (Entity Profile + Document Pack only); migration map from CandidateProfile.config.
