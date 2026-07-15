# ADR-022: Intake Form Purpose and Submission Policy Model

**Status:** Proposed (L1 — pending architecture review)  
**Date:** 2026-07-15  
**Layer of change:** Platform | Domain contract | Intake runtime  
**Authors:** Product + Platform architecture  
**Supersedes / clarifies:** implicit behaviour in [ADR-007](ADR-007-forms-platform-capability.md) (Forms Platform presentation layer), [ADR-013](ADR-013-public-intake-strategy.md) (public intake transport), targeted-advertising seed and channel-specific submit paths

**Related (not replaced):** [ADR-021](ADR-021-unified-intake-resolution-model.md) (Application / Submission / resolution), [entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) (Entity Profile, Decision Layer, Outcome Executor), [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)

**Review artifact:** [ADR-022-review-checklist.md](ADR-022-review-checklist.md)

> **Terminology:** **Form Definition** — tenant-owned intake contract (purpose + target profile + submission policy + presentation draft). **Publication** — a public entry point bound to a published form version and attribution. **Invite** — a personal entry point bound to a known Application. **Presentation** — fields, sections, labels, options, conditional visibility only. Presentation **must not** determine post-submit behaviour.

---

## 1. Context

### 1.1 Problem

HostFlow forms are implemented as a composition of `TenantLeadForm`, `IntakeSourceProfile`, `EpIntakePresentation`, and channel-specific submit handlers. Behaviour after submit is **implicit** — derived from session kind (`lead_draft` vs `questionnaire_invite`) and hardcoded paths (e.g. targeted-advertising seed, sales questionnaire merge).

This produces:

| Symptom | Root cause |
|---------|------------|
| One canonical B2B questionnaire per tenant | Auto-seed creates operational form, not editable preset |
| Public link always creates new Lead draft | No `match_or_create` policy |
| Invite hard-wired to targeted-advertising | No generic attach contract |
| `Lead.normalized` overwrite on re-submit | No Submission append contract wired at form layer |
| Sales / recruitment / public intake exceptions | No platform-level Purpose + Policy model |

**Risk:** adding `purpose` and `submission_policy` directly in module code without L1 canon recreates channel-specific exceptions.

### 1.2 Relationship to adjacent ADRs

| ADR | Scope | ADR-022 scope |
|-----|-------|---------------|
| **ADR-007** | Forms platform capability: publication bridge, handlers, presentation runtime | ADR-022 defines **semantic axes** that ADR-007 publications must carry |
| **ADR-021** | Application projection, Submission immutability, resolution, matching informational contract | ADR-022 defines **when** Application is created vs supplemented at submit time; ADR-021 governs **after** Application exists |

ADR-022 answers: **How does a Form Definition declare intent, business context, and post-submit behaviour?**

### 1.3 Decision (summary)

**Chosen:** Every Form Definition exposes three mandatory axes — **Purpose**, **Target Entity Profile**, **Submission Policy**. Presentation is orthogonal. Entity Profile constrains valid combinations. Publication and Invite supply entry context; Submission stores an effective policy snapshot.

**Not chosen:**

- Purpose silently creating Application (Purpose ≠ outcome)
- Matching against ClientAccount / Candidate directly at submit (match **Application** first — ADR-021 §2.1, §8)
- Universal matching for all entity types in Phase 1 (Sales Inquiry only)
- New `applications` table (ADR-021 Phase 1 facade over Lead transport)

---

## 2. Three mandatory axes

Every **Form Definition** MUST declare:

### 2.1 Purpose — why the form exists

Purpose is **semantic intent**. It does **not** determine runtime outcome alone.

| `purpose` | Meaning | Typical Application? |
|-----------|---------|----------------------|
| `questionnaire` | Collect answers; operational follow-up optional | Only if policy says so |
| `inquiry` | Start or continue a commercial / service inquiry | Usually yes |
| `application` | Apply for a role, program, or slot | Yes (Recruitment, etc.) |
| `registration` | Register entity in platform | Yes |
| `update` | Supplement existing profile data | No new Application by default |
| `consent` | Capture legal consent | No |
| `survey` | Analytics / feedback | No |
| `document_collection` | Collect documents + metadata | Optional |

**Rule:** Purpose MUST NOT implicitly create an Application. Actual behaviour is defined by **Submission Policy** (§3).

**Valid combinations (examples):**

| Purpose | Policy mode | Outcome |
|---------|-------------|---------|
| `inquiry` | `match_or_create` | Match open Application or create Sales Inquiry |
| `inquiry` | `review` | Review Queue Item; operator routes later |
| `questionnaire` | `attach` | Supplement known Application (invite / clarification) |
| `document_collection` | `attach` | Append documents to known Application |
| `survey` | `ignore` | Submission only |

