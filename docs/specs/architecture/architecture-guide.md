# Architecture Guide (platform canon)

## L0 FROZEN

[`L0-platform-architecture.md`](L0-platform-architecture.md) · [`ADR-030`](ADR-030-l0-platform-architecture-closure.md) · [`architecture-invariants.md`](architecture-invariants.md)

```text
L0 Constitution → L1 Platform → L2 Business → L3 Implementation
```

Работа на L1–L3. L0 — только Architecture RFC / `l0-errata`.

## Артефакты

| Doc | Role |
|-----|------|
| L0 constitution | Freeze + pyramid |
| P-01…P-05 | ADR-025…029 |
| Catalog Passports | Owns · **Non-Goals** · Exposes(+stability) · … |
| Settings Manifest | P-05 ops |
| Invariants | INV-01…15 axioms |
| Checklist | Обязателен перед ADR/PR |

## Forbidden ≠ Non-Goals

- **Forbidden** — нельзя реализовать внутри.  
- **Non-Goals** — не миссия capability.

## История

- 2026-07-18: L0 closed then **final seal / FROZEN**.
