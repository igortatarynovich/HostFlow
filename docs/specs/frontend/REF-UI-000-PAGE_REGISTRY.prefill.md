# REF-UI-000 — PAGE_REGISTRY (Prefill from frontend routes)

Source: `src/app/routes.tsx` + explicit public/auth routes in `src/App.tsx`

| page_id | route | module | layout_type | owner | status | canonical_match | notes |
|---|---|---|---|---|---|---|---|
| marketing_root | / | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | CrmLandingPage (ADR-034 Growth) |
| marketing_faq | /faq | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | FaqPage (sectional FAQ + JSON-LD) |
| marketing_docs | /docs | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | DocsHubPage (Phase 5) |
| marketing_docs_slug | /docs/:slug | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | DocsArticlePage (Phase 5) |
| marketing_academy | /academy | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | AcademyPage (Phase 5) |
| marketing_demo | /demo | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | DemoPage (Demo Wave-1) |
| not-found | /app/* | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | NotFoundRedirect |
| activities-legacy | /app/activities | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | LegacyActivitiesRedirect |
| analytics | /app/analytics | Overview | UTILITY_LAYOUT_V1 | Product | Candidate | n/a | RedirectLegacyAnalyticsToInsights |
| analytics-lead-conversion | /app/analytics/lead-conversion | Overview | UTILITY_LAYOUT_V1 | Product | Candidate | n/a | RedirectLeadConversionFunnelToInsights |
| automation-log | /app/automation-log | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | AutomationLogPage |
| automation-rules | /app/automation-rules | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | AutomationRulesPage |
| automations | /app/automations | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | AutomationsHubPage |
| calendar | /app/calendar | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommFeature(CommunicationsCalendarPage |
| candidates | /app/candidates | Recruitment | LIST_LAYOUT_V1 | Recruitment | Candidate | 100% | Candidates |
| candidate-detail | /app/candidates/:id | Recruitment | ENTITY_LAYOUT_V1 | Recruitment | Candidate | 100% | CandidateCard |
| candidate-tab | /app/candidates/:id/:tab | Recruitment | ENTITY_LAYOUT_V1 | Recruitment | Candidate | 100% | CandidateCard |
| candidates-no-next-action | /app/candidates/no-next-action | Recruitment | UTILITY_LAYOUT_V1 | Recruitment | Candidate | n/a | CandidatesNoNextActionCanonicalRedirect |
| clients | /app/clients | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | AgencyClientsPage |
| client-detail | /app/clients/:id | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | Companies |
| client-tab | /app/clients/:id/:tab | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | Companies |
| clients-directory | /app/clients/directory | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | Companies |
| client-link-detail | /app/clients/link/:linkId | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | ClientLinkDetailPage |
| communications | /app/communications | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | LegacyCommunicationsRedirect |
| command-audit | /app/communications/command-audit | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommFeature(CommunicationsCommandAuditPage |
| communications-thread | /app/communications/threads/:threadId | Operations | DETAIL_LAYOUT_V1 | Operations | Candidate | 70% | withCommAnyFeature(CommunicationsThreadPage |
| companies-legacy | /app/companies | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | LegacyCompaniesRedirect |
| company-detail-legacy | /app/companies/:id | Platform | DETAIL_LAYOUT_V1 | Platform | Candidate | 70% | LegacyCompanyDetailRedirect |
| company-tab-legacy | /app/companies/:id/:tab | Platform | DETAIL_LAYOUT_V1 | Platform | Candidate | 70% | LegacyCompanyDetailRedirect |
| do-procesowania-legacy | /app/do-procesowania | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | LegacyDoProcesowaniaRedirect |
| documents | /app/documents | Documents | WORKSPACE_LAYOUT_V1 | Document Operations | Candidate | 80% | DocumentsHubPage |
| email-inbox | /app/email | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommFeature(CommunicationsEmailInboxPage |
| fleet | /app/fleet | Fleet | WORKSPACE_LAYOUT_V1 | Fleet Ops | Candidate | 80% | FleetModulePage |
| fleet-drivers | /app/fleet/drivers | Fleet | WORKSPACE_LAYOUT_V1 | Fleet Ops | Candidate | 80% | FleetModulePage |
| fleet-operating-lines | /app/fleet/operating-lines | Fleet | WORKSPACE_LAYOUT_V1 | Fleet Ops | Candidate | 80% | FleetModulePage |
| fleet-trailers | /app/fleet/trailers | Fleet | WORKSPACE_LAYOUT_V1 | Fleet Ops | Candidate | 80% | FleetModulePage |
| fleet-vehicles | /app/fleet/vehicles | Fleet | WORKSPACE_LAYOUT_V1 | Fleet Ops | Candidate | 80% | FleetModulePage |
| hr-workspace | /app/hr | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrDashboardPage |
| hr-compliance | /app/hr/compliance | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrComplianceDocumentsPage |
| hr-employees | /app/hr/employees | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrEmployeesPage |
| hr-employee-detail | /app/hr/employees/:employeeId | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrEmployeeDetailPage |
| hr-handoff-detail | /app/hr/handoffs/:id | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrHandoffDetailPage |
| hr-inbox | /app/hr/inbox | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrInboxPage |
| hr-tasks | /app/hr/tasks | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrTasksPage |
| hr-zus-legacy-alias | /app/hr/zus | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | () => <Navigate to={CRM.hrZusWorkspace |
| hr-zus-workspace | /app/hr/zus-workspace | HR | HR_WORKSPACE_LAYOUT_V1 | HR Operations | Candidate | 75% | HrZusWorkspacePage |
| communications-inbox-hub | /app/inbox | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommAnyFeature(CommunicationsInboxHubPage |
| communications-inbox-center | /app/inbox/threads/:threadId | Operations | DETAIL_LAYOUT_V1 | Operations | Candidate | 70% | withCommAnyFeature(CommunicationsInboxCenterPage |
| invoices | /app/invoices | FinanceOps | WORKSPACE_LAYOUT_V1 | Finance Operations | Candidate | 80% | InvoicesPage |
| invoice-detail | /app/invoices/:id | FinanceOps | WORKSPACE_LAYOUT_V1 | Finance Operations | Candidate | 80% | InvoiceDetailPage |
| invoice-edit | /app/invoices/:id/edit | FinanceOps | WORKSPACE_LAYOUT_V1 | Finance Operations | Candidate | 80% | InvoiceCreatePage |
| invoice-create | /app/invoices/new | FinanceOps | WORKSPACE_LAYOUT_V1 | Finance Operations | Candidate | 80% | InvoiceCreatePage |
| leads | /app/leads | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | LeadsPage |
| lead-detail | /app/leads/:leadId | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | LeadDetailPage |
| leads-distribution | /app/leads/distribution | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | LeadsDistributionPage |
| leads-distribution-rules | /app/leads/distribution/rules | Recruitment | WORKSPACE_LAYOUT_V1 | Recruitment | Candidate | 80% | LeadsDistributionRulesPage |
| messages-inbox | /app/messages | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommFeature(CommunicationsMessagesPage |
| my-availability | /app/my-availability | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | withCommFeature(MyAvailabilityPage |
| my-company | /app/my-company | Company | UTILITY_LAYOUT_V1 | Company Operations | Candidate | n/a | MyCompanyPage |
| my-company-detail | /app/my-company/:id | Company | DETAIL_LAYOUT_V1 | Company Operations | Candidate | 70% | Companies |
| my-company-tab | /app/my-company/:id/:tab | Company | DETAIL_LAYOUT_V1 | Company Operations | Candidate | 70% | Companies |
| orders | /app/orders | FinanceOps | UTILITY_LAYOUT_V1 | Finance Operations | Candidate | n/a | OrdersStandaloneRedirect |
| overview | /app/overview | Overview | DASHBOARD_LAYOUT_V1 | Product | Candidate | n/a | Dashboard |
| pipeline | /app/pipeline | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | PipelineRedirect |
| planner-legacy | /app/planner | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | LegacyPlannerRedirect |
| procesowani | /app/procesowani | Recruitment | UTILITY_LAYOUT_V1 | Recruitment | Candidate | n/a | DoProcesowaniaPage |
| profile | /app/profile | Account | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | ProfilePage |
| reminders-legacy | /app/reminders | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | LegacyRemindersRedirect |
| services | /app/services | FinanceOps | WORKSPACE_LAYOUT_V1 | Finance Operations | Candidate | 80% | ServicesPage |
| settings | /app/settings | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | SettingsLandingPage |
| settings-audit | /app/settings/audit | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | AuditLogPage |
| settings-billing | /app/settings/billing | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | BillingWorkspacePage |
| settings-candidate-profiles | /app/settings/candidate-profiles | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | CandidateProfilesPage |
| settings-communications | /app/settings/communications | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | withCommFeature(CommunicationsSettingsPage |
| settings-communications-messengers | /app/settings/communications/messengers | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | withCommFeature(CommunicationsMessengerSettingsPage |
| settings-communications-queue | /app/settings/communications/queue | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | withCommFeature(CommunicationsQueueSettingsPage |
| settings-communications-sla | /app/settings/communications/sla | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | withCommFeature(CommunicationsSlaSettingsPage |
| settings-company-access | /app/settings/company-access | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | CompanyAccessPage |
| settings-custom-fields | /app/settings/custom-fields | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | CustomFieldsPage |
| settings-docs | /app/settings/docs | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | DocumentTypesPage |
| settings-email | /app/settings/email | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | EmailSettingsPage |
| settings-funnels | /app/settings/funnels | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | FunnelsPage |
| settings-hiring-pipeline-gates | /app/settings/hiring-pipeline-gates | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | HiringPipelineGatesSettingsPage |
| settings-integrations | /app/settings/integrations | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | IntegrationsHubPage |
| settings-integrations-google | /app/settings/integrations/google | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | IntegrationsSourcePlaceholderPage |
| settings-integrations-messenger-channel | /app/settings/integrations/messenger/:messengerChannel | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | withCommFeature(MessengerIntegrationChannelPage |
| settings-integrations-meta | /app/settings/integrations/meta | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | MetaLeadsAdminPage |
| settings-integrations-webhook | /app/settings/integrations/webhook | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | IntegrationsWebhookPage |
| settings-lead-forms | /app/settings/lead-forms | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | LeadFormsSettingsPage |
| settings-leads-alias | /app/settings/leads | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | LegacySettingsLeadsToMetaRedirect |
| settings-legal | /app/settings/legal | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | LegalDocumentsPage |
| settings-message-templates | /app/settings/message-templates | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | LeadMessageTemplatesPage |
| settings-risk-intel | /app/settings/risk-intel | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | RiskIntelSettingsPage |
| settings-ruleset | /app/settings/ruleset | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | RulesetVersionsPage |
| settings-tenant-links | /app/settings/tenant-links | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | TenantLinksSettingsPage |
| settings-tenants | /app/settings/tenants | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | TenantsPage |
| settings-ttv-report | /app/settings/ttv-report | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | TtvReportPage |
| settings-users | /app/settings/users | Admin | SETTINGS_LAYOUT_V1 | Platform Admin | Candidate | 90% | UsersPage |
| communications-setup | /app/setup/communications | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | withCommAnyFeature(RedirectSetupCommunicationsToIntegrations |
| sla-incidents | /app/sla-incidents | Operations | UTILITY_LAYOUT_V1 | Operations | Candidate | n/a | withCommAnyFeature(CommunicationsSlaIncidentsPage |
| team-availability | /app/team-availability | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | withCommFeature(TeamAvailabilityPage |
| time-off | /app/time-off | Platform | UTILITY_LAYOUT_V1 | Platform | Candidate | n/a | withCommFeature(TimeOffRequestsPage |
| vacancies | /app/vacancies | Recruitment | LIST_LAYOUT_V1 | Recruitment | Candidate | 100% | Vacancies |
| vacancy-detail | /app/vacancies/:id | Recruitment | ENTITY_LAYOUT_V1 | Recruitment | Candidate | 100% | VacancyDetailRoute |
| vacancy-tab | /app/vacancies/:id/:tab | Recruitment | ENTITY_LAYOUT_V1 | Recruitment | Candidate | 100% | VacancyDetailRoute |
| work | /app/work | Operations | WORKSPACE_LAYOUT_V1 | Operations | Candidate | 80% | WorkHubPage |
| tasks | /app/work/tasks | Operations | WORKSPACE_LAYOUT_V1 | Operations | Candidate | 80% | RemindersPage |
| clientportal_client-portal | /client-portal | ClientPortal | PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | LazyRoute |
| marketing_comparison_hostflow-vs-spreadsheets | /comparison/hostflow-vs-spreadsheets | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | ComparisonHostflowVsSpreadsheetsPage |
| marketing_comparison_recruitment-crm-vs-ats | /comparison/recruitment-crm-vs-ats | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | ComparisonRecruitmentCrmVsAtsPage |
| marketing_features_candidate-pipeline | /features/candidate-pipeline | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | FeatureCandidatePipelinePage |
| marketing_features_document-control | /features/document-control | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | FeatureDocumentControlPage |
| auth_forgot-password | /forgot-password | Auth | AUTH_LAYOUT_V1 | Platform | Candidate | n/a | ForgotPasswordPage |
| auth_invite_accept | /invite/accept | Auth | AUTH_LAYOUT_V1 | Platform | Candidate | n/a | InviteAcceptPage |
| auth_login | /login | Auth | AUTH_LAYOUT_V1 | Platform | Candidate | n/a | Login |
| marketing_pricing | /pricing | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | CrmLandingPage |
| public_public | /public | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | Navigate |
| public_public_apply-old_token | /public/apply-old/:token | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | Navigate → /public/apply/:token (ADR-034) |
| public_public_apply_token | /public/apply/:token | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | LazyRoute |
| public_public_documents_token | /public/documents/:token | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | LazyRoute |
| public_public_intake | /public/intake | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | PublicIntakeStart |
| public_public_portal | /public/portal | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | PublicPortalLanding |
| public_public_scan | /public/scan | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | Navigate |
| public_public_scan-sessions | /public/scan-sessions | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | Navigate |
| public_public_status_token | /public/status/:token | Public | PUBLIC_PORTAL_LAYOUT_V1 | Platform | Candidate | n/a | LazyRoute |
| auth_reset-password | /reset-password | Auth | AUTH_LAYOUT_V1 | Platform | Candidate | n/a | ResetPasswordPage |
| auth_signup | /signup | Auth | AUTH_LAYOUT_V1 | Platform | Candidate | n/a | SignupPage |
| marketing_use-cases_high-volume-onboarding | /use-cases/high-volume-onboarding | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | UseCaseHighVolumeOnboardingPage |
| marketing_use-cases_trucking-recruitment | /use-cases/trucking-recruitment | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | UseCaseTruckingRecruitmentPage |
| marketing_use-cases_recruitment-agencies | /use-cases/recruitment-agencies | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_use-cases_transport-companies | /use-cases/transport-companies | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_use-cases_driver-recruitment | /use-cases/driver-recruitment | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_features_whatsapp-recruitment | /features/whatsapp-recruitment | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_features_meta-ads-recruitment | /features/meta-ads-recruitment | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_use-cases_ats-for-drivers | /use-cases/ats-for-drivers | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_use-cases_ats-for-transport | /use-cases/ats-for-transport | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
| marketing_use-cases_ats-europe | /use-cases/ats-europe | Marketing | MARKETING_LAYOUT_V1 | Growth | Candidate | n/a | SeoCatalogPage (Wave-2) |