### 2.2 Target Entity Profile — what object class the form works with

`target_entity_profile_code` references **Entity Profile Definition Registry** (`EpEntityProfile.profile_code`).

The form knows **abstract** entity class (`Client`, `Candidate`, `Employee`, …) via profile metadata — not tenant business variants (agency client vs beauty salon vs licensed user). Those variants are **different profiles** or profile extensions, not form types.

Entity Profile determines (§7):

- `route_intent`, `module_owner`, destination inbox
- allowed `purpose` values
- allowed Submission Policy modes
- default match identifier fields
- allowed operator decision codes

**Anti-pattern (forbidden):** form-level flags such as `create_client=true` or hardcoded `sales_inquiry` routing bypassing Entity Profile.

### 2.3 Submission Policy — what happens after submit

```json
{
  "mode": "match_or_create",
  "match_policy": {
    "identifier_fields": ["email", "phone"],
    "target_route_intent": "sales_inquiry",
    "require_entity_profile_match": true,
    "require_offering_match": false,
    "allowed_lifecycle_statuses": ["new", "reviewing", "waiting_for_information"],
    "window_days": 90,
    "auto_attach_on": "strong_single",
    "review_on": ["possible", "conflict", "multiple"]
  }
}
```

---

## 3. Submission Policy modes (v1)

| Mode | Behaviour | Entry context |
|------|-----------|---------------|
| `create` | Always create new Application | Public / API |
| `match_or_create` | Attach to matching open Application, else create new | **Default for public acquisition** |
| `attach` | Require known `application_id`; append Submission | Personal invite |
| `review` | Create Review Queue Item; **no** domain Application until operator routes | Unknown / ambiguous intake |
| `ignore` | Persist Submission only | Surveys, NPS |
| `notify` | Persist Submission + notification; no Application | Alerts, feedback |

### 3.1 `review` vs Application with `lifecycle_status=new`

These MUST NOT converge into one undifferentiated queue.

| Aspect | `review` policy | `create` / `match_or_create` |
|--------|-----------------|------------------------------|
| Domain Application | **Not created** at submit | Created (or attached) at submit |
| Queue | **Intake Review Queue Item** references Submission | Module inbox (Sales, Recruitment, …) |
| Operator action | Choose route intent → create Application | Triage existing Application |
| Use when | Unknown route, conflict, policy-driven hold | Normal operational intake |

**Phase 1:** `review` outcome stored as Submission + `match_result` block; dedicated Intake Review UI is out of scope (ADR-021 Phase 3).

### 3.2 Default policy by entry type

| Entry type | Default mode |
|------------|--------------|
| Publication (public link) | `match_or_create` |
| Invite (personal link) | `attach` (forced; overrides publication) |

---

## 4. Match Policy

Matching runs at submit for `match_or_create` (and optionally informs `review`).

### 4.1 Match target

Search **Application projections** (Phase 1: Lead transport records matching Application criteria) — **not** ClientAccount, Candidate, or User tables directly.

### 4.2 Minimum parameters (v1)

| Parameter | Purpose |
|-----------|---------|
| `identifier_fields` | Fields used for lookup (email, phone, …) |
| `target_route_intent` | Scope match to module intent |
| `require_entity_profile_match` | Same `entity_profile_code` on Application |
| `require_offering_match` | Same offering / service context when applicable |
| `allowed_lifecycle_statuses` | Open Application stages only |
| `window_days` | Ignore Applications older than window |
| `auto_attach_on` | Confidence tier for automatic attach (`strong_single`) |
| `review_on` | Confidence tiers requiring operator review |

### 4.3 Outcomes

| Match result | Action |
|--------------|--------|
| Zero matches | Create new Application + Submission #1 |
| Exactly one strong match | Append Submission to existing Application |
| Possible / conflict / multiple | **No auto-attach**; Submission flagged for review |

### 4.4 Context rules (canonical)

| Scenario | Action |
|----------|--------|
| Open `sales_inquiry`, same profile & service | May attach (if strong single) |
| Closed Application (historical) | **New** Application; may link ClientAccount at decision time |
| Open Application, different service / offering | **New** Application |
| Candidate found, B2B form | **Do not attach** (cross-module) |

Aligns with ADR-021 §2.1: **match ≠ merge**.

---

## 5. Publication and Invite

### 5.1 Form Definition

Stores:

- default `purpose`, `target_entity_profile_code`, `submission_policy`
- presentation **draft**
- `published_version` (integer, monotonic)

### 5.2 Publication

