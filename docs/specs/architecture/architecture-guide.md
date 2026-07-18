# Architecture Guide (platform canon)

## Phase 0 complete · L0 FROZEN

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)

```text
Phase 0 Constitution (done) → Phase 1 Platform (L1) → Phase 2 Business (L2) → Phase 3 Implementation (L3)
```

Организационные правила (спор → L0; не раздувать конституцию; ADR ссылается на P-rules; Catalog ежедневно; модуль только по шаблону) — в L0 § Organizational rules.

## Phase 1 lock (2026-07-18)

1. **Сейчас:** Epic P — Acquisition Stage **3D** ([`../tasks/acquisition-epic-p-stage-3d.md`](../tasks/acquisition-epic-p-stage-3d.md)).  
2. **После Epic P DoD:** Forms Sprint 1 = Passport + Manifest + Public Contract + Adapter + Contract Tests — **не** Builder.  
3. **Каждая новая L1 capability** идёт только по [`capability-contract.md`](capability-contract.md).

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
