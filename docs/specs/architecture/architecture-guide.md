# Architecture Guide (platform canon)

## Phase 0 complete · L0 FROZEN

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)

```text
Phase 0 Constitution (done) → Phase 1 Platform (L1) → Phase 2 Business (L2) → Phase 3 Implementation (L3)
```

Организационные правила (спор → L0; не раздувать конституцию; ADR ссылается на P-rules; Catalog ежедневно; модуль только по шаблону) — в L0 § Organizational rules.

## Phase 1 lock (2026-07-18 · updated after Forms Sprint 1)

1. **Acquisition Stage 3D / Epic P:** ✅ **COMPLETE** ([`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)).
2. **Forms Sprint 1:** ✅ **COMPLETE** ([`../tasks/forms-sprint-1.md`](../tasks/forms-sprint-1.md) · PR #36 · `37b652af`).
3. **Forms Sprint 2:** ✅ **COMPLETE** ([`../tasks/forms-sprint-2.md`](../tasks/forms-sprint-2.md) · PR #37 · `ec5fcd86`).
4. **Forms Sprint 3:** ✅ **COMPLETE** ([`../tasks/forms-sprint-3.md`](../tasks/forms-sprint-3.md) · PR #38 · `f5771df6`).
5. **Forms Sprint 4:** ✅ **COMPLETE** ([`../tasks/forms-sprint-4.md`](../tasks/forms-sprint-4.md) · PR #39 · `779cffd3`).
6. **Forms Sprint 5:** ✅ **COMPLETE** ([`../tasks/forms-sprint-5.md`](../tasks/forms-sprint-5.md) · PR #40 · `a6df02f0`).
7. **Forms Sprint 6:** ✅ **COMPLETE** ([`../tasks/forms-sprint-6.md`](../tasks/forms-sprint-6.md) · PR #41 · `7e259f22`) — backend platform contour closed.
8. **Forms Product Layer:** **ACTIVE** — P1.1–P1.2 ✅ COMPLETE; **P1.3 Standard Library READY FOR IMPLEMENTATION**.
9. **Builder:** **LOCKED** until **P1.3**. Stdlib registers only via public Registry/Descriptors (no Catalog-core special cases).
10. **Каждая новая L1 capability** идёт только по [`capability-contract.md`](capability-contract.md).  
11. Integration base-known CI failures: [`../tasks/acquisition-epic-p-base-known-ci-failures.md`](../tasks/acquisition-epic-p-base-known-ci-failures.md).

## Ежедневный путь проектирования (L1)

1. [`platform-capability-catalog.md`](platform-capability-catalog.md) — Owner + Passport  
2. Settings Manifest keys  
3. **Public Capability Contract** ([`capability-contract.md`](capability-contract.md))  
4. Adapter (P-01)  
5. Contract Tests  
6. Checklist + Invariants  
7. UI / L3 runtime  

```text
Passport → Manifest → Public Contract → Adapter → Contract Tests → UI
```

UI **не** определяет архитектуру.

## Артефакты

| Doc | Role |
|-----|------|
| L0 constitution | Freeze + org rules + phases |
| Catalog | **Рабочий справочник** |
| Settings Manifest | P-05 ops schema |
| **Capability Contract** | Публичный boundary surface до Adapter |
| Invariants | INV-01…15 |
| Checklist | Обязателен перед ADR/PR |
| Epic P (3D) | Закрытие Acquisition V1 vertical |

## История

- 2026-07-18: L0 FROZEN; Phase 0 complete; switch to Phase 1.  
- 2026-07-18: Phase 1 lock — Epic P first; Capability Contract sequence; Forms Sprint 1 after V1.  
- 2026-07-18: Epic P COMPLETE — Forms Sprint 1 unlocked; Builder locked.
- 2026-07-18: Forms Sprint 1 infra started (Public Contract + Adapter).
- 2026-07-18: Forms Sprint 6 COMPLETE — submission envelope; Forms backend platform contour closed; Builder remains LOCKED.
- 2026-07-18: Forms Product Layer epic OPEN — Field Catalog SoT; Builder must not invent types; P1 next.
- 2026-07-18: Product Layer ACTIVE (`29f4057f`); P1 designed as component registry.
- 2026-07-18: P1 implementation plan P1.1 Registry → P1.2 Descriptors → P1.3 Stdlib → P1.4 Extension API.
- 2026-07-18: P1 decomposition ACTIVE (`51063d1c`); P1.1 READY FOR IMPLEMENTATION; Builder LOCKED until P1.3.
- 2026-07-18: P1.1 Registry COMPLETE (`644b102a`); P1.2 Descriptors READY; Builder LOCKED.
- 2026-07-18: P1.2 Design ACTIVE; Descriptor Contract READY FOR IMPLEMENTATION; declarative-only descriptors rule.
- 2026-07-18: P1.2 Descriptors COMPLETE (`1f7b4aba`); P1.3 Standard Library READY FOR IMPLEMENTATION; Builder LOCKED.
