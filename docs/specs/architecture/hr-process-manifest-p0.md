# HR Process Manifest P0

**Status:** Shipped (Process Engine stage registration only).  
**Gate:** Follows [module-owned-pipelines-p0.md §7 gate closure](module-owned-pipelines-p0.md) — authorized work after Recruitment P0.

**Owner:** Platform core + HR module.

**Related:**

- [`process-engine.md`](../platform/process-engine.md) §3.1 — system stage registry canon
- [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) — company-scoped **Recruitment** funnels (separate from this doc)
- [`invariants-recruitment-hr-document-hub.md`](invariants-recruitment-hr-document-hub.md) — module boundary
- [`hr-acceptance-workflow-state-machine.md`](../workflows/hr-acceptance-workflow-state-machine.md) — logical states mapped to PE codes

---

## 1. Goal

Register **`hr.*` semantic system stages** in Process Engine so HR owns its stage namespace. Confirms platform canon:

> **Process Engine evaluator is shared; stage semantics belong to the module.**

This phase **does not** ship employee funnel runtime, `resolve_hr_funnel`, HR dashboard widgets, or cross-module handoff execution.

---

## 2. Scope (in)

| Item | Status |
|------|--------|
| `backend/app/process_engine/manifests/hr.py` | ✅ |
| `ProcessEngineRegistry.register_module` for `module=hr` | ✅ platform catalog + tenant when `hr` enabled |
| `PeSystemStage` rows with HR-specific `analytics_bucket` values | ✅ not recruitment four-bucket legacy |
| `PeStageTemplate` rows (`hr_intake_v1`, `hr_verification_v1`, …) | ✅ |
| Inbound handoff **contract placeholder** on HR module (`hr_inbound_handoff_contract_v1`) | ✅ config only — not wired |
| `validate_pe_system_stage(..., module=hr, code=...)` succeeds for registered codes | ✅ |
| Tests `tests/process_engine/test_process_engine_hr_manifest_p0.py` | ✅ |

---

## 3. Scope (out — explicit)

| Item | Reason |
|------|--------|
| `resolve_hr_funnel` | HR employee pipeline gate — separate milestone |
| HR `funnels` / `module_key=hr` rows | Module-owned pipeline pattern deferred |
| `PePipelineTemplate` / `PeProcessProfile` for HR | No HR pipeline runtime in P0 |
| HR transition / field / document requirement rules (runtime) | After manifest + HR pipeline ADR |
| Dashboard UI | Post-gate backlog |
| Wiring recruitment handoff evaluator to HR case creation | Future handoff contract implementation |
| Direct recruitment ↔ HR coupling in code paths | Only placeholder handoff rule documents target stage |

---

## 4. HR system stages (P0 catalog)

Qualified form: **`hr.<code>`** (module + code in registry).

| code | template | analytics_bucket | terminal | Notes |
|------|----------|------------------|----------|-------|
| `received_from_recruitment` | hr_intake_v1 | intake | no | Handoff entry (recruitment manifest references this target) |
| `handoff_pending` | hr_intake_v1 | intake | no | Inbox / pending accept |
| `accepted_by_hr` | hr_review_v1 | review | no | HR took ownership |
| `hr_review_in_progress` | hr_review_v1 | review | no | Checklist active |
| `waiting_documents` | hr_waiting_v1 | waiting | no | Review substate |
| `waiting_payments` | hr_waiting_v1 | waiting | no | Review substate |
| `waiting_work_permit` | hr_waiting_v1 | waiting | no | Review substate |
| `waiting_red_paper` | hr_waiting_v1 | waiting | no | Review substate |
| `verification` | hr_verification_v1 | verification | no | Compliance verification |
| `approved_for_employment` | hr_employment_v1 | employment | no | Employment approval |
| `contract` | hr_contract_v1 | employment | no | Contract branch |
| `employment_pending` | hr_employment_v1 | employment | no | Payroll/ZUS in flight |
| `active` | hr_active_v1 | active | yes | Active employment |
| `employed` | hr_active_v1 | active | yes | Product alias |
| `returned_to_recruitment` | hr_returned_v1 | returned | yes | Exit to recruitment |
| `rejected_by_hr` | hr_rejected_v1 | rejected | yes | Terminal reject |

**Prohibited for HR stages:** recruitment legacy analytics buckets `new`, `in_progress`, `hired`, `declined_rejected` (see [`module-owned-pipelines-p0.md`](module-owned-pipelines-p0.md) §2.5).

---

## 5. Seed paths

| Function | When |
|----------|------|
| `ensure_platform_process_engine_catalog` | Once per `run_seed` — registers HR manifest at `PLATFORM_TENANT_SCOPE` |
| `ensure_hr_process_engine_stages` | Per tenant when `tenant.settings.modules.hr` is enabled |

Recruitment tenant seed (`ensure_recruitment_process_engine_defaults`) is unchanged and independent.

---

## 6. Handoff contract placeholder

HR manifest includes **`hr_inbound_handoff_contract_v1`** with `handoff_mode=inbound_contract_placeholder`:

- Documents entry stage `received_from_recruitment`
- References `handoff_contract_v1` by name only
- **Does not** execute cross-module routing

Recruitment manifest continues to declare outbound target `hr.received_from_recruitment` in `handoff_internal_hr` — runtime validation requires HR stages registered (this P0).

---

## 7. Tests

| Test | Asserts |
|------|---------|
| `test_hr_manifest_declares_hr_module_stages_only` | No pipeline/profile; no recruitment stage codes |
| `test_hr_manifest_analytics_buckets_are_hr_specific` | Disjoint from recruitment legacy buckets |
| `test_hr_manifest_inbound_handoff_placeholder_only` | Single placeholder rule |
| `test_hr_module_registers_system_stages` | DB row counts |
| `test_validate_pe_system_stage_finds_hr_received_from_recruitment` | PE validation path |
| `test_ensure_hr_process_engine_stages_skips_when_hr_disabled` | Module gate |

---

## 8. Success criterion

**PASS:** HR operations can resolve **`hr.*`** stages via Process Engine registry and `validate_pe_system_stage` without borrowing recruitment funnel stages or legacy `system_stage` four-bucket semantics.

**Next milestone:** HR employee pipeline (`module_key=hr`, company-scoped funnel, `resolve_hr_funnel`) — separate gate referencing Recruitment P0 template.

---

## History

- 2026-06-30: HR Process Manifest P0 — stage registration, seed, tests, handoff placeholder.
