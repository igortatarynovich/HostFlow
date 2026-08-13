# ADR-037: Platform Object Kind Catalog (meta-canon)

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Constitution (meta) | Domain indexing  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-016`](ADR-016-requirement-evidence-document-separation.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) · [`ADR-012`](ADR-012-activity-notification-operating-layer.md) · [`platform-capability-catalog.md`](platform-capability-catalog.md) · L2 index [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest shape; ownership remains per Catalog (Documents, Automations, Forms, Field Registry); indexes existing SoT — does **not** become a fourth document-type dictionary; per P-01…P-05 and INV-01…17.

---

## Context

HostFlow already has several platform registries (Document Type, Requirement Definition/Policy, Field Registry, Entity Profile, Forms Standard Library, Communication Templates) and several live reaction engines (`automation_rules`, C2.2 communication automation, NBA). Without a shared **ontology of architectural object classes**, product and engineering treat DocumentType, Document, RequirementPolicy, and RequirementEvaluation as one category — which collapses publication lifecycle, instance lifecycle, configuration policy, and computed outcomes into a single informal status vocabulary.

Before a state canon (`ObjectKind → Object → State dimensions → State owner → Transition owner`) can exist, the platform needs a **meta-canon**: which classes of objects exist, who owns them, where the real SoT lives, and what each object is allowed to do at runtime.

---

## Decision

### 1. ADR-037 introduces a meta-canon, not a data catalog

This ADR defines vocabulary only. The inventory of concrete objects for the Documents / Requirements / Automation / Templates slice lives in L2 [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md).

**The Object Kind Catalog is not a source of truth for domain data.** It answers only:

1. Which architectural object classes exist?
2. Who owns each indexed object?
3. Where does the real SoT live?
4. What is the object allowed to do at runtime?

Zone owners (Document Hub, Requirements, Automations, Forms, Communications) do **not** change.

### 2. ObjectKind (closed)

| ObjectKind | Meaning |
|------------|---------|
| `ReferenceObject` | Types and definitions (what exists as a type) |
| `RuntimeInstance` | Concrete persisted runtime objects |
| `RuleObject` | Decision or reaction rules |
| `LibraryObject` | Reusable definition assets |
| `EvaluationFact` | Computed fact (outcome), not a process lifecycle |

### 3. RuleKind (subtype of RuleObject — not a separate ObjectKind)

| RuleKind | Meaning |
|----------|---------|
| `DomainPolicy` | Domain truth / applicability / readiness policy |
| `ProcessRule` | Process Engine transition / handoff rules |
| `AutomationReaction` | Reaction to already-computed facts |
| `PresentationRule` | UI visibility / layout — never blockers |

Per ADR-019: domain policy computes truth; automation only reacts.

### 4. LibraryKind (this slice — only classes that exist)

| LibraryKind | Notes |
|-------------|-------|
| `FormComponent` | Forms Standard Library (Basic set) |
| `FieldDefinition` | Field Registry canonical fields |
| `CommunicationTemplate` | C2.1 published template versions |
| `DocumentMergeTemplate` | Merge / generate file body |
| `NotificationTemplate` | Code constants — not C2.1 |
| `ProcessTemplate` | WP/OSW steps — legacy relative to Process Engine |
| `DocumentChecklistTemplate` | `document_templates` — checklist JSON; **not** a gate |

### 5. Hard classifications (must not dual-classify)

| Object | ObjectKind | RuleKind (if any) | Rationale |
|--------|------------|-------------------|-----------|
| `RequirementDefinition` (+ alternatives / accepted evidence) | `ReferenceObject` | — | Answers *what* a requirement is |
| `RequirementPolicy` | `RuleObject` | `DomainPolicy` | Answers *when / for whom* it applies — **never** also ReferenceObject |
| `DocumentPack` (named set of reference objects) | `ReferenceObject` | — | Pack itself is not a rule |
| Pack applicability (citizenship, role, stage) | `RuleObject` | `DomainPolicy` | Separate from the pack |
| Field Registry fields | `LibraryObject` (`FieldDefinition`) | — | Reusable asset — not Forms stdlib, not DomainPolicy |
| `RequirementEvaluation` | `EvaluationFact` | — | Computed fact — not instance process lifecycle |
| `CandidateEvidence` | `RuntimeInstance` | — | Persisted fact — not evaluation |

### 6. Catalog row contract (closed fields)

Every L2 catalog row uses the same card:

| Field | Closed vocabulary / meaning |
|-------|----------------------------|
| `kind` | ObjectKind |
| `code` | Stable id |
| `owner` | Capability + module |
| `sot` | Canonical path (file / table / ADR) |
| `scope` | `platform` \| `module` \| `tenant` |
| `runtime_role` | `definition` \| `persisted_instance` \| `computed_fact` \| `executable_rule` \| `reusable_asset` |
| `status` | `canonical` \| `target` \| `bridge` \| `legacy` \| `forbidden_as_sot` |
| `integrity` | `aligned` \| `split` \| `incomplete` \| `skeleton` |
| `parameters` | Fields belonging to this object only |
| `rules` | Attached RuleKind codes (for reference/instance/library) |
| `consumers` | Ownership & Consumption Matrix |

**`status` vs `integrity` must not mix.** Example: DocumentType → `status=canonical`, `integrity=split`. Reaction Orchestrator → `status=target`, `integrity=skeleton`. “Split seeds” is never a status value.

**Row check question:** *What is this architecturally, and what is it allowed to do at runtime?* A checklist (`DocumentChecklistTemplate`) must not act as a gate (`runtime_role` catches the mistake).

### 7. Ownership & Consumption Matrix (closed verbs)

| Verb | Meaning |
|------|---------|
| `owns` | SoT and lifecycle |
| `writes` | May create/mutate instance or evidence without owning the class |
| `consumes` | Reads |
| `reacts` | Reacts to a fact (automation / communications) without writing domain SoT |
| `forbidden` | Must not |

Example: Recruitment may `writes` Candidate Evidence and initiate evaluation, but `consumes` RequirementEvaluation (owner = platform). Communications may `reacts` to facts and is `forbidden` from writing Recruitment stage.

### 8. Scope of first inventory slice

Documents / Requirements / Automation / Templates only. Candidate / Lead / Employee appear only as matrix consumers — not full entity cards. No JSON registry, ORM, code alignment, or fallback removal in this ADR.

### 9. Next catalog (explicitly out of scope)

State canon must be built **on top of** ADR-037 rows:

```text
ObjectKind → Object → State dimensions → State owner → Transition owner
```

Different vocabularies: publication lifecycle (DocumentType), instance lifecycle (Document), outcome (RequirementEvaluation), execution lifecycle (AutomationExecution), configuration/publication (RequirementPolicy). Never one shared bag of `approved` / `active` / `blocked` / `running` / `published`.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport; indexes Documents / Automations / Forms / Field Registry
- [x] Non-Goals not silently expanded into Owns
- [x] Does not become Document Type SoT or Requirement SoT
- [x] INV-16 Decision Priority: ownership and contracts before convenience
- [x] ADR references P-rules / Catalog — does not rewrite L0
- [x] L0 freeze: no constitution edit; no Architecture RFC required for meta-index

---

## Consequences

- Positive: shared classes before state canon; dual-classification of RequirementDefinition vs RequirementPolicy forbidden; DocumentPack vs applicability rules separated; status vs integrity separable for docs-lint / future guards.
- Negative: inventory must be maintained when new platform objects appear in this slice; dual-classified rows are an architecture bug.
- Follow-on (separate PRs): DocumentType code alignment (`integrity=split` → `aligned`); retire ruleset / `document_configs` as runtime inputs; ADR-019 3A-2…3A-4; state-dimension catalog.

---

## Alternatives considered

1. **New runtime registry table + API** — rejected for first PR; would mix ontology with migration.
2. **Docs-only informal tables without ADR vocabulary** — rejected; status/integrity/runtime_role need a closed contract before state catalog.
3. **Treat RequirementPolicy as ReferenceObject** — rejected; collapses definition and applicability.
4. **Treat DocumentPack as RuleObject when it has applicability** — rejected; pack remains named set; conditions are separate rules.

---

## Cross-references (updated in same change set)

- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — parent Platform Standardization Model; this ADR supplies Object Kind / Rules / Libraries under Vocabulary + Policy & Reuse
- [`ADR-039-state-lifecycle-inventory.md`](ADR-039-state-lifecycle-inventory.md) — state dimensions for this slice
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area status map (`object_kind` / `rules` / `libraries` = exists)
- [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) — L2 inventory + Ownership & Consumption Matrix
- [`../platform/state-lifecycle-inventory.md`](../platform/state-lifecycle-inventory.md) — L2 state dimensions
- [`platform-capability-catalog.md`](platform-capability-catalog.md) — Documents / Automations / Forms linkage
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — §0.1 index
- [`architecture-guide.md`](architecture-guide.md) — navigation entry
