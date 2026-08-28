# Module ownership coverage — record

**Status:** L2 OPERATING CANON (coverage record; not a gate outcome)
**Date:** 2026-08-28
**Owner:** Architecture canon owner (classification) + Engineering lead (enforcement)
**Parents:** [`module_independence_program.md`](module_independence_program.md) · [`module_independence_program_closeout.md`](module_independence_program_closeout.md) · AGENTS.md **Rule 3** (Ownership Card Required Before New Domain Creation) · **Rule 7** (Every Boundary Requires Enforcement)
**Consumers:** [`release-readiness-gate.md`](release-readiness-gate.md) RR1 · [`v1-unowned-work-register.md`](v1-unowned-work-register.md)

> **Why this record exists.** The Module Independence Program closed `PASS` on 2026-05-29 with the outcome sentence «all active core modules have ownership boundaries documented». That sentence was true of the **five logical modules it certified** and is **no longer true of the system**: domains that carry v1 blocker traffic today — Sales, Forms, Acquisition — have runtime code and no ownership card. This record does not reopen the program gate; it states the coverage that actually exists, so that Rule 3 stops being retroactively self-certifying.

---

## 1. What the closeout certified

| Module | Card | Contract map | Dependency audit | Test boundary |
|---|---|---|---|---|
| Documents | ✅ | ✅ | ✅ | ✅ |
| Recruitment | ✅ | ✅ | ✅ | ✅ |
| HR | ✅ | ✅ | ✅ | ✅ |
| Workforce | ✅ | ✅ | ✅ | ✅ |
| Integrations | ✅ | ✅ | ✅ | ✅ |

All four artifacts live under `docs/modules/<module>/`. Three of these five (HR, Workforce, Integrations) have **no package** under `backend/app/modules/`; their code lives in `backend/app/services/hr_*.py`, `backend/app/api/v1/workforce/`, `backend/app/api/public/intake.py` and `backend/app/acquisition/`. The card set is therefore **logical**, not path-derived — which is why no card names a Python package.

---

## 2. Domains with runtime code and no ownership card

| Domain | Runtime evidence | On a v1 blocker path? | Disposition |
|---|---|---|---|
| **Sales** | `backend/app/modules/sales/` (16 `.py`: `intake/`, `communication/`, `services/sales_inquiry_service.py`) · `client_accounts/` (6) · `sales_orders/` (5) · separated from Recruitment by [ADR-023](../architecture/ADR-023-recruitment-sales-module-separation.md) | **Yes** — sales inquiry → communication is the queue's own name and the RS-6 acceptance path | **Card required before Release Readiness Gate** (§4) |
| **Forms** | `backend/app/forms_platform/` · `docs/forms/module-scope.md` · Field Catalog v1 FROZEN | **Yes** — v1 blocker 3 ([Forms Publish](../tasks/external-intake-forms-publish.md)) | **Card required before Release Readiness Gate** (§4) |
| **Acquisition** | `backend/app/acquisition/` (48 files) · `modules/intake_routing/` · `modules/outcome_rules/` · `docs/acquisition/module-scope.md` | **Yes** — v1 blocker 1 ([Mapping Authority](../tasks/mapping-authority.md)) and public intake | **Card required before Release Readiness Gate** (§4) |
| **Communication** | `backend/app/communications/` · Communication Platform Foundation complete (C0.0–C0.3) | Adjacent (RS-6 uses it, Sales card must cite the boundary) | **Later** — covered for v1 by the Sales card's outbound contract section |
| **Finance / Billing** | `backend/app/api/v1/invoices`, `api/v1/settings/billing/` (12 files) · `docs/finance/module-scope.md` · `backend/app/modules/finance/` is **empty** | No — self-service Billing is explicitly «later» | **Later**, registered |
| **Fleet** | `backend/app/api/v1/fleet/` (9 files) · `docs/fleet/module-scope.md` | No | **Later**, registered |
| **Services** | `backend/app/api/v1/services.py` · `docs/services/module-scope.md` · `backend/app/modules/services/` is **empty** | No | **Later**, registered |
| **Compliance** | Scattered: `modules/sales/communication/compliance_pipeline.py`, `modules/recruitment/communication/compliance_pipeline.py`, `models/workforce_compliance_state.py` · `docs/specs/modules/compliance.md` | No | **Later**, registered — and it is **not** a domain today: it is a per-module pipeline. Do not mint a Compliance domain without a card. |
| **Payroll** | `models/workforce_payroll_profile.py` + references only | No | **Not a domain.** No card, no domain creation. |
| **Housing**, **Training** | No runtime code found (`docs/specs/modules/training.md` is a spec without code) | No | **Not a domain.** Queued in the closeout's expansion list. |

