# Employment Formalization Coverage Audit

**Status:** research draft (L3)  
**Date:** 2026-09-13  
**Trusted observation base:** ESO machine + HR bindings through **ESO-5 Started HR Binding** ([#372](https://github.com/igortatarynovich/HostFlow/pull/372) / tip stamp `@ 0a30595c` on `feat/eso5-started-hr-binding`); Formalize contract `employment_formalize.v1`; current-tree HR/ZUS/eligibility/docs inventory on `integration/release-product-a-b`  
**Parent briefs:** [`../specs/tasks/employment-spine-orchestrator-v1.md`](../specs/tasks/employment-spine-orchestrator-v1.md) · ESO-line SoT `docs/specs/architecture/employment-formalize.md` · ESO-line L3 `docs/analysis/hr-employment-eso-inventory.md` (machine/UI ladder — **not** this audit; do not merge PASS-stamps here)  
**Does not amend:** L0 · ADR-042 · Recruitment Architecture CLOSED · ESO-1…5 named gate PASS stamps · Full Spine Gate  
**Not SoT:** this file is L3 implementation context. It does **not** define Production Employment Minimum and does **not** schedule gap closure.

> Inventory of **what HostFlow already has** when Formalize reports completion.  
> **Does not** mix with ESO-5 PASS-stamp. **Does not** propose a Formalize redesign.  
> **Does not** claim Full Spine PASS.

---

## One-line verdict

**`ready_to_create_employee=true` is an allow-create threshold, not proof of completed employment formalization.**

ESO-4 answers: *may HostFlow allow Employee create for this context?*  
It does **not** answer: *have the кадровые actions required for a lawful and operationally acceptable start already been executed and proven?*

Full Spine remains **NOT PASS**. The blocking reason is now precise: missing proven semantics **Formalize = реально выполнено то, что необходимо для законного и операционно допустимого выхода этого человека в данном employment context** — not the absence of Started UI (ESO-5 binding closes that UI slice only).

---

## What ESO-4 proves vs does not prove

### Proved at `ready_to_create_employee=true`

| Signal | Authority |
|--------|-----------|
| `ready_to_formalize` | ESO-3 `employment_missing_resolution.v1` |
| `employable` + unique pathway | ESO-2 `early_employability.v1` |
| Thin formal actions only | EU/EEA: `identity_facts_present` + `confirm_employment_contract_basis` · Third-country: `work_authorization_evidence` + `confirm_employment_contract_basis` |
| Allow-create threshold | `formalization_complete` → `ready_to_create_employee=true` · `employee_created=false` by contract |

Machine: `backend/app/reference/employment_formalize.py` · orchestrator does not mint Employee · UI Formalize panel stops at allow signal.

### Explicitly not proved

- Employee mint / HR card  
- Signed employment / civil contract  
- ZUS ZUA/ZZA filed or accepted at ZUS  
- Insurance titles registered with an external party  
- BHP training completed  
- Occupational medical examination completed  
- Portable document **A1** issued  
- **Zgłoszenie delegacji** submitted  
- Official legalization completed at urząd  
- Physical **Started** (ESO-5 owns that fact; Started ≠ formalization complete)

---

## Four evidence layers (mandatory distinction)

Every domain below is scored against **four layers**. Mixing them is how Formalize was over-read as “оформление done.”

| Layer | Meaning | HostFlow examples |
|-------|---------|-------------------|
| **Decision** | Policy / pathway / gate says what is required or allowed | ESO-2 pathway · ESO-4 thin required_actions · ADR-017 ZUS registration gate · RPM work_authorization |
| **Internal task** | Operator queue / checklist / activity inside HostFlow | ZUS workspace task · HR review checklist item · handoff activity stub |
| **Evidence** | Stored facts, docs, profiles, confirmations in HostFlow | Package identity · hub `medical_certificate` · insurance profile flags · `confirm_employment_contract_basis` ack |
| **Actual external execution** | Real-world / authority-facing completion | Signed umowa · ZUS/Płatnik filing accepted · urząd decision · A1 issued · posting notification filed |

**Rule for this baseline:** an internal task marked done, or evidence uploaded, is **not** external execution unless HostFlow can point to a completion proof that survives audit outside the app.

---

## Coverage matrix (8 minima)

**BUILT count: 0 / 8.**

Status vocabulary for this audit:

| Status | Meaning |
|--------|---------|
| **BUILT** | End-to-end: decision → workflow → evidence → **external execution** proven in HostFlow |
| **LEGACY** | Parallel HR path exists; not on ESO Formalize happy path |
| **PARTIAL** | Decision and/or internal task and/or evidence exist; external execution absent or incomplete |
| **MISSING** | No meaningful runtime for the domain |
| **NOT REQUIRED** | Explicitly out of scope for a named employment scenario (not claimed here — deferred to Production Employment Minimum) |

| Domain | Status | Decision | Internal task | Evidence | External execution | Gap |
|--------|--------|----------|---------------|----------|--------------------|-----|
| **Contract** | **PARTIAL** (+ post-employee LEGACY draft) | ESO-4 `confirm_employment_contract_basis` only | — | Operator confirmation; draft merge log post-employee | **None** (no sign / send / ePUAP) | Confirm ≠ umowa signed/archived |
| **ZUS** | **PARTIAL** | ADR-016/017 gate registration tasks | ZUS workspace queue (ZUA/ZZA/ZWUA, monthly) | Task + `WorkforceZusProfile` + doc types | **None** (no Płatnik / KEDU / ZUS API — ADR-016) | Task done ≠ filed/accepted at ZUS |
| **Insurance** | **PARTIAL** | ADR-015 legal flags | Patch profile → may auto-create ZUS tasks | `WorkforceInsuranceProfile` flags | **None** | Flags ≠ titles registered externally |
| **BHP** | **PARTIAL** | Catalog / expected-doc (`blocks_employment=false`) | No dedicated orchestrator; not in HR checklist codes | Doc type + `szkolenia_BHP` meta | **None** | Catalog ≠ training completed as Formalize proof |
| **Medical** | **PARTIAL** (+ LEGACY handoff stub) | Requirement slots / packs; expected-doc can block employment in catalog | Handoff activity `medical_examination` | Hub `medical_certificate` (+ psychotest packs) | **None** | Docs/activity ≠ Formalize-proven badania |
| **A1** | **MISSING** | — | — | — | — | No portable-document A1 runtime |
| **Zgłoszenie delegacji** | **MISSING** | Catalog aliases only | — | Alias list | — | No posting-notification path; may be **NOT REQUIRED** for some domestic scenarios (product decision later) |
| **Legalization** | **PARTIAL** (+ LEGACY review) | ESO-2 pathway + eligibility rules + RPM | Work-eligibility journey / fees / checklist | Profile + hub stay/permit docs + package work-auth evidence | Portal URL link-out only | Employable ≠ urząd completion |

---

## Domain inventory (existing HostFlow only)

### 1. Contract — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | ESO-4 thin ack `confirm_employment_contract_basis`. Registry: `employment_contract` / `civil_contract` (`employment_formalization` purpose). |
| Internal task | No Formalize contract-execution task. |
| Evidence | Formalize confirmation set; post-employee draft preview via `contract_generation.py` + trusted identity consumer. |
| External | Explicit non-goal in contract-generation MVP (no send/sign/ePUAP). |
| UI | Formalize confirm CTA; `HrContractPreviewPanel` after Employee. |

### 2. ZUS — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | ADR-017 work-eligibility gates **registration** task create; monthly settlement ungated in v1. |
| Internal task | `workforce_zus_workspace_tasks` + autocreate + monthly job. |
| Evidence | Form kind/status fields; export_status **placeholder**; doc types `zus_zua` / `zus_zza`. |
| External | Forbidden by ADR-016 (no ZUS API / Płatnik / KEDU). |
| UI | `HrZusWorkspacePage`, employee ZUS section — post-employee ops, not ESO-4 thin table. |

### 3. Insurance — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | ADR-015 legal materialisation (distinct from ZUS workspace). |
| Internal task | Profile patch can trigger ZUS auto-tasks. |
| Evidence | social/health/sickness/accident flags; expected-doc `insurance` often non-blocking. |
| External | None. |

### 4. BHP — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | Document catalog / training category docs only. |
| Internal task | None dedicated; not in `CHECKLIST_ITEM_CODES`. |
| Evidence | `szkolenia_BHP` meta schema + scanner preset. |
| External | None. |

### 5. Medical — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | Requirement / pack / expected-document machinery (stronger on driver readiness). |
| Internal task | Handoff activity stub `medical_examination`. |
| Evidence | Hub medical certificate (+ psychotest where packed). |
| External | None (no e-skierowanie). |
| Note | **Not** on ESO-4 thin required-actions table. |

### 6. A1 — MISSING

No L2 Formalize contract, service, API, model, or UI for portable document A1. (Driver license category `A1` is unrelated.) Competitive notes / wishlists are not runtime.

### 7. Zgłoszenie delegacji — MISSING

Document-catalog aliases (`delegation` / `assignment`) only. No notification workflow or external filing. Scenario dependency (international posting vs domestic hire) is **out of scope for this audit** — reserved for Production Employment Minimum.

### 8. Legalization — PARTIAL

| Layer | What exists |
|-------|-------------|
| Decision | ESO-2 pathways; work-eligibility rules; RPM stay/work-auth; legacy checklist legal_stay / work_permit / red_paper. |
| Internal task | Eligibility journey steps + fee rows; HR review parallel path. |
| Evidence | Profile fields; hub permit/stay docs; package `work_authorization_evidence` reuse in ESO-4. |
| External | `WorkPermitSubmissionChannel` portal URL metadata — operator leaves HostFlow. |

---

## Parallel paths (not Formalize proof)

| Surface | Role | Why it does not close this audit |
|---------|------|----------------------------------|
| Legacy HR review checklist | identity / stay / permit / red paper / payments / docs / `zus_readiness` / employment_data → approve | Parallel path; checklist satisfaction ≠ external filing; ESO inventory treats it as secondary |
| Handoff accept activities | includes `zus_registration`, `medical_examination`, … | Activity stubs — titles, not completion proof for Formalize |
| ESO-5 Started | physical start confirm; may mint Employee | **Started ≠ formalization complete**; binding PASS ≠ Full Spine PASS |

---

## Locked sequence (product order after this baseline)

Do **not** jump from ESO-5 to closing all eight gaps or to Full Spine Gate.

1. **ESO-5** [#372](https://github.com/igortatarynovich/HostFlow/pull/372) — Started HR binding (UI slice; machine already gated).  
2. **This L3 Coverage Audit** — baseline: allow-create ≠ formalization complete; **0/8 BUILT**.  
3. **Production Employment Minimum / blocking-boundary decision** (next product step) — for the **first real HostFlow scenario**, decide:
   - which of the eight are **required / deferred / NOT REQUIRED**;
   - what must be true **before Employee create**;
   - what may complete **after Employee create but before Started**;
   - what is a **separate lifecycle** (post-Started satellites).  
4. Close **only** gaps that the Minimum marks blocking.  
5. **Three-host Full Spine Gate** — [`../specs/tasks/three-host-full-spine-gate-pem1.md`](../specs/tasks/three-host-full-spine-gate-pem1.md) **OPEN** (proof only; only after Formalize/`start_allowed` semantics match PEM-1 Minimum).

**Risk if skipped:** turning HostFlow into a full Polish HR / legalization suite (A1 + delegacja + Płatnik + …) before naming the first production employment context.

**Example (illustrative, not a decision):** A1 and Zgłoszenie delegacji may be critical for an international driver posting and **NOT REQUIRED** for a specific domestic employment case. That classification belongs in step 3, not here.

---

## Full Spine status

| Claim | Status |
|-------|--------|
| Full Spine Gate | **NOT PASS** — proof brief [`../specs/tasks/three-host-full-spine-gate-pem1.md`](../specs/tasks/three-host-full-spine-gate-pem1.md) **STOP** 2026-09-15 (Ready / DQC hole) |
| Reason (precise) | Formalize allow-create is not proven completion of the кадровый minimum required for lawful/operational start in context |
| Reason (rejected) | “Started UI missing” — addressed as ESO-5 binding slice; not the Full Spine blocker |
| ESO-5 PASS-stamp | **Separate artifact** — must not be rewritten by or merged into this audit |

---

## Non-goals of this document

- Designing Production Employment Minimum (step 3 above).  
- Expanding `employment_formalize.v1` thin table.  
- Scheduling ZUS API / Płatnik / A1 / posting products.  
- Reopening Recruitment Architecture.  
- Claiming or amending any ESO named gate PASS.

---

## References

- ESO Formalize SoT (ESO line): `docs/specs/architecture/employment-formalize.md` · `backend/app/reference/employment_formalize.py`  
- ESO ladder inventory (ESO line): `docs/analysis/hr-employment-eso-inventory.md` — separate from this coverage baseline  
- Employment spine brief: [`../specs/tasks/employment-spine-orchestrator-v1.md`](../specs/tasks/employment-spine-orchestrator-v1.md)  
- ZUS: [`../adr/ADR-016-zus-workspace-mvp.md`](../adr/ADR-016-zus-workspace-mvp.md) · [`../adr/ADR-017-work-eligibility-gates-zus.md`](../adr/ADR-017-work-eligibility-gates-zus.md)  
- Contract draft: `backend/app/services/contract_generation.py` · `docs/specs/workflows/hr-contract-generation-mvp.md`  
- Related research: [`hrappka-live-session-audit-brief.md`](hrappka-live-session-audit-brief.md)  
- Companion canvas (IDE only, not repo SoT): `employment-formalization-coverage-audit.canvas.tsx`
