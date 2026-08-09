# RBAC role usage inventory (ADR-036 migration gate)

**Status:** NORMATIVE checklist (L2) — gate before Phase 2 runtime delete of legacy role branches  
**Parent:** [`ADR-036-four-trust-roles-rbac.md`](ADR-036-four-trust-roles-rbac.md) · [`rbac_matrix.md`](rbac_matrix.md)  
**Full machine dump:** [`scripts/rbac/role_usage_inventory.csv`](../../../scripts/rbac/role_usage_inventory.csv)  
**Scanner:** [`scripts/rbac/scan_role_usage.py`](../../../scripts/rbac/scan_role_usage.py)

## Summary

- Auto-collected call sites: **1189** (see CSV)
- Distinct High-risk paths: **137**
- By class: `ALIAS`=93, `DOC`=35, `JOB_PROXY`=466, `ORG_PROXY`=135, `PORTAL_LEGACY`=98, `SEAT`=9, `TEST`=53, `TRUST`=291, `UI_ONLY`=9

### Gate rules

1. Phase 2 starts only when every **H** path below has an agreed `target_mapping` (defaults from class; refine in PR notes if needed).
2. Phase 3 delete of a legacy role string only when CSV rows for that role are `removed` or `aliased` on the shim allowlist.
3. Re-run `python scripts/rbac/scan_role_usage.py` after refactors; unexplained new H paths block merge.

### Migration map

| Legacy | Canonical trust | Extra |
|--------|-----------------|-------|
| administrator, owner, admin | administrator | — |
| recruiter, hr, compliance_officer, hr_officer | employee | preset |
| supervisor, manager | employee | preset `team_lead` + `supervisor_id` |
| client_manager, client_processor | viewer | `access_context=portal` + scope |
| viewer, user | viewer | `tenant` or `portal` |
| superadmin | superadmin | — |

## High-risk paths (aggregated)

