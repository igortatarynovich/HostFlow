# Oświadczenie country-set drift

**Status:** **OPENED** — blocker. Not the Active Product. Not corrected in the Poland baselines.  
**Date:** 2026-10-02  
**Parents:** [Poland presets](../architecture/poland-work-authorization-presets.md) · [Poland brief](poland-work-authorization-presets.md)

> Who may use `employer_declaration` is a country rule. It is not a submission requirement of either Poland baseline.  
> This task does not edit `citizenship_rules.json` or `oswiadczenie_eligible_alpha2`. Runtime is not authorized.

---

## Blocker

The in-force country rule is the regulation of 21 November 2025 (Dz.U. 2025 poz. 1617; [ELI DU/2025/1617](https://eli.gov.pl/eli/DU/2025/1617/ogl)), in force since 1 December 2025. § 2 names citizens of Armenia, Belarus, Moldova, and Ukraine. § 3 only continues a declaration already entered before that date.

The product lists do not match that rule:

| List | What it contains | Drift |
|---|---|---|
| `citizenship_rules.json` `oswiadczenie_list` | `AM`, `BY`, `GE`, `MD`, `UA` | includes Georgia |
| pack `oswiadczenie_eligible_alpha2` | `UA`, `BY`, `MD`, `GE` | includes Georgia and omits Armenia |

## What this task is not

It is not a Poland preset row. It is not a `kod_zawodu` mapping. It does not change who the two baselines require documents from. Poland Work Authorization Presets Gate **PASS** does not close this blocker.
