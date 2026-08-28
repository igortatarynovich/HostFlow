# Lifecycle Identity LI-1 — Existence Guard

**Status:** **PASS** — LI-1 Existence Guard Gate closed by [#300](https://github.com/igortatarynovich/HostFlow/pull/300) / `c9ca41cc` after CL1 Gate ✅ [#299](https://github.com/igortatarynovich/HostFlow/pull/299); LI-2+ stay queued in the [Lifecycle brief](lifecycle-identity-l0-contract-seal.md)  
**Phase class:** platform  
**Branch:** `feat/lifecycle-identity-li1-existence-guard`  
**Parents:** [Lifecycle Identity L0](lifecycle-identity-l0-contract-seal.md) · [ADR-037](../architecture/ADR-037-lifecycle-identity-canon.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> LI-1 establishes **one producer** for “is `{module}.{entity_kind}.{stage_key}` registered?”. It does not cut over funnel schema, `/meta/stages`, or Candidate UI (LI-2+).

---

## Original Goal → Completion Proof

**Problem:** Stage identity still spreads across `constants/stages.py`, funnel presets, PE manifests, Lead literals, and FE lists. Without a named existence producer, the next pipeline PR will mint another parallel catalog.

**Completion proof:** `is_stage_registered` is the sole existence API; v0 manifest seeds `recruitment.candidate.*` keys; repo guard blocks new competing producers. Legacy stranglers remain untouched.

**False close:** funnel FK migration; `/meta/stages` cutover; Candidate kanban rewrite; Sales/HR full catalogs; tenant custom stages.

---

## Scope (v1)

| In scope | Out of scope |
|----------|--------------|
| v0 JSON manifest (`recruitment.candidate.*`) | Funnel schema change |
| `is_stage_registered` producer module | UI / `/meta/stages` cutover |
| Architectural gate test + boundary guard | Registry DB loader (LI-2) |
| CI named **LI-1 Existence Guard Gate** | LI-3 funnel reference bind |

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| v0 manifest | [module-stage-registry-recruitment-candidate-v0.json](../platform/module-stage-registry-recruitment-candidate-v0.json) |
| Existence API | `backend/app/platform/module_stage_registry/existence.py` |
| Boundary guard | `scripts/architecture/check_stage_existence_boundary.py` |
| Gate test | `backend/tests/platform/test_lifecycle_identity_li1_existence_guard_gate.py` |

---

## LI-1 Existence Guard Gate (named)

PASS when:

1. Brief + v0 manifest committed.  
2. `is_stage_registered` answers registration for manifest keys only.  
3. Boundary guard: no second `is_stage_registered` outside allowlisted producer.  
4. No runtime cutover of `constants/stages.py`, `meta.py`, or funnel resolvers.

Unlocks: **DR1-contract** prep (not merge until LI-1 Gate PASS on integration).

---

## History

- 2026-08-23: LI-1 feat slice opened — existence guard only; merge blocked until CL1 Gate.