| path | hits | classes | legacy_roles_seen | target_mapping | status |
|------|------|---------|-------------------|----------------|--------|
| `backend/app/api/public/intake.py` | 4 | JOB_PROXY | recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/admin/companies_access.py` | 3 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/automation_log.py` | 1 | ORG_PROXY | admin,administrator,manager,recruiter,superadmin,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/automation_rules.py` | 4 | ORG_PROXY | admin,administrator,manager,superadmin,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/candidate_documents.py` | 5 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/candidate_employments.py` | 4 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/candidate_notes/router.py` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/candidate_permits.py` | 5 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/candidate_profile.py` | 1 | PORTAL_LEGACY | admin,client_manager,client_processor,manager | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/candidate_profiles.py` | 2 | PORTAL_LEGACY | client_manager,client_processor | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/candidate_requirements.py` | 4 | JOB_PROXY | compliance_officer,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/candidates/acl.py` | 8 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/candidates/pipeline_overrides_api.py` | 10 | PORTAL_LEGACY | client_manager,client_processor | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/candidates/router.py` | 2 | JOB_PROXY | recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/candidates_delete.py` | 5 | JOB_PROXY,ORG_PROXY | administrator,recruiter,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/communications/routes/dispatch.py` | 2 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/communications/routes/planner.py` | 4 | JOB_PROXY,ORG_PROXY,PORTAL_LEGACY | administrator,client_manager,client_processor,recruiter,supervisor | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/company_module_settings.py` | 3 | ORG_PROXY | administrator,hr_officer,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/custom_fields.py` | 7 | ORG_PROXY | admin,administrator,recruiter,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/document_merge/router.py` | 4 | JOB_PROXY | compliance_officer,hr_officer,recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/document_policies.py` | 4 | ORG_PROXY | admin,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/documents.py` | 1 | JOB_PROXY | admin,manager,recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/funnels.py` | 1 | JOB_PROXY | admin,hr_officer,manager | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/global_search.py` | 4 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/handoffs.py` | 1 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/hr_dashboard.py` | 4 | ORG_PROXY | administrator,hr_officer,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/hr_inbox.py` | 8 | ORG_PROXY | administrator,hr_officer,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/next_actions.py` | 1 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/notifications.py` | 1 | ORG_PROXY | administrator,superadmin,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/own_companies.py` | 2 | ORG_PROXY | admin,administrator,manager,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/platform/acquisition_activity.py` | 4 | JOB_PROXY,PORTAL_LEGACY | administrator,client_manager,hr_officer,recruiter,superadmin,supervisor,viewer | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/platform/campaigns.py` | 5 | JOB_PROXY,PORTAL_LEGACY | administrator,client_manager,hr_officer,recruiter,superadmin,supervisor,viewer | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/platform/forms_builder.py` | 3 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/platform/marketing_diagnostics.py` | 4 | JOB_PROXY,PORTAL_LEGACY | administrator,client_manager,hr_officer,recruiter,superadmin,supervisor,viewer | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/platform/marketing_sources.py` | 5 | JOB_PROXY,ORG_PROXY,PORTAL_LEGACY | administrator,client_manager,hr_officer,recruiter,superadmin,supervisor,viewer | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/recruiters/router.py` | 1 | ORG_PROXY | admin,manager,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/services.py` | 12 | ORG_PROXY | administrator,recruiter,supervisor,viewer | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/billing/routes.py` | 3 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/communications.py` | 5 | JOB_PROXY,ORG_PROXY,PORTAL_LEGACY | administrator,client_manager,client_processor,recruiter,supervisor | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/settings/hiring_pipeline_gates_impl.py` | 3 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/settings/intake_forms.py` | 6 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/lead_forms.py` | 1 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/lead_lifecycle_email.py` | 1 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/leads.py` | 16 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/api/v1/settings/team.py` | 20 | JOB_PROXY,ORG_PROXY,PORTAL_LEGACY | administrator,client_manager,client_processor,compliance_officer,employee,hr_officer,manager,recruiter,supervisor,viewer | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/tenants/router.py` | 4 | JOB_PROXY | admin,compliance_officer,hr_officer,manager,owner,recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/tenants/service.py` | 24 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/vacancies/launch_search_setup_api.py` | 1 | JOB_PROXY | admin,manager,recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/vacancies/router.py` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | migrated |
| `backend/app/api/v1/workforce/router.py` | 6 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/api/v1/workforce/zus_workspace_router.py` | 1 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | migrated |
| `backend/app/auth/deps.py` | 11 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/auth/fleet_access.py` | 4 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/auth/hiring_workspace_roles.py` | 8 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/auth/module_gate.py` | 6 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/auth/router.py` | 7 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/db/seeds/recruitment_team_flow_scenario.py` | 3 | JOB_PROXY | hr_officer,recruiter | employee + permission/module gate + preset | open |
| `backend/app/jobs/hr_operational_alerts_dispatch.py` | 2 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | open |
| `backend/app/modules/applications/router.py` | 14 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/modules/client_accounts/router.py` | 5 | ORG_PROXY | admin,manager,recruiter,supervisor,viewer | employee + supervisor_id/org + permission | migrated |
| `backend/app/modules/companies/router.py` | 16 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/modules/documents/router.py` | 1 | ORG_PROXY | administrator,supervisor | employee + supervisor_id/org + permission | migrated |
| `backend/app/modules/leads/next_action_api.py` | 1 | JOB_PROXY | admin,manager,recruiter,viewer | employee + permission/module gate + preset | migrated |
| `backend/app/modules/leads/router.py` | 27 | JOB_PROXY,ORG_PROXY | admin,manager,recruiter,supervisor,viewer | employee + supervisor_id/org + permission | migrated |
| `backend/app/modules/sales_orders/router.py` | 2 | ORG_PROXY | admin,manager,recruiter,supervisor,viewer | employee + supervisor_id/org + permission | migrated |
| `backend/app/modules/vacancies/router.py` | 5 | ORG_PROXY | administrator,recruiter,supervisor,viewer | employee + supervisor_id/org + permission | migrated |
| `backend/app/services/candidate_deletion.py` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `backend/app/services/document_dossier_access.py` | 6 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/services/global_search_v1.py` | 2 | PORTAL_LEGACY | client_manager,client_processor | viewer + access_context=portal + scope | migrated |
| `backend/app/services/handoff.py` | 2 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | open |
| `backend/app/services/handoff_snapshot_acl.py` | 5 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter | viewer + access_context=portal + scope | migrated |
| `backend/app/services/hr_operational_alerts.py` | 1 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | open |
| `backend/app/services/lead_distribution.py` | 2 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `backend/app/services/recruiter_assignment.py` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `backend/app/services/recruitment_lead_assignee.py` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `backend/app/services/stage_meta_recruitment_filter.py` | 6 | JOB_PROXY,PORTAL_LEGACY | client_manager,client_processor,hr_officer | viewer + access_context=portal + scope | migrated |
| `backend/app/services/users.py` | 30 | JOB_PROXY,PORTAL_LEGACY,SEAT | client_manager,client_processor,compliance_officer,hr_officer,recruiter | trust seats + portal non-billable | migrated |
| `hostflow-frontend/src/api/analytics.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/billing.ts` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/api/client.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/communications.ts` | 1 | PORTAL_LEGACY | client_manager,client_processor,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/api/types.ts` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/api/types/document.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/types/index.ts` | 1 | UI_ONLY | roles | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/api/types/user.ts` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/api/users.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/admin/RoleModuleMatrixPanel.tsx` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/components/admin/UserFormCreate.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/components/admin/UserFormInvite.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/components/admin/UserTable.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/components/candidate/CandidateDocsRailPanel.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/communications/CommunicationsInboxWorkflowCard.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/companies/CompanyModuleSettingsPanel.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/hr/EmployeeDossierDocumentBlock.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/EmployeeLinkedCandidateJourney.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/HrDocumentCorrectionForm.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/HrSequentialDocumentVerification.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/nav/Sidebar.tsx` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/components/nav/Topbar.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/vacancy/useVacancyNextAction.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/constants/communicationsSettingsAccess.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/content/seo/seoPageCatalog.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/contexts/TeamOverviewNavContext.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/hooks/useLicenseStatus.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/hooks/useOwnCompanyWorkspace.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/hooks/usePermissions.ts` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/modules/candidates/hooks/useCandidatesCatalogs.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/candidates/internal.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/dashboard/hooks/useDashboardRiskOps.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/documents/CandidateDocuments.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/tenants/utils.ts` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/modules/users/constants.ts` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/modules/workHub/HandoffQueuePanel.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/modules/workHub/ManagerLoadPanel.tsx` | 1 | PORTAL_LEGACY | client_manager,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/modules/workHub/MyTasksPanel.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/workHub/RiskDigestPanel.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/workHub/TodayPlannerPanel.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/workHub/profile.ts` | 1 | PORTAL_LEGACY | client_manager,client_processor,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/pages/AutomationRulesPage.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/pages/CandidateCard.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/CommunicationsInboxHubPage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/MyCompanyPage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/Pipeline.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/pages/ProfilePage.tsx` | 2 | ORG_PROXY,SEAT | client_manager,supervisor | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/pages/RemindersPage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/WorkHubPage.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/BillingTeamPage.tsx` | 2 | PORTAL_LEGACY,SEAT | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | trust seats + portal non-billable | migrated |
| `hostflow-frontend/src/pages/admin/BillingWorkspacePage.tsx` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/pages/admin/DeletionRequestsPage.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/MetaLeadsAdminPage.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/pages/admin/RiskIntelSettingsPage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/RolesAccessPage.tsx` | 1 | UI_ONLY | client_manager | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/pages/admin/SettingsLandingPage.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/pages/admin/TenantsPage.tsx` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | migrated |
| `hostflow-frontend/src/pages/admin/UsersPage.tsx` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/platform/detail-rail/detailRailTypes.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/utils/hrDocumentReviewRole.ts` | 1 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | open |

## Status workflow

`open` → `aliased` (normalize live) → `migrated` → `removed`.

### Slice progress (auth gates — PR follow-up to ADR-036)

Migrated (runtime bridges + trust-aware ACL/gates):

- `backend/app/auth/deps.py` — `require_roles` uses `actor_satisfies_role_allowlist` (employee ↔ JOB_PROXY; viewer+portal ↔ PORTAL_LEGACY)
- `backend/app/auth/trust_roles.py` — `actor_satisfies_role_allowlist`, `is_portal_actor`, `is_hr_workspace_actor`, `is_team_lead_org_actor`
- `backend/app/auth/hiring_workspace_roles.py` — canonical `employee` / `viewer` in hiring role tuples
- `backend/app/auth/fleet_access.py` — trust allowlist + bridges
- `backend/app/auth/module_gate.py` — portal via `access_context`; employee write fallback; team-lead org bypass
- `backend/app/api/v1/candidates/acl.py` — trust/org/hr helpers; subordinates include `employee`

### Slice progress (require_roles → trust deps — this PR)

- `backend/app/auth/trust_role_deps.py` — `require_trust_read/write/admin`, `require_trust_write_or_portal`, `require_portal_context`
- Backend router/module `require_roles(job/portal…)` call sites rewritten to trust deps
- HR workspace routes: trust write + `require_hr_workforce_module_access` (module matrix permission)
- Services ACL helpers: dossier / handoff snapshot / global search / stage meta / handoff lock override

### Slice progress (Users UI + presets)

- Users create/invite/detail assign only Administrator / Employee / Viewer
- Job titles are `permission presets` applied as user_overrides (or Employee matrix column)
- APIs: `GET/POST /settings/team/permission-presets…`, create/invite/role accept `preset_id`

### Slice progress (seats / portal)

- Billable seats: Administrator (`max_supervisors`) / Employee (`max_recruiters`) / Viewer (`max_viewers`)
- Portal guests (`client_*` or `access_context=portal` / `preset_id=portal_guest`) are **non-billable**
- Usage API exposes `administrator_count` / `employee_count` / `portal_guest_count` (+ legacy aliases)
- JWT carries `access_context` from user preferences

Still `open` (next RBAC PRs): FE leftover job-role checks outside Users/Billing; enum delete; seed/job role strings; license column rename (optional).

## DB appendix

```sql
SELECT role, count(*) FROM users GROUP BY 1 ORDER BY 2 DESC;
```
Record counts in Phase 2 PR description.
