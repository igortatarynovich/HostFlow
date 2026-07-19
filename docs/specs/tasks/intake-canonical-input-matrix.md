# Intake Canonical Input Matrix — Epic

**Status:** **COMPLETE**  
**Matrix artifact:** [`../architecture/intake-canonical-input-matrix.md`](../architecture/intake-canonical-input-matrix.md) · **ACCEPTED / FROZEN**  
**Next:** [`intake-runtime-split-v1.md`](intake-runtime-split-v1.md) · **READY FOR IMPLEMENTATION**  
**Prerequisite:** Forms Builder MVP **COMPLETE** (`4cb2a148` / [PR #61](https://github.com/igortatarynovich/HostFlow/pull/61))  
**Parents:** [`ADR-024`](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [`intake-routing-foundation.md`](../modules/intake-routing-foundation.md) · [`ADR-023`](../architecture/ADR-023-recruitment-sales-module-separation.md)  

---

## Why this epic (before routes)

Builder MVP closed the Forms composition path. The next platform risk is **mixed Candidate Application and Sales Inquiry queues**.

Fixing that started with a **canonical input matrix**, not with new route code:

```text
Source profile → Provider → Published form binding → route_intent → intake_handoff → Destination
```

The matrix is now **ACCEPTED / FROZEN**. Runtime isolation continues in Intake Runtime Split V1.

---

## Goal (achieved)

One Forms Platform accepts submissions; **Intake Routing** alone decides which business process receives the canonical handoff.

| Minimal split | Destination |
|---------------|-------------|
| `candidate_application` | Recruitment intake |
| `sales_inquiry` | Sales intake |

Recruitment and Sales **must not** depend on Public Form ownership.

---

## Scope

### In (this epic) — done

- Canonical matrix doc (**ACCEPTED / FROZEN**)  
- Vocabulary anti-collision  
- Debt register (handlers / defaults / Lead-centric queues)  
- Status pointers from Forms / Acquisition / Intake foundation  

### Out (handed to Runtime Split)

- IntakeRouter / handler implementation (R1–R6)  
- Migrations / FE queue rebuild  
- Stage 3E Timeline  
- Forms P3 Publish UI  

---

## Gates

| Gate | Status |
|------|--------|
| Forms Builder MVP | ✅ COMPLETE (`4cb2a148`) |
| Canonical Input Matrix | ✅ **ACCEPTED / FROZEN** |
| Intake Routing Matrix epic | ✅ **COMPLETE** |
| Intake Runtime Split V1 | **READY FOR IMPLEMENTATION** |
| Flights / Intake Routing runtime | **UNLOCKED** |
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
- 2026-07-19: Matrix **ACCEPTED / FROZEN**; epic **COMPLETE**; Runtime Split V1 opened; runtime UNLOCKED.
