# Requirement Rules Engine — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** **Requirement Rules Engine v1 — closed** (2026-06-23). P0 canon + P1–P3B runtime complete.  
**Hierarchy:** L2 operating canon — platform layer. **Evaluation layer** between Entity Profile composition and Documents / Process Engine / Readiness runtime.  
**Owner:** Architecture canon + platform core team.

**Next platform track (post-v1):** [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) — Document Expiry Notifications P0 canon. **Not** Requirement Rules P4 (custom expressions, rule builder, scripting).

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) | Entity Profile defines *which* fields/documents/process profile apply; Requirement Engine evaluates *what is still required* |
| [`field-registry-card-configuration.md`](field-registry-card-configuration.md) | Canonical field codes; requirement rules reference `qualified_code` only |
| [`process-engine.md`](process-engine.md) | Transition / handoff evaluation consumes requirement results; Field & Document Requirement Registries migrate here |
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | Document lifecycle runtime (**v1 closed** §20); feeds back into requirement satisfaction |
| [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) | Downstream expiry notification events (post-v1) |
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
| **P2 — Consumer wiring** | Readiness (P2A), PE transition gate (P2B), Document Hub (P2C) | Legacy validators dual-run; requirement engine overlays |
| **P3A — Process Profile hooks** | `stage_requirement` source; stage/transition context; merge order EP → Pack → Process Profile | Legacy stage validators dual-run |
| **P3B — Tenant overrides** | Audited relax/add/severity registry + admin write API | Legacy parallel validators dual-run |
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
| **Process Profile** | ❌ | **P3A** — stage/transition hooks |
| **Tenant Override** | ❌ | **P3B** ✅ — audited relax/add/severity |

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

**Next implementation step:** Superseded — **v1 closed** (§20). Post-v1 maintenance: legacy validator deprecation. Next platform track: [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md).

**Do not implement requirement logic in Form Presentation or Form Builder.**

---

## 16. P1 implementation status (2026-06-22)

| Deliverable | Status | Location |
|-------------|--------|----------|
| Document pack manifests | Done | `backend/app/requirement_rules/manifests/recruitment.py` |
| Rule compiler (Entity Profile + Document Pack only) | Done | `backend/app/requirement_rules/registry.py` |
| Evaluator | Done | `backend/app/requirement_rules/evaluator.py` |
| Facade | Done | `backend/app/requirement_rules/facade.py` |
| Read API | Done | `GET /api/v1/platform/requirement-rules/{entity_profile_code}` |
| Evaluate API | Done | `POST /api/v1/platform/requirement-rules/evaluate` |
| `driver_ce` proof case | Done | EP required fields + `recruitment.driver_ce_documents` pack |
| Tests | Done | `backend/tests/requirement_rules/` |

**P1 acceptance:** `driver_ce` + `readiness` → required fields (first/last/phone) + 4 documents; `intake` → fields only; evaluate reports blockers; Process Profile + Tenant Override excluded.

---

## 17. P2 implementation status (2026-06-23)

**P2 consumer wiring milestone — closed.**

| Milestone | Consumer | Status | Location |
|-----------|----------|--------|----------|
| **P2A** | Readiness / Recruitment Package | ✅ Done | `backend/app/requirement_rules/readiness_bridge.py` |
| **P2B** | Process Engine transition gate | ✅ Done | `backend/app/requirement_rules/transition_bridge.py` |
| **P2C** | Document Hub | ✅ Done | `backend/app/requirement_rules/document_hub_bridge.py` |

**P2A acceptance:** vacancy → `entity_profile_code`; `evaluate_candidate_readiness_requirements` maps blockers with `source_layer=requirement_engine`; legacy fallback when profile unresolved; embedded on recruitment package.

**P2B acceptance:** `ready_for_handoff` gate overlay on transfer policy; `merge_transition_requirement_gate` adds `requirement_engine` to `source_layers`.

**P2C acceptance:** Document Hub reads required documents from Requirement Engine; driver_ce pack (passport, driver_license, code95, tacho_card) → required/missing/satisfied; legacy ruleset path when `entity_profile_code` unresolved; API output includes `source_layer=requirement_engine`.

**Next implementation step:** Superseded by P3A–P3B and **v1 closed** (§20).

---

## 18. P3A implementation status (2026-06-23)

**Process Profile hooks — done.**

| Deliverable | Status | Location |
|-------------|--------|----------|
| Process Profile source compiler | Done | `backend/app/requirement_rules/process_profile_source.py` |
| Merge order EP → Pack → Process Profile | Done | `backend/app/requirement_rules/registry.py` |
| Stage context (`stage_code`, `transition_code`) | Done | registry, evaluator, facade, API |
| P2B transition bridge stage wiring | Done | `backend/app/requirement_rules/transition_bridge.py` |
| Stage-specific PE manifest proof | Done | `backend/app/process_engine/manifests/recruitment.py` |
| Tests | Done | `backend/tests/requirement_rules/test_process_profile_hooks_p3a.py` |

