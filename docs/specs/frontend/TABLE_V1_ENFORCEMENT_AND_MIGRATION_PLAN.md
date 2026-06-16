# TABLE_V1_ENFORCEMENT_AND_MIGRATION_PLAN

Status: Complete  
Date: 2026-05-31  
Input: `TABLE_V1.md`, `TABLE_V1_ADAPTATION_BACKLOG.md`  
Purpose: define how `TABLE_V1` becomes real for operational list tables.

## Question Answered

> Как TABLE_V1 станет реальным стандартом, а не только документом?

---

## 1) Enforcement

| Mechanism | What it blocks | Status |
|---|---|---|
| PR review checklist | New non-compliant operational tables | ✅ PR template |
| Migrate on touch | Legacy tables gain TABLE_V1 on edit | ✅ |
| Governance exceptions | Bulk-off, pagination model C | REF-UI only |
| TABLE CI grep | Ad-hoc table spacing in diff | ⬜ Phase 2 |

Foundation CI (`foundation:check`) covers deprecated tokens in table markup.

---

## 2) Forbidden in New Operational List Tables

See `TABLE_V1.md` §7 Deprecated list.

---

## 3) Migration Phases

| Phase | Target | Status |
|---|---|---|
| **Lock** | `TABLE_V1.md` spec | ✅ |
| **Validation** | Manual checklist before M1 | ⬜ |
| **M1** | Vacancies alignment | ⬜ |
| **M2** | Leads table mode | ⬜ |
| **M3** | Employees | ⬜ |
| **M4** | Companies | ⬜ |
| **Optional** | Extract shared `TableFrame` utilities | When duplication justifies |

No big-bang rewrite of candidates reference — adapt outward.

---

## 4) Success Metrics

| Metric | Target |
|---|---|
| New entity list tables TABLE_V1 compliant | 100% |
| M1 vacancies frame alignment | Sticky header, filter placement, bulk zone |
| Legacy module count decreasing | Non-increasing per sprint |

---

## 5) Chain Status

| Artifact | Status |
|---|---|
| `TABLE_V1.md` | ✅ Locked |
| **`TABLE_V1_ENFORCEMENT_AND_MIGRATION_PLAN.md`** | ✅ This document |
| Manual validation | ⬜ Before M1 |
