# Forms Product Layer P1 — Field Catalog (component registry)

**Status:** **READY** (design canon · implementation not started)  
**Epic:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md) · merge `29f4057f` / PR #43  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE**  
**Unlocks:** Product Layer P2 (Builder)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md) · [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md)

---

## Goal

Ship Field Catalog as a **component registry**, not a flat list of field type strings.

Builder becomes a universal composer: it shows the Catalog and persists only **form composition**. All type logic stays centralized in the Catalog and composes Sprint 1–6 runtime contracts.

---

## Architectural boundary (reaffirmed)

| Layer | Responsibility |
|-------|----------------|
| **Platform (done)** | Runtime · Publication · Ledger · Validation · Normalization · Submission · Shared Intake · Audit |
| **Product / P1** | What components exist and how they behave end-to-end |
| **Builder (P2)** | Which Catalog components are on this form, in what order |

**Rule:** Builder **must not** invent field types. New capabilities = register a Catalog component once.

---

## Component descriptor (stable contract)

Each Catalog entry is a **versioned component** with:

| Field | Purpose |
|-------|---------|
| `component_id` | Stable identifier (e.g. `forms.field.text`, `forms.field.phone`) |
| `component_version` | Semver / integer version of the component definition |
| `category` / search tags | Discoverability in Builder palette |
| `supported_properties` | Allowed configuration knobs |
| `config_schema` | JSON Schema (or equivalent) for instance config |
| `validation_rules` | How values are validated (compose Sprint 4/5 contracts) |
| `normalization_rules` | How values are normalized (compose Sprint 5 canonical paths) |
| `storage_contract` | How the answer is represented in raw/normalized envelope |
| `builder_renderer` | How the component is edited / previewed in Builder |
| `public_renderer` | How the component is rendered on Public Form |

```text
Catalog.component (id + version)
        ↓
Builder places instance (field_id, order, config ⊆ config_schema)
        ↓
Publish freezes schema referencing component_id (+ version pin)
        ↓
Public Form uses public_renderer
        ↓
validate / normalize / envelope use Catalog rules
```

---

## Design principles

1. **Registry, not enum dump** — components are first-class, versioned artifacts.  
2. **Composition only in Builder** — form definition stores references + config, not ad-hoc type logic.  
3. **One registration scales the platform** — Address / Passport / Driver License / Company / Location / Salary Range / Vehicle arrive via Catalog; Builder/runtime/pipeline unchanged.  
4. **Extend Sprint contracts** — Catalog hooks into `forms.field_schema.v1`, `forms.normalized_answers.v1`, submission envelope; no parallel stacks.  
5. **Surgical platform gaps only** — if P1 needs a missing hook, extend surgically; do not rewrite L0 contour.

---

## Scope

### In

- Component registry model + stable `component_id` / version  
- Initial Basic set (text, textarea, select, checkbox, file, phone, email, …) as Catalog components  
- config_schema · validation · normalization · storage_contract bindings  
- Builder + Public renderer **contracts** (metadata; full UI may wait for P2/P4)  
- Search / categorization metadata  
- Contract tests: published schemas only reference registered components  

### Out

- Visual Builder UI (P2)  
- Publish UI (P3)  
- Themes (P4)  
- Analytics (P5)  
- Domain mapping / second intake / Forms Outcome-KPI  

---

## DoD (implementation gate)

- [ ] Component registry exists with versioned descriptors  
- [ ] Basic components registered and covered by contract tests  
- [ ] Published `forms.field_schema.v1` may only cite Catalog `component_id`s  
- [ ] Validation / normalization / storage resolve through Catalog hooks  
- [ ] Builder remains LOCKED for inventing types; P2 unlock documented  
- [ ] No rewrite of Sprint 1–6 foundation  

---

## History

- 2026-07-18: Design canon after Product Layer epic merge `29f4057f` (#43).