One Form Definition → many Publications.

Publication stores:

- `form_id`, bound `published_version` (immutable snapshot reference)
- public slug / URL
- attribution: `source`, `campaign`, `channel`
- optional **limited** policy override (attribution-only fields; mode override requires admin flag — Phase 2)
- `destination` hints (inbox, route intent — derived from Entity Profile if omitted)

Publication MUST NOT silently change Purpose or Entity Profile.

### 5.3 Invite

Always:

- `submission_policy.mode = attach` (forced)
- `application_id` known at creation
- no Match Policy execution

### 5.4 Submission attribution

Every Submission MUST record:

| Field | Required |
|-------|----------|
| `submission_id`, `submitted_at` | ✓ |
| `form_id`, `published_version`, `presentation_code` | ✓ |
| `publication_id` or `invite_id` | one of |
| `effective_submission_policy` | ✓ (snapshot) |
| `source` attribution | ✓ |
| `normalized_values`, `consent_metadata` | ✓ |
| `match_result` | when matching ran |

Phase 1 storage: `Lead.normalized.submissions_v1[]` append-only (ADR-021 §5.1).

### 4.4 Match Matrix (Product B — canonical)

Auto-attach (`match_or_create` → attach) **only** when **all** conditions hold:

| # | Condition |
|---|-----------|
| 1 | Submission provides **both** normalized email and phone |
| 2 | Exactly **one** open Sales Inquiry (`lead_type=client`, `lead_target_type=client_lead`) |
| 3 | Same `tenant_id` |
| 4 | Same `entity_profile_code` when `require_entity_profile_match=true` |
| 5 | Same offering context when `require_offering_match=true` (`publication_id` / `intake_source_profile_id` on `intake_attribution_v1`) |
| 6 | Target lifecycle ∈ allowed set (`new`, `reviewing`, `waiting_for_information`) |
| 7 | Target **not** terminal (`processed`, `rejected`, `closed`, …) or abandoned (`intake_draft_abandoned`) |
| 8 | Both identifiers match on target Application (not email-only or phone-only) |
| 9 | Entry is **not** personal invite (invite always uses forced `attach` to known Application) |

| Match outcome | Action |
|---------------|--------|
| Zero matches | Create new Application + Submission #1 |
| One strong match (matrix satisfied) | Append Submission to existing Application |
| Partial identifier / multiple / conflict | **No auto-attach** — create on draft Application or review (Phase 1: create + `match_result_v1` flag) |
| Closed / historical Application | **Never** auto-attach — new Application |

---

## 5.5 Component ownership (reuse-first)

| Concern | Canonical owner | ADR-022 layer role |
|---------|-----------------|-------------------|
| Route / inbox (`route_intent`) | `IntakeRouter`, `IntakeSourceProfile` | Reads profile; does **not** re-route |
| Entity disposition | Decision Layer + Outcome Executor | **Reused** after target Application selected |
| Candidate duplicate match | `duplicate_resolution.py` | **Not replaced** — different entity (Candidate) |
| Sales Application match | `intake_platform.application_matcher` | **New** — Lead→Lead open Inquiry |
| Contact normalization | `services/contact_identifiers.py` | **Shared** by duplicate + matcher |
| Draft session | `public_intake_draft_session` | Unchanged transport for in-progress fill |
| Immutable Submission | `intake_platform.submission_store` | Append-only; preserves blocks on Lead PATCH |
| Form purpose / policy | `intake_platform.form_definition`, `policy_resolver` | **New** platform contract |
| Publication view | `forms_platform/publication_bridge` | Extended in Phase 2; not full Publication CRUD |

**Anti-pattern (forbidden):** second routing engine, second Decision Layer, or matching ClientAccount directly at submit.

---

## 6. Versioning

| Rule | Statement |
|------|-----------|
| Published version immutable | Submissions reference `published_version`; never reinterpret against live draft |
| Publish creates snapshot | New integer version; presentation + policy snapshot at publish time |
| Draft edits | Do not affect in-flight sessions bound to older version |
| Policy change | Changing purpose or submission_policy requires new published version |

**Non-compliant:** upserting `EpIntakePresentation` in place for live published forms without version increment.

**Phase 1 honesty (2026-07-15):** `published_version` column and `is_system_preset` are **preparation only**. Phase 1 does **not** implement immutable published snapshots, publish workflow, or version-bound presentation storage. Do not claim versioning is shipped until Phase 2 publish slice lands.

---

## 7. Entity Profile responsibility

Entity Profile registry entry defines:

