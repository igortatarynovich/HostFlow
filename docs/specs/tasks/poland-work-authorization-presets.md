# Poland Work Authorization Presets

**Status:** **OPENED** — Poland Work Authorization Presets Gate **PASS**, 2026-10-03. No `kod_zawodu` row. Feat locked. Runtime not authorized.  
**Date:** 2026-10-02  
**Trusted base:** `integration/release-product-a-b` @ `020cb4e5` ([#402](https://github.com/igortatarynovich/HostFlow/pull/402))  
**Parents:** [presets](../architecture/poland-work-authorization-presets.md) · [Work Authorization Procedure](work-authorization-procedure.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> The [accepted contract](../architecture/work-authorization-procedure-contract.md) stays the selector. This slice does not reopen it.  
> For `PL`, the closed `procedure_type` set is `employer_declaration` and `work_permit_a`.  
> Many `kod_zawodu` values resolve to one procedure baseline. The two baselines are filled. A profession preset is company policy and is not an official attachment list. `profession_is_regulated` is optional and does not block this gate. The declaration country-set drift is a separate blocker. Minimal Recruitment → HR stays **not** scheduled. HostFlow v1 is not release-ready.

---

## Problem

The accepted selector needs a `procedure_type` before a Polish preset can name requirements. HostFlow already chooses between two Poland work-authorization procedures. Those choices are stored as document codes.

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
An operator cannot tell which Poland work-authorization procedure a preset belongs to, because the product stores that choice as a document code.

**Completion proof (named consumer):**
For country `PL`, a preset selects one of the closed procedure types, and a document code is not that type. Many occupation codes resolve to that procedure's one baseline. The two official baselines are filled. A profession preset carries a purpose the company sets. Poland Work Authorization Presets Gate **PASS**.

**False close (reject):** one preset row per `kod_zawodu`, a KZiS to regulated mapping, or a Driver CE default treated as the official attachment list of these procedures.

## Order

1. This brief and the [procedure type set](../architecture/poland-work-authorization-presets.md). The set is closed.
2. The preset schema: one baseline per procedure, five requirement kinds, and `kod_zawodu` as the profession key.
3. The two filled baselines. No row per `kod_zawodu`.
4. KZiS identifies the profession. `profession_is_regulated` is optional and does not block the gate. Poland Work Authorization Presets Gate **PASS**.
5. Runtime only after that. Not authorized.

## What stays closed

| Slice | State |
|---|---|
| Work Authorization Procedure contract | **PASS**; not reopened |
| `kod_zawodu` rows | not written |
| Two procedure baselines | filled; Poland Work Authorization Presets Gate **PASS** |
| Declaration country lists | blocker [oswiadczenie-country-set-drift.md](oswiadczenie-country-set-drift.md); not corrected by this PASS |
| `profession_is_regulated` | optional; does not block the gate; further research stopped |
| Filing to praca.gov.pl | formularz ids named; no public submit API; connection not implemented |
| Legal Eligibility decision chain | unchanged; Matrix Gate is not passed |
| Runtime, pack, engine | not authorized; feat locked |
| Minimal Recruitment → HR | queued, not scheduled |

## History

- 2026-10-03: **Filing workflow named.** `employer_declaration` files as `PSZ-OPPC`. `work_permit_a` files as `ZC-WWZPP`. Attachment origin stays visible. No public submit API was found. HRappka's published path is the employer's portal session. Browser automation is not the first path. Further research of `profession_is_regulated` stops.
- 2026-10-03: **Profession preset is company policy.** Official baselines stay the system Poland preset. A requirement purpose is `employment`, `submission`, or `both`. `profession_is_regulated` is optional and does not block the gate. A Driver CE default is not the official attachment list. `r5_required_set` stays the only writer.
- 2026-10-03: **Poland Work Authorization Presets Gate PASS.** Two baselines. Shared requirement schema. Fee policy differs. Temporary-agency agreement is conditional. Authority-requested extras stay outside the baseline. No `kod_zawodu` row. Existing evidence is reused. `r5_required_set` stays the only writer. Country-set drift stays a separate blocker. Feat stays locked. Runtime is not authorized.
- 2026-10-02: **Baselines filled.** `employer_declaration` and `work_permit_a`. Same declarations, conditionals, and translation constraint. Payment amount differs. `profession_is_regulated = true` requires qualification evidence and names no licence. No `kod_zawodu` row. Poland Work Authorization Presets Gate **not PASS**. Country-set drift stays a separate blocker.
- 2026-10-02: **Preset schema named.** One baseline per `employer_declaration` and `work_permit_a`. Many `kod_zawodu` values resolve to that baseline. Five requirement kinds. No filled preset. No `kod_zawodu` row. Poland Work Authorization Presets Gate **not PASS**. The declaration country-list drift is recorded and not corrected here.
- 2026-10-02: **Procedure types named.** Closed set for `PL`: `employer_declaration`, `work_permit_a`. Document codes are not procedure types. No `kod_zawodu` row. No document list. Poland Work Authorization Presets Gate **not PASS**. Feat locked. Runtime not authorized.
