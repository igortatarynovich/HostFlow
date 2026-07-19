# Forms Product Layer P1 — Field Catalog (component registry)

**Status:** **ACTIVE** (decomposition canon · merge `51063d1c` / [PR #45](https://github.com/igortatarynovich/HostFlow/pull/45))  
**Epic:** [`forms-product-layer-epic.md`](forms-product-layer-epic.md) · merge `29f4057f` / PR #43 · registry framing `8320dc7a` / PR #44  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE**  
**Unlocks:** Product Layer P2 (Builder) **only after P1.3 Standard Library DoD**  
**Canon:** [`forms-public-contract.md`](../architecture/forms-public-contract.md) · [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md)

---

## Closed / active gates (after P1.3)

| Gate | Status |
|------|--------|
| P1 decomposition (P1.1–P1.4) | ✅ **ACTIVE** |
| **P1.1 Registry** | ✅ **COMPLETE** |
| **P1.2 Descriptors** | ✅ **COMPLETE** |
| **P1.3 Standard library** | ✅ **COMPLETE** (`0cf7fc00` / #52) |
| Basic Component Library | ✅ **ACTIVE** |
| Builder | ✅ **UNLOCKED** |
| `forms.feature_flags.builder_enabled` | **true** |
| **P1.4 Extension API** | ✅ **COMPLETE** ([`forms-product-p1-4-extension-api.md`](forms-product-p1-4-extension-api.md)) |
| P1 Product Layer Foundation | ✅ **COMPLETE** |
| Catalog contracts v1 | **FROZEN** ([`forms-field-catalog-v1-freeze.md`](../architecture/forms-field-catalog-v1-freeze.md)) |
| P2 Builder | **READY FOR IMPLEMENTATION** ([`forms-product-p2-builder.md`](forms-product-p2-builder.md)) |

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

| Sprint | Name | Outcome | Builder | Status |
|--------|------|---------|---------|--------|
| **P1.1** | Registry | Register / find / get by id+version / version compatibility | LOCKED | ✅ **COMPLETE** |
| **P1.2** | Runtime descriptors | Builder / Public / Validation / Normalization descriptors via Catalog | LOCKED | ✅ **COMPLETE** |
| **P1.3** | Standard library | First Basic component set | **UNLOCKED after DoD** | ✅ **COMPLETE** |
| **P1.4** | Extension API | Modules register own components | unlocked path | ✅ **COMPLETE** |

### P1.1 — Registry (✅ COMPLETE)

See [`forms-product-p1-1-registry.md`](forms-product-p1-1-registry.md). Platform-wide register/get/find/resolve_compatible; semver compatibility within major.

**Can:**

- register a component  
- find / list components  
- get by `component_id` + `component_version`  
- check version compatibility  

**Out:** Builder UI · descriptors surface · standard library · module extension API  

### P1.2 — Runtime descriptors (✅ COMPLETE)

See [`forms-product-p1-2-descriptors.md`](forms-product-p1-2-descriptors.md).

Each component exposes four **declarative** descriptors (no executable logic). Builder learns nothing about Email or Phone specifically — only:

> “Give me the descriptor.”

| Descriptor | Purpose |
|------------|---------|
| Builder descriptor | Palette / property editors / preview contract |
| Public descriptor | Public Form render contract |
| Validation descriptor | Compose Sprint 4/5 validation |
| Normalization descriptor | Compose Sprint 5 canonical normalization |

### P1.3 — Standard library (✅ COMPLETE)

See [`forms-product-p1-3-standard-library.md`](forms-product-p1-3-standard-library.md).

Register Basic components **only** via public Registry + Descriptors — no Catalog-core special cases.

After P1.3 DoD, **Builder is UNLOCKED**. Preferred sequence: **P1.4** then P2 Builder.

### P1.4 — Extension API (✅ COMPLETE)

See [`forms-product-p1-4-extension-api.md`](forms-product-p1-4-extension-api.md).

Modules register via a separate public surface; same validations; no Basic override; no silent version replace; `source` = platform | module; one module failure must not corrupt Catalog; no tenant extensions; Builder sees a unified catalog.

P1 foundation **COMPLETE**. Catalog contracts v1 **FROZEN**. **P2 Builder READY.**

| Module | Example components |
|--------|-------------------|
| Recruitment | Driver License · CE Category · Tachograph Card |
| HR | PESEL · Bank Account |
| Fleet | Vehicle · Trailer |
| Service | Service Type |

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
- 2026-07-18: **ACTIVE** — decomposition merged `51063d1c` (#45); P1.1 READY FOR IMPLEMENTATION; Builder LOCKED until P1.3.  
- 2026-07-18: P1.1 **COMPLETE** (`644b102a` / #47); P1.2 Descriptors **READY**.  
- 2026-07-18: P1.2 Design **ACTIVE**; Descriptor Contract READY FOR IMPLEMENTATION; descriptors must be declarative (no executable logic); P1.3 LOCKED.  
- 2026-07-18: P1.2 **COMPLETE** (`1f7b4aba` / #50); P1.3 Standard Library **READY FOR IMPLEMENTATION**.  
- 2026-07-19: P1.3 **COMPLETE** (`0cf7fc00` / #52); Builder **UNLOCKED**; P1.4 Extension API **READY FOR IMPLEMENTATION**.  
- 2026-07-19: P1.4 **COMPLETE**; Catalog v1 **FROZEN**; P1 foundation **COMPLETE**; P2 Builder **READY**.
