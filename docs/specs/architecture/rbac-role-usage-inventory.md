# RBAC role usage inventory (ADR-036 migration gate)

**Status:** NORMATIVE checklist (L2) — gate before Phase 2 runtime delete of legacy role branches  
**Parent:** [`ADR-036-four-trust-roles-rbac.md`](ADR-036-four-trust-roles-rbac.md) · [`rbac_matrix.md`](rbac_matrix.md)  
**Full machine dump:** [`scripts/rbac/role_usage_inventory.csv`](../../../scripts/rbac/role_usage_inventory.csv)  
**Scanner:** [`scripts/rbac/scan_role_usage.py`](../../../scripts/rbac/scan_role_usage.py)

## Summary

- Auto-collected call sites: **531** (see CSV)
- Distinct High-risk paths: **52**
- By class: `ALIAS`=7, `DOC`=36, `JOB_PROXY`=23, `ORG_PROXY`=12, `PORTAL_LEGACY`=5, `SEAT`=7, `TEST`=56, `TRUST`=372, `UI_ONLY`=13

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
| `hostflow-frontend/src/api/analytics.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/billing.ts` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/api/client.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/communications.ts` | 1 | PORTAL_LEGACY | client_manager,client_processor,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/api/types.ts` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/api/types/document.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/api/types/index.ts` | 1 | UI_ONLY | roles | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/api/types/user.ts` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/api/users.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/auth/trustRoles.ts` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/components/admin/RoleModuleMatrixPanel.tsx` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/components/admin/UserFormCreate.tsx` | 1 | UI_ONLY | recruiter | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/components/admin/UserFormInvite.tsx` | 1 | UI_ONLY | recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/components/admin/UserTable.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/components/candidate/CandidateDocsRailPanel.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/communications/CommunicationsInboxWorkflowCard.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/companies/CompanyModuleSettingsPanel.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/components/hr/EmployeeDossierDocumentBlock.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/EmployeeLinkedCandidateJourney.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/HrDocumentCorrectionForm.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/hr/HrSequentialDocumentVerification.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/vacancies/VacancyDetail.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/vacancies/detail/workspace/AttentionPanel.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/components/vacancy/useVacancyNextAction.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/constants/communicationsSettingsAccess.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/content/seo/seoPageCatalog.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/hooks/usePermissions.ts` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/modules/candidates/hooks/useCandidatesCatalogs.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/candidates/internal.ts` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/dashboard/hooks/useDashboardRiskOps.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/documents/CandidateDocuments.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/tenants/utils.ts` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/modules/users/constants.ts` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/modules/users/roleOptions.ts` | 1 | UI_ONLY | recruiter | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/modules/workHub/HandoffQueuePanel.tsx` | 1 | PORTAL_LEGACY | client_manager,client_processor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/modules/workHub/ManagerLoadPanel.tsx` | 1 | PORTAL_LEGACY | client_manager,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/modules/workHub/MyTasksPanel.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/workHub/RiskDigestPanel.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/modules/workHub/TodayPlannerPanel.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/modules/workHub/profile.ts` | 1 | PORTAL_LEGACY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | viewer + access_context=portal + scope | open |
| `hostflow-frontend/src/pages/AutomationRulesPage.tsx` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/pages/ProfilePage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/WorkHubPage.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/BillingTeamPage.tsx` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/pages/admin/BillingWorkspacePage.tsx` | 1 | SEAT | client_manager | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/pages/admin/DeletionRequestsPage.tsx` | 1 | ORG_PROXY | recruiter,supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/RiskIntelSettingsPage.tsx` | 1 | ORG_PROXY | supervisor | employee + supervisor_id/org + permission | open |
| `hostflow-frontend/src/pages/admin/RolesAccessPage.tsx` | 1 | UI_ONLY | recruiter | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/pages/admin/TenantsPage.tsx` | 2 | SEAT,UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | recount seats Admin/Employee/Viewer | open |
| `hostflow-frontend/src/pages/admin/UsersPage.tsx` | 1 | UI_ONLY | client_manager,client_processor,compliance_officer,hr_officer,recruiter,supervisor | align FE with BE trust + permissions | open |
| `hostflow-frontend/src/platform/detail-rail/detailRailTypes.ts` | 1 | JOB_PROXY | recruiter | employee + permission/module gate + preset | open |
| `hostflow-frontend/src/utils/hrDocumentReviewRole.ts` | 1 | JOB_PROXY | hr_officer | employee + permission/module gate + preset | open |

## Status workflow

`open` → `aliased` (normalize live) → `migrated` → `removed`.

## DB appendix

```sql
SELECT role, count(*) FROM users GROUP BY 1 ORDER BY 2 DESC;
```
Record counts in Phase 2 PR description.
