# Architecture Guide (platform canon)

Краткая навигация. Полные нормы — в ADR и catalog.

## Канон платформы

| Документ | Содержание |
|----------|------------|
| [`platform-architecture-principles.md`](platform-architecture-principles.md) | §0 Platform Rules **P-01…P-04** |
| [`platform-capability-catalog.md`](platform-capability-catalog.md) | Kinds + Passport (**Owns / Configures / Exposes / Consumes**) |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | Product keys + §0.1 owners index |
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | **P-01** Standard Adapter Boundary |
| [`ADR-026`](ADR-026-capability-ownership.md) | **P-02** Capability Ownership |
| [`ADR-027`](ADR-027-capability-composition.md) | **P-03** Capability Composition |
| [`ADR-028`](ADR-028-configuration-ownership.md) | **P-04** Configuration Ownership |
| [`architecture-review-checklist.md`](architecture-review-checklist.md) | PR checklist |
| [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md) | Endpoint spine |
| [`ADR-007`](ADR-007-forms-platform-capability.md) | Forms |

## Два уровня

```text
Endpoint → Submission → Routing → Decision → Business Entity   ← поток
Module A → Standard Adapter → Module B                         ← граница
```

## Пять вопросов перед кодом

1. Только стандартные адаптеры? (**P-01** / Exposes)  
2. Только к владельцу функциональности? (**P-02** / Owns)  
3. Композиция, не дубликат? (**P-03** / Consumes)  
4. Не чужой Forbidden? (**Boundary**)  
5. Настройки только у configuration owner? (**P-04** / Configures)

Проектирование: не «в какой модуль?», а **«какой capability / какая из четырёх границ?»**.

Business Capability **не** владеет Infrastructure — только Consumes.

## История

- 2026-07-18: P-01…P-03 canon.  
- 2026-07-18: P-04 + four boundaries + capability kinds.
