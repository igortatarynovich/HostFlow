# Recruitment Architecture — CLOSED

**Status:** **CLOSED** (2026-09-12)  
**Decision ID:** `RECRUITMENT_ARCHITECTURE_CLOSED`  
**Type:** Architecture closure record (docs stamp — not a product feature)  
**Line:** `feat/eso4-formalize` @ `61cbc3eb`  
**Parents:** [`ADR-042`](../architecture/ADR-042-operator-host-boundary.md) · [Recruitment Spine Orchestrator v1](../tasks/recruitment-spine-orchestrator-v1.md) · [Vacancy Recruitment Requirements SoT](../tasks/vacancy-recruitment-requirements-sot.md) · [Canonical Facts Completeness](../tasks/canonical-facts-completeness.md) · [Full Spine Gate](full-spine-gate.md)  
**Closure review:** canvas `recruitment-closure-review` (operator decision 2026-09-12)

> Recruitment is **architecturally closed** on this line through a valid `ready_for_employment.v1` handoff to HR/Employment.  
> Missing HR UI does **not** keep Recruitment open.  
> Full product spine remains **NOT PASS / BLOCKED BY HR UI**.

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `CLOSED` |
| **Date** | 2026-09-12 |
| **Trusted line** | `feat/eso4-formalize` @ `61cbc3eb` (merge [#365](https://github.com/igortatarynovich/HostFlow/pull/365)) |
| **Recruitment ends at** | Valid `ready_for_employment.v1` transferred to the next owner (HR / Employment) |
| **Full Spine** | **NOT PASS / BLOCKED BY HR UI** — [`full-spine-gate.md`](full-spine-gate.md) remains **STOP** |
| **Formalize → Started** | **HR / Employment scope** — not Recruitment debt |
| **Next product work** | Existing HR / Employment track — not further Recruitment expansion |

**Rationale:** Closure matrix accepted: ten Recruitment boundary criteria **PASS**; Full Spine **BLOCKED**; Formalize→Started **NOT IN RECRUITMENT SCOPE**; leftover items **LEGACY DEBT** (not reopening criteria).

---

## Evidence (immutable)

| Slice | PR | Evidence SHA |
|-------|-----|--------------|
| Canonical Facts Occupancy | [#366](https://github.com/igortatarynovich/HostFlow/pull/366) | `bd0bf284` |
| Vacancy Requirements Evaluator | [#367](https://github.com/igortatarynovich/HostFlow/pull/367) | `6d2586a5` |
| Vacancy Overlay Write UI | [#368](https://github.com/igortatarynovich/HostFlow/pull/368) | `18bef9f0` |
| Operator Host Cutover (RSO-2) | [#365](https://github.com/igortatarynovich/HostFlow/pull/365) | tip `efb48c34` / merge `61cbc3eb` |

Named CI on the assembled line (Occupancy · Evaluator · Overlay Write UI · Operator Host Cutover) green at cutover validation. Baseline CI reds retain prior provenance — not reopening criteria.

---

## Closed Recruitment boundary (PASS)

1. Intake yields an actionable Application.  
2. Requirements SoT closed: operator write → evaluator read.  
3. Canonical facts use one decision read path.  
4. Fits enters existing Candidate runtime — not Employment.  
5. Candidate runs existing Recruitment process until Ready.  
6. Transfer is impossible before Ready.  
7. Ready assembles `ready_for_employment.v1`.  
8. Transfer creates a valid HR handoff without re-entering Person / Vacancy / Employer.  
9. Application / Candidate do not host Formalize / Started.  
10. HR owns the process after handoff (contract + package emit).

---

## Explicitly not reopening Recruitment

| Class | Item | Note |
|-------|------|------|
| **BLOCKED** | Full product spine operator → Started | STOP / BLOCKED BY HR UI |
| **NOT IN RECRUITMENT SCOPE** | Formalize → Employee → Started | Employment Spine / HR |
| **LEGACY DEBT** | `lead_criteria_v1` / Candidate Requirements tab · historical row retirement · rates/contracts/legalization/RPM UI · broader occupancy beyond Driver CE · baseline CI reds | Cleanup ≠ reopen |

**Return rule:** do not reopen Recruitment for improvements or cleanup. Return only for a concrete defect of a closed contract, or when the next module proves an interface gap on the handoff boundary.

---

## History

- 2026-09-12: Operator accepts closure matrix. **Recruitment Architecture = CLOSED** on `61cbc3eb`. Docs stamp only.
