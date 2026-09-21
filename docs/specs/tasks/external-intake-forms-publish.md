# External Intake / Forms Publish

**Status:** **ACTIVE** — Forms Publish Contract Gate **PASS**. Publish Action Gate **PASS**. Public Serve Gate **PASS**. Operator Publish Gate **PASS**. External Intake Acceptance Gate **PASS**. Active Product = External Intake program close (brief; feat locked).
**Phase class:** platform
**Branch (docs):** `docs/forms-publish-fp1-contract-seal`
**Branch (code):** `feat/forms-publish-fp5-runtime`. External Intake Acceptance Gate **PASS**.
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 3) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-2](../journeys/release-readiness-acceptance-suite.md) · [Forms product layer epic](forms-product-layer-epic.md) · [Forms Platform C6](forms-platform-c6-optimization.md) ✅ · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Publish Contract](../architecture/forms-publish-contract.md) (`forms_publish.v1`) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Mapping Authority](mapping-authority.md) · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 5–7 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 3: **`publish → public form → submit → mapping → canonical entity → visible in workspace`.**
> This is the work the [Forms product layer epic](forms-product-layer-epic.md) calls **P3 Publish UI**. The Release Goal makes it a **v1 blocker**. FP-1 sealed the publish contract.
> **Not** P4 Themes. **Not** P5 Analytics. **Not** FormTemplate SoT migration. **Not** a second submit engine. **Not** Mapping Authority (consumed, not rebuilt).
>
> **U-2:** [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) is **Accepted** (Purpose + Policy unchanged). Publish definition SoT: [forms-publish-contract.md](../architecture/forms-publish-contract.md) (`forms_publish.v1`).
> Mapping program is **DONE**. Unlock ≠ schedule of leftover-store deletion / Hiring / RS-3. The queue’s Active Product is External Intake program close after External Intake Acceptance Gate **PASS**.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**
HostFlow cannot acquire an external candidate through a form that an operator published. The platform has everything except the act of publishing: `commit_publish` exists in the Forms adapter, appends an immutable publication version, and freezes `field_schema` + `contract_identity` — but **no production HTTP route or admin service calls it**. Meanwhile the intake admin bumps `published_version` on presentation save without writing the ledger, the Builder saves drafts and says so in its own UI (“publish remains a separate action (P3 locked)”), and the public renderer is driven by Entity Profile presentation rather than the frozen publication. The result is a *de facto* publish that no contract governs, and two competing definitions of “what the form is”.

**Completion proof (named consumer):**
**RS-2 in the [acceptance suite](../journeys/release-readiness-acceptance-suite.md)**: an operator publishes a form from the product, a stranger submits it at the public URL in a private browser, and the submission appears in the workspace as a canonical entity — where “published” means a frozen publication version exists and the public form was served from **that** snapshot. The consumer that must **not** fork: the public intake path must serve the frozen publication instead of keeping a parallel presentation-only definition.

**False close (reject):** copying a `public_slug` URL and calling it publish; bumping `published_version` outside the ledger; a Publish button that writes the draft table; proving the chain with the admin smoke test (it creates a draft lead, not a canonical entity); shipping themes/analytics; declaring done while Builder composition still cannot reach the public renderer.

---

## Canon contradiction this brief must resolve first

