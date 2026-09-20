# Forms Publish Contract

**Status:** **Accepted** (L2 contract — Forms Publish Contract Gate)  
**Date:** 2026-09-20  
**Trusted base:** `integration/release-product-a-b` @ `41be635a`  
**Related:** [`ADR-007`](ADR-007-forms-platform-capability.md) · [`forms-public-contract.md`](forms-public-contract.md) · [`ADR-022`](ADR-022-intake-form-purpose-and-submission-policy-model.md) · [`../tasks/external-intake-forms-publish.md`](../tasks/external-intake-forms-publish.md) · [`../gates/hostflow-v1-release-goal.md`](../gates/hostflow-v1-release-goal.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** (one owner of this write), **INV-01** (one SoT for the operator question), **INV-16** (contract before a second publish action). Does not rewrite L0. Does not mint a second submit engine, FormTemplate SoT, or P4 / P5.

> This file is the **SoT** for the operator question and the single write of HostFlow Form publish.  
> [`forms-public-contract.md`](forms-public-contract.md) remains the Forms Adapter inventory (`publish` = `commit_publish`).  
> [ADR-022](ADR-022-intake-form-purpose-and-submission-policy-model.md) remains Purpose + Target Profile + Submission Policy. This contract names **what publish is**.  
> Machine copy: `forms_publish.v1` in `backend/app/reference/forms_publish_contract.py`.  
> Feat `feat/forms-publish-fp2-publish-action` shipped the authenticated product route. Publish Action Gate **PASS**. Feat `feat/forms-publish-fp3-public-serve` is open. Public Serve Gate **not PASS**. This stamp does not ship runtime.

---

## Operator question (one)

For this HostFlow form, **what is published — the frozen snapshot a stranger fills at the public URL — and which act created that snapshot?**

Answer shape: **draft** · **published** · **live** · **inactive** · **never published**.

No second question is this contract. Mapping Authority, Hiring E2E, min HR, Themes, Analytics, and FormTemplate SoT are other programs.

---

## Write authority (one)

**`commit_publish`** on `forms.endpoint_adapter_v1`. One append-only ledger: `form_publication_versions`.

| May write | Must not write |
|-----------|----------------|
| Adapter `commit_publish` — append an immutable `FormPublicationVersion`, freeze `field_schema` + Contract Identity, update the current pointer | An out-of-band `published_version` increment |
| `TenantLeadForm.published_version` / `published_snapshot_v1` **only** as the denormalized current pointer of that ledger row | Presentation save as publish |
| Idempotent replay of the same `idempotency_key` (no new ledger row) | Builder draft save as publish |
| | A second publication ledger |
| | A public slug / copied URL treated as publish |
| | A new writer on the `TenantLeadForm` bridge (U-5 residual) |

Producer: `backend/app/forms_platform/adapter.py` (`commit_publish`).  
Ledger: `backend/app/models/form_publication_version.py`.  
This contract forbids a second **write** of the same question. The authenticated product route (FP-2) calls this write. It does not ship the operator UI (FP-4). Public serve cutover is FP-3; this stamp opens that feat and does not ship runtime.

---

## Operator-visible semantics (frozen)

These states are what an operator must be able to tell apart. FP-4 surfaces them. This contract names them.

| State | Meaning | Live for a stranger? |
|-------|---------|----------------------|
| **Draft** | Builder / FormDefinition composition. Mutable. Not a publication. | No |
| **Published** | A frozen `FormPublicationVersion` exists for this form. Immutable per version. | Only if that version is the current pointer **and** lifecycle is active |
| **Live** | Current pointer + active lifecycle. The public URL must serve **that** frozen snapshot. | Yes |
| **Inactive** | `deactivate` without rewriting the snapshot. History remains. | No |
| **Never published** | No ledger row. `published_version` on the bridge is not evidence of publish. | No — fail closed |

**Publish** is only `commit_publish`. Copying `public_slug` is not publish. Saving presentation is not publish. Saving a Builder draft is not publish.

**`published_version` is derived from the ledger.** It is the current pointer, not an independent counter. Incrementing it outside `commit_publish` is forbidden.

**Public serve definition (surviving):** the frozen publication snapshot (`FormPublicationVersion` via Adapter `resolve` → Form Runtime).  
**Named leftover (expiry FP-3):** `/public/intake` driven by Entity Profile `form_presentation_runtime_v1` instead of that snapshot. Owner: Forms / Intake. This leftover may not gain a new writer.

When no publication was ever committed, public serve and HostFlow-Form submit **fail closed**. Today's inconsistent path is leftover, not a second definition.

---

## Contract shape (frozen)

- Publish appends a new ledger row. Schema / identity mutation of an existing row is forbidden (`forms_publication_version_immutable`).
- Frozen payload includes `field_schema` + Contract Identity. Missing schema freezes an empty `forms.field_schema.v1` so identity is always complete.
- Submissions pin `form_id` + `published_version` against **that** snapshot.
- `activate` / `deactivate` change lifecycle, not the snapshot.
- Republish with the same identity / `idempotency_key` is idempotent (FP-2 proves the product route).
- ADR-022 Purpose / Submission Policy travel **with** the published snapshot. Changing purpose or policy requires a new published version (ADR-022 §6). This file does not add axes to ADR-022.

---

## Answerer classification (frozen — twelve rows)

A later FP slice may **retire** a leftover. It may not add a thirteenth write of this question.

| # | Live answerer | FP role | Evidence (paths) |
|---|---------------|---------|------------------|
| 1 | Adapter `commit_publish` + `form_publication_versions` + authenticated product route | **Write authority** | `backend/app/forms_platform/adapter.py` · `backend/app/models/form_publication_version.py` · `backend/app/api/v1/platform/forms_publications.py` |
| 2 | `TenantLeadForm.published_version` current pointer | **Consume** | `backend/app/models/tenant_lead_form.py` |
| 3 | Intake admin presentation save | **Not this write** (retired FP-2) | `backend/app/services/intake_form_write_service.py` |
| 4 | Form Definition `published_version` field | **Not this write** (retired FP-2) | `backend/app/intake_platform/form_definition.py` |
| 5 | Builder draft save | **Not this write** | `backend/app/forms_platform/builder/draft_persistence.py` |
| 6 | Entity Profile `form_presentation_runtime_v1` | **Leftover** public-serve definition (FP-3) | `backend/app/entity_profile/presentation_runtime.py` |
| 7 | Publication bridge / Adapter `resolve` | **Consume** | `backend/app/forms_platform/publication_bridge.py` |
| 8 | Form Runtime `serve` | **Consume** | `backend/app/forms_platform/runtime/serve.py` |
| 9 | C6 `public_submit_bridge` | **Consume** | `backend/app/forms_platform/public_submit_bridge.py` |
| 10 | `activate` / `deactivate` | **Consume** (lifecycle, not a new snapshot) | `backend/app/forms_platform/adapter.py` |
| 11 | Communications automation `published_version` | **Not this write** | `backend/app/communications/automation/lifecycle.py` |
| 12 | Public intake HTTP without a ledger row | **Leftover** fail-closed (FP-3) | `backend/app/api/public/intake.py` · `backend/app/entity_profile/public_intake_presentation_bridge.py` |

Roles are closed: `write_authority` · `not_this_write` · `leftover` · `consume`. Exactly one row is `write_authority`.

---

## Architecture review (L0 — ten questions)

| # | Answer |
|---|--------|
| 1 | **Owner:** Forms platform (ADR-007) writes publish via Adapter `commit_publish`. Shared Intake consumes submission. Mapping Authority is a later edge (FP-5), not this write. |
| 2 | Not a new capability. Collapses the de facto presentation bump and the orphaned Adapter op into one publish definition. Does not mint a second form stack. |
| 3 | Existing Adapter: `forms.endpoint_adapter_v1` **Stable** op `publish` = `commit_publish`. No new adapter. |
| 4 | P4 Themes / P5 Analytics stay locked. FormTemplate SoT stays U-5. No second submit engine. Mapping / Hiring / min HR are other programs. |
| 5 | No new Manifest keys. Existing consent / adapter keys unchanged. |
| 6 | SoT for the operator question = this file + `forms_publish.v1`. Parallel leftover writers are classified, not blessed. |
| 7 | `form.published` stays **Experimental**. This seal does not stabilize the event. |
| 8 | **Requires:** Forms Public Contract, publication ledger, Adapter `commit_publish`. **Optional:** ADR-022 axes on the snapshot (Accepted; not expanded here). |
| 9 | No new licence. |
| 10 | Public contract **additive**: publish-write classification + operator-visible states. No breaking Adapter op change. |

**INV-01:** one SoT for “what is published?”. **INV-16:** this contract before a second publish action / editor.

---

## Forms Publish Contract Gate

**PASS** when:

1. This file is the SoT; machine copy `forms_publish.v1` matches the twelve-row table.
2. The only write of “what is published?” is Adapter `commit_publish` onto `form_publication_versions`.
3. Operator-visible states are **draft · published · live · inactive · never published**.
4. Surviving public serve is the frozen publication snapshot; leftover serve is `form_presentation_runtime_v1` (expiry FP-3).
5. Out-of-band `published_version` increment is forbidden. Presentation save and Form Definition leftover writers are retired (FP-2).
6. P3 is unlocked in echoing canon; P4 / P5 stay locked.
7. ADR-022 is Accepted without expanding Purpose / Policy / Match Matrix.
8. Named CI (`test_forms_publish_contract_gate.py`) and the boundary guard are green.
9. The FP-1 PR named FP-2 and did not start runtime (historical; Gate remains PASS). A later feat/open may start FP-2 without reopening this Gate.

---

## Publish Action Gate

**PASS** when:

1. An authenticated product route calls Adapter `commit_publish` and a `form_publication_versions` row exists afterwards.
2. Presentation save does not increment `published_version`.
3. Form Definition apply does not write `published_version`.
4. Republish with the same `idempotency_key` returns the original version and does not append a second ledger row.
5. Named CI (`test_forms_publish_action_gate.py`) is green.
6. FP-3 public serve / embed is not started in the same stamp.

---

## Public Serve Gate

**not PASS.** PASS when:

1. A public request resolves the **live** publication and renders the frozen `form_publication_versions` snapshot through canonical Form Runtime (`resolve` → `serve`).
2. `/public/intake` driven by `form_presentation_runtime_v1` is no longer the working authority surface to the extent of this cutover. Leftover handling follows the named expiry; this is not general cleanup.
3. Public link and later embed remain two access methods to **that one** serve surface. Embed compatibility may be preserved; distribution UX / snippet is FP-4.
4. No second renderer, second publication state, or second submit engine.
5. Draft markers are rejected. Never-published fails closed.
6. This feat/open stamp does not ship runtime.

---

## False close

Reject: bumping `published_version` outside the ledger; a Publish button that writes the draft table; copying a `public_slug` and calling it publish; declaring Builder composition and Entity Profile presentation both “the form”; accepting ADR-022 by rewriting Purpose / Policy / Match Matrix; declaring Publish Action Gate PASS without an authenticated product route that calls `commit_publish`; starting P4 / P5; adding a writer to `TenantLeadForm`; a second submit engine; leftover-store deletion; Hiring E2E / min HR; Foundation ✅; a thirteenth write of this question; a second renderer or second publication state; treating Mapping Operator Surface inherited red as FP-3 scope; shipping an embed snippet / distribution UX in FP-3.

---

## Consequences

- FP-2 wired the orphaned `commit_publish` to an authenticated product route and retired leftover version bumps.  
- FP-3 makes public serve consume the frozen snapshot through one Form Runtime path; the presentation leftover retires to the named expiry. Embed is access compatibility, not a second renderer.  
- FP-4 is the operator surface over these states.  
- FP-5 binds RS-2 and consumes Mapping Authority.  
- ADR-022 Purpose + Policy remain the intake entry axes. Publish does not become a fourth axis.

---

## History

- 2026-09-20: Feat `feat/forms-publish-fp3-public-serve` opened from `41be635a`. Public Serve Gate **not PASS**. Close path = public request → resolve live publication → frozen snapshot → Form Runtime. Twelve-row classification unchanged. This stamp does not ship runtime.
- 2026-09-20: Publish Action Gate **PASS**. Authenticated `POST /api/v1/platform/forms/{form_id}/publish` → `commit_publish` → `form_publication_versions`. Leftover version bumps retired. Republish idempotent per identity. Twelve-row classification unchanged (rows 3–4 retired to `not_this_write`). This stamp does not start FP-3.
- 2026-09-20: Feat `feat/forms-publish-fp2-publish-action` opened from `7112279e`. Publish Action Gate **not PASS**. Twelve-row classification unchanged. This stamp does not ship runtime.
- 2026-09-20: Accepted as FP-1 Publish contract. Twelve-row classification frozen. Feat locked until a later FP-2 branch. Active Product → FP-2 (brief; feat locked).
