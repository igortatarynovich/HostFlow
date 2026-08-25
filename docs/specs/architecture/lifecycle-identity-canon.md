# Lifecycle Identity Canon (operating contract)

**Status:** canonical (L2)  
**Owner:** Architecture canon + platform core  
**Parent (L1):** [`ADR-037-lifecycle-identity-canon.md`](ADR-037-lifecycle-identity-canon.md)  
**Related:** [`process-engine.md`](../platform/process-engine.md) · [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) · [`handoff-contract.md`](handoff-contract.md) · queued runtime [`../tasks/lifecycle-identity-l0-contract-seal.md`](../tasks/lifecycle-identity-l0-contract-seal.md)

This file is **how** ADR-037 appears in subsystems. It does not replace Process Engine or Funnel P0. It forbids treating those layers as the owner of **stage existence**.

---

## 1. Layer split

```text
Module Stage Registry     →  what exists
Company Funnel Instance   →  how this company uses existing keys
Process Engine            →  what is allowed and what happens
Handoff / Conversion      →  how distinct lifecycles connect
UI / /meta/stages         →  resolved projection only
```

| Wrong question to a layer | Right layer |
|---------------------------|-------------|
| “Does `docs_wait` exist for candidates?” | Registry: `recruitment.candidate.docs_wait` |
| “What order does company X show?” | Funnel instance |
| “May we enter ready_for_handoff?” | PE transition evaluator |
| “Create an Employee after hire?” | Handoff / Conversion — not `Candidate.stage = hired` as HR SoT |

**Thesis:** Stage Registry defines what exists. Funnel defines how a company uses it. Process Engine defines what is allowed and what happens. Handoff joins different lifecycles. UI displays the resolved projection.

Same pattern as Country Registry: JSON/manifest → loader → API are **projections**, not three SoTs.

---

## 2. Identity

```text
stage_id = {module_key}.{entity_kind}.{stage_key}
```

- Unique key for existence, PE `maps_to`, funnel reference, analytics mapping, and UI projection.
- `module_key` + `entity_kind` are **mandatory** on every Funnel identity (not optional metadata).
- A funnel for `(recruitment, candidate)` may only reference `recruitment.candidate.*`.

Declared prefixes (register keys in module slices; do not invent a global unscoped enum):

| Prefix | Funnel-managed? | Ends / continues |
|--------|-----------------|------------------|
| `recruitment.lead.*` | Yes | Conversion → Candidate (same module, new entity) |
| `recruitment.candidate.*` | Yes | Terminal / handoff-ready **inside Recruitment** |
| `sales.application.*` | Yes (namespace sealed; catalog later) | Conversion → Client |
| `sales.client.*` | Yes (namespace sealed; catalog later) | Sales client lifecycle |
| `hr.employee.*` | Yes | Independent; inbound from Recruitment Handoff |
| `fleet.*` | Only if Fleet declares a funnel-managed entity | Not implied by this canon |

`Lead.status`, vehicle availability, technical status, assignment status are **not** funnel stages unless the module says so.

---

## 3. Module Stage Registry

**Owns:** existence, semantic identity, default lifecycle attributes, default labels (en / pl / ru when the product shows them), whether an attribute is overlay-allowed.

**Does not own:** company order, company-only labels, PE templates, requirement packs, document types.

Registration path (target): module manifest → registry loader → persisted registry rows. Union of historical lists (`stages.py`, `LeadStage`, FE `CLIENT_PIPELINE_STAGE_CODES`, presets) is **migration coverage discovery only**. Canonical keys are validated as **module-owned identities**, not “everything we ever stored”.

Pseudo-values (`OTHER`, `unknown`, UI “not in list”) are **presentation/input**, not registry countries-equivalent. They must not appear as stage identities.

Aliases (`docs_wait` → `recruitment.candidate.waiting_documents`) live in an **alias table pointing at a registered key**. An alias is not a second identity.

### Existence test (architectural)

For any proposed stage string, exactly one producer may answer:

> Is `{module}.{entity_kind}.{stage_key}` registered?

If two producers can answer independently, the slice is not done.

---

## 4. Company Funnel Instance

Table `funnels` / `funnel_stages` = **configuration**.

Logical row (target, not a required migration in the docs-only slice):

