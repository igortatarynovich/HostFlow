# Requirement Policy Management

**Status:** **RPM-1 PASS** · **RPM-2 PASS** · **RPM-3A PASS** — [Parallel Authority Retirement Gate](#rpm-3a--parallel-authority-retirement-pass). **Active Product = RPM-3B** Consumer parity.  
**Phase class:** platform  
**Branch (docs):** `docs/queue-schedule-rpm` · `feat/requirement-policy-authority-rpm1`  
**Branch (code):** `feat/requirement-policy-management-rpm2-operator` (RPM-2); RPM-3A feat not started  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [v1 Release DAG dependency-position](../gates/v1-release-dag-dependency-position.md) [#328](https://github.com/igortatarynovich/HostFlow/pull/328) · [Documents Platform E8-eval](documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [Requirement Policy Authority](../architecture/requirement-policy-authority.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Reference R5](platform-reference-identity-sot.md) · [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) · [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md)
**Estimate:** 4–6 slices — RPM-1 1 (docs), RPM-2 1–2, RPM-3A 1, RPM-3B 1–2 (1 slice = one docs PR + one feat PR; rolled up in the [queue release horizon](sales-to-comms-sequential-queue.md))

> First Product from the [Release DAG](../gates/hostflow-v1-release-goal.md), scheduled after [#328](https://github.com/igortatarynovich/HostFlow/pull/328).  
> Documents is the **first domain** of this capability — not a second Documents Admin vs Rules Admin.  
> E8-eval already evaluates D4 from R5 `merge(pack, tenant_delta)`. This program gives the operator **one** write of that authority (base, override, reason, result) and collapses parallel answerers.  
> **Not** Mapping Authority. **Not** External Intake. **Not** Hiring E2E. **Not** min HR. **Not** CL8. **Not** a Hub packages table. **Not** Overlay rewrite. **Not** reopening E8-eval / R5.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Nine live answerers still reply to “must this candidate provide type X for this tenant / client / vacancy / profile / country?” E8-eval proved **evaluation** on D4 against pack merge. It did not give an operator one overlay with reason. Without this program Hiring E2E cannot accept against policy authority, and Settings will keep splitting Documents / Ruleset / Transfer Policy / Hiring gates.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Documents surface** (`/app/candidates/:id` documents zone) **plus** one operator overlay that writes the **same** R5 merge D4 already reads. Operator sets base / override / reason; D4 result changes; remaining document-requirement consumers do not contradict. Proof is **not** Recruitment Application G4, not a new Hiring Product, not Mapping editors.

**False close (reject):** Documents Admin separate from Rules Admin; minting a Hub packages table; treating Overlay rewrite as RPM; CL8; reopening E8-eval / R5; walking Hiring E2E without the overlay; starting Mapping / Intake / min HR “while we are here”; Foundation ✅.

---

## Internal ladder (this program only)

One Active Product slice at a time. RPM-1 · RPM-2 · **RPM-3A PASS**. **Active = RPM-3B**. Mapping is **not** on this ladder.

```text
RPM-1 Authority contract
  → RPM-2 Operator overlay
  → RPM-3A Parallel authority retirement
  → RPM-3B Consumer parity
  → Requirement Policy Consumer Cutover Gate
  → RPM program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate | Depends on | Unlocks |
|---|--------|------------|------------|------------|---------|
| **RPM-1** | Authority contract | `rpm-authority` | **Requirement Policy Authority Gate** ✅ — one operator question; one write authority; nine answerers classified. SoT: [requirement-policy-authority.md](../architecture/requirement-policy-authority.md) (`requirement_policy_authority.v1`) | E8-eval Gate ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328) | RPM-2 |
| **RPM-2** | Operator overlay | `rpm-operator` | **Requirement Policy Operator Gate** ✅ — one job UI; Documents-first R5 `tenant_delta`; D4 tenant-level unconditional | **Requirement Policy Authority Gate** | RPM-3A |
| **RPM-3A** | Parallel authority retirement | `rpm-cutover-writers` | **Requirement Policy Parallel Authority Retirement Gate** ✅ — A `document_policies`, C leftover ruleset writes, J P3B `document_required` only | **Requirement Policy Operator Gate** | RPM-3B |
| **RPM-3B** | Consumer parity | `rpm-cutover-consumers` | **Requirement Policy Consumer Parity Gate** — remaining consumers’ **policy answer** matches R5 required-set (base / require X / remove X); Overlay confirm; R5 remains sole write | **Requirement Policy Parallel Authority Retirement Gate** | Consumer Cutover Gate |
| **RPM-3 close** | Consumer cutover close | `rpm-cutover` | **Requirement Policy Consumer Cutover Gate** — 3A ∧ 3B PASS; no live independent “need X?” answerer | RPM-3A Gate ∧ RPM-3B Gate | RPM program close. Hiring E2E **unlocked, not scheduled** |

Unlock ≠ schedule. Closing RPM does **not** auto-start Mapping or Hiring.

---

## RPM-1 — Authority contract (**PASS**)

**SoT:** [requirement-policy-authority.md](../architecture/requirement-policy-authority.md) · machine id `requirement_policy_authority.v1`.

**Operator question (one):** for this tenant / client / vacancy / profile / country, must this candidate provide document type X? Base rule, override, reason, result.

**Write authority (one):** R5 `merge(pack, tenant_delta)` and scoped overlays that feed that merge. Overlay vacancy delta stays the [Vacancy Overlay](entity-profile-vacancy-overlay-contract.md) write-set — **not** a second RPM product.

### Answerer classification (normative for RPM-1)

| Live answerer | RPM role |
|---------------|----------|
| R5 pack + `tenant_delta` (E8-eval canonical for D4) | **Write authority** |
| Vacancy Overlay + screening pack | **Not this write** — vacancy delta over Profile / Screening Pack (Overlay Gate already PASS) |
| leftover `sample_ruleset.json` / seeded `document_ruleset_versions` | **Leftover** — must not remain a parallel write |
| Hub `DOCUMENT_PACK_DEFINITIONS` | **Consume or retire** as a duplicate pack catalog (cutover in RPM-3) |
| DB `ref_packs` consumed by transfer policy | **Consume** merge (cutover in RPM-3) |
| ADR-018 requirement graph / Engine packs | **Consume or explicit contract** (cutover in RPM-3) |
| `document_applicability_policy.py` | **Consume** merge (cutover in RPM-3) |
| hiring pipeline gates / `candidateStageDocPolicy.ts` | **Consume** merge (cutover in RPM-3; **not** Hiring E2E Product) |
| `document_policies` table (TENANT/CLIENT/VACANCY flags) | **Consume or fold** into `tenant_delta` (cutover in RPM-3) |

RPM-1 does **not** ship the operator UI and does **not** cut over consumers. It forbids a second write authority for the same question.

### Requirement Policy Authority Gate

**Outcome:** **PASS**. Named CI: `backend/tests/platform/test_requirement_policy_authority_gate.py`. Boundary: `scripts/architecture/check_requirement_policy_authority_boundary.py`.

PASS when:

1. This brief is merged and the queue Active Product is RPM-1 (or a later RPM slice after this gate).  
2. The operator question and write authority above are the SoT — [requirement-policy-authority.md](../architecture/requirement-policy-authority.md).  
3. The nine-row classification is unchanged except by a later RPM slice that **retires** a leftover — not by adding a tenth write. Frozen in `requirement_policy_authority.v1`.  
4. No Documents Admin vs Rules Admin split; no Hub packages table; no Overlay rewrite; no CL8; E8-eval / R5 not reopened.  
5. Mapping / Intake / Hiring E2E / min HR are not this slice.

This slice **closes** the Authority Gate. Feat remains locked until **RPM-2**. Do not start RPM-2 in this PR (queue invariant 6).

---

## RPM-2 — Operator overlay (**PASS**)

Machine id: `requirement_policy_operator.v1`.

One operator job at `/app/settings/requirement-policy`. Settings that edit non-authority JSON (leftover ruleset) is **not** ready. Public write is Documents-first `{ require, remove, reason, expected_revision }` — compiled to R5 `candidate.overrides` with `when: {}`, then `validate_tenant_overlay_delta`. Empty require+remove resets to `delta = {}` (row kept). Optimistic concurrency via `revision`. Mutation + `UserAuditLog` are one transaction.

**base** = evaluate without tenant delta for the same preview context (not raw pack defaults). **result** = evaluate with stored delta. D4 resolve loads the same overlay through `load_tenant_delta` into existing `project_required_doc_applicability_via_contract`.

**Proof scope:** D4 proves **persisted tenant-level unconditional** policy authority reaches the live Documents consumer through R5. RPM-2 does **not** prove candidate-specific `owner_context` binding.

**Not this store:** P3B `tenant_requirement_overrides`, `document_policies`, `document_ruleset_versions`. No second evaluator. No RPM-3 consumer cutover.

Four checks from the [Release Goal](../gates/hostflow-v1-release-goal.md): runtime authority sealed (RPM-1); operator surface **sealed** (RPM-2); E2E consumption **partial — D4 tenant-level unconditional only**; release acceptance still OPEN until RPM-3 / suite.

Out: a second editor; Zapier; Mapping UI; Hiring funnel builder; Overlay rewrite; CL8; Hub packages; candidate-context proof.

### Requirement Policy Operator Gate

**Outcome:** **PASS**. Named CI: `backend/tests/platform/test_requirement_policy_operator_gate.py`.

PASS when:

1. One job UI with base / override / reason / result; write authority remains `r5_merge_pack_tenant_delta`.  
2. Compiler → `validate_tenant_overlay_delta` → `merge_resolved_policy`; no second merge definition; unknown/noncanonical codes rejected.  
3. `base` is evaluate-without-delta; `result` is evaluate-with-delta for the same preview context.  
4. Documents resolve loads overlay via the operator repository into the existing projector.  
5. Operator modules do not import P3B / `DocumentPolicy` / `DocumentRulesetVersion`.  
6. Reason required; empty require+remove compiles to `{}` (reset), not DELETE.  
7. GET = trust read, PUT = trust admin.  
8. Stale `expected_revision` → 409; authority not overwritten.  
9. Atomic audit payload: previous/new delta + reason + revisions; actor/tenant are columns.  
10. RLS on `document_policy_tenant_overlays`; ADR-039 participant claim lists the table.  
11. Mapping / Hiring E2E / Overlay rewrite / CL8 / Hub packages / candidate-context proof are not this slice.  
12. Named CI job **Requirement Policy Operator Gate**.

**Residual (does not reopen Operator Gate):** the shared TI coverage guard (`test_rls_coverage_guard.py` / empty `rls_uncovered_tables.txt`) lives on the tenant-isolation line, not this RPM stack. After those branches merge, run an **integration check** that `document_policy_tenant_overlays` is present in the live tenant-scoped set, carries a write-capable RLS policy + `FORCE`, and is **absent** from `rls_uncovered_tables.txt` and `rls_force_exceptions.txt`. Fail closed if it appears as an exception.

---

## RPM-3 — Consumer cutover (ladder; **Active = RPM-3B**)

**Entry:** RPM-1 Authority Gate PASS · RPM-2 Operator Gate PASS.  
**SoT rows:** the frozen nine-row table in [requirement-policy-authority.md](../architecture/requirement-policy-authority.md). Do not add a tenth write.  
**Adjacent:** P3B `tenant_requirement_overrides` — cut **`document_required` only**; keep `field_required` / severity / other P3B contracts.

**Main criterion (Consumer Cutover Gate):** no live path may independently decide that document type X is required for a candidate when that disagrees with R5 `merge(pack, tenant_delta)` for the same context.

### Consume / policy-answer proof standard (normative)

Importing a shared helper is **not** proof. Compare the consumer’s **policy answer** (is X required?), **not** its full output. Hiring may still say “transition blocked” for stage reasons — that is fine — as long as it does **not** invent a required-set that disagrees with R5.

For every row whose target is **consume R5** (or whose remaining read after fold/retire still answers required X), the gate must show **identical required-set membership** vs canonical R5 (`evaluate_required_doc_applicability_via_contract` / sealed checklist) under the **same** `preview_context` and the **same** persisted `tenant_delta`, for:

1. **base-only** — `delta = {}`  
2. **require X** — overlay `require: [X]`  
3. **remove X** — overlay `remove: [X]` where X is required in base  

X = fixed canonical code (e.g. `adr_certificate` / `passport`).

### Cutover matrix (accepted targets)

| # | Answerer | Live path today | Answers “need X?” now? | Target | Runtime change | Proof / gate |
|---|----------|-----------------|------------------------|--------|----------------|--------------|
| A | `document_policies` (row 9) | `DocumentPolicy` via `document_requirements.py`, `requirement_checker.py`, `hr_expected_documents_resolver.py`; Companies CLIENT CRUD | **Yes** | **Fold/retire authority**; any remaining read that answers required X **only via R5** | Stop table/UI as authority; fold enabled required types into overlay **or** retire writers; leftover readers must consume R5 | 3A: no independent authority write. 3B: remaining readers pass base/require/remove policy-answer parity **or** zero readers for the operator question |
| B | Hiring pipeline gates (row 8) | `candidate_doc_pipeline_guard.py` (ruleset / Engine codes); FE `candidateStageDocPolicy.ts`; Settings stage gate sets | **Partial** | **Consume R5 required-set**; stage-specific gate stays **derivative logic over that set** | Guard takes required-set from R5+overlay; stage sets only decide *when* to enforce; FE must not invent types | Policy-answer parity (base/require/remove). Full “blocked” output may differ for stage reasons |
| C | Leftover ruleset / versions (row 3) | `document_ruleset_versions` + `/app/settings/ruleset` | **Yes** | **Retire write + retire as authority**; historical/read-only storage may remain | Quarantine activate/edit UI; runtime must not use `json_data` as “need X?” SoT | 3A: no admin path can change required types via ruleset. History rows OK if inert |
| D | `document_applicability_policy.py` (row 7) | Country/visa/attestation helpers; sibling resolver over ref_packs | **Partial** | **Consume R5** | Applicability that affects required X driven by resolved R5, not a sibling catalog | Policy-answer parity for codes in its domain |
| E | Transfer / `ref_packs` (row 5) | `transfer_policy_resolver.py` → applicable docs / handoff `required_documents` | **Yes** (mixed) | **Split semantics:** (1) “required for candidate” → **R5**; (2) “needed for transfer operation” may stay **derivative** / separate | Do not let transfer invent candidate-required X. Operation-specific docs must be labelled as transfer requirements, not candidate policy | Candidate-required subset ≡ R5 (base/require/remove). Transfer-operation extras explicitly not operator-question answers |
| F | Hub `DOCUMENT_PACK_DEFINITIONS` (row 4) | `pack_definitions.py` / projection / owner_summary | **Yes** if emitting required codes | **Retire as answerer**; may remain **catalog/grouping** only | Packs must not emit policy required-set; grouping/labels OK | Gate: packs do not answer “need X?” (no required-code authority). Catalog-only proof |
| G | ADR-018 Engine packs (row 6) | `requirement_rule_graph` + Engine evaluation; used by hiring guard | **Yes** | **Explicit contract:** Engine may keep orchestration logic; **document-required input from R5** | Engine must not own document_required SoT; pull required codes from R5 merge | Policy-answer for document_required ≡ R5 (base/require/remove). Orchestration outputs out of scope if they do not redefine required X |
| H | Vacancy Overlay (row 2) | `vacancy_overlay_runtime.py` | **No** for this write | **not-this-write** (confirm only) | No RPM change | Overlay still rejects R5 fork keys; Overlay contract unchanged |
| I | R5 pack + `tenant_delta` (row 1) | merge + overlay store + operator UI + D4 | **Yes** | **Keep sole write authority** | No second write | Authority + Operator gates green |
| J | P3B overrides (adjacent) | `apply_tenant_overrides`; `document_required` add/relax | **Yes** for `document_required` | **Retire `document_required` as independent answerer only**; keep `field_required` / severity / other P3B contracts | Stop applying P3B `document_required` into the operator-question path; do **not** delete whole P3B | 3A: active `document_required` overrides cannot change required-set vs R5. Other P3B rule types still work |

### RPM-3A — Parallel authority retirement (**PASS**)

**Rows:** A · C · J (`document_required` branch only).  
**Named gate:** Requirement Policy Parallel Authority Retirement Gate (`requirement_policy_parallel_authority_retirement.v1`).  
**Named CI:** `backend/tests/platform/test_requirement_policy_parallel_authority_retirement_gate.py`.  
**PASS when:** those three cannot independently answer “need X?”; ruleset write retired as authority (history OK); P3B non-document_required intact; R5/operator unchanged.

**Runtime this slice:** 410 on `document-policies` writes + readers short-circuited; 410 on ruleset create/activate/rollback/PATCH (GET history kept); P3B create rejects `document_required` and `apply_tenant_overrides` filters it out.

**Residual (does not reopen 3A):** frozen `document_ruleset_versions.json_data` may still be *read* by legacy hiring/owner_summary paths until **RPM-3B** stops using it as required-set SoT. 3A closed the admin write path.

### RPM-3B — Consumer parity (**Active**; feat not started)

**Rows:** B · D · E · F · G; confirm H · I.  
**Depends on:** RPM-3A Gate PASS.  
**Named gate:** Requirement Policy Consumer Parity Gate.  
**PASS when:** each consume/retire-as-answerer/contract row meets the matrix proof; policy-answer parity where required; Overlay confirm; no new write.

### Requirement Policy Consumer Cutover Gate

**Depends on:** RPM-3A Gate ∧ RPM-3B Gate. Closes the RPM-3 program ladder. Hiring E2E unlocked, **not** scheduled.

Out: Hiring E2E walk; Mapping; reopening RPM-2; retiring all of P3B; forcing Overlay into R5; treating Hub catalog as policy.

---

## Program close = two results

| Field | Meaning |
|-------|---------|
| **Program outcome** | Operator manages document-requirement policy through one authority; classified consumers do not contradict |
| **Release delta** | Requirement Policy Management four-checks PASS (Documents domain). Mapping, External Intake, Hiring E2E, min HR remain **OPEN**. HostFlow v1 is **not** release-ready. Documents Foundation stays 🔄 |

Hiring E2E is **unlocked** by this close (known acceptance edge). Unlock ≠ schedule.

---

## Queue position

**Depends on:** E8-eval Gate ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · DAG dependency-position [#328](https://github.com/igortatarynovich/HostFlow/pull/328)  
**RPM-1:** **PASS** (Authority Gate).  
**RPM-2:** **PASS** (Operator Gate; `document_policy_tenant_overlays` + Settings write; D4 tenant-level unconditional).  
**Active:** **RPM-3B** (consumer parity).  
**Queued inside this program:** Consumer Cutover Gate → program close.  
**Does not:** schedule Mapping; start Hiring E2E / Intake / min HR; invent CL8; mint a packages table; rewrite Overlay / CL7 / DR1 / E8-eval / R5; retire all of P3B; mark Foundation ✅

---

## Refs

- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — v1 acceptance; four checks; Release DAG  
- [Dependency-position review](../gates/v1-release-dag-dependency-position.md) — why RPM is first; Mapping startable but must not precede  
- [E8-eval](documents-platform-e8-eval.md) — evaluation runtime this program operates  
- [Requirement Policy Authority](../architecture/requirement-policy-authority.md) — operator question + write + nine-row classification (`requirement_policy_authority.v1`)
- [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) — Admin UI for policy was out of Slice 1; this program is that operator job for Documents
- [ADR-039](../architecture/ADR-039-tenant-data-lifecycle.md) — overlay table claimed as lifecycle participant (runtime OL-6)

---

## History

- 2026-09-03: **RPM-3A Parallel Authority Retirement** feat — 410 writers A/C; P3B `document_required` inert; named gate. Active stays RPM-3A until gate PASS then RPM-3B.
- 2026-09-03: **RPM-3 matrix accepted with corrections.** Internal ladder RPM-3A → RPM-3B → Consumer Cutover Gate (one Active slice). Targets refined (E split candidate vs transfer; F retire as answerer/catalog; G Engine contract + R5 document-required input; J cut `document_required` only). Policy-answer parity normative. Active = **RPM-3A**. Code not started.
- 2026-09-02: **RPM-3 cutover matrix** (docs only). Nine rows + P3B; consume proof = base/require/remove parity; recommend RPM-3A writer retirement then RPM-3B consumer parity. Code not started.
- 2026-09-02: **RPM-2 Operator Gate** — Documents-first compiler, `document_policy_tenant_overlays` (revision + RLS + ADR-039 claim), D4 resolve loads stored delta. Proof = tenant-level unconditional. RPM-3 queued.
- 2026-09-02: RPM-1 Authority Gate **PASS**. SoT = [requirement-policy-authority.md](../architecture/requirement-policy-authority.md). Named CI + boundary. Active successor = RPM-2 (feat not started in the RPM-1 PR).
- 2026-08-27: Brief opened after DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328). Feat locked. Gate not PASS.
  
