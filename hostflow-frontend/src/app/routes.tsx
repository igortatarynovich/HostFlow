import type { ComponentType } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import type { Permission } from '../hooks/usePermissions'
import CommunicationsFeatureGate from '../components/communications/CommunicationsFeatureGate'
import Dashboard from '../pages/Dashboard'
import Candidates from '../pages/Candidates'
import CandidateCard from '../pages/CandidateCard'
import Companies from '../pages/Companies'
import Vacancies from '../pages/Vacancies'
import VacancyDetailRoute from '../pages/VacancyDetailRoute'
import { ServicesPage } from '../pages/ServicesPage'
import InvoicesPage from '../pages/InvoicesPage'
import InvoiceCreatePage from '../pages/InvoiceCreatePage'
import InvoiceDetailPage from '../pages/InvoiceDetailPage'
import LeadsPage from '../pages/LeadsPage'
import ProfilePage from '../pages/ProfilePage'
import RemindersPage from '../pages/RemindersPage'
import CommunicationsThreadPage from '../pages/CommunicationsThreadPage'
import CommunicationsMessagesPage from '../pages/CommunicationsMessagesPage'
import CommunicationsEmailInboxPage from '../pages/CommunicationsEmailInboxPage'
import CommunicationsCalendarPage from '../pages/CommunicationsCalendarPage'
import CommunicationsPlannerPage from '../pages/CommunicationsPlannerPage'
import CommunicationsSlaIncidentsPage from '../pages/CommunicationsSlaIncidentsPage'
import CommunicationsSetupPage from '../pages/CommunicationsSetupPage'
import CommunicationsCommandAuditPage from '../pages/CommunicationsCommandAuditPage'
import TeamAvailabilityPage from '../pages/TeamAvailabilityPage'
import MyAvailabilityPage from '../pages/MyAvailabilityPage'
import TimeOffRequestsPage from '../pages/TimeOffRequestsPage'
import UsersPage from '../pages/admin/UsersPage'
import TenantsPage from '../pages/admin/TenantsPage'
import RulesetVersionsPage from '../pages/admin/RulesetVersionsPage'
import MetaLeadsAdminPage from '../pages/admin/MetaLeadsAdminPage'
import DeletionRequestsPage from '../pages/admin/DeletionRequestsPage'
import AuditLogPage from '../pages/admin/AuditLogPage'
import DocumentsRegistryPage from '../pages/DocumentsRegistryPage'
import SettingsLandingPage from '../pages/admin/SettingsLandingPage'
import DocumentTypesPage from '../pages/admin/DocumentTypesPage'
import CompanyAccessPage from '../pages/admin/CompanyAccessPage'
import CandidateProfilesPage from '../pages/admin/CandidateProfilesPage'
import FunnelsPage from '../pages/admin/FunnelsPage'
import CustomFieldsPage from '../pages/admin/CustomFieldsPage'
import BillingWorkspacePage from '../pages/admin/BillingWorkspacePage'
import EmailSettingsPage from '../pages/admin/EmailSettingsPage'
import CommunicationsSettingsPage from '../pages/admin/CommunicationsSettingsPage'
import CommunicationsMessengerSettingsPage from '../pages/admin/CommunicationsMessengerSettingsPage'
import CommunicationsQueueSettingsPage from '../pages/admin/CommunicationsQueueSettingsPage'
import CommunicationsSlaSettingsPage from '../pages/admin/CommunicationsSlaSettingsPage'
import TenantLinksSettingsPage from '../pages/admin/TenantLinksSettingsPage'
import AgencyClientsPage from '../pages/AgencyClientsPage'
import ClientLinkDetailPage from '../pages/ClientLinkDetailPage'
import LegalDocumentsPage from '../pages/admin/LegalDocumentsPage'
import DoProcesowaniaPage from '../pages/DoProcesowaniaPage'

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
  permission?: Permission
  action?: 'logout'
  superadminOnly?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { key: 'overview', labelKey: 'app.nav.items.overview', path: '/app/overview', group: 'overview' },
  {
    key: 'candidates',
    labelKey: 'app.nav.items.candidates',
    path: '/app/candidates',
    group: 'people',
    permission: 'candidates.view',
  },
  {
    key: 'clients',
    labelKey: 'app.nav.items.clients',
    path: '/app/clients',
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'do-procesowania',
    labelKey: 'app.nav.items.do_procesowania',
    path: '/app/procesowani',
    group: 'people',
    permission: 'companies.view',
  },
  {
    key: 'vacancies',
    labelKey: 'app.nav.items.vacancies',
    path: '/app/vacancies',
    group: 'people',
    permission: 'vacancies.view',
  },
  {
    key: 'documents',
    labelKey: 'app.nav.items.documents',
    path: '/app/documents',
    group: 'workflows',
    permission: 'documents.manage',
  },
  {
    key: 'services',
    labelKey: 'app.nav.items.services',
    path: '/app/services',
    group: 'workflows',
    permission: 'services.view',
  },
  {
    key: 'invoices',
    labelKey: 'app.nav.items.invoices',
    path: '/app/invoices',
    group: 'workflows',
    permission: 'admin.users', // TODO: Add proper permission
  },
  {
    key: 'communications-setup',
    labelKey: 'app.nav.items.communications_setup',
    path: '/app/setup/communications',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'messages-inbox',
    labelKey: 'app.nav.items.messages_inbox',
    path: '/app/messages',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'email-inbox',
    labelKey: 'app.nav.items.email_inbox',
    path: '/app/email',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'calendar',
    labelKey: 'app.nav.items.calendar',
    path: '/app/calendar',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'planner',
    labelKey: 'app.nav.items.planner',
    path: '/app/planner',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'sla-incidents',
    labelKey: 'app.nav.items.sla_incidents',
    path: '/app/sla-incidents',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'command-audit',
    labelKey: 'app.nav.items.command_audit',
    path: '/app/communications/command-audit',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'team-availability',
    labelKey: 'app.nav.items.team_availability',
    path: '/app/team-availability',
    group: 'admin',
    permission: 'notifications.view',
  },
  {
    key: 'my-availability',
    labelKey: 'app.nav.items.my_availability',
    path: '/app/my-availability',
    group: 'account',
    permission: 'notifications.view',
  },
  {
    key: 'time-off',
    labelKey: 'app.nav.items.time_off',
    path: '/app/time-off',
    group: 'account',
    permission: 'notifications.view',
  },
  {
    key: 'reminders',
    labelKey: 'app.nav.items.reminders',
    path: '/app/reminders',
    group: 'workflows',
    permission: 'notifications.view',
  },
  {
    key: 'leads',
    labelKey: 'app.nav.items.leads',
    path: '/app/leads',
    group: 'leads',
    permission: 'leads.view',
  },
  {
    key: 'settings',
    labelKey: 'app.nav.items.settings',
    path: '/app/settings',
    group: 'admin',
    permission: 'settings.view',
  },
  {
    key: 'settings-users',
    labelKey: 'app.nav.items.settings_users',
    path: '/app/settings/users',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-billing',
    labelKey: 'app.nav.items.settings_billing',
    path: '/app/settings/billing',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-tenants',
    labelKey: 'app.nav.items.settings_tenants',
    path: '/app/settings/tenants',
    group: 'admin',
    permission: 'admin.companyAcl',
    superadminOnly: true,
  },
  {
    key: 'settings-funnels',
    labelKey: 'app.nav.items.settings_funnels',
    path: '/app/settings/funnels',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-docs',
    labelKey: 'app.nav.items.settings_docs',
    path: '/app/settings/docs',
    group: 'admin',
    permission: 'documents.manage',
  },
  {
    key: 'settings-legal',
    labelKey: 'app.nav.items.settings_legal',
    path: '/app/settings/legal',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-company-access',
    labelKey: 'app.nav.items.settings_company_access',
    path: '/app/settings/company-access',
    group: 'admin',
    permission: 'admin.companyAcl',
  },
  {
    key: 'settings-email',
    labelKey: 'app.nav.items.settings_email',
    path: '/app/settings/email',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-tenant-links',
    labelKey: 'app.nav.items.settings_tenant_links',
    path: '/app/settings/tenant-links',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-integrations',
    labelKey: 'app.nav.items.settings_integrations',
    path: '/app/settings/integrations',
    group: 'admin',
    permission: 'admin.metaLeads',
  },
  {
    key: 'settings-communications',
    labelKey: 'app.nav.items.settings_communications',
    path: '/app/settings/communications',
    group: 'admin',
    permission: 'admin.users',
  },
  {
    key: 'settings-ruleset',
    labelKey: 'app.nav.items.settings_ruleset',
    path: '/app/settings/ruleset',
    group: 'admin',
    permission: 'admin.ruleset',
  },
  {
    key: 'settings-audit',
    labelKey: 'app.nav.items.settings_audit',
    path: '/app/settings/audit',
    group: 'admin',
    permission: 'admin.deletionQueue',
  },
  { key: 'profile', labelKey: 'app.nav.items.profile', path: '/app/profile', group: 'account' },
  { key: 'logout', labelKey: 'app.nav.items.logout', group: 'account', action: 'logout' },
]