| Capability | Owner |
|------------|-------|
| `route_intent`, `module_owner` | Entity Profile |
| Allowed `purpose` values | Entity Profile |
| Allowed Submission Policy modes | Entity Profile |
| Default / suggested Match Policy | Entity Profile |
| Allowed operator decision codes | Entity Profile |
| Outcome Executor capabilities | Entity Profile |

**Validation rule:** Form Definition save MUST reject incompatible triples (e.g. `recruitment.candidate.driver_ce` + `route_intent=sales_inquiry`).

Form constructor UI MUST filter Purpose and Policy options from Entity Profile — not hardcode per module.

---

## 8. System preset vs tenant form

| Layer | Role |
|-------|------|
| **System preset** | Seed template: default fields, suggested purpose/policy; `is_system_preset=true` |
| **Tenant form** | Editable Form Definition owned by tenant |
| **Published version** | Immutable operational snapshot |
| **Publication** | Campaign / channel entry point |

Auto-seed (e.g. targeted-advertising) MUST create **preset + optional tenant draft**, not a single eternal operational form.

---

## 9. Phase 1 implementation scope

### 9.1 In scope

- `purpose`, `target_entity_profile_code`, `submission_policy` on Form Definition
- Enum validation + Entity Profile compatibility checks
- Effective policy resolver (Form + Publication + Invite)
- Submission append with policy snapshot
- Modes: `attach`, `match_or_create`
- Sales Inquiry matching by email / phone
- Targeted-advertising system preset
- Tests: public publication + personal invite (Product B acceptance)

### 9.2 Out of scope (Phase 1) — explicit

**Not implemented in Phase 1 backend slice (do not claim in release notes):**

- Immutable published versions / publish workflow
- Publication CRUD as first-class object (multi-campaign per form)
- Intake Review Queue UI (`review` mode enum only)
- Candidate / universal Application matching
- `document_collection`, `notify` runtime paths
- Visual policy builder
- `applications` table
- ADR-021 Phase 2 `reviewed_data` writes

**Phase 1 does implement:** purpose/policy fields, effective policy resolver, Sales `match_or_create` + invite `attach`, append-only `submissions_v1[]` (MVP storage), targeted-ad preset, P1 safety fixes per implementation contract.

### 9.3 Implementation contract

See [intake-form-purpose-phase1-backend.md](../tasks/intake-form-purpose-phase1-backend.md).

---

## 10. Consequences

### Positive

- One Intake Platform contract across Sales, Recruitment, Services
- Public forms default to intelligent `match_or_create`
- Invite remains deterministic `attach`
- Submission history interpretable via version + policy snapshot
- Entity Profile owns business semantics; form constructor stays generic

### Negative / cost

- Policy validation layer before save
- Match resolver adds submit-path complexity
- Versioning requires publish workflow (admin UI Phase 2)
- Migration from implicit session-kind routing

### Guardrails

1. Purpose MUST NOT silently create Application (§2.1).
2. Match searches Application, not domain entity (§4.1).
3. Published version MUST be immutable (§6).
4. Invite MUST force `attach` (§5.3).
5. Submission MUST append; MUST NOT overwrite prior snapshots (ADR-021 §5.1).

---

## 11. Acceptance criteria (ADR approval)

- [ ] Architecture review: three mandatory axes (§2)
- [ ] Architecture review: Purpose vs Policy separation (§2.1, §3)
- [ ] Architecture review: `review` vs new Application (§3.1)
- [ ] Architecture review: Match Policy + three outcomes (§4)
- [ ] Architecture review: Publication / Invite contract (§5)
- [ ] Architecture review: Versioning (§6)
- [ ] Architecture review: Entity Profile validation (§7)
- [ ] Product: Product B acceptance scenarios accepted (§9.1)
- [ ] Engineering: Phase 1 feasible without `applications` table
- [ ] Security: tenant isolation on policy + submission data

**After approval:** set ADR-022 to Accepted; verify already-implemented backend slice matches contract; merge per backend merge gate. UI/publication slice and product release gate follow in separate PR(s).

---

## 12. Links

| Document | Relationship |
|----------|--------------|
| [ADR-022-review-checklist.md](ADR-022-review-checklist.md) | Review checklist |
| [ADR-021-unified-intake-resolution-model.md](ADR-021-unified-intake-resolution-model.md) | Application / Submission / resolution |
| [ADR-007-forms-platform-capability.md](ADR-007-forms-platform-capability.md) | Forms platform bridge |
| [intake-form-purpose-phase1-backend.md](../tasks/intake-form-purpose-phase1-backend.md) | Phase 1 implementation contract |
| [entity-profile-definition-registry.md](../platform/entity-profile-definition-registry.md) | Entity Profile registry |
