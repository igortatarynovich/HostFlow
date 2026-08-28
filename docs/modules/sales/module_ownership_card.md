# Sales Module Ownership Card

Status: baseline-established (MOC-1)
Date: 2026-08-28

Program: [`module_independence_program.md`](../../specs/gates/module_independence_program.md) §4 · required by [`module-ownership-coverage.md`](../../specs/gates/module-ownership-coverage.md) MOC-1 (RR1 evidence)
Canon: [`ADR-023`](../../specs/architecture/ADR-023-recruitment-sales-module-separation.md) (separation) · [`ADR-020`](../../specs/architecture/ADR-020-sales-to-engagement-commercial-model.md) (commercial model) · [`sales-domain-pipeline-v1.md`](../../specs/architecture/sales-domain-pipeline-v1.md) (sealed spine) · [`sales_orders.md`](../../specs/modules/sales_orders.md)

## Module

Name: `Sales`
Owner: `Sales`

Layer: ADR-004 product module (licensed), deployed on the Sales host per ADR-023. Not a platform capability.

## Module-Owned Capabilities

1. sales inquiry lifecycle — the commercial result object of an inbound demand;
2. inquiry review, convert and traceability decisions (ambiguous-match review, convert mapping, lineage);
3. commercial client relationship — client account creation, conversion from inquiry, commercial defaults;
4. service order commercial layer — order, order lines, billable accrual, invoice composition **request**;
5. Sales-scoped outbound communication policy (which purposes Sales may send, on which result type);
6. Sales capability spine read model for the inquiry workspace.

## Source-of-Truth Areas

| Zone | Model | Table |
|------|-------|-------|
| Sales inquiry | `SalesInquiry` (`models/sales_inquiry.py`) | `sales_inquiries` |
| Commercial client | `ClientAccount` (`models/client_account.py`) | `client_accounts` |
| Service order | `SalesOrder` (`models/sales_order.py`) | `sales_orders` |
| Order line (commercial fields) | `SalesOrderLine` | `sales_order_lines` |
| Accrual rows for invoicing | `SalesBillableItem` | `sales_billable_items` |

Sales-owned meta keys on the inquiry: `sales_inquiry_lineage_v1`, `convert_mapping_v1`, `ambiguous_match_review_v1`.

Runtime lives in `backend/app/modules/sales/`, `.../client_accounts/`, `.../sales_orders/`; the inquiry HTTP surface is `sales_router` (`/sales/inquiries`) in `backend/app/modules/applications/router.py`.

## Explicitly Out of Scope

Sales does **not** own:

1. Candidate, Recruitment Application, Vacancy lifecycle — Recruitment (ADR-023 §2.2);
2. Employee lifecycle — HR / Workforce (ADR-023 §2.2);
3. invoice and payment statuses, numbering, taxes, KSeF, receivables — Finance (ADR-023 §2.2 names this as a forbidden leak; Sales composes a **draft** and stops);
4. `Lead` as a product entity — Lead is intake transport only (ADR-020, ADR-021); Sales reads it as a transport link on `sales_inquiries.lead_id`;
5. communication transport, thread / message SoT, intent execution — Communication Platform; Sales owns a **policy adapter and binders**, nothing below them;
6. campaign, flight, attribution, dispatch provenance — Acquisition / Flights (ADR-024);
7. form definitions, field types, publish lifecycle — Forms Platform (ADR-007);
8. country / citizenship / document-type and other reference catalogs — Platform Reference Layer (Rule 1);
9. document taxonomy, expiry, requests — Document Hub;
10. requirement / policy merge semantics — RPM;
11. Service catalog lifecycle — Services module (ADR-023 §2.2: Sales may initiate a Service Order; Services owns the lifecycle).

## Delivery Contracts

Outbound (what other modules may call):

- `sales_orders/contracts.py` — `notify_candidate_hired`, `notify_candidate_started_work` (consumed by Recruitment candidate service and HR review);
- `sales/intake/port_adapter.py` — `SalesIntakeAdapter.accept`, registered in the Flights dispatcher as `DISPATCHER_SALES_INQUIRY`;
- `sales/communication/policy_adapter.py` — `SalesCommunicationPolicyAdapter`, registered in `communications/policy_gate.py`;
- `sales/services/sales_inquiry_service.py` — `ensure_sales_inquiry_for_transport_lead`.

Inbound (what Sales consumes through contracts): Communication platform (entity link, result link, send pipeline), Flights destination contract, Intake platform destination handler contract, Entity Profile intake runtime, Forms Platform constants, Companies service for party creation.

## Boundary Rules

1. Sales consumes shared language through platform contracts only; it does not own platform reference semantics.
2. No imports from `backend.app.modules.recruitment` — enforced by `backend/tests/intake_platform/test_intake_runtime_split_r3.py`.
3. Sales sends no SMTP directly. Every outbound message goes binder → policy gate → intent → platform send. The Sales package contains no mail transport.
4. Sales result type is `sales_inquiry` only; the allowed purpose list in the policy adapter is the whole permission surface.
5. Sales may **initiate** a Finance invoice draft; it may not define invoice semantics.

## Current Boundary State

1. Sales / Recruitment package isolation: **enforced and passing**.
2. Outbound compliance and ops mail: **migrated to Pipeline** (2026-07-26). Residual: the legacy SMTP allowlist is smaller but not empty — carried as Epic C R2 in the [unowned work register](../../specs/gates/v1-unowned-work-register.md).
3. `require_module_gate("sales")` exists in `backend/app/auth/module_gate.py` but **no Sales router uses it**; the registry comment claims Sales paths must pass through it. Gate wiring is incomplete.
4. `/api/v1/sales/clients` is registered as a Sales gate prefix, but the router is mounted at the legacy `/api/v1/client-accounts`. The ADR-023 target surface does not exist yet.
5. `/api/v1/sales-orders`, `/sales-order-lines`, `/sales-billable-items` appear in neither the gated nor the exempt prefix list.
6. `sales_orders/compose_invoice.py` imports Finance CRUD directly to create the draft invoice — the ADR-032 v1 pattern, not a registered exception.
7. `vacancies/order_line_bind.py` (Recruitment) reads `SalesOrderLine` / `SalesOrder` ORM directly — ADR-032 bind, not a registered exception.
8. Sales intake imports `modules.leads.duplicate_resolution`; the `leads` package ownership is adjudicated in the [Acquisition card](../acquisition/module_ownership_card.md) §Lead adjudication.
9. Lead is still the transport SoT behind product UI/API until R6 (locked).

Items 3–7 are boundary facts, not gate failures: none of them is a v1 blocker on its own, and none is currently owned by a slice. They belong in a Sales `module_dependency_audit.md`, which this card does **not** substitute for — MOC-1 delivers ownership, not certification.
