# Forms Product Layer — Epic

**Status:** **OPEN** (ready · not started)  
**Prerequisite:** Forms Sprint 1–6 **COMPLETE** — backend platform contour closed ([`forms-sprint-6.md`](forms-sprint-6.md) · merge `7e259f22` / PR #41)  
**Canon:** [`ADR-007`](../architecture/ADR-007-forms-platform-capability.md) · [`forms-public-contract.md`](../architecture/forms-public-contract.md)  
**Builder:** **LOCKED** until Product Layer P1 (Field Catalog) lands and unlocks P2 by gate

---

## Why this is an epic (not Sprint 7)

Sprint 1–6 built the **L0 Forms platform** (publish → validate → normalize → immutable envelope → Shared Intake).  

**Forms Product Layer** is the **user-facing product** on top of that platform. It does not rewrite foundation contracts; it configures and surfaces them.

```text
Platform (done)                         Product Layer (this epic)
─────────────────────────────────       ─────────────────────────────────
Publish / ledger / snapshots            P1 Field Catalog
Schema / validation / normalization  →  P2 Builder
Immutable submission envelope           P3 Publish UI
Shared Intake handoff / audit           P4 Themes
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
| Which field types exist | **Field Catalog** |
| Supported parameters / options | **Field Catalog** |
| Available validation rules | **Field Catalog** |
| Normalization behavior | **Field Catalog** (must compose Sprint 5 canonical normalization) |
| Builder presentation (palette / editors) | **Field Catalog** |
| Public Form render contract | **Field Catalog** |

### Builder must not invent field types

**Rule:** Builder **не имеет права** изобретать новые типы данных.  
Builder может **только** использовать типы и параметры из Field Catalog.

| Layer | Answers |
|-------|---------|
| **Field Catalog** | *What exists?* |
| **Builder** | *Which of those fields are on this form, in what order?* |

Consequences:

1. New types (Address, Passport, Driver License, Company, Location, Salary Range, Vehicle, …) are added **once** to Field Catalog.  
2. They become available in Builder, publish through existing runtime, and flow through existing validation / normalization / submission pipeline.  
3. Product work **extends** Sprint 1–6 contracts; it does **not** fork a second schema/validation/storage stack.  
4. If Builder work discovers a genuine gap, extend the platform **surgically** — do not rewrite the contour.

---

## Phases

| Phase | Name | Goal | Depends on |
|-------|------|------|------------|
| **P1** | Field Catalog | Library of field types, params, validation, normalization, Builder + Public render contracts | Sprint 1–6 |
| **P2** | Builder | Visual form assembly from Catalog blocks only | P1 |
| **P3** | Publish UI | Drafts, publish, version management over existing ledger/pointer | P2 (or thin admin on P1+) |
| **P4** | Themes | Public form presentation skins | P2/P3 |
| **P5** | Analytics | Views, submits, conversion, errors, sources | Envelope + Publish (read-only compose) |

### P1 — Field Catalog (next)

**In**

- Canonical field type registry (text, textarea, select, checkbox, file, phone, email, …)  
- Per-type params, validation hooks, normalization hooks  
- Builder palette metadata + Public Form render metadata  
- Contract tests that published schemas only reference Catalog types  

**Out**

- Visual Builder UI (P2)  
- Themes (P4)  
- Analytics (P5)  
- Domain mapping / second intake / Forms Outcome-KPI  

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
| Product Layer epic | **OPEN** |
| P1 Field Catalog | next |
| Builder (P2) | **LOCKED** until P1 DoD |
| Rewrite of Sprint 1–6 foundation | **FORBIDDEN** |

---

## History

- 2026-07-18: Opened after Sprint 6 COMPLETE (`7e259f22` / #41). Backend contour closed; product surface next.
