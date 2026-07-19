# Intake Canonical Input Matrix — Epic

**Status:** **ACTIVE** (design)  
**Matrix artifact:** [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) · **READY**  
**Prerequisite:** Forms Builder MVP **COMPLETE** (`4cb2a148` / [PR #61](https://github.com/igortatarynovich/HostFlow/pull/61))  
**Parents:** [`ADR-024`](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md) · [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md)  
**Unlocks (later):** Flights / Intake Routing runtime split · handler `module_owner` correction · queue separation  

---

## Why this epic (before routes)

Builder MVP closed the Forms composition path. The next platform risk is **mixed Candidate Application and Sales Inquiry queues**.

Fixing that starts with a **canonical input matrix**, not with new route code:

```text
Source profile → Provider → Published form binding → route_intent → intake_handoff → Destination
```

Until this matrix is frozen, route implementation will re-encode the current mix under new names.

---

## Goal

One Forms Platform accepts submissions; **Intake Routing** alone decides which business process receives the canonical handoff.

| Minimal split | Destination |
|---------------|-------------|
| `candidate_application` | Recruitment intake |
| `sales_inquiry` | Sales intake |

Recruitment and Sales **must not** depend on Public Form ownership.

---

## Scope

### In (this epic)

- Canonical matrix doc (READY)  
- Vocabulary anti-collision  
- Debt register (handlers / defaults / Lead-centric queues)  
- Status pointers from Forms / Acquisition / Intake foundation  

### Out

- IntakeRouter / handler implementation  
- Migrations / FE queue rebuild  
- Stage 3E Timeline  
- Forms P3 Publish UI  

---

## Gates

| Gate | Status |
|------|--------|
| Forms Builder MVP | ✅ COMPLETE (`4cb2a148`) |
| Canonical Input Matrix | ✅ **READY** |
| Intake Routing Matrix epic | ✅ **ACTIVE** (design) |
| Flights / Intake Routing runtime | **LOCKED** until matrix accepted |
| Forms P3–P5 | **LOCKED** |

---

## Success criterion

Operators and implementers can answer, for any published form binding:

1. Which **Source profile** owns routing?  
2. Which **Provider** adapts the signal?  
3. Which **Published form** is the Endpoint?  
4. Which **`route_intent`** is SoT?  
5. What **`intake_handoff`** shape Shared Intake receives?  
6. Which **Destination module** owns the Result object?  

Without inventing FormPurpose / Goal Type / `application_kind` as routing SoT.

---

## History

- 2026-07-19: Opened ACTIVE after Builder MVP; matrix READY; runtime routes still LOCKED.
