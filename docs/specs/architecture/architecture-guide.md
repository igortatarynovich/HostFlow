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
5. **Forms Sprint 4:** **IN PROGRESS** — schema contract + validation ([`../tasks/forms-sprint-4.md`](../tasks/forms-sprint-4.md)).
6. **Forms Builder:** **LOCKED**.
3. **Forms Builder:** **LOCKED** until Sprint 1 contracts land.  
4. **Каждая новая L1 capability** идёт только по [`capability-contract.md`](capability-contract.md).  
5. Integration base-known CI failures: [`../tasks/acquisition-epic-p-base-known-ci-failures.md`](../tasks/acquisition-epic-p-base-known-ci-failures.md).

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
