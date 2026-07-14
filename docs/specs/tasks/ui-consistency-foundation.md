# Task: UI Consistency Foundation (PR14)

**Status:** Phase 0–1 **completed (engineering)** — visual sign-off pending → then Phase 2  
**Label:** PR14 — UI Consistency Foundation (**not** [`docs/PR14-hr-verification-ux.md`](../../PR14-hr-verification-ux.md))  
**ADR:** [`ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md)  
**Canon:** [`../frontend/entity-table-governance.md`](../frontend/entity-table-governance.md)  
**UI standard:** [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md)

## Goal

Единый визуальный контракт для blockers + document rows на Candidate / Employee / HR. Layout shells и tables — **следующие фазы**, не смешивать с Phase 0–1.

## Epic phases (summary)

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Severity + blocker primitives | **Done** |
| **1A** | `DocumentRow` + Employee pilot | **Done** |
| **1B** | HR verification rows | **Done** |
| **1C** | Candidate docs rail | **Done** |
| **Gate** | Parity canon + automated tests | **Done** (visual checklist open) |
| **2** | Entity / table normalization (ADR-010) | **Next** |
| **3** | PersonCardLayout (touch-only) | Planned |
| **4** | Parity sweep | Planned |

## Phase 0 — Primitives — **completed**

- [x] `BlockerPanel`, `BlockerListItem`, `SeverityBanner`, `ReadinessPanel`, `.hf-severity-*`
- [x] i18n `app.surfaces.*` (en)
- [x] Pilots: HR review blockers, HR verification blocking list, candidate docs gate, candidate what-blocks, employee missing queue
- [x] `.cursor/rules/hostflow-ui-surfaces.mdc` + `AGENTS.md` UI governance

## Phase 1A — DocumentRow foundation — **completed**

- [x] `DocumentRow`, `DocumentStatus`, `documentStatusMapping.ts`
- [x] `mapEmployeeDocumentRow.ts`
- [x] Pilot: `HrEmployeeDocumentsSection` only
- [x] `CandidateCard.tsx` not touched

## Phase 1B — HR verification rows — **completed**

- [x] `mapHrVerificationDocument.ts`
- [x] `HrSequentialDocumentVerification` — active + queue → `DocumentRow`; header → `DocumentStatus`
- [x] `HrVerificationStepShell.statusBadge` (backward compatible)
- [x] Flow / approval / field editors / `handleOpenDocument` unchanged

## Phase 1C — Candidate docs rail — **completed**

- [x] `mapCandidateDocsRailRow.ts`
- [x] `CandidateDocsRailPanel` checklist → `DocumentRow`
- [x] `BlockerPanel` retained for «what blocks»
- [x] `CandidateCard.tsx` not touched; gate logic unchanged

## Parity gate — **completed (engineering)**

- [x] [`ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md)
- [x] `documentStatusParity.test.ts` (14 tests)
- [ ] **Formal visual screenshot sign-off** (tables in gate doc) — **blocks closing PR14 Phase 0–1 in process**

## Closing step (before Phase 2 kickoff)

1. Run visual pass per [`ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md) § Visual screenshot sign-off.  
2. Check **Sign-off record** in that doc.  
3. Start **Phase 2 — Entity/table normalization** only after step 1–2.

## Phase 2 — Entity / table governance (next — blocked on Phase 0–1 visual sign-off)

**Canon:** [`entity-table-governance.md`](../frontend/entity-table-governance.md)  
**Principle:** `EntityDataTable` = **governance layer** (shell, interactions, spacing, row states, loading/empty/bulk, pagination). **Not** a universal table with all columns/actions inside.

**Domain stays in module:** columns, density, business cells, contextual row actions, API/filters.

### Phase 2A — Shell only (no list page rewrite) — **done (engineering)**

**API:** composition + slots + render props + controlled state — **no** boolean prop explosion on shell (see entity-table-governance § API shape).

- [x] Zone-based `EntityListShell` (header, toolbar, activeFilters, table, pagination, **bulkBar**)
- [x] **Selection + bulk bar day-one** (sticky, show on selection, clear, demo smoke)
- [x] Filter bar + active filter chips (`EntityListActiveFilters`)
- [x] Loading / empty / error states (`EntityListTableFrame` + explicit `status`)
- [x] Pagination canon (`EntityListPagination`)
- [x] Types: `EntityListDefinition`, `EntityListColumnDef`, `EntityListFilterDef` (domain rendering stays in module)
- [x] Demo/fixture: `EntityListShellDemo` — DEV routes `/dev/entity-list-shell` (public smoke) and `/app/dev/entity-list-shell`
- [ ] PR review gate: reject new `showX` / `enableY` booleans on shell (ongoing process)
- [x] Manual smoke on demo route (2026-05-20) — see [`entity-table-governance.md`](../frontend/entity-table-governance.md) § PR14 Phase 2A–2B merge gate

### Phase 2B — Vacancies pilot — **done (engineering)**

- [x] `VacancyList.tsx` wired to `EntityListShell` (zones, selection, bulk, table frame, pagination)
- [x] Business logic / API / filter semantics unchanged; domain cells (`StatusBadge`, links) in module
- [x] `Candidates.tsx` not touched (2B scope)

### Phase 2C — Later

- [ ] Additional lists — migration-by-touch only
- [ ] Candidates list — **last** (richest case), dedicated slice

**Out of scope Phase 2:** `PersonCardLayout`, `CandidateCard.tsx`, document rules, giant abstraction PR.

## Phase 3 — PersonCardLayout (later)

Touch-only migration; after table shell pilot proves stable.

## Out of scope (whole epic)

- Новая бизнес-логика, document rules, HR verification engine changes  
- Mass «выравнивание всего CRM» в одном PR  

## Delivered artifacts (Phase 0–1)

```
hostflow-frontend/src/components/surfaces/
  BlockerPanel.tsx, BlockerListItem.tsx, SeverityBanner.tsx, ReadinessPanel.tsx
  DocumentRow.tsx, DocumentStatus.tsx
  documentStatusMapping.ts, documentStatusTypes.ts
  mapEmployeeDocumentRow.ts, mapHrVerificationDocument.ts, mapCandidateDocsRailRow.ts
  __tests__/documentStatusParity.test.ts, ...
```

## Delivered artifacts (Phase 2A)

```
hostflow-frontend/src/components/surfaces/
  EntityListShell.tsx, EntityListBulkBar.tsx, EntityListPagination.tsx
  EntityListActiveFilters.tsx, EntityListTableFrame.tsx
  EntityListSelectionCheckbox.tsx, useEntityListSelection.ts
  entityListTypes.ts, entityListShell.fixture.ts, EntityListShellDemo.tsx
  __tests__/entityListShell.test.tsx
hostflow-frontend/src/pages/dev/EntityListShellDemoPage.tsx  (DEV: /app/dev/entity-list-shell)
```

## History

- **2026-05-20:** PR14 Phase 2A–2B — `EntityListShell` + Vacancies pilot; merge gate in entity-table-governance.
- **2026-05-20:** Task created (UI governance; separate from HR verification UX PR14).
- **2026-05-20:** Phase 0–1 engineering complete; parity gate doc; Phase 2 reordered to Entity/table (was PersonCard in early draft).
