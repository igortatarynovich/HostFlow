# Requirement Policy Management

**Status:** **RPM-1 PASS** — [Requirement Policy Authority Gate](../architecture/requirement-policy-authority.md) (`requirement_policy_authority.v1`). Active Product successor = **RPM-2** (operator overlay; feat not started this PR).  
**Phase class:** platform  
**Branch (docs):** `docs/queue-schedule-rpm` · `feat/requirement-policy-authority-rpm1`  
**Branch (code):** none this slice — feat locked until RPM-2; later slices `feat/requirement-policy-management-rpmN-…`  
**Parents:** [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) · [v1 Release DAG dependency-position](../gates/v1-release-dag-dependency-position.md) [#328](https://github.com/igortatarynovich/HostFlow/pull/328) · [Documents Platform E8-eval](documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [Requirement Policy Authority](../architecture/requirement-policy-authority.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Reference R5](platform-reference-identity-sot.md) · [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md)
**Estimate:** 3–5 slices — RPM-1 1 (docs), RPM-2 1–2, RPM-3 1–2 (1 slice = one docs PR + one feat PR; rolled up in the [queue release horizon](sales-to-comms-sequential-queue.md))

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

One Active Product slice at a time. RPM-1 Authority Gate **PASS**. This PR names **RPM-2** as Active successor and does **not** start it. RPM-3 stays queued. Mapping is **not** on this ladder.

```text
RPM-1 Authority contract
  → RPM-2 Operator overlay
  → RPM-3 Consumer cutover
  → RPM program close (outcome + release delta)
```

| # | Slice | Machine id | Named gate | Depends on | Unlocks |
|---|--------|------------|------------|------------|---------|
| **RPM-1** | Authority contract | `rpm-authority` | **Requirement Policy Authority Gate** ✅ — one operator question; one write authority; nine answerers classified (write / consume / leftover / not-this-write). SoT: [requirement-policy-authority.md](../architecture/requirement-policy-authority.md) (`requirement_policy_authority.v1`). Docs + contract; feat locked | E8-eval Gate ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) · DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328) | RPM-2 |
| **RPM-2** | Operator overlay | `rpm-operator` | **Requirement Policy Operator Gate** — one job UI: base rule, override, reason, result; writes the RPM-1 authority; Documents domain first | **Requirement Policy Authority Gate** | RPM-3 |
| **RPM-3** | Consumer cutover | `rpm-cutover` | **Requirement Policy Consumer Cutover Gate** — classified consumers read the same merge (or are retired); D4 result matches operator write; stage/transfer do not contradict | **Requirement Policy Operator Gate** | RPM program close. Hiring E2E **unlocked, not scheduled** |

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

## RPM-2 — Operator overlay (Active successor; feat not started)

One operator job. Settings that edit non-authority JSON is not ready. Four checks from the [Release Goal](../gates/hostflow-v1-release-goal.md) apply: runtime authority (sealed in RPM-1), operator surface (this slice), E2E consumption and release acceptance (proven on D4 here, cutover completed in RPM-3).

Out: a second editor; Zapier; Mapping UI; Hiring funnel builder.

---

## RPM-3 — Consumer cutover (queued)

Remaining rows marked consume / leftover / fold must not answer the operator question independently. D4 already reads R5 merge via E8-eval — this slice makes the other consumers match that result.

Out: Hiring E2E as a walk of `stage → eligibility → transfer` (that is the next DAG node after RPM **program** close). Out: Mapping Authority.

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
**Active successor:** RPM-2 (operator overlay; feat not started this PR).  
**Queued inside this program:** RPM-3 after RPM-2.  
**Does not:** schedule Mapping; mint RPM → Mapping as an acceptance edge; start Hiring E2E / Intake / min HR; invent CL8; mint a packages table; rewrite Overlay / CL7 / DR1 / E8-eval / R5; mark Foundation ✅

---

## Refs

- [HostFlow v1 Release Goal](../gates/hostflow-v1-release-goal.md) — v1 acceptance; four checks; Release DAG  
- [Dependency-position review](../gates/v1-release-dag-dependency-position.md) — why RPM is first; Mapping startable but must not precede  
- [E8-eval](documents-platform-e8-eval.md) — evaluation runtime this program operates  
- [Requirement Policy Authority](../architecture/requirement-policy-authority.md) — operator question + write + nine-row classification (`requirement_policy_authority.v1`)
- [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) — Admin UI for policy was out of Slice 1; this program is that operator job for Documents

---

## History

- 2026-09-02: RPM-1 Authority Gate **PASS**. SoT = [requirement-policy-authority.md](../architecture/requirement-policy-authority.md). Named CI + boundary. Active successor = RPM-2 (feat not started).
- 2026-08-27: Brief opened after DAG review [#328](https://github.com/igortatarynovich/HostFlow/pull/328). Feat locked. Gate not PASS.
  