**P3A acceptance:** `stage_code=ready_for_handoff` + `context=transition` adds PE email/address fields and `medical_certificate` document; requirements absent without stage context; merge order preserved; Process Profile cannot override EP/Pack canonical targets; P2 readiness path unchanged without `stage_code`.

**Hard rule:** Process Profile adds stage requirements only — it does not redefine canonical field or document types already required by Entity Profile or Document Pack.

**Next implementation step:** Superseded — P3B complete; **v1 closed** (§20).

---

## 19. P3B implementation status (2026-06-23)

**Tenant override layer — done.**

| Deliverable | Status | Location |
|-------------|--------|----------|
| Tenant override model + migration | Done | `backend/app/models/tenant_requirement_override.py` |
| Override compiler / merge | Done | `backend/app/requirement_rules/tenant_override_source.py` |
| Merge order EP → Pack → Process Profile → Tenant | Done | `backend/app/requirement_rules/registry.py` |
| Admin write API (no UI) | Done | `backend/app/api/v1/platform/tenant_requirement_overrides.py` |
| Policy guards | Done | canonical EP fields + non-overridable docs |
| Tests | Done | `backend/tests/requirement_rules/test_tenant_overrides_p3b.py` |

**P3B allowed:** disable requirement (`relax`), add requirement (`add`), change severity (`severity`), tenant-scoped only.

**P3B forbidden:** custom expressions, arbitrary scripts, override canonical field meaning, per-user hacks, per-client overrides.

**Hard rule:** Tenant overrides apply after all platform sources; they cannot relax Entity Profile canonical fields or non-overridable document types (`passport`, `work_permit`, etc.).

**Next implementation step:** **Requirement Rules Engine v1 closed** — see §20. Post-v1: legacy validator deprecation only. Next foundation layer: [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md).

---

## 20. Requirement Rules Engine v1 — closed (2026-06-23)

**Milestone:** Requirement Rules Engine **v1 is closed**. This is a working runtime with wired consumers — not a concept doc.

### 20.1 Source stack (complete)

| # | Source | Status |
|---|--------|--------|
| 1 | **Entity Profile** | ✅ |
| 2 | **Document Pack** | ✅ |
| 3 | **Process Profile** | ✅ |
| 4 | **Tenant Overrides** | ✅ |

**Canonical merge order:**

```
Entity Profile → Document Pack → Process Profile → Tenant Overrides
```

### 20.2 Runtime consumers

| Consumer | Status | Bridge |
|----------|--------|--------|
| **Readiness** / Recruitment Package | ✅ | P2A `readiness_bridge.py` |
| **Process Engine** transition gate | ✅ | P2B `transition_bridge.py` |
| **Document Hub** required/missing/satisfied | ✅ | P2C `document_hub_bridge.py` |

Evaluation output: `requirement_evaluation_v1` with `source_layer=requirement_engine` at consumer boundaries.

### 20.3 Post-v1 maintenance (not new rule sources)

| Track | Scope |
|-------|--------|
| Legacy validator deprecation | Dual-run → remove tactical checks in `recruitment_package_readiness`, `TransferPolicyResolver` |
| Consumer hardening | Tests, parity, fail-safe guards |

### 20.4 Explicitly out of scope for Requirement Rules v2+ (do not expand now)

| Forbidden expansion | Why |
|---------------------|-----|
| Custom expressions | Becomes a second rule engine |
| Visual rule builder | UI/product scope; not evaluation canon |
| Tenant scripting | Arbitrary logic bypasses audited override layer |
| Per-client overrides | Breaks tenant-scoped override model (P3B) |
| Requirement admin UI | Separate product slice after runtime stabilizes |

**Next foundation layer for HostFlow platform:** **Document Runtime Engine v1 closed** — see [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) §20. Next downstream: Document Expiry Notifications P0.

---

## 15. Code anchors (P1)

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
- 2026-06-22: P1 complete — manifest-backed Document Pack + Entity Profile rule compiler; evaluate API; `driver_ce` proof case; tests.
- 2026-06-23: P2 consumer wiring closed — P2A Readiness, P2B PE transition gate, P2C Document Hub; next step P3A Process Profile hooks.
- 2026-06-23: P3A complete — Process Profile requirement source; stage/transition context; merge order EP → Pack → Process Profile; P2B stage wiring.
- 2026-06-23: P3B complete — Tenant override layer (relax/add/severity); merge order through tenant overrides; admin API; policy guards.
- 2026-06-23: **Requirement Rules Engine v1 closed** — full source stack + Readiness / PE / Document Hub consumers; §20 milestone record.
