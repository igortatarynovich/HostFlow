# Canonical Workspaces Roadmap — Four Screen Types

**Status:** **superseded** — retained for workspace **type** definitions only.  
**Active build order:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md)  
**UI platform canon:** [`hostflow-ui-platform-v1.md`](hostflow-ui-platform-v1.md)

---

## Supersession notice (2026-07-09)

**Workspace-first build order is withdrawn.**

Correct order:

1. **UI Primitives** (Universal Data Table, Detail Card, Documents, Timeline, Action Panel, …)  
2. **Workspace Engine** (composition)  
3. **Workspace types** (Application → Entity → Process → Collection) as **config only**

> **Workspace is not the canon. Workspace is a composition of canonical components.**

Everything below remains valid as **what** each workspace type means (see [`ui-constitution-v1.md`](ui-constitution-v1.md) §3). It is **not** the development sequence.

---

## Historical content (workspace types — reference only)

### Application Workspace structure

See [`ui-constitution-v1.md`](ui-constitution-v1.md) §4 — hero, tabs, table, card, Action Panel, work session.

**Implementation note:** Application Workspace table **must** be `Universal Data Table` (Phase 1), not an inline `<table>`.

### Entity / Process / Collection

See [`ui-constitution-v1.md`](ui-constitution-v1.md) §3.1–3.4.

### Migration register

See [`ui-constitution-v1.md`](ui-constitution-v1.md) §8 and [`operational-model-adoption-register.md`](operational-model-adoption-register.md).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | **Superseded** by ui-primitives-roadmap + design-system-constitution-v1 |
| 2026-07-09 | v1 initial — workspace-first order (withdrawn) |
