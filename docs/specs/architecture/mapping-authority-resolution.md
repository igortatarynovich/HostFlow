# Mapping Authority Resolution

**Status:** **Accepted** (L2 contract — Mapping Resolution Gate)  
**Date:** 2026-09-04  
**Trusted base:** `integration/release-product-a-b` @ `8b961598`  
**Related:** [`mapping-authority-contract.md`](mapping-authority-contract.md) (`mapping_authority.v1`) · [`../tasks/mapping-authority.md`](../tasks/mapping-authority.md) · [`ADR-021`](ADR-021-unified-intake-resolution-model.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for which rule applies), **INV-16** (contract before a second resolver). Does not rewrite L0. Does not mint a fourth mapping store.

> This file is the **SoT** for MA-2: ingest consults exactly one resolver over the MA-1 write authority.  
> Machine copy: `resolve_mapping_authority` in `backend/app/entity_profile/mapping_resolve.py`.  
> Binding / contract health / option maps remain [MA-1 contract](mapping-authority-contract.md). This slice does not add mapping semantics.

---

## Resolver (one)

**Question:** for this source, which mapping rules apply?

**Answerer:** `resolve_mapping_authority` reading **only** `intake_source_profiles.mapping_rules`.

Callers (ingest, C-5 mapping façade, leftover Meta wrapper) must not implement a second fallback. The previous silent precedence chain (`profile → meta_lead_form_mappings.mapping_rules → meta_lead_settings.field_mapping`) is **removed**, not documented as ingest behavior.

`mapping_applied_v1` remains applied-rule evidence (`rules_source = authority`). It is not contract health SoT.

---

## Leftover stores (read-through / migrate)

`meta_lead_form_mappings.mapping_rules` and `meta_lead_settings.field_mapping` stay classified leftover. They must not gain new authority writes.

When the authority is empty **and** an intake source profile exists, the resolver copies leftover rules into `intake_source_profiles.mapping_rules` (migrate once) and then returns the authority. Meta admin form-mapping writes are write-through onto the matching profile when that profile already exists.

When no profile exists, leftover stores do **not** answer. Empty authority is mapping uncertainty (MA-1: not candidate `no_fit`).

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Mapping Authority. Field Registry still owns destination identity. Acquisition C-5 remains an editor over the surviving store (MA-3 folds editors). |
| 2 | Not a new capability. Collapses the leftover fallback chain named in MA-1. |
| 3 | One resolver (`resolve_mapping_authority`). No new adapter. Evaluation still reads canonical facts only. |
| 4 | CL6 stays CL6. Sales convert stays Sales. OCR stays later. No Field Registry fork. No Zapier product. |
| 5 | Tenant `field_mapping` / per-form Meta rules remain leftover, not a second overlay product. |
| 6 | SoT for “which rule applies?” = this file + `resolve_mapping_authority`. MA-1 remains SoT for the operator question and write. |
| 7 | No new event family. `mapping_applied_v1` stays applied-rule evidence. |
| 8 | **Requires:** MA-1 write authority, intake source profile, ADR-021 route. **Optional:** leftover Meta stores as migrate input. |
| 9 | No new licence. |
| 10 | Public contract **additive**: one resolver. No breaking Hub/Passport change. |

**INV-01:** one SoT for which rules apply. **INV-16:** this resolver before a second ingest fallback.

---

## False close

Reject: documenting the old chain as “still how ingest works”; a second resolver in leads ingest; treating leftover Meta stores as a second write authority; collapsing binding and contract health; absorbing Sales convert / OCR / CL6; opening MA-3 editor in this PR; starting External Intake / Hiring E2E / min HR; Foundation ✅; a thirteenth write of the operator question; transformation DSL / Zapier-style conditions.

---

## Consequences

- MA-3 ships one editor over this authority. Remaining surfaces become views or are retired.  
- MA-4 makes `qualified_code` the only write vocabulary on the intake path.  
- RPM / evaluators still consume canonical facts only.

---

## History

- 2026-09-04: Mapping Resolution Gate **PASS**. One resolver over `intake_source_profiles.mapping_rules`. Active Product → MA-3 (brief; feat locked).
