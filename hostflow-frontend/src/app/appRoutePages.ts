/**
 * Lazy `/app/*` via shared bundles. Candidates list vs CandidateCard = separate Rollup chunks
 * (avoids OOM when rendering one giant CRM graph on small VPS).
 */
import { lazy } from 'react'

const loadCrmCore = () => import('./routeBundles/routeBundleCrmCore')
const loadCrmServices = () => import('./routeBundles/routeBundleServices')
const loadCrmMore = () => import('./routeBundles/routeBundleCrmMore')
const loadCandidatesList = () => import('./routeBundles/routeBundleCandidatesList')
const loadCandidateCard = () => import('./routeBundles/routeBundleCandidateCard')
const loadInvoices = () => import('./routeBundles/routeBundleInvoices')
const loadComms = () => import('./routeBundles/routeBundleComms')
const loadAdmin = () => import('./routeBundles/routeBundleAdmin')

export const Dashboard = lazy(() => loadCrmCore().then((m) => ({ default: m.Dashboard })))
export const Candidates = lazy(() => loadCandidatesList().then((m) => ({ default: m.Candidates })))
export const CandidateCard = lazy(() => loadCandidateCard().then((m) => ({ default: m.CandidateCard })))
export const CandidatesNoNextActionPage = lazy(() =>
  loadCandidatesList().then((m) => ({ default: m.CandidatesNoNextActionPage })),
)
export const Companies = lazy(() => loadCrmCore().then((m) => ({ default: m.Companies })))
export const MyCompanyPage = lazy(() => loadCrmCore().then((m) => ({ default: m.MyCompanyPage })))
export const Vacancies = lazy(() => loadCrmCore().then((m) => ({ default: m.Vacancies })))
export const VacancyDetailRoute = lazy(() => loadCrmCore().then((m) => ({ default: m.VacancyDetailRoute })))
export const ServicesPage = lazy(() => loadCrmServices().then((m) => ({ default: m.ServicesPage })))
export const LeadsPage = lazy(() => loadCrmMore().then((m) => ({ default: m.LeadsPage })))
export const ProfilePage = lazy(() => loadCrmCore().then((m) => ({ default: m.ProfilePage })))
export const RemindersPage = lazy(() => loadCrmCore().then((m) => ({ default: m.RemindersPage })))
export const ActivitiesPage = lazy(() => loadCrmCore().then((m) => ({ default: m.ActivitiesPage })))
export const AgencyClientsPage = lazy(() => loadCrmCore().then((m) => ({ default: m.AgencyClientsPage })))
export const ClientLinkDetailPage = lazy(() => loadCrmCore().then((m) => ({ default: m.ClientLinkDetailPage })))
export const DoProcesowaniaPage = lazy(() => loadCrmCore().then((m) => ({ default: m.DoProcesowaniaPage })))
export const DocumentsRegistryPage = lazy(() => loadCrmMore().then((m) => ({ default: m.DocumentsRegistryPage })))
export const AutomationLogPage = lazy(() => loadCrmMore().then((m) => ({ default: m.AutomationLogPage })))
export const AutomationRulesPage = lazy(() => loadCrmMore().then((m) => ({ default: m.AutomationRulesPage })))

export const InvoicesPage = lazy(() => loadInvoices().then((m) => ({ default: m.InvoicesPage })))
export const InvoiceCreatePage = lazy(() => loadInvoices().then((m) => ({ default: m.InvoiceCreatePage })))
export const InvoiceDetailPage = lazy(() => loadInvoices().then((m) => ({ default: m.InvoiceDetailPage })))

export const CommunicationsThreadPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsThreadPage })),
)
export const CommunicationsMessagesPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsMessagesPage })),
)
export const CommunicationsEmailInboxPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsEmailInboxPage })),
)
export const CommunicationsCalendarPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsCalendarPage })),
)
export const CommunicationsPlannerPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsPlannerPage })),
)
export const CommunicationsSlaIncidentsPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsSlaIncidentsPage })),
)
export const CommunicationsSetupPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsSetupPage })),
)
export const CommunicationsCommandAuditPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsCommandAuditPage })),
)
export const TeamAvailabilityPage = lazy(() => loadComms().then((m) => ({ default: m.TeamAvailabilityPage })))
export const MyAvailabilityPage = lazy(() => loadComms().then((m) => ({ default: m.MyAvailabilityPage })))
export const TimeOffRequestsPage = lazy(() => loadComms().then((m) => ({ default: m.TimeOffRequestsPage })))
export const CommunicationsSettingsPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsSettingsPage })),
)
export const CommunicationsMessengerSettingsPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsMessengerSettingsPage })),
)
export const CommunicationsQueueSettingsPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsQueueSettingsPage })),
)
export const CommunicationsSlaSettingsPage = lazy(() =>
  loadComms().then((m) => ({ default: m.CommunicationsSlaSettingsPage })),
)

export const UsersPage = lazy(() => loadAdmin().then((m) => ({ default: m.UsersPage })))
export const TenantsPage = lazy(() => loadAdmin().then((m) => ({ default: m.TenantsPage })))
export const RulesetVersionsPage = lazy(() => loadAdmin().then((m) => ({ default: m.RulesetVersionsPage })))
export const MetaLeadsAdminPage = lazy(() => loadAdmin().then((m) => ({ default: m.MetaLeadsAdminPage })))
export const DeletionRequestsPage = lazy(() => loadAdmin().then((m) => ({ default: m.DeletionRequestsPage })))
export const AuditLogPage = lazy(() => loadAdmin().then((m) => ({ default: m.AuditLogPage })))
export const TtvReportPage = lazy(() => loadAdmin().then((m) => ({ default: m.TtvReportPage })))
export const SettingsLandingPage = lazy(() => loadAdmin().then((m) => ({ default: m.SettingsLandingPage })))
export const DocumentTypesPage = lazy(() => loadAdmin().then((m) => ({ default: m.DocumentTypesPage })))
export const CompanyAccessPage = lazy(() => loadAdmin().then((m) => ({ default: m.CompanyAccessPage })))
export const CandidateProfilesPage = lazy(() => loadAdmin().then((m) => ({ default: m.CandidateProfilesPage })))
export const FunnelsPage = lazy(() => loadAdmin().then((m) => ({ default: m.FunnelsPage })))
export const HiringPipelineGatesSettingsPage = lazy(() =>
  loadAdmin().then((m) => ({ default: m.HiringPipelineGatesSettingsPage })),
)
export const CustomFieldsPage = lazy(() => loadAdmin().then((m) => ({ default: m.CustomFieldsPage })))
export const BillingWorkspacePage = lazy(() => loadAdmin().then((m) => ({ default: m.BillingWorkspacePage })))
export const EmailSettingsPage = lazy(() => loadAdmin().then((m) => ({ default: m.EmailSettingsPage })))
export const TenantLinksSettingsPage = lazy(() => loadAdmin().then((m) => ({ default: m.TenantLinksSettingsPage })))
export const LegalDocumentsPage = lazy(() => loadAdmin().then((m) => ({ default: m.LegalDocumentsPage })))