**Rule 3 reading.** Rule 3 forbids creating a **new** domain without a card. Sales, Forms and Acquisition were not created by this record — they already exist, so the violation is historical, not incoming. What this record forbids is the reverse move: treating their absence from the certification matrix as evidence that they are owned.

---

## 3. Runtime packages that are not domains

Eleven of the sixteen packages under `backend/app/modules/` are entity or plumbing packages inside a domain and need **no card of their own**: `applications`, `candidate_children`, `client_accounts`, `companies`, `intake_routing`, `notifications`, `outcome_rules`, `payments`, `sales_orders`, `vacancies`, plus `recruitment/` (destination handlers under the certified Recruitment module).

Two are ambiguous and must be resolved by the owning card, not by a new card:

- **`documents`** (39 `.py`) — the Documents card owns the lifecycle; only its dependency audit names the package. The card should name it.
- **`leads`** (45 `.py`, four routers) — the Recruitment card claims «lead intake processing», the Integrations audit scopes `backend/app/modules/leads/*.py` as an integration entrypoint, and the catalog demotes `/api/v1/leads` to «admin/ingest/transport only». Three claims, no adjudication. The Acquisition card (§4) is where this gets settled.

`finance/` and `services/` are empty packages whose documented modules run out of `backend/app/api/v1/`. Empty packages that imply ownership are worse than absent ones; either the runtime moves in or the packages go.

---

## 4. Required before the Release Readiness Gate

Three ownership cards, because each one sits on a v1 blocker write-path and RR1 cannot cite an owner that does not exist:

| # | Card | Must state | Sized |
|---|---|---|---|
| MOC-1 | `docs/modules/sales/module_ownership_card.md` | Sales boundary vs Recruitment (ADR-023), source-of-truth zones (inquiry, client account, sales order), outbound communication contract, forbidden zones | 0.5 slice |
| MOC-2 | `docs/modules/forms/module_ownership_card.md` | Forms as platform capability vs product consumer, Catalog non-ownership (Builder does not own types), publish boundary | 0.5 slice |
| MOC-3 | `docs/modules/acquisition/module_ownership_card.md` | Intake/routing ownership, the `leads` package adjudication from §3, mapping boundary vs Mapping Authority | 0.5 slice |

Each card follows `docs/modules/_template/module_ownership_card.md`. The other three artifacts (contract map, dependency audit, test boundary) are **not** required for v1 on these three domains: they are program-completion artifacts, and RR1 needs an owner, not a certification.

**Total: 1.5 slices.** These are docs-only and do not consume a Product Track slot; they may run on the Launch-ops track or inside the owning blocker's first slice.

---

## 5. Enforcement gap (Rule 7)

There is **no** test, lint rule, or CI check that verifies a module has an ownership card, or that the certification matrix matches the runtime module list. Searched `scripts/`, `.github/workflows/`, `backend/tests/`: the strings `ownership_card`, `module_independence`, `module_ownership` appear only inside the gate documents themselves.

Adjacent enforcement that does exist and must not be confused with it: `backend/app/modules/http_module_ownership.py` + `backend/app/auth/module_gate.py` (path → product-module HTTP gates, ADR-023), `backend/tests/services/test_phase1a_enforcement_guards.py` (import boundaries), `backend/tests/api/test_hr_handoff_module_gates_g3.py`.

Under Rule 7 the Module Independence Program is therefore **documentation only** on the coverage dimension. Closing that needs one check — «every domain listed in this record as a domain has a card» — which is a Launch-ops candidate, **not** a v1 blocker: it prevents future drift, it does not make v1 launchable. Registered as such.

---

## 6. What this record does not do

- Does not reopen `MODULE_INDEPENDENCE_PROGRAM_PASS` or downgrade any certified module.
- Does not create Sales, Forms, Acquisition, Compliance or Payroll as domains — it records which of them already are.
- Does not require contract maps, dependency audits or test boundaries for v1.
- Does not schedule work: scheduling is [`sales-to-comms-sequential-queue.md`](../tasks/sales-to-comms-sequential-queue.md).

---

## История

- **2026-08-28** — record introduced. Corrects the scope of the 2026-05-29 closeout outcome sentence; names three cards (MOC-1…MOC-3, 1.5 slices) as required before the Release Readiness Gate; records the Rule 7 enforcement gap.
