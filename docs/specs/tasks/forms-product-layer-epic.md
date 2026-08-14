# Forms Product Layer — Epic

**Status:** **OPEN** · Product Track = [Forms Platform C3 Builder Runtime](forms-platform-c3-builder-runtime.md) (**active**) · C1–C2 ✅ · P3 Publish UI / P4 / P5 **LOCKED**  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE** — backend platform contour closed ([`forms-sprint-6.md`](forms-sprint-6.md) · merge `7e259f22` / PR #41)  
**Canon:** [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md) · [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**P1 task:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md) ✅ **CLOSED**  
**P2 task:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md) · Builder MVP **COMPLETE** (P2.1–P2.5) · P3 LOCKED  
**Out of this Product Track slice:** Stage 5 settings/enable-disable · R6 table-cutover · P3 Publish UI / P4 Themes / P5 Analytics (locked) · C4 Form Runtime

---

## Why this is an epic (not Sprint 7)

Sprint 1–6 built the **L0 Forms platform** (publish → validate → normalize → immutable envelope → Shared Intake).  

**Forms Product Layer** is the **user-facing product** on top of that platform. It does not rewrite foundation contracts; it configures and surfaces them.

```text
Platform (COMPLETE)                     Product Layer
─────────────────────────────────       ─────────────────────────────────
Runtime / Publication / Ledger          P1 Field Catalog ✅ CLOSED (v1 FROZEN)
Validation / Normalization           →  P2 Builder MVP COMPLETE (P2.1–P2.5) · P3 Publish UI LOCKED
Submission / Shared Intake / Audit      P3 Publish UI LOCKED
                                        P4 Themes LOCKED
                                        P5 Analytics LOCKED
```

Full chain (target):

```text
Builder → Publish → Public Form → Validation → Normalization
  → Immutable Submission → Shared Intake → Routing
  → Recruitment / Sales / HR / Service
```

Missing today: only the **left** (user-facing) side.

---

## Architectural rule (normative)

### Field Catalog is Source of Truth

Field Catalog определяет:

| Concern | Owner |
|---------|--------|
| Which field / component types exist | **Field Catalog** |
| Supported properties / config schema | **Field Catalog** |
| Available validation rules | **Field Catalog** |
| Normalization behavior | **Field Catalog** (compose Sprint 5 canonical normalization) |
| Storage contract (raw/normalized shape) | **Field Catalog** |
| Builder presentation (palette / editors) | **Field Catalog** |
| Public Form render contract | **Field Catalog** |

### Builder must not invent field types

**Rule:** Builder **не имеет права** изобретать новые типы данных.  
Builder может **только** использовать компоненты и параметры из Field Catalog.

| Layer | Answers |
|-------|---------|
| **Field Catalog** | *What exists?* |
| **Builder** | *Which of these components are on this form, in what order?* |

This prevents the common low-code failure mode where the visual editor gradually **dictates** platform architecture.

Consequences:

1. New components (Address, Passport, Driver License, Company, Location, Salary Range, Vehicle, …) are registered **once** in Field Catalog.  
2. They become available in Builder, publish through existing runtime, and flow through existing validation / normalization / submission pipeline — **without Builder changes**.  
3. Product work **extends** Sprint 1–6 contracts; it does **not** fork a second schema/validation/storage stack.  
4. If Builder work discovers a genuine gap, extend the platform **surgically** — do not rewrite the contour.

---

## Phases

| Phase | Name | Goal | Depends on |
|-------|------|------|------------|
| **P1** | Field Catalog | **Component registry** (not a flat type list) | Sprint 1–6 |
| **P2** | Builder | Visual form assembly from Catalog components only | P1 |
| **P3** | Publish UI | Drafts, publish, version management over existing ledger/pointer | P2 (or thin admin on P1+) |
| **P4** | Themes | Public form presentation skins | P2/P3 |
| **P5** | Analytics | Views, submits, conversion, errors, sources | Envelope + Publish (read-only compose) |

### P1 — Field Catalog as component registry

See [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md).

**Not** a flat type enum (`text` / `email`) — **versioned components** (`TextInput` / `EmailInput` / `DriverLicense` / …) with full contracts.

Implementation split:

| Sprint | Focus |
|--------|--------|
| **P1.1** Registry | register · find · get(id/version) · version compatibility |
| **P1.2** Runtime descriptors | Builder / Public / Validation / Normalization descriptors |
| **P1.3** Standard library | Text · TextArea · Number · Email · Phone · Date · Checkbox · Radio · Select · MultiSelect · File · Hidden → **Builder may start** |
| **P1.4** Extension API | Modules register own components (Recruitment / HR / Fleet / Service) |

**Builder (P2)** is a thin Catalog **client**: show catalog · lay out · save composition. Not the owner of types. Same components may later serve entity cards, CRM internals, mobile, and other uniform input surfaces.

Builder stores **composition only**; logic stays in Catalog.

### P2–P5

Deferred detailed DoD until prior phase COMPLETE. Same non-goals as Sprint 1–6 for ownership: compose Acquisition; no Forms-owned routing/Outcome/KPI.

---

## Platform posture

Forms is a **platform capability**, same class as EntityWorkspace, ListWorkspace, Analytics Kit, RBAC, and Automations — not a product module (Recruitment / HR / Fleet / Finance / Services). Those modules consume one Forms Platform; they do not own parallel form stacks. Compatibility bar is **stricter** than for product modules.

