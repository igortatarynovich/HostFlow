# Forms Product Layer P1 — Field Catalog (component registry)

**Status:** **READY** (design canon · implementation not started)  
**Epic:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md) · merge `29f4057f` / PR #43 · registry framing `8320dc7a` / PR #44  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE**  
**Unlocks:** Product Layer P2 (Builder) after **P1.3** (standard library)  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md) · [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md)

---

## Goal

Ship Field Catalog as a **component registry**, not a flat list of field type strings.

Abstraction shift:

| Before (weak) | After (strong) |
|---------------|----------------|
| `text` / `email` / `phone` / `select` | `TextInput` / `EmailInput` / `PhoneInput` / `Select` |
| type string | full component with its own contract |
| — | `DriverLicense` · `Passport` · `Address` · `SalaryRange` · `CompanySelector` · `VehicleSelector` |

Builder becomes a **thin client** of Field Catalog — not its owner. It shows the catalog, lays out instances, and saves composition. The same components can later power entity cards, internal CRM surfaces, mobile, and any uniform data-entry context.

---

## Architectural boundary

| Layer | Responsibility |
|-------|----------------|
| **Platform (COMPLETE)** | Runtime · Publication · Ledger · Validation · Normalization · Submission · Shared Intake · Audit |
| **Product / P1** | What components exist and how they behave end-to-end |
| **Builder (P2)** | Catalog UI + layout + persist composition only |

**Rule:** Builder **must not** invent field types. New capabilities = register a Catalog component once.

```text
Field Catalog (SoT)
  ↑ register / resolve / descriptors
Builder | Public Form | Entity cards | CRM | Mobile   ← clients, not owners
```

---

## Implementation plan — four small sprints

| Sprint | Name | Outcome | Builder |
|--------|------|---------|---------|
| **P1.1** | Registry | Register / find / get by id+version / version compatibility | still LOCKED |
| **P1.2** | Runtime descriptors | Builder / Public / Validation / Normalization descriptors via Catalog | still LOCKED |
| **P1.3** | Standard library | First Basic component set | **P2 may start** |
| **P1.4** | Extension API | Modules register their own components | Catalog grows without Builder changes |

### P1.1 — Registry

First step. Component registry only.

**Can:**

- register a component  
- find / list components  
- get by `component_id` + `component_version`  
- check version compatibility  

**Out:** Builder UI · descriptors surface · standard library · module extension API  

### P1.2 — Runtime descriptors

Each component exposes descriptors. Builder learns nothing about Email or Phone specifically — only:

> “Give me the descriptor.”

| Descriptor | Purpose |
|------------|---------|
| Builder descriptor | Palette / property editors / preview contract |
| Public renderer descriptor | Public Form render contract |
| Validation descriptor | Compose Sprint 4/5 validation |
| Normalization descriptor | Compose Sprint 5 canonical normalization |

(Storage contract remains part of the component definition; may be exposed as its own descriptor facet if needed.)

### P1.3 — Standard library

First HostFlow Forms component pack (minimal):

| Component | Role |
|-----------|------|
| Text | single-line |
| TextArea | multi-line |
| Number | numeric |
| Email | email |
| Phone | phone |
| Date | date |
| Checkbox | boolean |
| Radio | single choice |
| Select | single select |
| MultiSelect | multi select |
| File | upload |
| Hidden | non-visible value |

After P1.3, **Builder (P2) may start** — it already has a usable catalog.

### P1.4 — Extension API

Last P1 stage. Any module registers its own components; they appear in Catalog (and later Builder) automatically.

| Module | Example components |
|--------|-------------------|
| Recruitment | Driver License · CE Category · Tachograph Card |
| HR | PESEL · Bank Account |
| Fleet | Vehicle · Trailer |
| Service | Service Type |

No Builder changes required to adopt new domain components.

---

## Component descriptor (stable contract)

Each Catalog entry is a **versioned component** with:

| Field | Purpose |
|-------|---------|
| `component_id` | Stable id (e.g. `forms.field.email`, later `recruitment.field.driver_license`) |
| `component_version` | Version of the component definition |
| `category` / search tags | Discoverability |
| `supported_properties` | Allowed knobs |
| `config_schema` | Instance config schema |
| `validation_rules` / validation descriptor | Validate (compose Sprint 4/5) |
| `normalization_rules` / normalization descriptor | Normalize (compose Sprint 5) |
| `storage_contract` | Raw/normalized envelope shape |
| Builder / Public descriptors | Dual render contracts |

```text
Catalog.component (id + version)
        ↓
Client asks for descriptor(s) — does not hardcode Email/Phone logic
        ↓
Builder places instance (field_id, order, config ⊆ config_schema)
        ↓
Publish freezes schema referencing component_id (+ version pin)
        ↓
Public Form / validate / normalize / envelope use Catalog rules
```

---

## Design principles

1. **Component > type string** — strong abstraction with a full contract per entry.  
2. **Registry first** — P1.1 before descriptors, library, or extension.  
3. **Descriptors over hardcoding** — clients ask Catalog; they do not special-case Email/Phone.  
4. **Builder is a Catalog client** — not owner; same components reusable beyond public forms.  
5. **Extend Sprint 1–6 contracts** — no parallel schema/validation/storage stacks.  
6. **Surgical platform gaps only** — do not rewrite L0 contour.

---

## Scope

### In (across P1.1–P1.4)

- Registry + version compatibility  
- Runtime descriptors  
- Standard library (Basic set above)  
- Extension API for module-owned components  
- Contract tests for registry resolve + published schemas cite Catalog ids  

### Out

- Visual Builder UI (P2 — may start after P1.3)  
- Publish UI (P3) · Themes (P4) · Analytics (P5)  
- Domain mapping / second intake / Forms Outcome-KPI  

---

## DoD

### P1 overall

- [ ] P1.1–P1.4 complete  
- [ ] Published `forms.field_schema.v1` may only cite Catalog `component_id`s  
- [ ] Validation / normalization / storage resolve through Catalog  
- [ ] Extension API usable by at least one module smoke registration (test double OK)  
- [ ] Builder remains non-owner of types; P2 unlock after P1.3 documented  
- [ ] No rewrite of Sprint 1–6 foundation  

### Per-sprint

| Sprint | Gate |
|--------|------|
| P1.1 | register / find / get / version compatibility tests green |
| P1.2 | descriptor fetch contract tests green; no client hardcodes Email/Phone |
| P1.3 | standard library registered + schema citation tests |
| P1.4 | extension registration API + isolation/ownership tests |

---

## History

- 2026-07-18: Design canon after Product Layer epic merge `29f4057f` (#43).  
- 2026-07-18: Component registry framing `8320dc7a` (#44).  
- 2026-07-18: Implementation split into P1.1–P1.4; Builder as thin Catalog client.
