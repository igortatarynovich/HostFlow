# Forms Platform C1 — Foundation contract seal

**Status:** **IN PROGRESS** (docs — this brief)  
**Branch (docs):** `docs/forms-platform-c1-contract-seal`  
**Branch (code):** `feat/forms-platform-c1-contract-seal` (after this brief merges)  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase C](../architecture/platform-completion-roadmap.md) · [ADR-007](../architecture/ADR-007-forms-platform-capability.md) · [Forms Public Contract](../architecture/forms-public-contract.md) · [Product Layer epic](forms-product-layer-epic.md) · [A2 gate](../gates/platform-governance-review-a2.md) (A2-F6)

> Sprint 1–6 + Field Catalog + Builder MVP already exist.  
> Foundation is **not** sealed: Passport / Manifest / Public Contract / runtime docs still drift.  
> This slice seals the platform contracts. It does **not** start Builder product (P3–P5).

---

## Why this slice

[A2-F6](../gates/platform-governance-review-a2.md): module-scope says Sprint 1–6 complete, but the maturity matrix cannot mark Forms Foundation ✅ while Passport / Manifest / Runtime contracts remain open.

Shipped runtime vs canon:

| Artifact | Shipped | Drift |
|----------|---------|--------|
| Passport | Catalog [Forms](../architecture/platform-capability-catalog.md#forms) | Still says Builder LOCKED until P1; P1 is closed |
| Manifest | [`capability-settings-manifest.md`](../architecture/capability-settings-manifest.md#forms) · `forms_platform/manifest.py` | Builder flag UNLOCKED; Themes / multi-language still false |
| Public Contract | [`forms-public-contract.md`](../architecture/forms-public-contract.md) `forms.public_contract.v1` | Header still frames Sprint 1–2; Product Track not Phase C |
| Adapter | `forms.endpoint_adapter_v1` · `backend/app/forms_platform/adapter.py` | Stable ops exist; consumers must keep Adapter-only |
| Runtime | Sprint 2–6 (snapshot, ledger, schema, answers, envelope) | `TenantLeadForm` remains publication bridge |
| Versioning | `form_publication_versions` append-only | FormTemplate SoT not yet |

Phase B listed slices are closed (#222 / #224 / #238). Locked queue next = Forms Platform.

---

## Goal

Seal Forms as a **platform capability** (Passport → Manifest → Public Contract → Adapter → Runtime → Versioning) so later Phase C slices have one SoT. Align docs with shipped runtime. Do not invent a second form stack.

This slice does **not** replace `TenantLeadForm`, accept ADR-022, or unlock Publish UI.

---

## In scope (this docs PR)

1. This brief.  
2. Queue / roadmap / AGENTS / maturity / module-scope / Product Layer epic point here.  
3. Stage 3 slice 4 marked ✅ [#238](https://github.com/igortatarynovich/HostFlow/pull/238).

## In scope (feat PR — after this brief)

1. Close stale “Builder LOCKED until P1” in Passport notes, ADR-007, [`capability-contract.md`](../architecture/capability-contract.md) — P1 closed; P2 MVP complete; **P3–P5 stay locked**.  
2. Public Contract header names Phase C as Product Track; inventory of Stable ops unchanged.  
3. Gate tests: contract id `forms.public_contract.v1`, adapter id `forms.endpoint_adapter_v1`, Manifest keys still resolve (no new keys).  
4. Architecture Review Checklist (10 questions) in the feat PR description.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Stage 5 settings / enable-disable | ADR-005 / ADR-035 — **not Forms** |
| R6 RecruitmentApplication table-cutover / physically separate queues | [intake-runtime-split-v1.md](intake-runtime-split-v1.md) R6 |
| Forms Builder / Publish UI / Themes / Analytics (P3–P5) | Locked until platform contracts |
| FormTemplate SoT (replace `TenantLeadForm` bridge) | Later Phase C slice |
| Accept ADR-022 (Purpose + Submission Policy) | Later Phase C slice |
| Meta → `FormSubmissionEnvelope` | Later Phase C slice ([meta-intake-completeness.md](meta-intake-completeness.md) deferred) |
| Event stability (`form.published` / `form.submission_received` Experimental → Stable) | Later Phase C slice |
| Entity Workspace | Phase D |

Do **not** mix Stage 5 settings or R6 into this PR.

---

## Architecture Review (L0 — this brief)

| # | Answer |
|---|--------|
| 1 Owner | Forms platform ([ADR-007](../architecture/ADR-007-forms-platform-capability.md)) |
| 2 Exists? | Yes — Sprint 1–6 + P1 Catalog + P2 Builder MVP |
| 3 Adapter | `forms.endpoint_adapter_v1` (**Stable**) |
| 4 Boundary | No Builder P3, no Recruitment/Sales form stacks, no Outcome/KPI |
| 5 Settings | Existing Manifest only; no new keys in C1 |
| 6 SoT | HostFlow Form via Adapter; `TenantLeadForm` remains bridge until a later C slice |
| 7 Events | `form.published` / `form.submission_received` stay **Experimental** this slice |
| 8 Requires | Endpoint, Submission (unchanged) |
| 9 License | None new (Basic = platform; Advanced = existing addon flags) |
| 10 Public contract | No breaking change; feat aligns docs, does not add ops |

Invariants INV-01…17 unchanged. Does **not** amend L0.

---

## Acceptance

- Product Track = this brief; Stage 3 slice 4 is closed (#238).  
- Operators / agents cannot treat P3 Builder or R6 as the active slice.  
- Feat PR closes Passport / ADR-007 / capability-contract drift without unlocking P3–P5.  
- Contract/adapter/manifest ids still match the sealed inventory.

---

## Likely files (feat PR)

| Area | Paths |
|------|--------|
| Passport notes | `docs/specs/architecture/platform-capability-catalog.md` (Forms row status only — not L0 shape) |
| ADR-007 / capability-contract | stale Builder-until-P1 lines |
| Public Contract | header / Product Track pointer |
| Tests | `backend/tests/forms_platform/test_forms_c1_contract_seal.py` (or extend sprint-1 gates) |

---

## DoD

- [x] Brief sealed with in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] Boundary vs Stage 5 settings / R6 / P3–P5 / FormTemplate / ADR-022 explicit  
- [x] Feat PR — docs drift closed + contract-id gates  
