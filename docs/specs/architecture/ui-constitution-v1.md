# HostFlow UI Constitution v1

**Status:** Accepted (product terminology)  
**Date:** 2026-07-13  
**Scope:** Product-facing names and entity mapping (RU/EN). Build mechanics — [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md).

> **Hierarchy:** [`hierarchy-of-truth.md`](../../governance/hierarchy-of-truth.md)

---

## 1. Core product terms

| Module | RU (UI) | EN (code) | Entity | Notes |
|--------|---------|-----------|--------|-------|
| Sales | **Обращение** | Inquiry | `Lead` (transport) | Не показывать «Lead» в UI |
| Sales | **Клиент** | Client | **`ClientAccount`** | **Не** `Company` |
| Sales | **Заказ** | Service Order | `ServiceOrder` | Stage 1B+ |
| Parties | **Компания** | Company | `Company` | Юрлицо / party, не операционный клиент |

**Канон:** продуктовое слово **«Клиент»** всегда означает **`ClientAccount`**.  
`Company` — юридическое лицо (NIP, реквизиты, договорные документы).

Commercial model: [`ADR-020`](ADR-020-sales-to-engagement-commercial-model.md).  
Stage 1A implementation: [`stage-1a-client-account-implementation-contract.md`](../tasks/stage-1a-client-account-implementation-contract.md).

---

## 2. Sales journey (Stage 1A)

```text
Source → Обращение (Inquiry) → Клиент (ClientAccount) → [Заказ — Stage 1B+]
```

- **Обращение** создаётся из intake; внутренний transport — `Lead` (`lead_type=client`).
- **Клиент** (`ClientAccount`) появляется на `convert-client`; может существовать без `Company`.
- Legacy UI может показывать `Company` там, где ещё не мигрировал список клиентов — без переименования `Company` в «Клиент».

---

## 3. Workspace & list standards

| Pattern | Canon |
|---------|-------|
| Collection list | [`ADR-010`](ADR-010-unified-resource-list-shell.md) |
| UI platform standard | [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) |

Client list route (target): `/app/clients/:id` → Entity workspace over `ClientAccount`.

---

## 4. References

- [`ADR-020`](ADR-020-sales-to-engagement-commercial-model.md) — Sales-to-Engagement commercial model
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) — tenant / company boundaries
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — routing map
- [`stage-1a-client-account-implementation-contract.md`](../tasks/stage-1a-client-account-implementation-contract.md) — Stage 1A contract
