# Acquisition Ownership Card

Status: baseline-established (MOC-3)
Date: 2026-08-28

Program: [`module_independence_program.md`](../../specs/gates/module_independence_program.md) §4 · required by [`module-ownership-coverage.md`](../../specs/gates/module-ownership-coverage.md) MOC-3 (RR1 evidence)
Canon: [`ADR-024`](../../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md) · [`ADR-021`](../../specs/architecture/ADR-021-unified-intake-resolution-model.md) (Lead = transport) · [`ADR-023`](../../specs/architecture/ADR-023-recruitment-sales-module-separation.md) · [`module-scope.md`](../../acquisition/module-scope.md) · [`intake-canonical-input-matrix.md`](../../specs/architecture/intake-canonical-input-matrix.md)
Sibling card: [`outcome-commercial-value-ownership.md`](outcome-commercial-value-ownership.md)

## Module

Name: `Acquisition`
Owner: `Acquisition / Growth`

Layer: **platform capability** (Acquisition / Campaigns), not an ADR-004 licensed product module and not a Marketing product.

Canonical statement (ADR-024): **Acquisition creates demand flow; destination modules own the resulting business objects.** A campaign never owns a candidate, an inquiry or a client.

## Module-Owned Capabilities

1. campaign and flight lifecycle — create, launch, pause, resume, targets, spend;
2. endpoint association on a flight (association only — the form belongs to Forms);
3. universal submission routing and routing-context stamping at ingest;
4. **Flights dispatch** — destination registry, destination contract, dispatch provenance ledger;
5. result attribution, outcome, qualification and KPI aggregates;
6. append-only acquisition activity timeline;
7. marketing source profile façade and mapping **diagnostics** (`mapping_applied_v1` fingerprint, mapping health, sample preview);
8. ops read models: live intake monitor, flight compare, cohort and portfolio analytics, source diagnostics, optimisation signals;
9. ROI compose over commercial-value snapshots declared by Sales.

## Source-of-Truth Areas

| Zone | Model | Table |
|------|-------|-------|
| Campaign / flight / targets / forms / sources | `Campaign`, `CampaignRun`, `CampaignTarget`, `CampaignRunForm`, `CampaignRunIntakeSource` | `acq_campaigns`, `acq_campaign_runs`, `acq_campaign_targets`, `acq_campaign_run_forms`, `acq_campaign_run_intake_sources` |
| Ad binding | `FlightAdBinding` | `acq_flight_ad_bindings` |
| Attribution / outcome / links / spend / qualification | `CampaignResultAttribution`, `CampaignOutcome`, `CampaignOutcomeResultLink`, `CampaignFlightSpendEntry`, `CampaignResultQualification` | `acq_result_attributions`, `acq_outcomes`, `acq_outcome_result_links`, `acq_flight_spend_entries`, `acq_result_qualifications` |
| Activity timeline (append-only) | `AcquisitionActivityEvent` | `acquisition_activity_events` |
| Dispatch provenance | `FlightDispatchLedger` | `acq_flight_dispatch_ledger` |
| Intake source profile / binding | `IntakeSourceProfile`, `IntakeSourceBinding` | `intake_source_profiles`, `intake_source_bindings` |

Runtime: `backend/app/acquisition/` (48 files: root services, `activity/`, `contracts/`, `flights/`, `ops/`), plus the thin reference packages `backend/app/modules/intake_routing/` and `.../outcome_rules/`. `backend/app/intake_platform/` is a **separate** platform orchestration layer (ADR-022); its `destination_registry` is a compat shim re-exporting `acquisition.flights.destination_registry`.

## Lead adjudication (the `leads` package)

`backend/app/modules/leads/` (45 files, four routers) was claimed simultaneously by the Recruitment card («lead intake processing»), by the Integrations dependency audit (which scopes `backend/app/modules/leads/*.py`), and by the module catalog (which demotes `/api/v1/leads` to «admin/ingest/transport only»). This card settles it, because [the coverage record](../../specs/gates/module-ownership-coverage.md) §3 assigned the adjudication here.

**Adjudication.** `Lead` is **intake transport**, not a product entity — ADR-020, ADR-021 («внутренний transport intake … не product object»), ADR-023 §4. Therefore the `leads` package is **not one module's property**: it is a legacy monolith holding four different owners' code behind one transport record. No card claims the package as a whole. Ownership is per concern:

| Concern | Owner | Paths |
|---------|-------|-------|
| Channel ingest, provider credentials, OAuth, webhook verification | **Integrations** (ADR-024 §3) | `webhook.py`, `inbound_public.py`, `pipeline.py`, `admin_service.py`, `meta_oauth_service.py`, `meta_tenant_resolve.py`, `meta_marketing_graph.py`; models `meta_lead_*`, `meta_ads_map`, `meta_form_routes`; `/api/v1/settings/leads/*` |
| Routing, routing-context stamping, intake duplicate resolution | **Acquisition / Shared Intake** | `intake_route.py`, routing stamps in `service/_processing.py`, `duplicate_resolution.py`, `duplicate_decision.py` |
| Field mapping resolution | **transitional** → [Mapping Authority](../../specs/tasks/mapping-authority.md) | `field_mapping_resolve.py` |
| Conversion to Candidate / Application and recruitment qualification | **Recruitment** | `lead_candidate_conversion.py`, `lead_qualification_rules.py`, `lead_criteria_eval.py`, `recruiter_validation.py`, `lead_stage_contract.py`, `lead_candidate_doc_loader.py`, recruitment paths in `service/intake_decision.py`, `service/intake_vacancy_confirm.py` |
| Conversion to client / service order, questionnaire invite, call result | **Sales** | `lead_client_conversion.py`, `lead_service_order_conversion.py`, `lead_questionnaire_invite.py`, `service/call_result.py`, `convert-client` on the router |
| `Lead` ORM, transport CRUD, normalizer, operational `/api/v1/leads` endpoints | **shared transport, no product owner** until R6 | `crud.py`, `normalizer.py`, `router.py`, `next_action_*`, `pipeline_hooks.py`, `tenant_business_type.py` |

