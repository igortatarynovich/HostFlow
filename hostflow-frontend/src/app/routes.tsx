import type { ComponentType } from 'react'
import { Navigate, useParams, useSearchParams } from 'react-router-dom'
import type { Permission } from '../hooks/usePermissions'
import CommunicationsFeatureGate from '../components/communications/CommunicationsFeatureGate'
import {
  AuditLogPage,
  AutomationsHubPage,
  AutomationLogPage,
  AutomationRulesPage,
  BillingWorkspacePage,
  CandidateCard,
  CandidateProfilesPage,
  Candidates,
  CommunicationsCalendarPage,
  CommunicationsCommandAuditPage,
  CommunicationsEmailInboxPage,
  CommunicationsInboxCenterPage,
  CommunicationsInboxHubPage,
  CommunicationsMessengerSettingsPage,
  CommunicationsMessagesPage,
  MessengerIntegrationChannelPage,
  CommunicationsQueueSettingsPage,
  CommunicationsSettingsPage,
  CommunicationsSlaIncidentsPage,
  NotificationAlertsPage,
  CommunicationsSlaSettingsPage,
  CommunicationsThreadPage,
  Companies,
  CompanyAccessPage,
  CustomFieldsPage,
  Dashboard,
  DeletionRequestsPage,
  DocumentTypesPage,
  DocumentsHubPage,
  EmailSettingsPage,
  FleetModulePage,
  FunnelsPage,
  HiringPipelineGatesSettingsPage,
  TransferPolicySettingsPage,
  HrComplianceDocumentsPage,
  HrDashboardPage,
  HrEmployeeDetailPage,
  HrEmployeesPage,
  HrHandoffDetailPage,
  HrInboxPage,
  HrTasksPage,
  HrZusWorkspacePage,
  HrWorkspaceLayout,
  RiskIntelSettingsPage,
  InvoiceCreatePage,
  InvoiceDetailPage,
  InvoicesPage,
  LeadDetailPage,
  LeadsPage,
  LeadsDistributionPage,
  LeadsDistributionRulesPage,
  LegalDocumentsPage,
  LeadFormsSettingsPage,
  IntakeFormDetailPage,
  FormsBuilderPage,
  LeadMessageTemplatesPage,
  IntegrationsHubPage,
  IntegrationsSourcePlaceholderPage,
  IntegrationsWebhookPage,
  MetaLeadsAdminPage,
  MyAvailabilityPage,
  MyCompanyPage,
  ProfilePage,
  RemindersPage,
  RulesetVersionsPage,
  ServicesPage,
  SettingsLandingPage,
  TeamAvailabilityPage,
  TenantLinksSettingsPage,
  TenantsPage,
  TimeOffRequestsPage,
  TtvReportPage,
  UsersPage,
  Vacancies,
  VacancyDetailRoute,
  WorkHubPage,
} from './appRoutePages'
import { CRM_APP_PATHS, crmAppRouteSegment } from './crmAppPaths'
import { SALES_HOME_PATH } from './salesPaths'
import { RECRUITMENT_INBOX_PATH } from './recruitmentInboxPaths'
import EntityListShellDemoPage from '../pages/dev/EntityListShellDemoPage'
import LaunchpadPage from '../pages/LaunchpadPage'
import SearchesListPage from '../pages/recruitment/SearchesListPage'
import ClientChannelsListPage from '../pages/client-acquisition/ClientChannelsListPage'

const seg = crmAppRouteSegment
const CRM = CRM_APP_PATHS

function RedirectSetupCommunicationsToIntegrations() {
  return <Navigate to={CRM_APP_PATHS.settingsIntegrations} replace />
}

function RedirectLegacyAnalyticsToInsights() {
  return <Navigate to={CRM.overview} replace />
}

function RedirectLeadConversionFunnelToInsights() {
  return <Navigate to={{ pathname: CRM.overview, hash: 'lead-conversion' }} replace />
}

/** §2.17.14 SSOT: `settingsLeads` is an alias; canonical Meta / lead-source admin is `settingsIntegrationsMeta`. */
function LegacySettingsLeadsToMetaRedirect() {
  return <Navigate to={CRM.settingsIntegrationsMeta} replace />
}

function ClientsRootRedirect() {
  return <Navigate to={CRM.clientsDirectory} replace />
}