| Layer | Role |
|-------|------|
| **Platform** | Tenants, entities, communications, shared infra, **Forms**, RBAC, Automations, workspace kits |
| **Acquisition** | Intake + routing spine |
| **Product modules** | Recruitment / HR / Fleet / Finance / Services — consume Forms Adapter |

Phase C ladder: C1 seal ✅ → C2 runtime gates ✅ → [C3 Builder Runtime](forms-platform-c3-builder-runtime.md) ← active → C4 Form Runtime → C5 Form Execution → C6 Optimization. C4 opens only after C3.

---

## Unlock gates

| Gate | Status |
|------|--------|
| Forms Sprint 1–6 (L0 platform) | ✅ COMPLETE |
| Forms Product Layer epic | ✅ **ACTIVE** (`29f4057f`) |
| P1 decomposition (P1.1–P1.4) | ✅ **ACTIVE** (`51063d1c` / #45) |
| **P1.1 Registry** | ✅ **COMPLETE** (`644b102a` / #47) |
| Field Catalog Registry / Identity / Compatibility | ✅ **ACTIVE** |
| **P1.2 Descriptors** | ✅ **COMPLETE** (`1f7b4aba` / #50) |
| Descriptor Contract / Declarative Multi-client Surface | ✅ **ACTIVE** |
| **P1.3 Standard Library** | ✅ **COMPLETE** (`0cf7fc00` / #52) |
| Basic Component Library / Builder UNLOCKED | ✅ **ACTIVE** |
| **P1.4 Extension API** | ✅ **COMPLETE** (`97aac4e3` / #54) |
| Extension Component Platform / Module Registration | ✅ **ACTIVE** |
| P1 Product Layer Foundation | ✅ **CLOSED** |
| Field Catalog contracts v1 | **FROZEN** |
| P2.1–P2.5 Builder | ✅ **COMPLETE** (MVP) |
| Builder Catalog Consumption | ✅ **ACTIVE** |
| P3 Publish UI / P4 Themes / P5 Analytics | **LOCKED** (C3 is Builder Runtime, not Publish UI — [forms-platform-c3-builder-runtime.md](forms-platform-c3-builder-runtime.md)) |
| Rewrite of Sprint 1–6 foundation | **FORBIDDEN** |
| Executable logic inside descriptors | **FORBIDDEN** |
| Catalog-core special cases for stdlib ids | **FORBIDDEN** |
| Silent Basic override / silent version replace | **FORBIDDEN** |
| Breaking changes to frozen Catalog v1 | **FORBIDDEN** (extend compatibly or add v2) |
| Builder inventing types / forking validation | **FORBIDDEN** |
| Builder UI before P2.1–P2.4 + UI gate | ✅ P2.5 **COMPLETE** |

---

## History

- 2026-07-18: Opened after Sprint 6 COMPLETE (`7e259f22` / #41). Backend contour closed; product surface next.  
- 2026-07-18: Canon merged PR #43 (`29f4057f`). P1 framed as component registry (not type enum).  
- 2026-07-18: P1 split into Registry → Descriptors → Standard library → Extension API; Builder = Catalog client.  
- 2026-07-18: P1 decomposition ACTIVE (`51063d1c` / #45); P1.1 READY FOR IMPLEMENTATION.  
- 2026-07-18: P1.1 COMPLETE (`644b102a` / #47); P1.2 Descriptors READY.  
- 2026-07-18: P1.2 Design ACTIVE; declarative-descriptors rule; Descriptor Contract READY FOR IMPLEMENTATION.  
- 2026-07-18: P1.2 COMPLETE (`1f7b4aba` / #50); P1.3 READY FOR IMPLEMENTATION.  
- 2026-07-19: P1.3 COMPLETE (`0cf7fc00` / #52); Builder UNLOCKED; P1.4 READY FOR IMPLEMENTATION.  
- 2026-07-19: P1.4 COMPLETE; Catalog v1 FROZEN; P1 foundation COMPLETE; P2 Builder READY.  
- 2026-07-19: P1.4 merge `97aac4e3` (#54) recorded; P2 hard boundary: Catalog client only.  
- 2026-07-19: P2 Design ACTIVE (`a142bd0c` / #55); P2.1–P2.5 plan; P2.1 READY; P3–P5 LOCKED.  
- 2026-07-19: P2.1 COMPLETE — `forms.builder.read_model.v1`; P2.2 READY; process rule: check existing assets.  
- 2026-07-19: P2.1 merge `ae767201` (#57); Catalog Consumption ACTIVE; P2.2 COMPLETE; P2.3 READY.  
- 2026-07-19: P2.3 Composition Commands COMPLETE; P2.4 Persistence READY.  
- 2026-07-19: P2.4 Draft Persistence COMPLETE; P2.5 UI gate OPEN.  
- 2026-07-19: P2.5 Minimal Builder UI COMPLETE — Builder MVP closed; next focus Flights / Intake Routing.  
- 2026-07-19: Intake Canonical Input Matrix epic ACTIVE; matrix READY (no route implementation yet).  
- 2026-07-19: Matrix ACCEPTED / FROZEN; Intake Runtime Split V1 READY; Forms P3–P5 remain LOCKED.  
- 2026-08-14: C1+C2 merged; Product Track → C3 Builder Runtime; P3 Publish UI / P4 / P5 stay locked.
