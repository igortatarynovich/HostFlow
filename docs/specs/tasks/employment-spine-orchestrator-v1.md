# Employment Spine Orchestrator v1

**Status:** **ESO-1…5 machine on integration** — Slice 4 Confirm↔`start_allowed` **PASS**; Full Spine **NOT PASS**. Contract: [ready-for-employment-contract.md](../architecture/ready-for-employment-contract.md).  
**Phase class:** product  
**Module owner:** **Employment / HR** (independent of Recruitment)  
**Parents:** [Recruitment Spine Orchestrator v1](recruitment-spine-orchestrator-v1.md) · [Ready for employment contract](../architecture/ready-for-employment-contract.md) (`ready_for_employment.v1`) · [Employment accept policy](../architecture/employment-accept-policy.md) · [Early employability](../architecture/early-employability.md) · [Employment missing resolution](../architecture/employment-missing-resolution.md) · [Employment formalize](../architecture/employment-formalize.md) (`employment_formalize.v1`) · [Employment started](../architecture/employment-started.md) (`employment_started.v1`) · [Employment start_allowed](../architecture/employment-start-allowed.md) · [Recruitment → HR minimal handoff](recruitment-hr-minimal-handoff.md) · [Hiring workflow E2E](hiring-workflow-e2e.md) · [ADR-017](../../adr/ADR-017-work-eligibility-gates-zus.md) · Strategy Lock · [HRappka live session audit brief](../../analysis/hrappka-live-session-audit-brief.md) (research — validates ESO direction; not a reopen)  
**Machine:** accept / employability / missing-resolution / formalize / started · gates ESO-1…ESO-5 · CI `eso1`…`eso5` + ESA4 enforcement · ESA2 ensure integration parity  
**L3 baseline (not a gate stamp):** [Employment Formalization Coverage Audit](../../analysis/employment-formalization-coverage-audit.md) — `ready_to_create_employee=true` is allow-create, not completed formalization; Full Spine **NOT PASS** for that reason.  

> Recruitment ends when the **Ready for employment contract** (handoff package) is emitted. This program **starts** there.  
> Not a Recruitment feature. Not “Recruitment create+accept Employee”.  
> User journey stays continuous; ownership does not.  
> **Seamless UX ≠ shared ownership.**

---

## Acceptance gates (every subsequent change)

1. **RSO does not know how to employ** — Employment receives a package; it does not inherit a Recruitment “employ” API.  
2. **ESO does not re-ask Recruitment.** Anything authoritative in the package (identity, employer/vacancy, recruitment facts, evidence) is **reused**. Additional prompts are **employment missing** only. Re-prompting package facts without a conflict reason is a product FAIL.  
3. **Operator does not service the boundary.** After **Передать на трудоустройство**, work continues on the same person; Accept/init are Employment-internal (auto when gates pass, else concrete blockers — never ritual Accept).

Gate 2 is the usual failure mode: citizenship asked twice, employer re-selected, documents re-uploaded. Domain boundary splits responsibility, not data for the user.

Machine gate: `backend/tests/platform/test_ready_for_employment_contract_gate.py`.

---

## Boundary

**Ready for employment** = inter-module **contract** (handoff package + audit: Recruitment completed → Employment started), not a candidate status alone.

| Recruitment delivers | Employment owns |
|----------------------|-----------------|
| Handoff package: who, target work/employer, recruitment facts, evidence/source, Fits reason | Accept / reject handoff (**Employment policy**) |
| **Recruitment missing** only (fit + package) | **Employment missing** (employability, legalization, contract, formalize) |
| Qualification / fits | Employability / legalization / Employee / Started |

Employment answers: *What is required to lawfully and actually employ this person in this context?*  

Facade: Employment may expose **read** preview before handoff; writes stay in Employment.  
Do not re-collect recruitment facts already in the package.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After handoff, cold start (ritual Accept, re-entry of known facts, eligibility only after Employee) — or Recruitment materializes Employee / Employment docs leak into ATS.