function ClientNewRedirect() {
  return <Navigate to={`${CRM.clientsDirectory}?add=1`} replace />
}

function ClientLinkDetailRedirect() {
  const { linkId } = useParams<{ linkId: string }>()
  return <Navigate to={`${CRM.clientsDirectory}?link=${encodeURIComponent(linkId || '')}`} replace />
}

export type NavGroup = 'overview' | 'people' | 'workflows' | 'leads' | 'admin' | 'account'

type NavGroupConfig = { key: NavGroup; labelKey: string }

export const NAV_GROUPS: NavGroupConfig[] = [
  { key: 'overview', labelKey: 'app.nav.groups.overview' },
  { key: 'people', labelKey: 'app.nav.groups.people' },
  { key: 'workflows', labelKey: 'app.nav.groups.workflows' },
  { key: 'leads', labelKey: 'app.nav.groups.leads' },
  { key: 'admin', labelKey: 'app.nav.groups.admin' },
  { key: 'account', labelKey: 'app.nav.groups.account' },
]

export const NAV_GROUP_MAP = NAV_GROUPS.reduce<Record<NavGroup, NavGroupConfig>>((acc, item) => {
  acc[item.key] = item
  return acc
}, {} as Record<NavGroup, NavGroupConfig>)

export type NavItem = {
  key: string
  labelKey: string
  path?: string
  group: NavGroup
  permission?: Permission | Permission[]
  action?: 'logout'
  superadminOnly?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { key: 'launchpad', labelKey: 'app.nav.items.launchpad', path: CRM.launchpad, group: 'overview' },
  { key: 'overview', labelKey: 'app.nav.items.overview', path: CRM.overview, group: 'overview' },
  { key: 'work-hub', labelKey: 'app.nav.items.work', path: CRM.work, group: 'people' },
  {
    key: 'hr-workspace',
    labelKey: 'app.nav.items.hr_workspace',
    path: CRM.hr,
    group: 'people',
    permission: 'workforce.view',
  },
  {
    key: 'recruitment-searches',
    labelKey: 'app.nav.items.recruitment_searches',
    path: CRM.recruitmentSearches,
    group: 'people',
    permission: 'vacancies.view',
  },
  {
    key: 'recruitment-inbox',
    labelKey: 'app.nav.items.recruitment_inbox',
    path: RECRUITMENT_INBOX_PATH,
    group: 'people',
    permission: 'leads.view',
  },
  {
    key: 'sales',
    labelKey: 'app.nav.items.sales',
    path: SALES_HOME_PATH,
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'client-acquisition-channels',
    labelKey: 'app.nav.items.client_acquisition',
    path: CRM.clientAcquisitionChannels,
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'candidates',
    labelKey: 'app.nav.items.candidates',
    path: CRM.candidates,
    group: 'people',
    permission: 'candidates.view',
  },
  {
    key: 'candidates-no-next-action',
    labelKey: 'app.nav.items.no_next_action',
    path: CRM.candidatesNoNextActionPage,
    group: 'people',
    permission: 'candidates.view',
  },
  {
    key: 'my-company',
    labelKey: 'app.nav.items.my_company',
    path: CRM.myCompany,
    group: 'account',
    permission: 'companies.view',
  },
  {
    key: 'clients',
    labelKey: 'app.nav.items.clients',
    path: CRM.clientsDirectory,
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'vacancies',
    labelKey: 'app.nav.items.vacancies',
    path: CRM.vacancies,
    group: 'people',
    permission: 'vacancies.view',
  },
  {
    key: 'fleet',
    labelKey: 'app.nav.items.fleet',
    path: CRM.fleet,
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'documents',
    labelKey: 'app.nav.items.documents',
    path: CRM.documents,
    group: 'workflows',
    permission: ['documents.manage', 'workforce.view'],
  },
  {
    key: 'automations',
    labelKey: 'app.nav.items.automations',
    path: CRM.automations,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'automation-rules',
    labelKey: 'app.nav.items.automation_rules',
    path: CRM.automationRules,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'automation-log',
    labelKey: 'app.nav.items.automation_log',
    path: CRM.automationLog,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'service-orders',
    labelKey: 'app.nav.items.orders',
    path: CRM.orders,
    group: 'workflows',
    permission: 'services.view',
  },
  {
    key: 'services',
    labelKey: 'app.nav.items.services',
    path: CRM.services,
    group: 'workflows',
    permission: 'services.view',
  },
  {
    key: 'invoices',
    labelKey: 'app.nav.items.invoices',
    path: CRM.invoices,
    group: 'workflows',
    permission: 'services.view',
  },
  {
    key: 'inbox',
    labelKey: 'app.nav.items.inbox',
    path: CRM.inbox,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'tasks',
    labelKey: 'app.nav.items.tasks',
    path: CRM.tasks,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'notification-alerts',
    labelKey: 'app.nav.items.notification_alerts',
    path: CRM.notificationAlerts,
    group: 'workflows',
    permission: ['admin.users', 'settings.view', 'notifications.view'],
  },
  {
    key: 'calendar',
    labelKey: 'app.nav.items.calendar',
    path: CRM.calendar,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'team-availability',
    labelKey: 'app.nav.items.team_availability',
    path: CRM.teamAvailability,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'my-availability',
    labelKey: 'app.nav.items.my_availability',
    path: CRM.myAvailability,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'time-off',
    labelKey: 'app.nav.items.time_off',
    path: CRM.timeOff,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'sla-incidents',
    labelKey: 'app.nav.items.sla_incidents',
    path: CRM.slaIncidents,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'command-audit',
    labelKey: 'app.nav.items.command_audit',
    path: CRM.communicationsCommandAudit,
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'leads',
    labelKey: 'app.nav.items.leads',
    path: CRM.leads,
    group: 'leads',
    permission: 'leads.view',
  },
  {
    key: 'leads-distribution',
    labelKey: 'app.nav.items.leads_distribution',
    path: CRM.leadsDistribution,
    group: 'leads',
    permission: 'leads.view',
  },
  {
    key: 'leads-distribution-rules',
    labelKey: 'app.nav.items.leads_distribution_rules',
    path: CRM.leadsDistributionRules,
    group: 'leads',
    permission: 'leads.view',
  },
  {
    key: 'settings',
    labelKey: 'app.nav.items.settings',
    path: CRM.settings,
    group: 'admin',
    permission: 'settings.view',
  },
  {
    key: 'settings-users',
    labelKey: 'app.nav.items.settings_users',
    path: CRM.settingsUsers,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-billing',
    labelKey: 'app.nav.items.settings_billing',
    path: CRM.settingsBilling,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-tenants',
    labelKey: 'app.nav.items.settings_tenants',
    path: CRM.settingsTenants,
    group: 'admin',
    permission: 'admin.companyAcl',
    superadminOnly: true,
  },
  {
    key: 'settings-funnels',
    labelKey: 'app.nav.items.settings_funnels',
    path: CRM.settingsFunnels,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-hiring-gates',
    labelKey: 'app.nav.items.settings_hiring_gates',
    path: CRM.settingsHiringPipelineGates,
    group: 'admin',
    permission: 'settings.view',
  },
  {
    key: 'settings-risk-intel',
    labelKey: 'app.nav.items.settings_risk_intel',
    path: CRM.settingsRiskIntel,
    group: 'admin',
    permission: 'settings.view',
  },
  {
    key: 'settings-docs',
    labelKey: 'app.nav.items.settings_docs',
    path: CRM.settingsDocs,
    group: 'admin',
    permission: 'documents.manage',
  },
  {
    key: 'settings-candidate-profiles',
    labelKey: 'app.nav.items.settings_candidate_profiles',
    path: CRM.settingsCandidateProfiles,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-custom-fields',
    labelKey: 'app.nav.items.settings_custom_fields',
    path: CRM.settingsCustomFields,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-legal',
    labelKey: 'app.nav.items.settings_legal',
    path: CRM.settingsLegal,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-company-access',
    labelKey: 'app.nav.items.settings_company_access',
    path: CRM.settingsCompanyAccess,
    group: 'admin',
    permission: 'admin.companyAcl',
  },
  {
    key: 'settings-email',
    labelKey: 'app.nav.items.settings_email',
    path: CRM.settingsEmail,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-tenant-links',
    labelKey: 'app.nav.items.settings_tenant_links',
    path: CRM.settingsTenantLinks,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-integrations',
    labelKey: 'app.nav.items.settings_integrations',
    path: CRM.settingsIntegrations,
    group: 'workflows',
    permission: ['admin.metaLeads', 'admin.users', 'settings.view', 'notifications.view'],
  },
  {
    key: 'integrations-meta',
    labelKey: 'app.nav.integrations.meta_leads',
    path: CRM.settingsIntegrationsMeta,
    group: 'admin',
    permission: 'admin.metaLeads',
  },
  {
    key: 'integrations-google',
    labelKey: 'app.nav.integrations.google',
    path: CRM.settingsIntegrationsGoogle,
    group: 'admin',
    permission: 'admin.metaLeads',
  },
  {
    key: 'integrations-webhook',
    labelKey: 'app.nav.integrations.webhook',
    path: CRM.settingsIntegrationsWebhook,
    group: 'admin',
    permission: 'admin.metaLeads',
  },
  {
    key: 'settings-communications',
    labelKey: 'app.nav.items.settings_communications',
    path: CRM.settingsCommunications,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-communications-messengers',
    labelKey: 'app.nav.items.settings_communications_messengers',
    path: CRM.settingsCommunicationsMessengers,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-communications-queue',
    labelKey: 'app.nav.items.settings_communications_queue',
    path: CRM.settingsCommunicationsQueue,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-communications-sla',
    labelKey: 'app.nav.items.settings_communications_sla',
    path: CRM.settingsCommunicationsSla,
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-ruleset',
    labelKey: 'app.nav.items.settings_ruleset',
    path: CRM.settingsRuleset,
    group: 'admin',
    permission: 'admin.ruleset',
  },
  {
    key: 'settings-audit',
    labelKey: 'app.nav.items.settings_audit',
    path: CRM.settingsAudit,
    group: 'admin',
    permission: 'admin.deletionQueue',
  },
  { key: 'profile', labelKey: 'app.nav.items.profile', path: CRM.profile, group: 'account' },
  { key: 'logout', labelKey: 'app.nav.items.logout', group: 'account', action: 'logout' },
]

