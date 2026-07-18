# Architecture Guide (platform canon)

Краткая навигация для разработки. Полные нормы — в ADR и principles.

## Канон платформы

| Документ | Содержание |
|----------|------------|
| [`platform-architecture-principles.md`](platform-architecture-principles.md) | Tenant/Company/Modules + **§0 Platform Rules P-01…P-03** |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | Product keys + **§0.1 Platform Capability Catalog** |
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | **P-01** Standard Adapter Boundary |
| [`ADR-026`](ADR-026-capability-ownership.md) | **P-02** Capability Ownership |
| [`ADR-027`](ADR-027-capability-composition.md) | **P-03** Capability Composition |
| [`architecture-review-checklist.md`](architecture-review-checklist.md) | **Обязательный чеклист PR** |
| [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) | Endpoint spine + Acquisition |
| [`ADR-007`](ADR-007-forms-platform-capability.md) | Forms Core Platform Module |

## Два уровня

```text
Endpoint → Submission → Routing → Decision → Business Entity   ← поток
Module A → Standard Adapter → Module B                         ← граница
```

## Три вопроса перед кодом

1. Только стандартные адаптеры? (P-01)  
2. Только к владельцу capability? (P-02)  
3. Композиция существующих capabilities, а не дубликат? (P-03)

## История

- 2026-07-18: guide для вехи platform canon (P-01…P-03).
