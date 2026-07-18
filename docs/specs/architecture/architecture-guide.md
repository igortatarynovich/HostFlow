# Architecture Guide (platform canon)

## Phase 0 complete · L0 FROZEN

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`architecture-invariants.md`](architecture-invariants.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md)

```text
Phase 0 Constitution (done) → Phase 1 Platform (L1) → Phase 2 Business (L2) → Phase 3 Implementation (L3)
```

Организационные правила (спор → L0; не раздувать конституцию; ADR ссылается на P-rules; Catalog ежедневно; модуль только по шаблону) — в L0 § Organizational rules.

## Ежедневный путь проектирования

1. [`platform-capability-catalog.md`](platform-capability-catalog.md)  
2. Owner + Passport  
3. Settings Manifest  
4. Checklist + Invariants  
5. Код / L1 ADR деталей  

## Артефакты

| Doc | Role |
|-----|------|
| L0 constitution | Freeze + org rules + phases |
| Catalog | **Рабочий справочник** |
| Settings Manifest | P-05 ops schema |
| Invariants | INV-01…15 |
| Checklist | Обязателен перед ADR/PR |

## История

- 2026-07-18: L0 FROZEN; Phase 0 complete; switch to Phase 1.