| Source | Says |
|--------|------|
| [Release Goal](../gates/hostflow-v1-release-goal.md) | Blocker 3 — `publish → public form → submit → mapping → canonical entity`; “Forms P4 / P5 stay later” |
| [Roadmap](../architecture/platform-completion-roadmap.md) § Anti-patterns 2 / § Phase C | **Amended with this brief:** P3 is v1 blocker 3; unlock instrument = FP-1 + queue amendment; P4 / P5 stay locked |
| [Forms product layer epic](forms-product-layer-epic.md) | `P3 Publish UI … LOCKED` → **amended with this brief** to “v1 blocker 3, feat locked until FP-1” |
| Status echoes | [capability catalog](../architecture/platform-capability-catalog.md) · [capability contract](../architecture/capability-contract.md) · [capability settings manifest](../architecture/capability-settings-manifest.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [forms module-scope](../../forms/module-scope.md) — P3 = v1 blocker 3 (contract sealed); P4 / P5 stay locked |

The roadmap no longer forbids the work v1 cannot ship without, and the epic no longer contradicts the Release Goal. **FP-1 sealed the publish semantics** (`forms_publish.v1`). **FP-2 Publish Action Gate PASS**. **FP-3 Public Serve Gate PASS**. Feat `feat/forms-publish-fp4-operator-surface` shipped the operator surface. Operator Publish Gate **PASS**. Feat `feat/forms-publish-fp5-runtime` shipped the stranger submit path. External Intake Acceptance Gate **PASS**.

---

## Starting point (measured, not assumed)

Evidence collected 2026-08-28.

### Exists and is contract-complete

| Capability | Where |
|------------|-------|
| Publish operation | `forms_platform/adapter.py` → `commit_publish` (appends `form_publication_versions`, updates current pointers, freezes `field_schema` + identity) |
| Append-only ledger | `models/form_publication_version.py` — “One immutable row per commit_publish” |
| Runtime (C4) | `forms_platform/runtime/serve.py` — rejects authoring payloads via `_DRAFT_MARKERS`; read-only Runtime Model |
| Execution (C5) | `forms_platform/execution/execute.py` — validate → pin → persist envelope |
| Shared-Intake wiring (C6) | `forms_platform/public_submit_bridge.py` invoked from public apply-submit |
| Builder (C3) | `forms_platform/builder/**` + `/api/v1/platform/forms/builder` — file header: “No publish, themes, analytics, or intake mapping. Save is Draft only.” |
| Public surface protections | `enforce_rate_limit(... scope="public:intake")` + `require_turnstile(...)` on public intake create and company submit |

### The gap, precisely

| Step of the chain | Today | Missing |
|-------------------|-------|---------|
| **publish** | `commit_publish` reachable only from tests; presentation save increments `published_version` in `services/intake_form_write_service.py` without a ledger row | An operator publish action that calls `commit_publish`; removal of the out-of-band version bump; draft → published promotion for Builder composition |
| **public form** | `/public/intake?lead_form_slug=…` → apply session → renders `form_presentation_runtime_v1` (Entity Profile presentation) | Public serve driven by the **frozen publication snapshot**; one definition instead of Builder composition vs presentation |
| **submit** | C6 `resolve → serve → execute` when the session is HostFlow-Form-bound | Deterministic behaviour when no publication was ever committed (today: inconsistent) |
| **mapping** | admin mapping editor + ingest rules | Consumes [Mapping Authority](mapping-authority.md) — acceptance edge, not this program’s write |
| **canonical entity** | `dispatch_public_intake_submit` → route_intent handlers | One proven path where a published form always yields a canonical entity |
| **visible in workspace** | entities appear when handlers succeed | Acceptance-tested closed loop (RS-2), not a draft-lead smoke test |

---

## Internal ladder (this program only)

```text
FP-1 Publish contract seal + roadmap unlock (docs)
  → FP-2 Publish action runtime
  → FP-3 Public serve from frozen publication
  → FP-4 Operator publish surface
  → FP-5 External submission (RS-2 path)
  → External Intake program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **FP-1** | Publish contract seal + unlock + **ADR-022 accept** | `fp-contract` | **Forms Publish Contract Gate** ✅ — publish is defined as `commit_publish` only; SoT [forms-publish-contract.md](../architecture/forms-publish-contract.md) (`forms_publish.v1`); P3 unlocked in echoing canon; out-of-band `published_version` bumps forbidden; [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) **Accepted** without expanding Purpose / Policy / Match Matrix | Queue amendment [#377](https://github.com/igortatarynovich/HostFlow/pull/377) / `54537f00` | 1–1.5 slices (docs) |
| **FP-2** | Publish action runtime | `fp-publish` | **Publish Action Gate** ✅ — an authenticated product route commits a publication version; presentation save no longer bumps versions; republish is idempotent per identity | FP-1 Gate | 1–2 slices |
| **FP-3** | Public serve from publication | `fp-serve` | **Public Serve Gate** ✅ — public request → resolve live publication → frozen snapshot → Form Runtime; unpublished/inactive not live; one renderer; FP-2 write unchanged | FP-2 Gate | 1–2 slices |
| **FP-4** | Operator publish surface | `fp-operator` | **Operator Publish Gate** ✅ — Never published → Publish (`commit_publish`) → Live v1 + public URL → Unpublish (`deactivate_endpoint`) → Inactive + URL absent. Feat `feat/forms-publish-fp4-operator-surface`. UI re-reads backend authority | FP-3 Gate | 1 slice |
| **FP-5** | External submission | `fp-accept` | **External Intake Acceptance Gate** ✅ — operator live public URL → stranger without auth opens → fills → submit → existing C6 / public-submit contracts → production intake → intake/person/application visible in workspace. Feat `feat/forms-publish-fp5-runtime`. Browser E2E through that URL | Operator Publish Gate | 1 slice |

---

## FP-1 — Publish contract seal (**PASS**)

Sealed: publish = `commit_publish`; the publication ledger is the only publish record; `published_version` is derived from the ledger and never incremented elsewhere; Builder draft is not a publication; the public renderer **must** consume the frozen snapshot (leftover presentation serve named, expiry FP-3).

SoT: [forms-publish-contract.md](../architecture/forms-publish-contract.md) (`forms_publish.v1`). Named CI + boundary guard. The FP-1 PR kept the feat locked.

Canon unlock: P3 only. P4 / P5 remain locked. ADR-022 Accepted without expanding the model.

## FP-2 — Publish action runtime (**PASS**; feat `feat/forms-publish-fp2-publish-action`)

Wired the orphaned operation: authenticated `POST /api/v1/platform/forms/{form_id}/publish` → Adapter `commit_publish` → `form_publication_versions`. Presentation save and Form Definition leftover version bumps retired. Republish is idempotent per identity. Out: themes, analytics, FormTemplate migration, a second submit engine, changing validation semantics, public serve/embed.

## FP-3 — Public serve from frozen publication (**PASS**; feat `feat/forms-publish-fp3-public-serve`)

Close path (narrow): **public request → resolve live publication → frozen `form_publication_versions` snapshot → canonical Form Runtime render**. Public link and later embed remain two access methods to **one** serve surface, not two renderer or publish mechanisms. Embed may be counted as serve-surface compatibility; distribution UX / snippet is a later product slice (not this FP-4 operator surface).

`/public/intake` driven by Entity Profile `form_presentation_runtime_v1` is no longer the working authority for HostFlow-form public serve. Leftover handling followed the named expiry already sealed in [forms-publish-contract.md](../architecture/forms-publish-contract.md) — not a pretext for general cleanup.

Unpublished / inactive forms are not served as live. The public renderer does not treat `form_presentation_runtime_v1` as authority. No second public renderer. FP-2 publish-write semantics are unchanged.

## FP-4 — Operator publish surface (**PASS**; feat `feat/forms-publish-fp4-operator-surface`)

Close path (operator): **Never published → Publish (`commit_publish`) → Live v1 + public URL → Unpublish (`deactivate_endpoint`) → Inactive + URL absent**. After each act the operator surface re-reads backend publication authority. Publish / unpublish call closed FP-2 authority (`commit_publish` / lifecycle). Live state and public URL read closed FP-3 authority (live publication → frozen snapshot → Form Runtime `serve()`). UI displays authority; it is not a new authority. No new publication or serve semantics. Embed snippet is a later product slice and keeps the one-serve-surface invariant. Out: embed snippet; themes / analytics; a second serve or publish mechanism; leftover-store deletion; Hiring; P4 / P5; Mapping Operator Surface inherited red at `54537f00`.

## FP-5 — External submission (**PASS**; feat `feat/forms-publish-fp5-runtime`)

Close path (RS-2 path): **live public URL (FP-4) → stranger without auth opens it → fills → submit → production intake accepts → real intake/person/application per existing contracts**, visible on the HostFlow candidates surface. Create → Publish → Serve → Operator controls live URL is **closed**. This slice is **Stranger opens → fills → submits → HostFlow receives**. Production intake consumes closed FP-3 serve and existing C6 / public-submit contracts. No second submit engine. No new form architecture.

Browser E2E through the real published URL is the close proof (`e2e/forms-publish-fp5-external-submit.ui.spec.ts`), together with named CI `test_forms_publish_acceptance_gate.py`. Rate limit remains fail-open when Redis is unavailable.

Out: Mapping / RS-3 field placement; Hiring E2E; min HR; embed snippet; leftover-store deletion; a new form architecture; a second submit engine; P4 / P5. Mapping program is **DONE**; RS-3 remains Mapping’s proof and is not this gate.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | Operators publish forms as versioned publications; the public form is served from that publication; submissions execute on the platform path |
| **Release delta** | External Intake / Forms Publish four-checks PASS. Forms P4 / P5 stay later. Hiring E2E and min HR handoff remain **OPEN** unless separately closed. HostFlow v1 is not release-ready until the [Release Readiness Gate](../gates/release-readiness-gate.md) passes |

---

## Queue position

**Depends on:** queue amendment [#377](https://github.com/igortatarynovich/HostFlow/pull/377). External Intake Acceptance Gate **PASS**. Mapping program is already **DONE**; this slice does not write Mapping and does not prove RS-3.  
**Active Product:** External Intake program close (brief; feat locked) after External Intake Acceptance Gate **PASS**. Operator Publish Gate **PASS**. Public Serve Gate **PASS**. Publish Action Gate **PASS**. Forms Publish Contract Gate **PASS**.  
**Unlocks:** nothing automatically — “unlock ≠ schedule”  
**Does not:** mix Mapping / RS-3; add embed snippet; mint a second renderer, publication state, or submit engine; open P4 / P5; migrate `TenantLeadForm` → FormTemplate SoT (U-5 residual: Publish ships on the bridge, and **no new writer may be added to it**); rebuild Shared Intake; touch C2.4; start leftover-store deletion / Hiring / min HR; invent a new form architecture; expand Mapping Operator Surface inherited reds

**Does:** ship feat `feat/forms-publish-fp5-runtime` against sealed [forms-publish-contract.md](../architecture/forms-publish-contract.md) (`forms_publish.v1`). Close path is `live public URL → stranger without auth opens → fills → submit → production intake accepts → real intake/person/application per existing contracts`, proven by browser E2E through that URL. ADR-022 stays Accepted without expansion.

---

## Refs

- [Forms Publish Contract](../architecture/forms-publish-contract.md) — FP-1 SoT (`forms_publish.v1`)
- [Forms product layer epic](forms-product-layer-epic.md) — P3 / P4 / P5 definitions
- [Forms Platform C6](forms-platform-c6-optimization.md) — Foundation ✅ and what it explicitly excluded
- [Acceptance suite RS-2](../journeys/release-readiness-acceptance-suite.md) — the path this slice must close (stranger through the published URL into production intake). RS-3 / Mapping stay out.
- [Mapping Authority](mapping-authority.md) — **DONE**. RS-3 remains Mapping’s proof; not this slice.
- [ADR-007](../architecture/ADR-007-forms-platform-capability.md) — Forms as capability; publication DTO
- [Intake canonical input matrix](../architecture/intake-canonical-input-matrix.md) — Forms does not own domain mapping

---

## History
- 2026-09-21: **External Intake Acceptance Gate PASS.** Feat `feat/forms-publish-fp5-runtime` from `de6383aa` ([#385](https://github.com/igortatarynovich/HostFlow/pull/385)). Close path = operator live public URL → stranger without auth opens → fills → submit → existing public submission/intake contract → production intake → intake/person/application visible in HostFlow workspace. Browser E2E through that published URL. Rate limit remains fail-open when Redis is unavailable. No second submit engine. Not Mapping/RS-3. Not leftover-store deletion. Not Hiring. Not embed snippet. Not P4 / P5. Mapping Operator Surface inherited red at `54537f00` is not this slice. Active Product → External Intake program close (brief; feat locked).
- 2026-09-21: **FP-5 External submission feat opened.** Branch `feat/forms-publish-fp5-external-submit` from `5e2a8f59` ([#384](https://github.com/igortatarynovich/HostFlow/pull/384)). Close path = live public URL → stranger without auth opens it → fills → submit → production intake accepts → real intake/person/application per existing contracts. Browser E2E through that published URL is the later runtime proof, not API composition. External Intake Acceptance Gate **not PASS**. This stamp does not ship runtime. Not Mapping/RS-3. Not leftover-store deletion. Not Hiring. Not embed snippet. Not a new form architecture. Not P4 / P5.
- 2026-09-20: **Operator Publish Gate PASS.** Never published → Publish (`commit_publish`) → Live v1 + public URL → Unpublish (`deactivate_endpoint`) → Inactive + URL absent. After each act the operator surface re-reads backend publication authority. UI does not compute live. Embed snippet is a later product slice. Active Product → **FP-5** (brief; feat locked). Do not start FP-5 / embed in this PR. Not leftover-store deletion. Not Hiring. Not P4 / P5. Mapping Operator Surface inherited red at `54537f00` is not this slice.
- 2026-09-20: **FP-4 Operator Publish Surface feat opened.** Branch `feat/forms-publish-fp4-operator-surface` from `9cc986ce` ([#382](https://github.com/igortatarynovich/HostFlow/pull/382)). Close path = operator opens form → sees current publication state/version → publish or unpublish → sees resulting live state → obtains public URL from product UI. Publish uses closed FP-2 `commit_publish` authority. Live/public URL uses closed FP-3 serve authority. Embed snippet is a later product slice (one serve surface). Operator Publish Gate **not PASS**. This stamp does not ship operator UI. Not leftover-store deletion. Not Hiring. Not P4 / P5. Mapping Operator Surface inherited red at `54537f00` is not this slice.
- 2026-09-20: **Public Serve Gate PASS.** public request → Adapter resolve live publication → frozen `form_publication_versions` snapshot → canonical Form Runtime. Unpublished/inactive not served as live. `form_presentation_runtime_v1` is not HostFlow-form public-serve authority. No second renderer. FP-2 publish-write unchanged. Active Product → **FP-4** (brief; feat locked). Do not start FP-4 in this PR. Not leftover-store deletion. Not Hiring. Not P4 / P5.
- 2026-09-20: **FP-3 Public Serve feat opened.** Branch `feat/forms-publish-fp3-public-serve` from `41be635a` ([#380](https://github.com/igortatarynovich/HostFlow/pull/380)). Close path = public request → resolve live publication → frozen `form_publication_versions` snapshot → canonical Form Runtime render. Leftover `/public/intake` → `form_presentation_runtime_v1` follows named expiry, not general cleanup. Embed is serve-surface compatibility, not FP-4 snippet UX. Public Serve Gate **not PASS**. This stamp does not ship runtime. Not Hiring / leftover-store deletion. Not P4 / P5.
- 2026-09-20: **Publish Action Gate PASS.** Authenticated `POST /api/v1/platform/forms/{form_id}/publish` → Adapter `commit_publish` → `form_publication_versions`. Leftover presentation / Form Definition version bumps retired. Republish idempotent per identity. Active Product → **FP-3** (brief; feat locked). Do not start FP-3 in this PR. Not Hiring / leftover-store deletion. Not P4 / P5.
- 2026-09-20: **FP-2 Publish Action feat opened.** Branch `feat/forms-publish-fp2-publish-action` from `7112279e` ([#378](https://github.com/igortatarynovich/HostFlow/pull/378)). Close path = authenticated product route → Adapter `commit_publish` → `form_publication_versions`; leftover presentation / Form Definition version bumps retire; republish is idempotent per identity. Publish Action Gate **not PASS**. This stamp does not ship runtime. Not FP-3 / Hiring / leftover-store deletion. Not P4 / P5.
- 2026-09-20: **Forms Publish Contract Gate PASS.** SoT = [forms-publish-contract.md](../architecture/forms-publish-contract.md) (`forms_publish.v1`). ADR-022 **Accepted** without expanding Purpose / Policy / Match Matrix. P3 unlocked in echoing canon; P4 / P5 stay locked. Feat still locked. Active Product → **FP-2** (brief; feat locked this PR). Do not start FP-2 in this PR. Hiring E2E / min HR remain queued. Not leftover-store deletion. Not P4 / P5.
- 2026-09-20: Queue amendment names **FP-1** Active Product (brief; feat locked). Mapping program **DONE**. Forms Publish Contract Gate **not PASS**. Do not seal the publish contract in this PR. Hiring E2E / min HR remain queued. Not leftover-store deletion. Not FP-2. Not P4 / P5.
