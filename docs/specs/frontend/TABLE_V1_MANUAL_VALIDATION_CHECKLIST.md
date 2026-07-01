# TABLE_V1_MANUAL_VALIDATION_CHECKLIST

Status: Active  
Date: 2026-05-31  
Input: `TABLE_V1.md`, `REF-UI-000-table-benchmark-sprint1.md`  
Purpose: manual UX validation before first post-lock migration (M1 — vacancies).

## Question Answered

> Подтверждает ли ручная проверка, что candidates baseline и TABLE_V1 spec соответствуют operator reality?

**Required before M1 migration.** Not a lock blocker for `TABLE_V1.md` (completed 2026-05-31).

---

## Environment

| Field | Value |
|---|---|
| Viewport | 1920×1080 or 1440×900 laptop, browser full height |
| Role | Recruiter / operator with bulk permissions |
| Page | `/app/candidates` (reference) |
| Date | |
| Validator | |

---

## Checks

| # | Check | Pass | Notes |
|---|---|:---:|---|
| 1 | Visible data rows (excl. header) count ≈ 12–18 on 1080p with default columns | ⬜ | Record actual count: ___ |
| 2 | Sticky header remains visible while scrolling tbody | ⬜ | |
| 3 | Sort: click column header → direction indicator + data reorder | ⬜ | |
| 4 | Filter bar: search above table; filter chips/controls above table | ⬜ | |
| 5 | Column filter (if enabled): opens from header, does not replace top bar | ⬜ | |
| 6 | Select row → bulk action zone appears in canonical top area | ⬜ | |
| 7 | Clear selection → bulk zone hides | ⬜ | |
| 8 | Empty state: readable message when no results | ⬜ | |
| 9 | Loading state: table area reserved / skeleton (no layout jump) | ⬜ | |
| 10 | Status badges in row use consistent semantic styling | ⬜ | |
| 11 | Batch-200 behavior: operator understands data cap (or document gap) | ⬜ | |
| 12 | Spot-check vacancies table: sticky header + pager visible | ⬜ | Comparison only |

---

## Cross-Table Consistency (Spot)

| Table | Sticky header | Filter above | Bulk zone | Pager/batch clear | Pass |
|---|---|---|---|---|:---:|
| Candidates | | | | | ⬜ |
| Vacancies | | | | | ⬜ |
| Leads | | | | | ⬜ |

---

## Sign-off

| Outcome | Action |
|---|---|
| All critical (1–7) pass | Proceed to M1 (vacancies) |
| Fail on density (1) | Adjust TABLE_V1 §2 or document exception |
| Fail on bulk (6–7) | Block M1 until candidates reference fixed |
| Fail on vacancies spot (12) | Prioritize M1 alignment items from backlog |

**Critical:** items 1–7. **Advisory:** 8–12.

---

## Record

```
Validated by:
Date:
Result: Pass / Pass with notes / Fail
Notes:
```
