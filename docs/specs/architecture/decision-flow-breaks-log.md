# Decision Flow Breaks — Living Log

**Status:** operational (Phase 1 audit).  
**Parent:** [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md) §0

> **A break stays open until it cannot be reproduced in real UI** — PR/code status does not close it.

---

## Verification gate (before any new work)

| Step | Action |
|------|--------|
| 1 | **Manual Decision Flow** on Candidates — user behavior only, not code |
| 2 | If break **reproduces** → stays **open** (reopen if was marked closed) |
| 3 | Only when verified gone → mark **verified** |
| 4 | Re-rank remaining breaks **P0 → P1 → P2** (flow impact, not discovery order) |
| 5 | Fix **highest P0** next — not next number |

### Priority classes

| Class | Meaning | Examples |
|-------|---------|----------|
| **P0** | Flow **cannot continue** | lost selection, lost context, manual hunt for next object, forced leave list |
| **P1** | Flow continues but **slower** | extra screen, extra click, action hidden in menu |
| **P2** | **Cognitive load** | unclear label, duplicate actions, noise |

---

## #1–#6 — awaiting UI verification

Code changes landed; **must be confirmed manually** on Candidates before any #7+ work.

| # | Class | Break | Code change (for testers) | UI verify |
|---|-------|-------|---------------------------|-----------|
| **#1** | P0 | After complete next-action → must advance to next object without re-select | `selectNext` after complete | ☐ |
| **#2** | P0 | Esc closes rail but **row stays highlighted** | `closeDetailRail` keeps `activeId` | ☐ |
| **#3** | P0 | ↑↓ with rail open **moves rail** to next/prev row | keyboard + `detailRailOpen` | ☐ |
| **#4** | P0 | Return from Entity → **same row + rail restored** | `returnFromCandidateId` + `selectRow` | ☐ |
| **#5** | P1 | Doc request opens task modal **with title prefilled** | `prefillTitle` on modal | ☐ |
| **#6** | P1 | After task create → **rail next_action updates** | `onSuccess` reload | ☐ |
| **#20** | P0 | Repeat row click **closes** rail; other row **switches** | Selection Model toggle | ☐ |

**Verification script:** open Candidates → saved view or «my today» → select row → rail → for each row above, perform action → confirm expected behavior → check box.

---

## Sales / Обращения — awaiting UI verification

| # | Class | Break | Fix | UI verify |
|---|-------|-------|-----|-----------|
| **#16** | P0 | Split view replaced **table with cards** | Table always; grid layout | ☐ |
| **#17** | P0 | Context panel ~50% width | Fixed **380px** rail column | ☐ |
| **#18** | P0 | No toggle (repeat click / Esc) | Row toggle + Esc → list | ☐ |
| **#19** | P0 | Candidates `asTelHref` crash | Moved before useMemo | ☐ |

---

## Remaining breaks — ranked by flow impact (not discovery order)

### P0 — flow cannot continue

| # | Break | Notes |
|---|-------|-------|
| **#9** | Document triage navigates to `/candidates/:id/documents` — **leaves list** | Worse than #7 for Decision Flow |
| **#10** | Handoff action navigates to full card — **leaves list** | |
| **#11** | Open Inbox from rail — **leaves list** | |
| **#14** | Row disappears from filter → rail closes + selection cleared | |
| **#7** | Stage change not in rail — forced context menu / bulk modal | Blocks in-flow stage moves |

### P1 — flow slower

| # | Break | Notes |
|---|-------|-------|
| **#8** | Vacancy assign hinted but no rail action | |
| **#12** | Stage via context menu ≥3 clicks | |
| **#6** | *(if verify fails)* task refresh | moved to verify block |
| **#5** | *(if verify fails)* doc prefill | moved to verify block |

### P2 — cognitive load

| # | Break | Notes |
|---|-------|-------|
| **#13** | `advance_pipeline` hint without primary button | |
| **#15** | Duplicate «Позвонить» surfaces | |

---

## Sales audit

Queued after Candidates: **#1–#6 verified** + P0 queue exhausted or accepted.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | Platform: rail 380px, row toggle, Sales table+fixed rail; #16–#20 await UI |
| 2026-07-09 | Verification gate; #1–#6 awaiting UI; P0/P1/P2 re-rank |
