# HostFlow Decision Model v1

**Status:** **FROZEN** — superseded by Entity Model projections. See [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md) §6.  
**Owner:** Product + Platform UX + Frontend Architecture  
**Parent:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)  
**Active canon:** [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md) · [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md)

> Do not extend `ObjectDecision` or Rail composers until `toDetailRailProjection()` reads Entity Model (Phase 2.3).

---

## Purpose (historical)

Decision Flow answers: **Что мне сейчас нужно сделать?**

The correct source for that answer is **Entity Model `state` + `actions` + `outcome`** — not a standalone Rail schema. This document remains as transitional code reference only.

---

## ObjectDecision (transitional — do not extend)

See `platform/decision-model/types.ts`. Replace with Entity Model projection in Phase 2.3.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | **FROZEN** — Entity Workspace Canon is source; Rail derives via §6 projection |
| 2026-07-09 | v1 — initial ObjectDecision (transitional) |
