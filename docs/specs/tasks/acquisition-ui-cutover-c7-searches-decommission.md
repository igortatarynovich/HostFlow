# Acquisition UI Cutover C-7 — Подборы decommission + cutover PASS

**Status:** **PASS** — Stage 4 product/UI cutover closed (2026-07-27)  
**Date:** 2026-07-26 (closed 2026-07-27)  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) (C-7 row + acceptance gate)  
**Parents:** ADR-024 · C-2 create-stop (#158) · [C-6 Forms](acquisition-ui-cutover-c6-form-builder.md) · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)  
**Shipped:** #184 (nav/redirects) · #185 (audience/bindings 410) · this close-out  
**Next Product Track:** **FlightAdBinding Ad-ID bind UI** (API #161 exists; Marketing UI missing) → Source Diagnostics → Stage 5+  
**Unpause:** Stage 5 PR-2 **may resume** (Optimization remains a separate concern; not absorbed into C-7)

> C-7 closed the **Stage 4 product/UI cutover**: Подборы retired as an advertising launch surface, reconciliation inventory documented, Marketing onboarding path is the only operator launch story.  
> **Not** Source Diagnostics ops console. **Not** Stage 5 Optimization implementation. **Not** deleting historical activity JSON (inventory only).

---

## 1. Why (historical)

C-1…C-6 delivered Marketing IA, Sources, Test lead, Mapping, and Forms. Legacy Подборы launch UI still existed (create/duplicate already **410** from C-2). Leaving it visible kept dual-path confusion and blocked Stage 5 PR-2.

```text
Connect → Source → Test Lead → Mapping → Form → Campaign → Flight → Lead
```

C-7 made that path the **only** operator launch story.

---

## 2. Product job (one sentence)

An operator cannot start a **new ad launch** from Подборы; legacy acquisition URLs are redirect or strictly read-only; reconciliation inventory is documented; production Marketing nav smoke passes — **cutover PASS**.

---

## 3. Locked boundary

| Concern | C-2 | C-7 | OUT |
|---------|-----|-----|-----|
| New launch via `searchAcquisition` create/duplicate | ✅ stopped (410) | keep enforcement | — |
| Подборы list / nav as launch surface | still visible | ✅ retire / redirect / read-only (#184) | ❌ wipe activity history |
| Audience / bindings writes on legacy rows | still live (constraint) | ✅ gated 410 (#185) | ❌ silent data loss |
| Reconciliation inventory | snapshot `linked`/`unresolved` | ✅ counts documented below | ❌ force-migrate all rows |
| Source Diagnostics | — | — | ❌ post–C-7 epic |
| Stage 5 PR-2 | paused | ✅ unpaused after PASS | ❌ sneak Optimization into C-7 |

---

## 4. Donor / reuse

| Need | Donor |
|------|--------|
| Create-stop / 410 | C-2 `LegacyLaunchDisabledError` + FE helpers / scan tests |
| Snapshot reconciliation | Campaign/Flight acquisition snapshot `reconciliation` |
| Marketing setup deep-link | `/app/marketing/new` prefill from vacancy when unambiguous |
| Nav / IA tables | [acquisition-ui-cutover.md](acquisition-ui-cutover.md) Sales / Recruitment / Marketing |

**Forbidden:** new Marketing host module; Stage 5 explainability; Diagnostics timeline epic.

---

## 5. Shipped UX

1. Подборы acquisition launch CTAs removed; list/new routes redirect to Marketing (#184).  
2. Legacy `/app/recruitment/searches/:id/acquisition/*` remains reachable for historical rows but audience is read-only; bindings/duplicate CTAs removed (#185).  
3. `PUT …/acquisition/audience` and `update_bindings` → **410** `legacy_launch_disabled` (same gate as create/duplicate).  
4. pause/resume/archive/sync remain for historical ops.  
5. Reconciliation inventory documented (next section).

---

## 6. OUT (unchanged)

- Source Diagnostics epic (post–C-7 Product)  
- **FlightAdBinding Ad-ID bind UI** (next product slice; API already exists)  
- Stage 5 PR-2 **implementation** (only **unpause** here)  
- Stage 6 Analytics  
- Hard-delete of legacy search acquisition rows  

---

## 7. Acceptance (cutover PASS) — evidence 2026-07-27

- [x] New ad launch cannot start from Подборы; legacy URLs redirect or read-only — #184  
- [x] C-2 leftover writable surfaces (audience/bindings) gated — #185; live `PUT …/audience` → **HTTP 410** on hostflow.cc backend  
- [x] Reconciliation inventory: migrated / unresolved counts documented — §8  
- [x] Sales / Recruitment / Marketing IA match cutover tables — nav hide + Marketing zones live  
- [x] End-to-end path (Connect → … → First processed lead) executable without a developer — Focus Personnel / Poltrakt Flight smoke (prior cutover sessions; Focus has **0** legacy `acquisition_v1`)  
- [x] Deploy smoke of full production Marketing nav — Campaigns / Sources / Forms / Activity → **200**; backend @ `aa9298ad` (#185)  
- [x] Cutover docs: C-7 **PASS**; Stage 5 PR-2 may resume; Product Track → **Ad-ID bind UI**  
- [x] Tests: launch-stop scans + #185 suite; `make docs-lint` on this PR  

---

## 8. Reconciliation inventory (production, 2026-07-27)

Method: vacancies with `extra.acquisition_v1`; reconcile via unique non-archived `acq_campaign_targets` (`target_type=vacancy`) — same rules as `resolve_search_campaign_reconciliation`.

| Status | Vacancies | Activities | Notes |
|--------|----------:|-----------:|-------|
| **linked** (exactly one Campaign) | 1 | 1 | Demo Superadmin seed |
| **unresolved** (`no_campaign_with_vacancy_target`) | 14 | 16 | No force-migrate; historical JSON kept |
| **unresolved** (`multiple_campaigns_for_vacancy`) | 0 | 0 | — |
| **Total with `acquisition_v1`** | **15** | **17** | Across 2 tenants |

**By tenant**

| Tenant | `acquisition_v1` vacancies | Active Campaigns | Notes |
|--------|---------------------------:|-----------------:|-------|
| Superadmin (`11111111-…`) | 14 | many (seed/demo) | C-2 test leftovers + migrate seeds; 1 linked |
| Игорь (`9e5133ae-…`) | 1 | 0 | «Офис — Poltrakt» legacy row; unresolved |
| **Focus Personnel** (`9497fc29-…`) | **0** | **1** | Already on Campaign/Flight; no legacy block |

**Policy after PASS:** do **not** hard-delete unresolved JSON. Operators use Marketing Campaign → Flight for new launches. Snapshot `reconciliation` remains on legacy GET for deep-links. Cleanup of seed leftovers is optional ops hygiene, not a cutover blocker.

---

## 9. Implementation order (done)

1. Docs / brief + queue linkage — ✅ #183  
2. UI retire / redirects — ✅ #184  
3. Legacy write gates (audience/bindings) — ✅ #185  
4. Close-out + production smoke + inventory — ✅ this PR  

---

## 10. STOP conditions (still apply post-PASS)

- Deleting activity/JSON history without a new documented inventory pass  
- Absorbing Source Diagnostics into Ad-ID bind UI  
- Re-enabling `searchAcquisition` create/duplicate/audience/bindings writes  
