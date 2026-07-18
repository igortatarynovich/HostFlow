# Forms Product Layer — Epic

**Status:** **OPEN** · **ACTIVE** (canon after merge `29f4057f` / [PR #43](https://github.com/igortatarynovich/HostFlow/pull/43))  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE** — backend platform contour closed ([`forms-sprint-6.md`](forms-sprint-6.md) · merge `7e259f22` / PR #41)  
**Canon:** [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md) · [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED** until Product Layer P1 (Field Catalog) lands and unlocks P2 by gate  
**P1 task:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Why this is an epic (not Sprint 7)

Sprint 1–6 built the **L0 Forms platform** (publish → validate → normalize → immutable envelope → Shared Intake).  

**Forms Product Layer** is the **user-facing product** on top of that platform. It does not rewrite foundation contracts; it configures and surfaces them.

```text
Platform (COMPLETE)                     Product Layer (OPEN)
─────────────────────────────────       ─────────────────────────────────
Runtime / Publication / Ledger          P1 Field Catalog (component registry)
Validation / Normalization           →  P2 Builder
Submission / Shared Intake / Audit      P3 Publish UI
                                        P4 Themes
                                        P5 Analytics
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

Three HostFlow platform layers:

| Layer | Role |
|-------|------|
| **Platform** | Tenants, entities, communications, shared infra |
| **Acquisition** | Intake + routing spine |
| **Forms** | Universal data-collection platform |

Downstream modules (Recruitment, HR, Services, Sales) **compose** Forms — they do not own parallel questionnaire / validation / answer-storage engines.

---

## Unlock gates

| Gate | Status |
|------|--------|
| Forms Sprint 1–6 (L0 platform) | ✅ COMPLETE |
| Forms Product Layer epic | ✅ **ACTIVE** (`29f4057f`) |
| P1 decomposition (P1.1–P1.4) | ✅ **ACTIVE** (`51063d1c` / #45) |
| **P1.1 Registry** | ✅ **COMPLETE** (`644b102a` / #47) |
| Field Catalog Registry / Identity / Compatibility | ✅ **ACTIVE** |
| **P1.2 Descriptors** | **READY** |
| Builder (P2) | **LOCKED** |
| Unlock Builder | **completed P1.3 Standard Library** only |
| Rewrite of Sprint 1–6 foundation | **FORBIDDEN** |

---

## History

- 2026-07-18: Opened after Sprint 6 COMPLETE (`7e259f22` / #41). Backend contour closed; product surface next.  
- 2026-07-18: Canon merged PR #43 (`29f4057f`). P1 framed as component registry (not type enum).  
- 2026-07-18: P1 split into Registry → Descriptors → Standard library → Extension API; Builder = Catalog client.  
- 2026-07-18: P1 decomposition ACTIVE (`51063d1c` / #45); P1.1 READY FOR IMPLEMENTATION.  
- 2026-07-18: P1.1 COMPLETE (`644b102a` / #47); P1.2 Descriptors READY.
