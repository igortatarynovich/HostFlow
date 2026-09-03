# Requirement Policy Management

**Status:** **RPM-1 PASS** · **RPM-2 PASS** — [Requirement Policy Operator Gate](#requirement-policy-operator-gate) (`tenant_document_policy_deltas` + `resolved_policy`). **Active Product = RPM-3A** Parallel authority retirement (feat locked this PR).  
**Phase class:** platform  
**Branch (docs):** `feat/requirement-policy-management-rpm3`  
**Branch (code):** `feat/requirement-policy-management-rpm2-operator-overlay` (RPM-2 ✅ [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64`). RPM-3A feat locked until this docs lock merges.  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [v1 Release DAG dependency-position](../gates/v1-release-dag-dependency-position.md) [#328](https://github.com/igortatarynovich/HostFlow/pull/328) · [Documents Platform E8-eval](documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [Requirement Policy Authority](../architecture/requirement-policy-authority.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Reference R5](platform-reference-identity-sot.md) · [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md)
**Estimate:** 4–6 slices — RPM-1 1 (docs), RPM-2 1–2, RPM-3A 1, RPM-3B 1–2 (1 slice = one docs PR + one feat PR; rolled up in the [queue release horizon](sales-to-comms-sequential-queue.md))

> First Product from the [Release DAG](../gates/hostflow-v1-release-goal.md), scheduled after [#328](https://github.com/igortatarynovich/HostFlow/pull/328).  
> Documents is the **first domain** of this capability — not a second Documents Admin vs Rules Admin.  
> E8-eval already evaluates D4 from R5 `merge(pack, tenant_delta)`. This program gives the operator **one** write of that authority (base, override, reason, result) and collapses parallel answerers.  
> **Not** Mapping Authority. **Not** External Intake. **Not** Hiring E2E. **Not** min HR. **Not** CL8. **Not** a Hub packages table. **Not** Overlay rewrite. **Not** reopening E8-eval / R5.  
> **Not** intake qualification / Meta screening / `lead_criteria_v1`. Documents domain first; a later RPM domain may evaluate canonical facts for fit — that domain is not this program and is not scheduled here.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
Nine live answerers still reply to “must this candidate provide document type X for this tenant / client / vacancy / profile / country?” E8-eval proved **evaluation** on D4 against pack merge. It did not give an operator one overlay with reason. Without this program Hiring E2E cannot accept against policy authority, and Settings will keep splitting Documents / Ruleset / Transfer Policy / Hiring gates.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Documents surface** (`/app/candidates/:id` documents zone) **plus** one operator overlay that writes the **same** R5 merge D4 already reads. Operator sets base / override / reason; D4 result changes; remaining document-requirement consumers do not contradict. Proof is **not** Recruitment Application G4, not a new Hiring Product, not Mapping editors.

**False close (reject):** Documents Admin separate from Rules Admin; minting a Hub packages table; treating Overlay rewrite as RPM; CL8; reopening E8-eval / R5; walking Hiring E2E without the overlay; starting Mapping / Intake / min HR “while we are here”; Foundation ✅; folding intake qualification, Meta screening rules, or `lead_criteria_v1` into RPM-1 so document requirements also answer “does this lead fit?”; treating recruiter Result / Why / Facts as this program’s named consumer; retiring all of P3B; treating two RPM-3 feats as one Active slice.

---

## Internal ladder (this program only)

One Active Product slice at a time. RPM-1 Authority Gate **PASS**. RPM-2 Operator Gate **PASS**. **Active = RPM-3A**. Mapping is **not** on this ladder.

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
| **RPM-1** | Authority contract | `rpm-authority` | **Requirement Policy Authority Gate** ✅ — one operator question; one write authority; nine answerers classified (write / consume / leftover / not-this-write). SoT: [requirement-policy-authority.md](../architecture/requirement-policy-authority.md) (`requirement_policy_authority.v1`). Docs + contract | E8-eval Gate ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328) | RPM-2 |
| **RPM-2** | Operator overlay | `rpm-operator` | **Requirement Policy Operator Gate** ✅ — one job UI: base rule, override, reason, result; writes the RPM-1 authority; Documents domain first | **Requirement Policy Authority Gate** | RPM-3A |
| **RPM-3A** | Parallel authority retirement | `rpm-cutover-writers` | **Requirement Policy Parallel Authority Retirement Gate** — A `document_policies`, C leftover ruleset writes, J P3B `document_required` only. Feat locked this PR | **Requirement Policy Operator Gate** | RPM-3B |
| **RPM-3B** | Consumer parity | `rpm-cutover-consumers` | **Requirement Policy Consumer Parity Gate** — remaining consumers’ **policy answer** matches R5 required-set (base / require X / remove X); Overlay confirm; R5 remains sole write | **Requirement Policy Parallel Authority Retirement Gate** | Consumer Cutover Gate |
| **RPM-3 close** | Consumer cutover close | `rpm-cutover` | **Requirement Policy Consumer Cutover Gate** — 3A ∧ 3B PASS; no live independent “need X?” answerer; D4 result matches operator write; stage/transfer do not contradict | RPM-3A Gate ∧ RPM-3B Gate | RPM program close. Hiring E2E **unlocked, not scheduled** |

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
6. Intake qualification / screening / `lead_criteria_v1` are not this slice and are not a tenth write on the table above.

This slice **closes** the Authority Gate. Feat remains locked until **RPM-2**. Do not start RPM-2 in this PR (queue invariant 6).

### Boundary — not this program (normative)

RPM-1’s operator question stays **document type X required?** Overlay + screening pack stays **Not this write**. `lead_criteria_v1` (`fit` / `no_fit` / `needs_info` on vacancy extra) answers a **different** question — inbound qualification against facts — and is **not** a tenth RPM-1 answerer.

Do not pull screening into RPM-1. That would make one Documents domain also own qualification, leave `lead_criteria_v1` as a parallel answerer, and create a new split instead of collapsing the nine.

A later RPM **domain** (not a slice of this ladder, not scheduled here) may let the operator set acceptance conditions on **canonical facts** (required / preferred / advantage) once [Mapping Authority](mapping-authority.md) supplies those facts. Until then:

- Evaluation of document requirements reads R5 merge + document facts, as E8-eval already does.
- Evaluation must not read Meta / provider payload. Mapping uncertainty is not candidate failure — that rule is sealed on the Mapping brief; RPM-1 does not implement it.
- Recruiter Result / Why / Facts / source evidence is the **target object** for intake after Mapping is consumed. It is **not** RPM-1 proof (D4 Documents + one overlay remains).

---

## RPM-2 — Operator overlay (**PASS**)

One operator job. The UI does **not** mint a rules model. It edits the existing `tenant_delta` that `validate_tenant_overlay_delta` already accepts and that `merge_resolved_policy` already consumes. D4 already reads that merge via E8-eval.

GET returns **`resolved_policy`** = `merge_resolved_policy(tenant_delta)` — the merged pack, not a hypothetical candidate evaluation. D4 applicability is the operational proof.

**Proof (one chain):**

```text
operator action → persisted tenant_delta → same R5 merge_resolved_policy → D4 effective requirement changes
```

Four checks from the [Release Goal](../gates/hostflow-v1-release-goal.md): runtime authority (sealed in RPM-1), operator surface (sealed this slice), E2E consumption and release acceptance (proven on D4 here; remaining consumers in RPM-3).

Writes: overlay delta only (`candidate.overrides` / `vacancy.additions` / `validity`). **reason** is a sibling column (audit metadata), not part of the JSONB delta and not a merge input.

Store: `tenant_document_policy_deltas`. API: GET/PUT `/platform/document-policy-overlay`. Settings page: `RequirementPolicyOverlayPage`. Named CI: `backend/tests/platform/test_requirement_policy_operator_gate.py`. Evidence: [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64`.

### Requirement Policy Operator Gate

**Outcome:** **PASS**.

PASS when:

1. One persistence table stores the R5 `tenant_delta` contract only.  
2. One GET/PUT API writes that delta; GET exposes `resolved_policy` from the existing merge.  
3. D4 resolve loads the persisted delta into `project_required_doc_applicability_via_contract`.  
4. One Settings job UI: base pack, overlay, reason, `resolved_policy`.  
5. No second merge, evaluator, store (`document_policies` / `tenant_requirement_overrides`), leftover ruleset editor, Mapping, or RPM-3 retirement.

Out: a second store; a second evaluator; a parallel rules JSON; a second editor; Zapier; Mapping UI; Mapping Authority; intake qualification / `lead_criteria_v1`; Result / Why / Facts; Hiring funnel builder; Documents Admin vs Rules Admin; `tenant_requirement_overrides`.

---

## RPM-3 — Consumer cutover (ladder; **Active = RPM-3A**)

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

### RPM-3A — Parallel authority retirement (**Active**; feat locked)

**Rows:** A · C · J (`document_required` branch only).  
**Named gate:** Requirement Policy Parallel Authority Retirement Gate (`requirement_policy_parallel_authority_retirement.v1`).  
**Named CI (feat PR):** `backend/tests/platform/test_requirement_policy_parallel_authority_retirement_gate.py`.  
**This PR:** docs lock only. Do not start the 3A feat here (queue invariant 6 vs the RPM-2 merge). Do not start RPM-3B.

**PASS when (feat PR, not this PR):**

1. A `document_policies` cannot independently write “need X?” (writes refused; remaining reads are not this slice).  
2. C leftover ruleset cannot change required types via admin write (create/activate/rollback/PATCH refused; GET history may remain).  
3. J P3B `document_required` cannot change the required-set vs R5; `field_required` / severity / other P3B contracts stay.  
4. R5 merge, operator overlay store (`tenant_document_policy_deltas`), and D4 resolve are unchanged.  
5. Mapping / Hiring E2E / Overlay rewrite / CL8 / Hub packages / retiring all of P3B are not this slice.

**Planned runtime (feat, not this PR):** 410 on `document-policies` writes; 410 on ruleset create/activate/rollback/PATCH (GET history kept); P3B create rejects `document_required` and `apply_tenant_overrides` filters it out.

**Residual (does not reopen 3A):** frozen `document_ruleset_versions.json_data` may still be *read* by legacy hiring/owner_summary paths until **RPM-3B** stops using it as required-set SoT. 3A closes the admin write path.

### RPM-3B — Consumer parity (queued)

**Rows:** B · D · E · F · G; confirm H · I.  
**Depends on:** RPM-3A Gate PASS.  
**Named gate:** Requirement Policy Consumer Parity Gate.  
**PASS when:** each consume/retire-as-answerer/contract row meets the matrix proof; policy-answer parity where required; Overlay confirm; no new write.

### Requirement Policy Consumer Cutover Gate

**Depends on:** RPM-3A Gate ∧ RPM-3B Gate. Closes the RPM-3 program ladder. Hiring E2E unlocked, **not** scheduled.

Out: Hiring E2E as a walk of `stage → eligibility → transfer` (that is the next DAG node after RPM **program** close). Out: Mapping Authority. Out: reopening RPM-2. Out: retiring all of P3B. Out: forcing Overlay into R5. Out: treating Hub catalog as policy.

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
**RPM-2:** **PASS** (Operator Gate; `tenant_document_policy_deltas`; GET `resolved_policy`; D4 loads persisted delta) [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64`.  
**Active:** **RPM-3A** (parallel authority retirement; feat locked this PR).  
**Queued inside this program:** RPM-3B after 3A Gate PASS → Consumer Cutover Gate → program close.  
**Does not:** schedule Mapping; mint RPM → Mapping as an acceptance edge; start Hiring E2E / Intake / min HR; invent CL8; mint a packages table; rewrite Overlay / CL7 / DR1 / E8-eval / R5; mark Foundation ✅; open intake qualification as a second RPM-1 question; fold `lead_criteria_v1` into the nine-row table; retire all of P3B; start RPM-3B in this PR

---

## Refs

- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — v1 acceptance; four checks; Release DAG  
- [Dependency-position review](../gates/v1-release-dag-dependency-position.md) — why RPM is first; Mapping startable but must not precede  
- [E8-eval](documents-platform-e8-eval.md) — evaluation runtime this program operates  
- [Requirement Policy Authority](../architecture/requirement-policy-authority.md) — operator question + write + nine-row classification (`requirement_policy_authority.v1`)
- [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) — Admin UI for policy was out of Slice 1; this program is that operator job for Documents  
- [Mapping Authority](mapping-authority.md) — canonical facts this capability will later consume for qualification; not this write; not scheduled by this brief

---

## History

- 2026-09-03: **RPM-3A docs lock.** Internal ladder RPM-3A → RPM-3B → Consumer Cutover Gate (one Active slice). Cutover matrix accepted with corrections (E split candidate vs transfer; F retire as answerer/catalog; G Engine contract + R5 document-required input; J cut `document_required` only). Policy-answer parity normative. Active = **RPM-3A**. Feat locked. Mapping / Hiring E2E not auto-scheduled. Not CL8. Foundation stays 🔄.
- 2026-09-03: RPM-2 Operator Gate **PASS** [#342](https://github.com/igortatarynovich/HostFlow/pull/342) / `5196ee64` — persist R5 `tenant_delta` in `tenant_document_policy_deltas`; GET `resolved_policy` from existing merge; D4 resolve consumes the row. reason is a sibling column.  
- 2026-09-03: Screening / `lead_criteria_v1` confirmed **not** a tenth RPM-1 write (integration boundary + this gate).  
- 2026-09-02: RPM-1 Authority Gate **PASS**. SoT = [requirement-policy-authority.md](../architecture/requirement-policy-authority.md). Named CI + boundary. Active successor = RPM-2.
- 2026-08-27: Brief opened after DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328). Feat locked. Gate not PASS.