**Completion proof (named consumer):**  
From **Передать на трудоустройство**, Employment receives a valid package → **employment missing** + employability → one next_action → **Оформить** under Employment policy (auto-materialize only if gates pass; else concrete blockers) → **Подтвердить выход** → Started. Audit shows Employment started after Recruitment completed.

**False close (reject):** Recruitment calling `accept_handoff` as its completion; Ready for employment as status-only; Employment re-asking recruitment qualification; ritual Accept when gates already pass.

---

## Employment orchestrator pipeline (sketch)

1. **accept_handoff** (Employment policy: auto when gates satisfied vs review).  
2. **evaluate_employability** — employable / blocked / insufficient_facts (LLM-OFF; unique pathway).  
3. **resolve employment missing** — minimal active path → patch → auto re-eval → ready_to_formalize.  
4. **formalize** — required formal actions → `ready_to_create_employee`; authoritative apply composes ESA2 `ensure_employee_after_formalize_apply` (not HR card / not Started).  
5. **confirm_start** → Started (physical start).  

ADR-017 post-hire ZUS journeys remain satellites — they do not replace step 2–3.

---

## Ladder

| Slice | Gate | Depends |
|-------|------|---------|
| **ESO-1** | **Employment Accept Policy Gate** — `employment_accept_policy.v1` + auto-accept via `accept_handoff` when gates pass | RSO-1 package |
| **ESO-2** | **Early Employability Gate** — `early_employability.v1` (no Employee) | ESO-1 |
| **ESO-3** | **Employment Missing / Resolution Gate** — `employment_missing_resolution.v1` → ready_to_formalize | ESO-2 |
| **ESO-4** | **Employment Formalize Gate** — `employment_formalize.v1` → `ready_to_create_employee`; mint via ESA2 ensure on authoritative apply only | ESO-3 |
| **ESO-5** | **Employment Started Gate** — `employment_started.v1` physical Confirm; PEM-1 requires `start_allowed` ([slice 4](employment-start-allowed-eso5-enforcement.md)) | ESO-4 + ESA3 |

---

## Non-goals

- Rebuilding Recruitment qualification.  
- Mapping Authority.  
- Full Legalization Engine v1 breadth (thin employability first is OK).

---

## Next

RSO-1 package shape is frozen (`ready_for_employment.v1`). **ESO-1:** accept policy that **reuses** package facts (gate 2) + auto-init when Employment gates pass. Then ESO-2 employability SoT (ownership card if Rule 3 requires).

**Locked product sequence after ESO-5 binding (L3 baseline):**  
Coverage Audit (`b88a6168`) → PEM-1 Accepted → `employment_start_allowed.v1` Accepted → inventory (`466016b6`) → adaptation design (**Accepted**) → [runtime foundation slice 1](employment-start-allowed-runtime-foundation.md) (**PASS** `d5767488`) → [mint cutover slice 2](employment-start-allowed-mint-cutover.md) (**ESA2 portable PASS** + Formalize→ensure integration parity **PASS** `322d0148`) → [HR host bind slice 3](employment-start-allowed-hr-host-binding.md) (**PASS**) → [RSO-2 cutover](recruitment-employment-handoff-rso2-cutover.md) **PASS** @ `909ce8a5` → [boundary E2E proof](recruitment-employment-handoff-boundary-e2e-proof.md) **PASS** (handoff `e9ef16f2-1ab6-49d0-91dd-aa7676995081`) → [ESO-5 Confirm ↔ start_allowed enforcement (slice 4)](employment-start-allowed-eso5-enforcement.md) **PASS** (2026-09-15) → **STOP** — Three-host Full Spine Gate = **separate decision** (not auto-opened).  
Do **not** collapse slices; do **not** operator-set `start_allowed`; Full Spine stays closed. Slice 4 **PASS**: Confirm requires `start_allowed=true`; mint-on-confirm retired.
