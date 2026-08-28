# External Intake / Forms Publish

**Status:** **QUEUED** (brief only; feat locked; **not scheduled**) — Active Product stays [RPM-1](requirement-policy-management.md)
**Phase class:** platform
**Branch (docs):** `docs/v1-blocker-briefs`
**Branch (code):** none — later slices `feat/forms-publish-fpN-…`
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) (blocker 3) · [Release Readiness Gate](../gates/release-readiness-gate.md) · [Acceptance suite RS-2](../journeys/release-readiness-acceptance-suite.md) · [Forms product layer epic](forms-product-layer-epic.md) · [Forms Platform C6](forms-platform-c6-optimization.md) ✅ · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Platform Completion Roadmap](../architecture/platform-completion-roadmap.md) · [Mapping Authority](mapping-authority.md) · [Sequential queue](sales-to-comms-sequential-queue.md)
**Estimate:** 5–7 slices (1 slice = one docs PR + one feat PR)

> v1 blocker 3: **`publish → public form → submit → mapping → canonical entity → visible in workspace`.**
> This is the work the [Forms product layer epic](forms-product-layer-epic.md) calls **P3 Publish UI** and marks `LOCKED`. The Release Goal makes it a **v1 blocker**. FP-1 resolves that contradiction in the canon before any code.
> **Not** P4 Themes. **Not** P5 Analytics. **Not** FormTemplate SoT migration. **Not** a second submit engine. **Not** Mapping Authority (consumed, not rebuilt).
>
> **Amended 2026-08-28 (U-2 decision):** accepting [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) *is* in FP-1 scope. v1 does not ship intake acceptance over a `Proposed` contract whose backend already runs.
> Opening this brief does **not** schedule it. The queue’s Active Product stays RPM-1.

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
| Status echoes not yet amended | [capability catalog](../architecture/platform-capability-catalog.md) · [capability contract](../architecture/capability-contract.md) · [capability settings manifest](../architecture/capability-settings-manifest.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [forms module-scope](../../forms/module-scope.md) — all still print `P3 LOCKED` |

The roadmap no longer forbids the work v1 cannot ship without, and the epic no longer contradicts the Release Goal. **FP-1 propagates the status to the echoing documents above** and seals the publish semantics. Until FP-1 merges and the queue schedules it, no FP feat slice may start — that is the process rule, not a preference.

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
  → FP-5 External intake acceptance bind (needs Mapping Authority)
  → External Intake program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate (PASS =) | Depends on | Estimate |
|---|-------|------------|---------------------|------------|----------|
| **FP-1** | Publish contract seal + unlock + **ADR-022 accept** | `fp-contract` | **Forms Publish Contract Gate** — publish is defined as `commit_publish` only; roadmap anti-pattern 2 amended to unlock **P3 only**; epic status updated; out-of-band `published_version` bumps declared forbidden; [ADR-022](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md) moves `Proposed` → `Accepted` with its review checklist closed | Queue amendment | 1–1.5 slices (docs) |
| **FP-2** | Publish action runtime | `fp-publish` | **Publish Action Gate** — an authenticated product route commits a publication version; presentation save no longer bumps versions; republish is idempotent per identity | FP-1 Gate | 1–2 slices |
| **FP-3** | Public serve from publication | `fp-serve` | **Public Serve Gate** — the public form is served from the frozen snapshot; draft markers rejected; one definition reaches the renderer | FP-2 Gate | 1–2 slices |
| **FP-4** | Operator publish surface | `fp-operator` | **Forms Publish Operator Gate** — operator publishes / unpublishes, sees version history and draft-vs-published state, and obtains the public URL from the product | FP-3 Gate | 1 slice |
| **FP-5** | Acceptance bind | `fp-accept` | **External Intake Acceptance Gate** — RS-2 passes end to end on a fresh tenant: publish → stranger submit → canonical entity visible; abuse protections stated (rate limit is fail-open when Redis is unavailable — declare or fix) | FP-4 Gate **∧** Mapping Authority program close | 1 slice |

---

## FP-1 — Publish contract seal (queued, docs only)

Seals: publish = `commit_publish`; the publication ledger is the only publish record; `published_version` is derived from the ledger and never incremented elsewhere; Builder draft is not a publication; the public renderer consumes the frozen snapshot.

Also performs the **canon unlock**: amends roadmap anti-pattern 2 and the Phase C “still locked” line to unlock **P3 only**, and updates the [epic](forms-product-layer-epic.md) status from `P3 LOCKED` to `P3 = v1 blocker, scheduled by the queue`. P4 / P5 remain locked.

---

## FP-2 — Publish action runtime (queued)

Wire the orphaned operation. Out: themes, analytics, FormTemplate migration, a second submit engine, changing validation semantics.

## FP-3 — Public serve from frozen publication (queued)

Resolve the dual definition. If Builder composition cannot yet drive the public renderer, the surviving definition must be stated in FP-1 and the other declared a named leftover with owner and expiry — not left ambiguous.

## FP-4 — Operator publish surface (queued)

The operator job: publish, unpublish, see what is live, get the URL. Out: theming, A/B, analytics dashboards.

## FP-5 — Acceptance bind (queued)

Depends on [Mapping Authority](mapping-authority.md) program close — the acceptance chain contains “mapping”, and the Release Goal names `Mapping Authority → External Intake` as a known acceptance edge.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | Operators publish forms as versioned publications; the public form is served from that publication; submissions execute on the platform path |
| **Release delta** | External Intake / Forms Publish four-checks PASS. Forms P4 / P5 stay later. Hiring E2E and min HR handoff remain **OPEN** unless separately closed. HostFlow v1 is not release-ready until the [Release Readiness Gate](../gates/release-readiness-gate.md) passes |

---

## Queue position

**Depends on:** queue amendment; FP-5 additionally on Mapping Authority close
**Unlocks:** nothing automatically — “unlock ≠ schedule”
**Does not:** open P4 / P5; migrate `TenantLeadForm` → FormTemplate SoT (U-5 residual: Publish ships on the bridge, and **no new writer may be added to it**); rebuild Shared Intake; touch C2.4

**Does (added 2026-08-28):** accept ADR-022 and close [`ADR-022-review-checklist.md`](../architecture/ADR-022-review-checklist.md).

---

## Refs

- [Forms product layer epic](forms-product-layer-epic.md) — P3 / P4 / P5 definitions and the current `LOCKED` status
- [Forms Platform C6](forms-platform-c6-optimization.md) — Foundation ✅ and what it explicitly excluded
- [Acceptance suite RS-2](../journeys/release-readiness-acceptance-suite.md) — the proof this program must satisfy
- [Mapping Authority](mapping-authority.md) — the acceptance edge FP-5 consumes
- [ADR-007](../architecture/ADR-007-forms-platform-capability.md) — Forms as capability; publication DTO
- [Intake canonical input matrix](../architecture/intake-canonical-input-matrix.md) — Forms does not own domain mapping
