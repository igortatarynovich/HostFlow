# ADR-020: Sales-to-Engagement Commercial Model

**Status:** Accepted (architectural direction)  
**Date:** 2026-07-13  
**Layer of change:** Domain | Life Cycle | Constitution  
**Start / Optimize / Scale:** Start (MVP vertical slice: targeting + paid invoice)  
**Authors:** Product + Platform architecture  
**Related:** [ADR-004](ADR-004-five-product-modules-and-billing-events.md), [ADR-003](ADR-003-tenant-company-module-data-boundaries.md), [ui-constitution-v1.md](ui-constitution-v1.md), [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)

> **Terminology (обязательно):** продуктовое **«Клиент»** в UI = **`ClientAccount`** (операционные отношения). **`Company`** = юридическое лицо / party. **`Lead`** остаётся внутренним transport-слоем intake; в Sales UI — только **«Обращение»** (Sales Inquiry).

---

## 1. Context

HostFlow продаёт услуги (таргетинг, рекрутинг, Fleet Services, консалтинг, подписки). Текущий операционный путь:

```text
Meta / Forms → Lead (client_lead) → Sales Inquiry → convert-client → Company → ServiceOrder → Invoice
```

Проблемы текущей модели:

1. **`Company` смешивает три роли:** операционный клиент, юридическое лицо, плательщик.
2. **Нет слоя коммерческого предложения** и отдельного Commercial Confirmation.
3. **Service Order создаётся без readiness gate.**

Цель ADR: зафиксировать канон **Sale → Order & Commerce → Activation → Delivery** без перестройки ядра на Stage 1.

---

## 2. Decision: Party model — ClientAccount отдельно от Company

### 2.1 Сущности

| Entity | Class | Назначение |
|--------|-------|------------|
| **ClientAccount** | Business | Операционные отношения с клиентом |
| **Company** | Business (party) | Юридическое лицо |
| **Contact** | Business | Физическое лицо |

**`ClientAccount` — не UI-фасад над `Company`.** У сущности собственный стабильный `id` и lifecycle.

### 2.2 Правила

- **Client Account может существовать без Company** (контакт известен, юрлицо — нет).
- **Company может существовать без ClientAccount** (legacy parties).
- **Один Service Order** (Stage 1B+) всегда имеет `client_account_id`; `billing_company_id` — nullable.
- **Удаление/archiving Company не удаляет ClientAccount.**

### 2.3 Stage 1A scope

Stage 1A вводит `ClientAccount` и link columns без Quote, CommercialConfirmation, Readiness, Engagement.

Implementation contract: [`stage-1a-client-account-implementation-contract.md`](../tasks/stage-1a-client-account-implementation-contract.md).

### 2.4 Поэтапная миграция

**Stage 1 — совместимость с текущим `convert-client`:**

1. Создаётся существующая `Company` (как сегодня), когда есть `company_name`.
2. **Параллельно** создаётся `ClientAccount`.
3. `ClientAccount.primary_company_id` → эта `Company` (если есть).
4. Legacy-экраны продолжают использовать `Company` / `converted_client_id`.
5. **Новые** Quote и ServiceOrder (Stage 1B+) используют `client_account_id`.

---

## 3. Security & tenant boundaries (Stage 1A)

| Rule | Requirement |
|------|-------------|
| Tenant ownership | `client_accounts.tenant_id` обязателен; RLS по tenant |
| Cross-tenant links | Запрещены: Lead, Company, ClientAccount должны совпадать по `tenant_id` |
| Cascade delete | **Нет** cascade delete ClientAccount ← Company; archiving Company сохраняет ClientAccount |
| RBAC | `viewer` — read; `admin` / `manager` / `supervisor` — create/update/convert |

---

## 4. References

- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) — Services vs Finance
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) — tenant vs company
- [`ui-constitution-v1.md`](ui-constitution-v1.md) — Обращение, Клиент, Заказ
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — module routing
- [`../../services/module-scope.md`](../../services/module-scope.md) — Services module scope
- [`stage-1a-client-account-implementation-contract.md`](../tasks/stage-1a-client-account-implementation-contract.md) — Stage 1A implementation contract