const PipelineRedirect = () => <Navigate to="candidates?view=kanban" replace />
const NotFoundRedirect = () => <Navigate to="overview" replace />
const ProcesowaniRetiredRedirect = () => <Navigate to={CRM.candidates} replace />
const LegacyCommunicationsRedirect = () => <Navigate to="../settings/communications" replace />
const LegacyRemindersRedirect = () => <Navigate to="../tasks" replace />
const LegacyActivitiesRedirect = () => <Navigate to="../tasks" replace />
const LegacyPlannerRedirect = () => <Navigate to="../calendar" replace />
const LegacyCompaniesRedirect = () => <Navigate to="../clients/directory" replace />
const LegacyCompanyDetailRedirect = () => {
  const { id, tab } = useParams<{ id?: string; tab?: string }>()
  if (!id) return <Navigate to="../clients/directory" replace />
  return <Navigate to={tab ? `../clients/${id}/${tab}` : `../clients/${id}`} replace />
}

/** Legacy bookmark: **`/app/candidates/no-next-action`** → main list with queue (§2.14). */
const CandidatesNoNextActionCanonicalRedirect = () => (
  <Navigate to={`${CRM.candidates}?queue=no_next_action`} replace />
)

/** Canonical first-class URL for Orders; same shell as Services → Orders (`ServicesPage`). */
const OrdersStandaloneRedirect = () => {
  const [searchParams] = useSearchParams()
  const next = new URLSearchParams(searchParams)
  next.set('tab', 'orders')
  return <Navigate to={`${CRM.services}?${next.toString()}`} replace />
}

