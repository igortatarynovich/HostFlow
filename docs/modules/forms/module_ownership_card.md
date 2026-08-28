# Forms Ownership Card

Status: baseline-established (MOC-2)
Date: 2026-08-28

Program: [`module_independence_program.md`](../../specs/gates/module_independence_program.md) §4 · required by [`module-ownership-coverage.md`](../../specs/gates/module-ownership-coverage.md) MOC-2 (RR1 evidence)
Canon: [`ADR-007`](../../specs/architecture/ADR-007-forms-platform-capability.md) (capability) · [`forms-public-contract.md`](../../specs/architecture/forms-public-contract.md) · [`forms-field-catalog-v1-freeze.md`](../../specs/architecture/forms-field-catalog-v1-freeze.md) · [`module-scope.md`](../../forms/module-scope.md)

## Module

Name: `Forms`
Owner: `Forms platform owner`

Layer: **Core Platform Module** — a platform capability, peer of Entity Workspace / RBAC / Automations. ADR-007: *«не часть Recruitment/Acquisition и не шестой лицензируемый продукт ADR-004»*. This matters for the card: Forms is a **provider** to product modules, and product modules are its **clients**, never its owners.

## Module-Owned Capabilities

1. HostFlow Form surface — form definition, composition and Builder draft lifecycle;
2. **Field Catalog** — the single registry of field components: type identity, properties, config schema, validation, normalization, storage contract, Builder palette, public render;
3. publication identity and versioning — frozen field schema per publish, monotonic version, immutable ledger row, idempotent republish, submission pinning;
4. form serve runtime and form execution;
5. submission envelope content;
6. endpoint activation / deactivation and publication resolution;
7. `normalized_answers.v1` as the answer output contract — explicitly *without* domain mapping.

## Source-of-Truth Areas

| Zone | Model / contract | Table |
|------|------------------|-------|
| Publication ledger (append-only) | `FormPublicationVersion` | `form_publication_versions` |
| Current publication pointer | `TenantLeadForm.published_*` | `tenant_lead_forms` |
| Submission content (append-only) | `FormSubmissionEnvelope` | `form_submission_envelopes` |
| Builder draft tip + revisions | `FormBuilderDraft`, `FormBuilderDraftRevision` | `form_builder_drafts`, `form_builder_draft_revisions` |
| Field components | in-memory registry `forms.field_catalog.registry.v1` | none (code SoT) |

Frozen contracts: `forms.field_catalog.registry.v1`, `.descriptors.v1`, `.stdlib.v1`, `.extension.v1`, `forms.field_schema.v1`. Runtime lives in `backend/app/forms_platform/`.

## Explicitly Out of Scope

Forms does **not** own:

1. universal endpoint, submission routing envelope, `route_intent` — Shared Intake / Acquisition (ADR-024);
2. campaign, flight, attribution, outcome, KPI — Acquisition (ADR-007 names this a forbidden zone);
3. domain entities — Candidate, Application, Sales Inquiry, and Lead as transport — Recruitment / Sales;
4. **entity field semantics** — a form places `recruitment.candidate.contacts.phone`; it does not mint `phone`. Field SoT is Entity Field Composition / Field Registry (CL0);
5. **answer → entity field mapping** — Mapping Authority. `normalized_answers.v1` is explicitly «no domain mapping»;
6. requirement / screening / document-requirement policy — Requirement Engine and RPM. A form field marked `required` is validation, not requirement policy;
7. reference catalogs (country, document types, …) — Platform Reference Layer (Rule 1);
8. document registry and file storage SoT — Documents;
9. notifications and mail transport;
10. themes and form analytics — P4 / P5, locked.

## Boundary Rules

1. **The Builder may not invent field types.** A new capability means registering a Catalog component once. The Builder is a Catalog client, composition only.
2. Catalog descriptors are declarative; no executable logic in a descriptor.
3. The Builder draft is not a publication and not a Catalog: `form_builder_draft.py` states it explicitly.
4. A published form is immutable per version. Change means a new version, not a rewrite of a snapshot.
5. Consumers reach Forms through the adapter (`resolve_publication`, serve, execute) and through handler constants — not by reading Forms tables.
6. Forms may not read or write a domain module's tables.

## Current Boundary State

1. **Form definition has more than one live source.** Three exist: the publication ledger (`commit_publish`, contract-complete), the Entity Profile presentation runtime (`form_presentation_runtime_v1`, actively written by intake admin), and Builder drafts (saved, never promoted). The public renderer uses the presentation runtime, not the frozen publication.
2. **`commit_publish` is orphaned in production.** It is defined in `forms_platform/adapter.py` and exported, and no HTTP route or admin service calls it; only contract and gate tests do. Owned by v1 blocker 3 — [External Intake / Forms Publish](../../specs/tasks/external-intake-forms-publish.md).
3. `services/intake_form_write_service.py` increments `published_version` after a presentation upsert **without** writing a ledger row. Two version counters, one name.
4. `TenantLeadForm` is a bridge until a `FormTemplate` SoT exists. No `FormTemplate` class exists in code; the migration is register row U-5 and is excluded from the Publish brief.
5. Recruitment and Sales intake handlers read `TenantLeadForm` **directly** instead of going through the adapter (`lead_draft_handler.py`, `inquiry_draft_handler.py`). Not registered in the direct-access exceptions registry.
6. P1 Field Catalog **CLOSED**, contracts v1 **FROZEN**; P2 Builder MVP **COMPLETE**; **P3 Publish is v1 blocker 3**; P4 / P5 remain locked.
7. Forms Foundation C1–C6 is `PASS_WITH_CONSTRAINTS`: true for the HostFlow-Form-bound intake write path, not true that every module questionnaire is platform-only (the Sales questionnaire Lead glue remains).

Items 1–5 are the reason blocker 3 exists. This card records ownership; it does not close them, and it is not a substitute for a Forms `module_contract_map.md` / `module_dependency_audit.md`.