```text
funnel:     (tenant_id, company_id, module_key, entity_kind, name, is_default)
funnel_stage:
  stage_key     → registered recruitment.candidate.docs_wait
  order
  label_overlay → optional
  terminal_overlay / outcome_overlay → only if registry allows
```

Not: `code = docs_wait` as a free existence claim.

`system_stage` four buckets (`new` / `in_progress` / `hired` / `declined_rejected`) are **legacy analytics**, not identity ([module-owned-pipelines-p0.md](module-owned-pipelines-p0.md) §2.5). Do not add new gate logic on that column.

**Merge semantics:** platform/module pack (registry + default pipeline template) is the **base**. Company funnel is an **overlay** (subset, order, allowed attribute overlays). A company must not copy the full pack and then diverge as an independent catalog (fork). Same overlay rule as tenant document policy vs platform pack.

---

## 5. Process Engine

PE §3.1 system stages remain the **mechanism catalog** (templates, evaluator hooks) until a runtime slice binds them to registry ids with `entity_kind`.

**Forbidden after this canon:** describing PE `module.code` as the owner of “does this stage exist for this entity kind?”

Recruitment PE rows `processing_by_hr`, `hired`, `processing_by_client` are **strangler identities** on the recruitment module. Target:

- Recruitment Candidate: stop at handoff-ready / recruitment terminal
- HR: `hr.employee.*` (already a separate manifest)
- Client processing of a **candidate** stays Recruitment only if ownership is still the candidate dossier; client **account** lifecycle is `sales.client.*`

Pipeline templates: every visible step `maps_to` a **fully qualified registry id**, not an unscoped code.

---

## 6. Handoff / Conversion

| Kind | Examples | Not |
|------|----------|-----|
| FunnelTransition | `recruitment.candidate.docs_wait` → `recruitment.candidate.docs_got` | Creating Employee |
| Conversion (same or paired module, new entity) | Recruitment Lead → Candidate; Sales Application → Client | Sharing one stage axis |
| Handoff (cross-module) | Candidate handoff-ready → HR Employee / HR case | `Candidate.stage = processing_by_hr` as HR SoT |

PE already distinguishes `evaluate_transition` vs `evaluate_handoff`. Runtime that PATCHes `Candidate.stage` into HR/client lanes is strangler ([ADR-002](ADR-002-modular-recruitment-hr-boundary.md)).

---

## 7. Custom stages

**First runtime slices: none.** Company picks a subset of the module registry.

A future tenant extension registry requires its own ADR. Until then, `candidate_stage_dict` and arbitrary `FunnelStage.code` are **legacy**, not an extension model.

---

## 8. Strangler inventory (not canon)

These currently **mint or imply** identity. They must become projections or die, in queued slices — not in this document PR.

| Artifact | Today | Target |
|----------|--------|--------|
| `constants/stages.py` | Existence + kanban groups + handoff lanes | Projection / compatibility map → registry |
| `GET /meta/stages` | Mix funnel order + hardcoded groups | Resolved projection of company funnel + registry |
| `FunnelStage.code` | Free identity | FK / qualified `stage_key` |
| `LeadStage` + FE CRM list | Second lead catalog | `recruitment.lead.*` or projection until Sales split |
| Sales UI 3-stage + dual-write Lead | Sales SoT missing | `sales.application.*` |
| `Company.client_stage` + FE list | Unscoped string | `sales.client.*`; then drop column |
| `candidate_stage_dict` | Tenant catalog | Remove or replace with overlay of registry keys |
| Vacancy `profile_stages` | Third column map | Overlay on resolved funnel, keys must be registered |
| PE recruitment `hired` / `processing_by_hr` | HR semantics on recruitment | Handoff; `hr.employee.*` |

**Do not** take the union of these lists as the Recruitment Candidate registry.

---

## 9. What this file does not authorize

- Runtime, migrations, UI cutover
- Expanding `funnels` to “universal engine” without registry references
- Documents E8, Forms P3–P5, Entity Field Composition feat, Fleet funnels
- Promoting the existence rule into L0 `architecture-invariants.md` (needs Architecture RFC)

Enforcement of “no new unregistered identities” starts with the **queued** existence-test slice, not with this L2 file alone.
