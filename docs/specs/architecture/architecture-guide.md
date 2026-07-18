# Architecture Guide (platform canon)

## Канон платформы

| Документ | Содержание |
|----------|------------|
| [`platform-architecture-principles.md`](platform-architecture-principles.md) | §0 **P-01…P-05** |
| [`platform-capability-catalog.md`](platform-capability-catalog.md) | **Capability Passport** (архитектура) |
| [`capability-settings-manifest.md`](capability-settings-manifest.md) | **Settings Manifest** (эксплуатация, P-05) |
| [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) | Product keys + §0.1 index |
| [`ADR-025`](ADR-025-standard-adapter-boundary.md) | **P-01** Adapter Boundary |
| [`ADR-026`](ADR-026-capability-ownership.md) | **P-02** Capability Ownership |
| [`ADR-027`](ADR-027-capability-composition.md) | **P-03** Composition |
| [`ADR-028`](ADR-028-configuration-ownership.md) | **P-04** Configuration Ownership |
| [`ADR-029`](ADR-029-settings-contract.md) | **P-05** Settings Contract |
| [`architecture-review-checklist.md`](architecture-review-checklist.md) | PR checklist |

## Два документа на capability

```text
Passport (arch)     Manifest (ops)
Purpose             General
Owns                Integrations
Exposes/Consumes    Defaults / Policies
Events              Feature Flags
Forbidden           License Gates
Configures ──────►  Validation + keys
```

## Шесть вопросов перед кодом

1. Adapters? (**P-01**)  
2. Functional owner? (**P-02**)  
3. Compose? (**P-03**)  
4. Not Forbidden?  
5. Config owner? (**P-04**)  
6. Published via Settings Manifest / capability space UI? (**P-05**)

Пользователь настраивает **capability**, не «систему».

## История

- 2026-07-18: P-01…P-04.  
- 2026-07-18: P-05 Settings Contract; Passport vs Manifest.
