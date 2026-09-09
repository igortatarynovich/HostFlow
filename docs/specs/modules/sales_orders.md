# Sales Orders (Service Order + Order Line + Billable Item)

**Status:** canonical (L2 module spec)  
**Owner module:** Sales  
**ADR:** [`ADR-032`](../architecture/ADR-032-client-order-vacancy-flight-chain.md)  
**Not:** Services-module [`additional_services` / `service_orders`](additional_services.md)

## Purpose

Commercial staffing (and related sales) demand: deal snapshot, line-level needs, billable accrual. Recruitment Vacancy executes **one Order Line**; Finance invoices from **Billable Items**.

## Tables

### `sales_orders` (product: Service Order)

Commercial agreement snapshot for one Client Account (and optional Company payer).

Key fields: `client_account_id`, `company_id`, `own_company_id`, `title`, `status`, currency, payment_term_days, payment_model, payer_company_id, vat_rate, guarantee_days, invoice_right_policy, billing_notes, commercial snapshot JSON as needed.

### `sales_order_lines` (Order Line)

One demand line under a Service Order.

Key fields: `sales_order_id`, `title` / role, `location`, `quantity_needed`, `unit_rate`, `charge_unit`, `billing_trigger`, `status`, optional guarantee override.

**Rule:** at most one Vacancy with `vacancies.order_line_id = line.id`.

### `sales_billable_items`

Accrual ready for invoicing.

Key fields: `sales_order_id`, `sales_order_line_id`, `trigger_code`, `amount`, `currency`, `quantity`, `source_entity_type` / `source_entity_id` (e.g. candidate / application), `status` (`pending` \| `invoiced` \| `void`), `invoice_id` nullable.

## Vacancy link

`vacancies.order_line_id` nullable UNIQUE. When set, Vacancy `company_id` and `headcount_target` are aligned from the Line (headcount = `quantity_needed`).

## API (V1)

- `GET/POST /api/v1/sales-orders`
- `GET/PATCH /api/v1/sales-orders/{id}`
- `GET/POST /api/v1/sales-orders/{id}/lines`
- `GET/PATCH /api/v1/sales-order-lines/{id}`
- `GET /api/v1/sales-order-lines?company_id=&unlinked=true`
- `GET/POST /api/v1/sales-billable-items` (create stub / list)

## Auto accrual (V1)

Delivery facade: `backend.app.modules.sales_orders.contracts`.

| Trigger on Order Line | Event | Hook |
|----------------------|-------|------|
| `candidate_hired` | Candidate stage → `hired` / `employed` | `notify_candidate_hired` from candidates PATCH / bulk stage |
| `headcount_completed` | Same hire path; when hired count on vacancy ≥ `quantity_needed` | one billable, source = line |
| `candidate_started_work` | Employee `onboarding` → `active` | `notify_candidate_started_work` from HR review approve |

Idempotent on `(line, trigger, source_entity_type, source_entity_id)` among non-`void`. Amount = `unit_rate` (× qty for headcount). Freeform vacancies (no `order_line_id`) skipped. Not wired: guarantee / milestone / monthly.

## Invoice composer (V1)

- `GET /api/v1/sales-billable-items?sales_order_id=&status=pending`
- `POST /api/v1/sales-orders/{id}/invoices` body `{ billable_item_ids: [...] }`
- Creates Finance **draft** Invoice via existing invoice CRUD; sets selected rows `status=invoiced` + `invoice_id`
- Partial selection allowed; mixed currencies / void / pending+invoiced mix → 422/409
- Sales UI: order detail → Billable Items checklist → «Создать счёт»

## Client Account commercial defaults (V1)

- Column `client_accounts.commercial_defaults` (JSON): `currency`, `payment_term_days`, `payment_model`, `vat_rate`, `guarantee_days`, `invoice_right_policy`
- `PATCH /api/v1/client-accounts/{id}` accepts `commercial_defaults`
- Sales order create: selecting Client Account **prefills** form; «Сохранить как defaults клиента» writes back
- Changing defaults **must not** rewrite existing Service Orders (snapshot SoT)

## Commercial amendment (V1)

- After non-`void` billables, commercial PATCH → **409** (unchanged)
- `POST /api/v1/sales-orders/{id}/amend` — append prior commercial state to `commercial_versions`, bump `commercial_version`, apply new terms
- Columns: `commercial_version` (int, default 1), `commercial_versions` (JSON history)
- UI: order detail → «Amend commercial terms»

## SPA (V1)

- List / create / detail: `/app/sales/orders` (`CRM_APP_PATHS.salesOrders`)
- **Not** Services-module `/app/orders` (additional-services fulfillment)

Operator flow: create Service Order (deal snapshot) → add Order Lines → open Vacancy create and bind a free line.

## Forbidden

See ADR-032 §2.8.