const PipelineRedirect = () => <Navigate to="candidates?view=kanban" replace />
const NotFoundRedirect = () => <Navigate to="overview" replace />
const LegacyDoProcesowaniaRedirect = () => <Navigate to="../procesowani" replace />
const LegacyCommunicationsRedirect = () => <Navigate to="../settings/communications" replace />
const LegacyCompaniesRedirect = () => <Navigate to="../clients" replace />
const LegacyCompanyDetailRedirect = () => {
  const { id, tab } = useParams<{ id?: string; tab?: string }>()
  if (!id) return <Navigate to="../clients" replace />
  return <Navigate to={tab ? `../clients/${id}/${tab}` : `../clients/${id}`} replace />
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
  { key: 'overview', path: 'overview', Component: Dashboard },
  { key: 'candidates', path: 'candidates', Component: Candidates, permission: 'candidates.view' },
  { key: 'candidate-detail', path: 'candidates/:id', Component: CandidateCard, permission: 'candidates.view' },
  { key: 'candidate-tab', path: 'candidates/:id/:tab', Component: CandidateCard, permission: 'candidates.view' },
  { key: 'clients', path: 'clients', Component: AgencyClientsPage, permission: 'companies.view' },
  { key: 'companies-legacy', path: 'companies', Component: LegacyCompaniesRedirect, permission: 'companies.view' },
  { key: 'client-link-detail', path: 'clients/link/:linkId', Component: ClientLinkDetailPage, permission: 'companies.view' },
  { key: 'procesowani', path: 'procesowani', Component: DoProcesowaniaPage, permission: 'companies.view' },
  { key: 'do-procesowania-legacy', path: 'do-procesowania', Component: LegacyDoProcesowaniaRedirect, permission: 'companies.view' },
  { key: 'client-detail', path: 'clients/:id', Component: Companies, permission: 'companies.view' },
  { key: 'client-tab', path: 'clients/:id/:tab', Component: Companies, permission: 'companies.view' },
  { key: 'company-detail-legacy', path: 'companies/:id', Component: LegacyCompanyDetailRedirect, permission: 'companies.view' },
  { key: 'company-tab-legacy', path: 'companies/:id/:tab', Component: LegacyCompanyDetailRedirect, permission: 'companies.view' },
  { key: 'vacancies', path: 'vacancies', Component: Vacancies, permission: 'vacancies.view' },
  { key: 'vacancy-detail', path: 'vacancies/:id', Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'vacancy-tab', path: 'vacancies/:id/:tab', Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'documents', path: 'documents', Component: DocumentsRegistryPage, permission: 'documents.manage' },
  { key: 'services', path: 'services', Component: ServicesPage, permission: 'services.view' },
  { key: 'invoices', path: 'invoices', Component: InvoicesPage, permission: 'admin.users' }, // TODO: Add proper permission
  { key: 'invoice-create', path: 'invoices/new', Component: InvoiceCreatePage, permission: 'admin.users' },
  { key: 'invoice-edit', path: 'invoices/:id/edit', Component: InvoiceCreatePage, permission: 'admin.users' },
  { key: 'invoice-detail', path: 'invoices/:id', Component: InvoiceDetailPage, permission: 'admin.users' },
  { key: 'communications-setup', path: 'setup/communications', Component: withCommAnyFeature(CommunicationsSetupPage, ['messages', 'email']), permission: 'notifications.view' },
  { key: 'messages-inbox', path: 'messages', Component: withCommFeature(CommunicationsMessagesPage, 'messages'), permission: 'notifications.view' },
  { key: 'email-inbox', path: 'email', Component: withCommFeature(CommunicationsEmailInboxPage, 'email'), permission: 'notifications.view' },
  { key: 'calendar', path: 'calendar', Component: withCommFeature(CommunicationsCalendarPage, 'calendar'), permission: 'notifications.view' },
  { key: 'planner', path: 'planner', Component: withCommFeature(CommunicationsPlannerPage, 'planner'), permission: 'notifications.view' },
  { key: 'sla-incidents', path: 'sla-incidents', Component: withCommAnyFeature(CommunicationsSlaIncidentsPage, ['messages', 'email']), permission: 'notifications.view' },
  { key: 'command-audit', path: 'communications/command-audit', Component: withCommFeature(CommunicationsCommandAuditPage, 'communicationsAdmin'), permission: 'notifications.view' },
  { key: 'team-availability', path: 'team-availability', Component: withCommFeature(TeamAvailabilityPage, 'teamAvailability'), permission: 'notifications.view' },
  { key: 'my-availability', path: 'my-availability', Component: withCommFeature(MyAvailabilityPage, 'myAvailability'), permission: 'notifications.view' },
  { key: 'time-off', path: 'time-off', Component: withCommFeature(TimeOffRequestsPage, 'timeOffRequests'), permission: 'notifications.view' },
  { key: 'communications', path: 'communications', Component: LegacyCommunicationsRedirect, permission: 'notifications.view' },
  { key: 'communications-thread', path: 'communications/threads/:threadId', Component: withCommAnyFeature(CommunicationsThreadPage, ['messages', 'email']), permission: 'notifications.view' },
  { key: 'reminders', path: 'reminders', Component: RemindersPage, permission: 'notifications.view' },
  { key: 'leads', path: 'leads', Component: LeadsPage, permission: 'leads.view' },
  { key: 'pipeline', path: 'pipeline', Component: PipelineRedirect, permission: 'candidates.pipeline' },
  { key: 'settings', path: 'settings', Component: SettingsLandingPage, permission: 'settings.view' },
  { key: 'settings-users', path: 'settings/users', Component: UsersPage, permission: ['admin.users', 'users.manage', 'users.view'] },
  { key: 'settings-billing', path: 'settings/billing', Component: BillingWorkspacePage, permission: 'admin.users' },
  { key: 'settings-tenants', path: 'settings/tenants', Component: TenantsPage, permission: 'admin.companyAcl' },
  { key: 'settings-docs', path: 'settings/docs', Component: DocumentTypesPage, permission: 'documents.manage' },
  { key: 'settings-legal', path: 'settings/legal', Component: LegalDocumentsPage, permission: 'admin.users' },
  { key: 'settings-funnels', path: 'settings/funnels', Component: FunnelsPage, permission: ['admin.users', 'users.manage'] },
  { key: 'settings-candidate-profiles', path: 'settings/candidate-profiles', Component: CandidateProfilesPage, permission: 'admin.users' },
  { key: 'settings-custom-fields', path: 'settings/custom-fields', Component: CustomFieldsPage, permission: 'admin.users' },
  { key: 'settings-email', path: 'settings/email', Component: EmailSettingsPage, permission: 'admin.users' },
  { key: 'settings-communications', path: 'settings/communications', Component: withCommFeature(CommunicationsSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-messengers', path: 'settings/communications/messengers', Component: withCommFeature(CommunicationsMessengerSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-queue', path: 'settings/communications/queue', Component: withCommFeature(CommunicationsQueueSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-communications-sla', path: 'settings/communications/sla', Component: withCommFeature(CommunicationsSlaSettingsPage, 'communicationsAdmin'), permission: 'admin.users' },
  { key: 'settings-tenant-links', path: 'settings/tenant-links', Component: TenantLinksSettingsPage, permission: 'admin.users' },
  { key: 'settings-integrations', path: 'settings/integrations', Component: MetaLeadsAdminPage, permission: 'admin.metaLeads' },
  { key: 'settings-ruleset', path: 'settings/ruleset', Component: RulesetVersionsPage, permission: 'admin.ruleset' },
  { key: 'settings-audit', path: 'settings/audit', Component: AuditLogPage, permission: 'admin.deletionQueue' },
  { key: 'settings-company-access', path: 'settings/company-access', Component: CompanyAccessPage, permission: 'admin.companyAcl' },
  { key: 'profile', path: 'profile', Component: ProfilePage },
  { key: 'not-found', path: '*', Component: NotFoundRedirect },
]
