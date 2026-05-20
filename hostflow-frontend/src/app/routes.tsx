import type { ComponentType } from 'react'
import { Navigate } from 'react-router-dom'
import type { Permission } from '../hooks/usePermissions'
import Dashboard from '../pages/Dashboard'
import Candidates from '../pages/Candidates'
import CandidateCard from '../pages/CandidateCard'
import Companies from '../pages/Companies'
import Vacancies from '../pages/Vacancies'
import VacancyDetailRoute from '../pages/VacancyDetailRoute'
import { ServicesPage } from '../pages/ServicesPage'
import InvoicesPage from '../pages/InvoicesPage'
import LeadsPage from '../pages/LeadsPage'
import ProfilePage from '../pages/ProfilePage'
import RemindersPage from '../pages/RemindersPage'
import UsersPage from '../pages/admin/UsersPage'
import TenantsPage from '../pages/admin/TenantsPage'
import RulesetVersionsPage from '../pages/admin/RulesetVersionsPage'
import MetaLeadsAdminPage from '../pages/admin/MetaLeadsAdminPage'
import DeletionRequestsPage from '../pages/admin/DeletionRequestsPage'
import DocumentsRegistryPage from '../pages/DocumentsRegistryPage'
import SettingsLandingPage from '../pages/admin/SettingsLandingPage'
import DocumentTypesPage from '../pages/admin/DocumentTypesPage'
import CompanyAccessPage from '../pages/admin/CompanyAccessPage'
import EntityListShellDemoPage from '../pages/dev/EntityListShellDemoPage'

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
    permission: 'admin.users',
  },
  {
    key: 'settings-users',
    labelKey: 'app.nav.items.settings_users',
    path: '/app/settings/users',
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
    key: 'settings-docs',
    labelKey: 'app.nav.items.settings_docs',
    path: '/app/settings/docs',
    group: 'admin',
    permission: 'documents.manage',
  },
  {
    key: 'settings-integrations',
    labelKey: 'app.nav.items.settings_integrations',
    path: '/app/settings/integrations',
    group: 'admin',
    permission: 'admin.metaLeads',
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
const SettingsBillingRedirect = () => <Navigate to="../settings/users" replace />

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
  { key: 'clients', path: 'clients', Component: Companies, permission: 'companies.view' },
  { key: 'client-detail', path: 'clients/:id', Component: Companies, permission: 'companies.view' },
  { key: 'client-tab', path: 'clients/:id/:tab', Component: Companies, permission: 'companies.view' },
  { key: 'vacancies', path: 'vacancies', Component: Vacancies, permission: 'vacancies.view' },
  { key: 'vacancy-detail', path: 'vacancies/:id', Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'vacancy-tab', path: 'vacancies/:id/:tab', Component: VacancyDetailRoute, permission: 'vacancies.view' },
  { key: 'documents', path: 'documents', Component: DocumentsRegistryPage, permission: 'documents.manage' },
  { key: 'services', path: 'services', Component: ServicesPage, permission: 'services.view' },
  { key: 'invoices', path: 'invoices', Component: InvoicesPage, permission: 'admin.users' }, // TODO: Add proper permission
  { key: 'reminders', path: 'reminders', Component: RemindersPage, permission: 'notifications.view' },
  { key: 'leads', path: 'leads', Component: LeadsPage, permission: 'leads.view' },
  { key: 'pipeline', path: 'pipeline', Component: PipelineRedirect, permission: 'candidates.pipeline' },
  { key: 'settings', path: 'settings', Component: SettingsLandingPage, permission: 'admin.users' },
  { key: 'settings-users', path: 'settings/users', Component: UsersPage, permission: 'admin.users' },
  { key: 'settings-billing', path: 'settings/billing', Component: SettingsBillingRedirect, permission: 'admin.users' },
  { key: 'settings-tenants', path: 'settings/tenants', Component: TenantsPage, permission: 'admin.companyAcl' },
  { key: 'settings-docs', path: 'settings/docs', Component: DocumentTypesPage, permission: 'documents.manage' },
  { key: 'settings-integrations', path: 'settings/integrations', Component: MetaLeadsAdminPage, permission: 'admin.metaLeads' },
  { key: 'settings-ruleset', path: 'settings/ruleset', Component: RulesetVersionsPage, permission: 'admin.ruleset' },
  { key: 'settings-audit', path: 'settings/audit', Component: DeletionRequestsPage, permission: 'admin.deletionQueue' },
  { key: 'settings-company-access', path: 'settings/company-access', Component: CompanyAccessPage, permission: 'admin.companyAcl' },
  { key: 'profile', path: 'profile', Component: ProfilePage },
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