function withCommFeature(Component: ComponentType, feature: Parameters<typeof CommunicationsFeatureGate>[0]['feature'], fallbackPath?: string): ComponentType {
  const Wrapped = () => (
    <CommunicationsFeatureGate feature={feature} fallbackPath={fallbackPath}>
      <Component />
    </CommunicationsFeatureGate>
  )
  return Wrapped
}

function withCommAnyFeature(Component: ComponentType, anyOf: NonNullable<Parameters<typeof CommunicationsFeatureGate>[0]['anyOf']>, fallbackPath?: string): ComponentType {
  const Wrapped = () => (
    <CommunicationsFeatureGate anyOf={anyOf} fallbackPath={fallbackPath}>
      <Component />
    </CommunicationsFeatureGate>
  )
  return Wrapped
}

export type AppRouteConfig = {
  key: string
  path: string
  Component: ComponentType
  permission?: Permission | Permission[]
}

export const APP_ROUTES: AppRouteConfig[] = [
  { key: 'launchpad', path: seg(CRM.launchpad), Component: LaunchpadPage },
  { key: 'overview', path: seg(CRM.overview), Component: Dashboard },
  {
    key: 'analytics',
    path: seg(CRM.analytics),
    Component: RedirectLegacyAnalyticsToInsights,
    permission: 'manager.tools',
  },
  {
    key: 'analytics-lead-conversion',
    path: seg(CRM.analyticsLeadConversionFunnel),
    Component: RedirectLeadConversionFunnelToInsights,
    permission: ['manager.tools', 'leads.view'],
  },
  /** Rendered under nested `path="work"` + index in `App.tsx` (`WorkAreaLayout` + `<Outlet />`). Kept here for nav/permission scripts. */
  { key: 'work', path: seg(CRM.work), Component: WorkHubPage },
  {
    key: 'recruitment-searches',
    path: seg(CRM.recruitmentSearches),
    Component: SearchesListPage,
    permission: 'vacancies.view',
  },
  {
    key: 'client-acquisition-channels',
    path: seg(CRM.clientAcquisitionChannels),
    Component: ClientChannelsListPage,
    permission: 'companies.view',
  },
  { key: 'my-company', path: seg(CRM.myCompany), Component: MyCompanyPage, permission: 'companies.view' },
  { key: 'my-company-detail', path: `${seg(CRM.myCompany)}/:id`, Component: Companies, permission: 'companies.view' },
  { key: 'my-company-tab', path: `${seg(CRM.myCompany)}/:id/:tab`, Component: Companies, permission: 'companies.view' },
  { key: 'candidates', path: seg(CRM.candidates), Component: Candidates, permission: 'candidates.view' },
  {
    key: 'candidates-no-next-action',
    path: seg(CRM.candidatesNoNextActionPage),
    Component: CandidatesNoNextActionCanonicalRedirect,
    permission: 'candidates.view',
  },
  { key: 'candidate-detail', path: `${seg(CRM.candidates)}/:id`, Component: CandidateCard, permission: 'candidates.view' },
  { key: 'candidate-tab', path: `${seg(CRM.candidates)}/:id/:tab`, Component: CandidateCard, permission: 'candidates.view' },
  { key: 'companies-legacy', path: seg(CRM.companiesLegacy), Component: LegacyCompaniesRedirect, permission: 'companies.view' },
  { key: 'client-new', path: seg(CRM.clientNew), Component: ClientNewRedirect, permission: 'companies.view' },
  { key: 'clients-directory', path: seg(CRM.clientsDirectory), Component: Companies, permission: 'companies.view' },
  { key: 'clients', path: seg(CRM.agencyClients), Component: ClientsRootRedirect, permission: 'companies.view' },
  { key: 'client-link-detail', path: `${seg(CRM.clientsLinkBase)}/:linkId`, Component: ClientLinkDetailRedirect, permission: 'companies.view' },
  { key: 'procesowani', path: seg(CRM.procesowani), Component: ProcesowaniRetiredRedirect, permission: 'companies.view' },
  { key: 'do-procesowania-legacy', path: seg(CRM.doProcesowaniaLegacy), Component: ProcesowaniRetiredRedirect, permission: 'companies.view' },
  { key: 'client-detail', path: `${seg(CRM.agencyClients)}/:id`, Component: Companies, permission: 'companies.view' },
  { key: 'client-tab', path: `${seg(CRM.agencyClients)}/:id/:tab`, Component: Companies, permission: 'companies.view' },
  { key: 'company-detail-legacy', path: `${seg(CRM.companiesLegacy)}/:id`, Component: LegacyCompanyDetailRedirect, permission: 'companies.view' },
  { key: 'company-tab-legacy', path: `${seg(CRM.companiesLegacy)}/:id/:tab`, Component: LegacyCompanyDetailRedirect, permission: 'companies.view' },
  { key: 'vacancies', path: seg(CRM.vacancies), Component: Vacancies, permission: 'vacancies.view' },
  { key: 'vacancy-detail', path: `${seg(CRM.vacancies)}/:id`, Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'vacancy-tab', path: `${seg(CRM.vacancies)}/:id/:tab`, Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'fleet', path: seg(CRM.fleet), Component: FleetModulePage, permission: 'companies.view' },
  {
    key: 'fleet-operating-lines',
    path: seg(CRM.fleetOperatingLines),
    Component: FleetModulePage,
    permission: 'companies.view',
  },
  { key: 'fleet-vehicles', path: seg(CRM.fleetVehicles), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'fleet-trailers', path: seg(CRM.fleetTrailers), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'fleet-drivers', path: seg(CRM.fleetDrivers), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'fleet-vehicles', path: seg(CRM.fleetVehicles), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'fleet-trailers', path: seg(CRM.fleetTrailers), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'fleet-drivers', path: seg(CRM.fleetDrivers), Component: FleetModulePage, permission: 'companies.view' },
  { key: 'documents', path: seg(CRM.documents), Component: DocumentsHubPage, permission: ['documents.manage', 'workforce.view'] },
  { key: 'orders', path: seg(CRM.orders), Component: OrdersStandaloneRedirect, permission: 'services.view' },
  { key: 'services', path: seg(CRM.services), Component: ServicesPage, permission: 'services.view' },
  { key: 'invoices', path: seg(CRM.invoices), Component: InvoicesPage, permission: 'services.view' },
  { key: 'invoice-create', path: seg(CRM.invoiceNew), Component: InvoiceCreatePage, permission: 'services.view' },
  { key: 'invoice-edit', path: `${seg(CRM.invoices)}/:id/edit`, Component: InvoiceCreatePage, permission: 'services.view' },
  { key: 'invoice-detail', path: `${seg(CRM.invoices)}/:id`, Component: InvoiceDetailPage, permission: 'services.view' },
  {
    key: 'communications-setup',
    path: seg(CRM.setupCommunications),
    Component: withCommAnyFeature(RedirectSetupCommunicationsToIntegrations, ['messages', 'email']),
    permission: 'notifications.view',
  },
  {
    key: 'communications-inbox-center',
    path: `${seg(CRM.inboxThreadsBase)}/:threadId`,
    Component: withCommAnyFeature(CommunicationsInboxCenterPage, ['messages', 'email']),
    permission: 'notifications.view',
  },
  {
    key: 'communications-inbox-hub',
    path: seg(CRM.inbox),
    Component: withCommAnyFeature(CommunicationsInboxHubPage, ['messages', 'email']),
    permission: 'notifications.view',
  },
  { key: 'messages-inbox', path: seg(CRM.messages), Component: withCommFeature(CommunicationsMessagesPage, 'messages'), permission: 'notifications.view' },
  { key: 'email-inbox', path: seg(CRM.email), Component: withCommFeature(CommunicationsEmailInboxPage, 'email'), permission: 'notifications.view' },
  { key: 'calendar', path: seg(CRM.calendar), Component: withCommFeature(CommunicationsCalendarPage, 'calendar'), permission: 'notifications.view' },
  { key: 'planner-legacy', path: seg(CRM.plannerLegacy), Component: LegacyPlannerRedirect, permission: 'notifications.view' },
  { key: 'sla-incidents', path: seg(CRM.slaIncidents), Component: withCommAnyFeature(CommunicationsSlaIncidentsPage, ['messages', 'email']), permission: 'notifications.view' },
  { key: 'command-audit', path: seg(CRM.communicationsCommandAudit), Component: withCommFeature(CommunicationsCommandAuditPage, 'communicationsAdmin'), permission: 'notifications.view' },
  { key: 'team-availability', path: seg(CRM.teamAvailability), Component: withCommFeature(TeamAvailabilityPage, 'teamAvailability'), permission: 'notifications.view' },
  { key: 'my-availability', path: seg(CRM.myAvailability), Component: withCommFeature(MyAvailabilityPage, 'myAvailability'), permission: 'notifications.view' },
  { key: 'time-off', path: seg(CRM.timeOff), Component: withCommFeature(TimeOffRequestsPage, 'timeOffRequests'), permission: 'notifications.view' },
  { key: 'communications', path: seg(CRM.communicationsLegacyHub), Component: LegacyCommunicationsRedirect, permission: 'notifications.view' },
  { key: 'communications-thread', path: `${seg(CRM.communicationsThreadsBase)}/:threadId`, Component: withCommAnyFeature(CommunicationsThreadPage, ['messages', 'email']), permission: 'notifications.view' },
  { key: 'tasks', path: seg(CRM.tasks), Component: RemindersPage, permission: 'notifications.view' },
  {
    key: 'notification-alerts',
    path: seg(CRM.notificationAlerts),
    Component: NotificationAlertsPage,
    permission: ['admin.users', 'settings.view', 'notifications.view'],
  },
  { key: 'reminders-legacy', path: seg(CRM.remindersLegacy), Component: LegacyRemindersRedirect, permission: 'notifications.view' },
  { key: 'activities-legacy', path: seg(CRM.activitiesLegacy), Component: LegacyActivitiesRedirect, permission: 'notifications.view' },
  {
    key: 'leads-distribution-rules',
    path: seg(CRM.leadsDistributionRules),
    Component: LeadsDistributionRulesPage,
    permission: 'leads.view',
  },
  {
    key: 'leads-distribution',
    path: seg(CRM.leadsDistribution),
    Component: LeadsDistributionPage,
    permission: 'leads.view',
  },
  { key: 'lead-detail', path: `${seg(CRM.leads)}/:leadId`, Component: LeadDetailPage, permission: 'leads.view' },
  { key: 'leads', path: seg(CRM.leads), Component: LeadsPage, permission: 'leads.view' },
  { key: 'automations', path: seg(CRM.automations), Component: AutomationsHubPage, permission: 'notifications.view' },
  { key: 'automation-log', path: seg(CRM.automationLog), Component: AutomationLogPage, permission: 'notifications.view' },
  { key: 'automation-rules', path: seg(CRM.automationRules), Component: AutomationRulesPage, permission: 'notifications.view' },
  { key: 'pipeline', path: seg(CRM.pipeline), Component: PipelineRedirect, permission: 'candidates.pipeline' },
  { key: 'settings', path: seg(CRM.settings), Component: SettingsLandingPage, permission: 'settings.view' },
  { key: 'settings-users', path: seg(CRM.settingsUsers), Component: UsersPage, permission: ['admin.users', 'users.manage', 'users.view'] },
  { key: 'settings-billing', path: seg(CRM.settingsBilling), Component: BillingWorkspacePage, permission: 'admin.users' },
  { key: 'settings-tenants', path: seg(CRM.settingsTenants), Component: TenantsPage, permission: 'admin.companyAcl' },
  { key: 'settings-docs', path: seg(CRM.settingsDocs), Component: DocumentTypesPage, permission: 'documents.manage' },
  { key: 'settings-legal', path: seg(CRM.settingsLegal), Component: LegalDocumentsPage, permission: 'admin.users' },
  { key: 'settings-funnels', path: seg(CRM.settingsFunnels), Component: FunnelsPage, permission: ['admin.users', 'users.manage'] },
  {
    key: 'settings-hiring-pipeline-gates',
    path: seg(CRM.settingsHiringPipelineGates),
    Component: HiringPipelineGatesSettingsPage,
    permission: 'settings.view',
  },
  {
    key: 'settings-transfer-policy',
    path: seg(CRM.settingsTransferPolicy),
    Component: TransferPolicySettingsPage,
    permission: 'settings.view',
  },
  {
    key: 'settings-risk-intel',
    path: seg(CRM.settingsRiskIntel),
    Component: RiskIntelSettingsPage,
    permission: 'settings.view',
  },
  { key: 'settings-candidate-profiles', path: seg(CRM.settingsCandidateProfiles), Component: CandidateProfilesPage, permission: 'admin.users' },
  { key: 'settings-custom-fields', path: seg(CRM.settingsCustomFields), Component: CustomFieldsPage, permission: 'admin.users' },
  {
    key: 'settings-lead-forms',
    path: seg(CRM.settingsLeadForms),
    Component: LeadFormsSettingsPage,
    permission: ['admin.users', 'leads.view'],
  },
  {
    key: 'settings-forms-builder',
    path: `${seg(CRM.settingsLeadForms)}/:formId/builder`,
    Component: FormsBuilderPage,
    permission: ['admin.users', 'leads.view'],
  },
  {
    key: 'settings-intake-form-detail',
    path: `${seg(CRM.settingsLeadForms)}/:formId`,
    Component: IntakeFormDetailPage,
    permission: ['admin.users', 'leads.view'],
  },
  {
    key: 'settings-message-templates',
    path: seg(CRM.settingsMessageTemplates),
    Component: LeadMessageTemplatesPage,
    permission: 'admin.metaLeads',
  },
  {
    key: 'settings-leads-alias',
    path: seg(CRM.settingsLeads),
    Component: LegacySettingsLeadsToMetaRedirect,
    permission: ['admin.metaLeads', 'admin.users', 'settings.view'],
  },
  { key: 'settings-email', path: seg(CRM.settingsEmail), Component: EmailSettingsPage, permission: 'admin.users' },
  { key: 'settings-communications', path: seg(CRM.settingsCommunications), Component: withCommFeature(CommunicationsSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-messengers', path: seg(CRM.settingsCommunicationsMessengers), Component: withCommFeature(CommunicationsMessengerSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-queue', path: seg(CRM.settingsCommunicationsQueue), Component: withCommFeature(CommunicationsQueueSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-sla', path: seg(CRM.settingsCommunicationsSla), Component: withCommFeature(CommunicationsSlaSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-tenant-links', path: seg(CRM.settingsTenantLinks), Component: TenantLinksSettingsPage, permission: 'admin.users' },
  {
    key: 'settings-integrations',
    path: seg(CRM.settingsIntegrations),
    Component: IntegrationsHubPage,
    permission: ['admin.metaLeads', 'admin.users', 'settings.view', 'notifications.view'],
  },
  { key: 'settings-integrations-meta', path: seg(CRM.settingsIntegrationsMeta), Component: MetaLeadsAdminPage, permission: 'admin.metaLeads' },
  {
    key: 'settings-integrations-google',
    path: seg(CRM.settingsIntegrationsGoogle),
    Component: IntegrationsSourcePlaceholderPage,
    permission: 'admin.metaLeads',
  },
  {
    key: 'settings-integrations-webhook',
    path: seg(CRM.settingsIntegrationsWebhook),
    Component: IntegrationsWebhookPage,
    permission: 'admin.metaLeads',
  },
  {
    key: 'settings-integrations-messenger-channel',
    path: `${seg(CRM.settingsIntegrations)}/messenger/:messengerChannel`,
    Component: withCommFeature(MessengerIntegrationChannelPage, 'communicationsAdmin'),
    permission: 'admin.users',
  },
  { key: 'settings-ruleset', path: seg(CRM.settingsRuleset), Component: RulesetVersionsPage, permission: 'admin.ruleset' },
  { key: 'settings-audit', path: seg(CRM.settingsAudit), Component: AuditLogPage, permission: 'admin.deletionQueue' },
  { key: 'settings-company-access', path: seg(CRM.settingsCompanyAccess), Component: CompanyAccessPage, permission: 'admin.companyAcl' },
  { key: 'settings-ttv-report', path: seg(CRM.settingsTtvReport), Component: TtvReportPage, permission: 'manager.tools' },
  { key: 'profile', path: seg(CRM.profile), Component: ProfilePage },
  {
    key: 'hr-workspace',
    path: seg(CRM.hr),
    Component: HrDashboardPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-inbox',
    path: seg(CRM.hrInbox),
    Component: HrInboxPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-tasks',
    path: seg(CRM.hrTasks),
    Component: HrTasksPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-compliance',
    path: seg(CRM.hrCompliance),
    Component: HrComplianceDocumentsPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-zus-legacy-alias',
    path: 'hr/zus',
    Component: () => <Navigate to={CRM.hrZusWorkspace} replace />,
    permission: 'workforce.view',
  },
  {
    key: 'hr-zus-workspace',
    path: seg(CRM.hrZusWorkspace),
    Component: HrZusWorkspacePage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-employees',
    path: seg(CRM.hrEmployees),
    Component: HrEmployeesPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-employee-detail',
    path: `${seg(CRM.hrEmployees)}/:employeeId`,
    Component: HrEmployeeDetailPage,
    permission: 'workforce.view',
  },
  {
    key: 'hr-handoff-detail',
    path: `${seg(CRM.hrHandoffs)}/:id`,
    Component: HrHandoffDetailPage,
    permission: 'workforce.view',
  },
  ...(import.meta.env.DEV
    ? [
        {
          key: 'dev-entity-list-shell',
          path: 'dev/entity-list-shell',
          Component: EntityListShellDemoPage,
        },
      ]
    : []),
  { key: 'not-found', path: '*', Component: NotFoundRedirect },
]
