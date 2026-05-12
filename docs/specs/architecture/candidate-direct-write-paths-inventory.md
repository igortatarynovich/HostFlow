# Candidate direct write paths (inventory)

**Rule (canonical):** any mutation of `Candidate` must be either (1) a **recruitment write** routed through `update_candidate_full` / a guarded service that calls `require_agency_recruitment_write_allowed`, or (2) a **system / HR / client / pre-handoff** write with an explicit guard and audit / `operation_source` reason. Avoid silent `candidate.field = …` without ownership context.

**Legend — contour:** `recruitment` = agency recruiter dossier; `system` = schedulers / automation; `pre-handoff` = public intake before handoff; `hr` = workforce materialization; `mixed` = depends on caller.

| File / area | What changes | Contour | Resolution / status |
|-------------|--------------|----------|---------------------|
| `app/api/v1/candidates/service.py` | Stage, manager, recruiter, deletes, bulk, `update_candidate_full` | recruitment | Canonical + `require_agency_recruitment_write_allowed` / bulk errors |
| `app/api/v1/candidates/repo.py` | `update(Candidate)` (incl. soft-delete flags) | recruitment | Keep aligned with router ACL; ensure new call sites use guard |
| `app/api/v1/candidate_profile.py` | Base columns + `extra` JSON (profile, questionnaire, autofill) | recruitment (agency) / client | `patch_profile`: `can_agency_edit` / `can_client_edit`. **Fixed:** `patch_questionnaire`, `autofill_from_docs` now use the same checks (previously bypassed lock) |
| `app/api/v1/candidate_documents.py` | `docs_progress`, `updated_at` | recruitment / system read aggregate | **Contract:** `_recalc_docs_progress` only touches `docs_progress` + `updated_at` (not stage/status); not recruitment-lock-blocked; document mutations stay behind `_check_document_edit_permission` |
| `app/api/v1/candidate_links.py` | `company_id`, `vacancy_id` | recruitment | **Done:** strict `require_agency_recruitment_write_allowed(..., bypass=None)` + client `can_client_edit`; mounted at `/api/v1/candidate-links` |
| `app/api/v1/vacancies/router.py` | Assign candidate to vacancy (`vacancy_id`, `company_id`) | recruitment | **Done:** `_require_can_reassign_candidate_to_vacancy` (no bypass) before `update(Candidate)` |
| `app/api/public/intake.py` | `stage`, `status`, tokens, `intake_state`, etc. | pre-handoff / candidate portal | Allowed before handoff; must not mutate agency-recruitment locked dossier when session is agency-scoped (audit `source`); review cross-tenant |
| `app/services/intake_channel_candidate.py` | Intake columns after `create_candidate_full` | pre-handoff | Service-layer intake; OK for draft bootstrap; document |
| `app/services/contact_attempts.py` | `stage`, `status`, auto-reject | recruitment | **Recruitment lock:** agency `create_attempt` blocked when locked. **Workforce lock:** stage/status/auto-reject skipped with `observe_skipped_system_candidate_mutation_due_to_workforce_lock` |
| `app/services/reminders.py` | `update(Candidate)` → `stage=docs_wait` on doc-expiry “due today” | system | **Workforce lock:** skip stage bump + audit/metrics skip (HR owns row) |
| `app/services/candidate_telegram_notifications.py` | `sync_candidate_ready_for_handoff_gate`: `stage`/`status`/`intake_state` | system | **Workforce lock:** skip promotion + observe |
| `app/services/workforce_employees.py` | `update(Candidate)` | hr | Explicit HR materialization path; keep audit |
| `app/services/recruiter_assignment.py` | `candidate.manager` / `recruiter_id` | recruitment | **Done:** `record_candidate_reassignment(write=True)` enforces recruitment guard; optional `agency_recruitment_bypass` for aligned privileged callers |
| `app/services/onboarding_demo_seed.py` | `updated_at` only | system | Demo seed only |
| `app/scripts/*.py` | Various `update(Candidate)` | ops | Out of product guard path; document / restrict env |
| Webhook consumers (app) | *(no `update(Candidate)` hits in current grep)* | — | Re-scan when adding integrations |
| CSV / import | *(route through candidates service or workers — verify per job)* | mixed | Inventory in worker modules when touched |
| Automation workers / schedulers | reminders, telegram gate, contact attempts | system | Use `is_candidate_locked_by_workforce` + observe for stage/status |

## External ingest entrypoints (production)

| Entry | Path into code | Candidate mutation risk | Mitigation |
|-------|----------------|---------------------------|------------|
| Meta lead webhook | `modules/leads/webhook.py` → `service.process_meta_lead` → `process_normalized_lead` | Replay on `processed`/`duplicated` lead patched `Candidate.own_company_id` / `extra` | **Done:** `_agency_candidate_recruitment_locked_for_ingest` skips dossier ORM writes when agency recruitment locked |
| Leads CSV import (async job) | `services/imports/leads.py` `run_import_job` → `process_normalized_lead` | Same as webhook | Same guard (shared pipeline) |
| Leads bulk / generic webhook | `modules/leads/service/_bulk.py` → `process_normalized_lead` | Same | Same guard |
| Stripe / billing webhooks | `settings/billing/routes.py` | Billing only | No `Candidate` writes |
| `execute_automation_rule` | `services/automation_rules.py` | Reminders + activity log | No direct `Candidate` column updates |
| `scripts/*.py`, onboarding demo seed | ops / demo | `update(Candidate)` | Out of band; document only |

_Last reviewed: inventory PR (grep `update(Candidate)`, `candidate.stage` / `status` assignments in `backend/app`)._
