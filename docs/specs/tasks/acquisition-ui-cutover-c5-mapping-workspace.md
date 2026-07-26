# Acquisition UI Cutover C-5 — Mapping workspace

**Status:** DONE — implementation shipped (API + Marketing UI); Product Track → **C-6**  
**Date:** 2026-07-26  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) (C-5 row + onboarding lifecycle)  
**Parents:** ADR-024 · C-3 / C-3.1 Sources · [C-4 test lead](acquisition-ui-cutover-c4-test-lead-field-discovery.md) · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)  
**Next:** [C-6 Form Builder cutover](acquisition-ui-cutover-c6-form-builder.md) — **ACTIVE Product Track**  
**Blocks:** Stage 5 PR-2 remains paused until cutover C-7 PASS

> C-5 closes **Mapping decisions + routing preview** for a Source.  
> Operator **confirms** (or changes) field placements discovered in C-4, sees what will become Person / Candidate / answers / ignored, and gets a **dry-run routing preview** — **without** silent drop of unknown fields.  
> **Not** a new mapping engine. **Not** Source Diagnostics (post–C-7).

---

## 1. Why now

C-4 delivers sample + field discovery + propose/dry-run normalize. Without C-5, operators still cannot **persist** mapping decisions in Marketing or see routing consequences before live leads.

```text
Connect → Source → [C-4 Test Lead + Discovery] → [C-5 Mapping + routing preview] → Destination → Flight → First Lead
```

---

## 2. Product job (one sentence)

From a Source, a non-developer operator can **edit and save** `mapping_rules`, see **Mapping Health** update, and **preview routing** (entity / queue / duplicate / needs-review) without creating production entities unless an explicit later opt-in exists.

---

## 3. Locked boundary vs C-4 / Diagnostics

| Concern | C-4 | C-5 | Diagnostics (post–C-7) |
|---------|-----|-----|-------------------------|
| Obtain sample / masked inspect | ✅ | may deep-link sample | full ops timeline |
| Propose HostFlow targets | ✅ | ✅ editable | — |
| Persist `mapping_rules` / versioning | ❌ | ✅ | drift alerts on live |
| Routing preview (Person / Candidate / answers / ignored / queue / duplicate) | ❌ stub only | ✅ | explain one live lead |
| Create Candidate / Application / Inquiry | ❌ | ❌ default | replay tools |
| New mapping engine | ❌ | ❌ | ❌ |

**Rule:** C-5 writes mapping SoT on **`IntakeSourceProfile.mapping_rules`** (and existing versioning hooks if already present). It must **not** invent a parallel rules registry.

---

## 4. Donor / reuse (do not re-invent)

| Need | Donor |
|------|--------|
| Field discovery / sample | C-4 `sources_sample.py` + Test lead page |
| Mapping rules shape | Existing `IntakeSourceProfile.mapping_rules` + Meta mapping Settings UI patterns |
| Mapping Health summary | C-3 `sources_read.compute_mapping_health` (or equivalent) |
| Normalize dry-run | Existing `normalize_meta_payload` / intake normalize path used by C-4 preview |
| Human form labels | `campaign_source_cards` + Connect Source picker hydrate (already shipped) |

**Forbidden:** second Forms runtime; Graph live-fetch as mapping SoT; embedding full Diagnostics console.

---

## 5. UX sketch (minimum)

1. Entry from Marketing → Sources row → **Mapping** (and/or from Test lead “confirm mapping” CTA).  
2. Table: provider field · sample (masked) · HostFlow target · action (standard / domain / custom / answer / ignore).  
3. Save → Mapping Health refreshes on Sources list.  
4. Routing preview panel: destination entity class, duplicate policy note, assignee/queue if already modeled — **read-only preview**.  
5. Unknown / unmapped fields → force **Needs review** path in preview (no silent loss).

---

## 6. OUT

- Form Builder under Marketing (C-6)  
- Подборы decommission (C-7)  
- FlightAdBinding Ad-ID bind UI (separate runtime/product slice if still open)  
- Source Diagnostics epic  
- Stage 5 PR-2  

---

## 7. Acceptance

- [x] Operator can open Mapping workspace for a Source from Marketing  
- [x] Can change and **persist** mapping decisions on `mapping_rules`  
- [x] Mapping Health on Sources list updates after save  
- [x] Routing preview shows entity / ignored / needs-review without creating production rows by default  
- [x] Unmapped fields cannot disappear silently in preview  
- [x] Cutover docs: C-5 DONE; Product Track → C-6  
- [x] Tests: API persist + FE scope scan; `make docs-lint`  

**Shipped surface:**

| Layer | Path |
|-------|------|
| API | `GET/PUT /api/v1/platform/marketing/sources/{id}/mapping` · `POST …/mapping/routing-preview` |
| Façade | `backend/app/acquisition/sources_mapping.py` |
| UI | `/app/marketing/sources/:sourceId/mapping` (`MarketingSourceMappingPage`) |
| Paths | `build_source_paths.mapping_path` → Marketing-native |

**Constraints / honesty notes:**

- Action column is thin (`map` / `ignore`) — full standard/domain/custom/answer taxonomy remains Settings/Form Builder territory until C-6 expands UX.  
- Routing preview is destination + unmapped/ignored + C-4 normalize dry-run — not full duplicate/assignee queue simulation.  
- Read still falls back to Meta form mapping when profile rules are empty; **writes** always go to profile `mapping_rules`.

---

## 8. Implementation order (suggested PR split)

1. **Docs / brief** (this file) + queue linkage  
2. **API:** get/put mapping for Marketing Source façade (thin over existing profile rules)  
3. **UI:** Mapping workspace page  
4. **Routing preview** endpoint (dry-run only)  
5. Close-out docs + acceptance
