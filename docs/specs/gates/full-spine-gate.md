# Full Spine Gate

**Status:** **STOP** — superseded by [`ADR-042`](../architecture/ADR-042-operator-host-boundary.md). Named operator PASS of this gate is **not pursued**.  
**Date (freeze):** 2026-09-09  
**Date (STOP):** 2026-09-10  
**Trusted base:** `feat/eso4-formalize`  
**Successor SoT:** [`ADR-042-operator-host-boundary.md`](../architecture/ADR-042-operator-host-boundary.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Does not rewrite L0. Does not open ESO-6. Does not merge ESO into `integration` on this withdrawn contract.

> This file is **not** the operator journey SoT.  
> Do **not** retune it into a three-host Full Spine. The original product hypothesis is false.  
> Machine ESO composition (`full_spine.v1` / `walk_full_spine_happy_path_v1`) may remain as **ESO API evidence**. It is not Full Spine operator PASS.

---

## Why STOP (do not “slightly fix”)

The freeze treated process continuity as **one UI card**:

Отклик → Подходит → Передать → Оформить → Подтвердить выход → Вышел.

That mixed:

- Fits with Ready for employment  
- Fits with Transfer  
- Seamless handoff with the same UI host  

The hypothesis is withdrawn. A corrected operator journey is **not** this gate with different verbs. It is ADR-042 (hosts) plus a later **runtime cutover** (routing / ownership only). ESO-1…5 are not rewritten here.

---

## Withdrawn hypothesis (historical)

Operator question this gate asked: can an untrained operator take one inbound lead to Started on a **single continuous Application card**, without changing host.

**Completion proof that is no longer valid:** Application Workspace → **Подходит** → **Передать** → **Оформить** → **Подтвердить выход** → Started.

**Forbidden-on-happy-path that is no longer valid as a lock:** treating “open HR card” as a FAIL. After Transfer the operator **should** open an already-prepared HR / Employment case.

Machine walk on a valid `ready_for_employment.v1` package (Accept → Employability → Missing → Formalize → Employee → Started) stays useful. It does not prove Application-hosted Employment.

---

## Successor

Canonical spine: Отклик → Fits → Кандидат → Recruitment → Ready for employment → Transfer → HR/Employment → ESO-1…5 → Started.

Negative locks: Fits ≠ Ready for employment; Fits ≠ Transfer; Seamless handoff ≠ same UI host.

[#359](https://github.com/igortatarynovich/HostFlow/pull/359) one-card PASS is not a goal. Intake Readiness / citizenship remain a separate facts problem.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
A live Full Spine operator contract whose happy path is Application-hosted Employment after Fits.

**Completion proof (named consumer):**  
This STOP record + ADR-042. No operator PASS of the withdrawn one-card journey.

**False close (reject):** rewriting the tables below this heading into the ADR-042 spine and calling that Full Spine Gate PASS; deleting ESO-1…5; merging ESO into `integration` to satisfy this file.