**Consequences of this adjudication:**

1. Acquisition claims routing, provenance and diagnostics inside `leads` — **not** Lead CRM operations, **not** Meta credential SoT, **not** candidate or inquiry creation.
2. The Recruitment card's phrase «lead intake processing» must be read as **conversion and qualification**, not intake transport. It is overbroad as written and should be narrowed when the Recruitment card is next revised; this card does not edit another module's card.
3. The last row is the honest one: the operational `/api/v1/leads` surface and the legacy `/app/leads` UI still expose Lead as if it were a product object, which ADR-021 forbids. That is the **R6 cutover**, locked, and recorded as a residual — not something this card resolves.
4. No physical package split is scheduled. This card assigns owners to code that stays where it is; moving files is a separate slice and is not a v1 blocker.

## Explicitly Out of Scope

Acquisition does **not** own:

1. Candidate, Application, Vacancy — Recruitment (ADR-023 §2.2, ADR-024 §3);
2. Sales Inquiry, Client Account, Service Order — Sales (ADR-020, ADR-023);
3. form builder, field schema, consent versions, publish lifecycle — Forms (ADR-007);
4. field registry / entity profile semantics — Entity Field Composition (Rule 1);
5. requirement policy — RPM;
6. **answer → field mapping write authority** — Mapping Authority (v1 blocker 1). Acquisition keeps consumption and diagnostics;
7. communication transport and delivery — Communication Platform (ADR-012);
8. reference catalogs — Platform Reference Layer (Rule 1);
9. Meta OAuth credentials and webhook verify tokens — Integrations (ADR-024 §3);
10. SalesOrder / invoice / billable amount SoT — Sales and Finance (ADR-032). Acquisition owns the ROI **compose** over values Sales declares;
11. document taxonomy — Documents;
12. a Marketing product (`marketing.*`) — explicit ADR-024 anti-scope.

## Delivery Contracts

- `acquisition/flights/destination_contract.py` — `DestinationSubmitRequest`, `DestinationDispatchResult`, `OpaqueResultRef`; dispatcher ids `DISPATCHER_CANDIDATE_APPLICATION`, `DISPATCHER_SALES_INQUIRY`;
- `acquisition/flights/destination_registry.py` — contract `flights.destination_registry.v1`, destinations `DESTINATION_RECRUITMENT`, `DESTINATION_SALES`;
- `acquisition/contracts/outcome_commercial_value.py` — `OutcomeCommercialValueRead`.

Registered destination adapters: `RecruitmentIntakeAdapter`, `SalesIntakeAdapter`. Consumers: `intake_platform/handler_dispatch.py`, `forms_platform/handlers.py`, communication threads (`OpaqueResultRef` for traceability), the platform campaigns API.

## Boundary Rules

1. Routing happens **once**, at Lead creation; continuation submissions inherit context.
2. A destination is reached only through the published destination contract; Acquisition never constructs a domain entity itself.
3. Acquisition consumes resolved mapping rules; it does not become a second mapping write authority.
4. The dispatch ledger is provenance, append-only; it is not a business audit log for the destination module.
5. Acquisition surfaces read models over destination results; it does not own the results.

## Current Boundary State

1. Stage 3A–3E, Stage 4 and Stage 6 delivered; **Acquisition Automation 🔄** — Stage 5 / R6 residual (register D2).
2. **R6 physically separate queues / APIs: LOCKED.** Lead remains the transport SoT behind product UI and API; the compat surface stays until R6.
3. `leads` package ownership: adjudicated above per concern; **no split scheduled**.
4. Mapping: three stores (`intake_source_profiles.mapping_rules`, `meta_lead_form_mappings.mapping_rules`, `meta_lead_settings.field_mapping`) with a silent fallback chain resolved in `modules/leads/field_mapping_resolve.py` + `entity_profile/ingest_runtime.py`. Collapsing them is v1 blocker 1; Acquisition loses its parallel write surfaces there.
5. Stage 3E deferred items D1–D5 (Meta → Submission normalisation, duplicate disposition choke-point, transaction boundaries) remain open with suggested homes, not owners.
6. No Acquisition / intake / leads rows in the [direct-access exceptions registry](../../specs/gates/system_direct_access_exceptions_registry.md) — the absence means «never registered», not «no direct access».

This card delivers ownership only. Acquisition has no `module_contract_map.md`, `module_dependency_audit.md` or `module_test_boundary.md`, and is therefore **not certified** under the Module Independence Program.
