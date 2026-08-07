import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconAlertTriangle,
  IconBell,
  IconChecklist,
  IconClipboardList,
  IconCreditCard,
  IconFileText,
  IconFilter,
  IconHome,
  IconLink,
  IconPlugConnected,
  IconSettings,
  IconShield,
  IconUsersGroup,
} from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { getTenantModules } from '../../api/tenants'
import type { TenantModuleSettings } from '../../api/types'
import { useCommunicationsAccess, type CommunicationsFeatureKey } from '../../hooks/useCommunicationsAccess'
import { useAuth } from '../../store/useAuth'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'

type SettingsSectionKey =
  | 'workspace'
  | 'crm_setup'
  | 'team'
  | 'automations'
  | 'integrations'
  | 'billing'
  | 'personal'

type CardDef = {
  key: string
  label: string
  description: string
  target: string
  roles: string[]
  section: SettingsSectionKey
  requiresModules?: Array<keyof TenantModuleSettings>
  requiresCommFeatures?: CommunicationsFeatureKey[]
  superadminOnly?: boolean
  requiresCompaniesView?: boolean
  /** Single entry to `/settings/integrations` (connections); duplicate per-integration cards live only in the hub. */
  integrationsHubEntry?: boolean
}
const DEFAULT_CARD_ICON: TablerIcon = IconSettings
const CARD_ICONS: Partial<Record<string, TablerIcon>> = {
  team: IconUsersGroup,
  tenants: IconShield,
  notifications: IconBell,
  communications_queue: IconFilter,
  communications_sla: IconBell,
  documents: IconFileText,
  funnels: IconFilter,
  'settings-hiring-gates': IconChecklist,
  risk_intel: IconAlertTriangle,
  candidate_profiles: IconUsersGroup,
  custom_fields: IconSettings,
  lead_forms: IconClipboardList,
  company_access: IconShield,
  legal: IconShield,
  tenant_links: IconLink,
  my_company: IconHome,
  billing: IconCreditCard,
  integrations_hub: IconPlugConnected,
  ruleset: IconSettings,
  audit: IconShield,
  profile: IconUsersGroup,
}

export default function SettingsLandingPage() {
  const { t } = useI18n()
  const { role, can } = usePermissions()
  const { me } = useAuth()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const isSuperAdmin = useMemo(() => {
    const directRole = String((me as any)?.role || '').toLowerCase().trim()
    if (directRole === 'superadmin' || directRole === 'super_admin') return true
    const currentTenantId = String((me as any)?.tenant_id || '')
    const membershipRole = Array.isArray((me as any)?.memberships)
      ? (me as any).memberships.find((m: any) => String(m?.tenant_id || '') === currentTenantId)?.role
      : ''
    const normalizedMembershipRole = String(membershipRole || '').toLowerCase().trim()
    return normalizedMembershipRole === 'superadmin' || normalizedMembershipRole === 'super_admin'
  }, [me])
  const [modules, setModules] = useState<TenantModuleSettings | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const data = await getTenantModules()
        if (mounted) setModules(data)
      } catch {
        if (mounted) setModules(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [])

  const sectionMeta = useMemo(
    () => ({
      workspace: {
        label: t('admin.settings.sections.workspace.label', { defaultValue: 'Workspace' }),
        description: t('admin.settings.sections.workspace.description', { defaultValue: 'Company profile, workspace identity and high-level access scope.' }),
      },
      crm_setup: {
        label: t('admin.settings.sections.crm_setup.label', { defaultValue: 'CRM Setup' }),
        description: t('admin.settings.sections.crm_setup.description', { defaultValue: 'Funnels, statuses, profiles and fields needed for CRM operation.' }),
      },
      team: {
        label: t('admin.settings.sections.team.label', { defaultValue: 'Team' }),
        description: t('admin.settings.sections.team.description', { defaultValue: 'Users, roles and tenant/company access rules.' }),
      },
      automations: {
        label: t('admin.settings.sections.automations.label', { defaultValue: 'Automations' }),
        description: t('admin.settings.sections.automations.description', { defaultValue: 'Queue routing, SLA, reminders and operational policies.' }),
      },
      integrations: {
        label: t('admin.settings.sections.integrations.label', { defaultValue: 'Integrations' }),
        description: t('admin.settings.sections.integrations.description', { defaultValue: 'External channels, webhooks and integration-level controls.' }),
      },
      billing: {
        label: t('admin.settings.sections.billing.label', { defaultValue: 'Billing' }),
        description: t('admin.settings.sections.billing.description', { defaultValue: 'Subscription, plan and payment lifecycle.' }),
      },
      personal: {
        label: t('admin.settings.sections.personal.label', { defaultValue: 'Personal' }),
        description: t('admin.settings.sections.personal.description', { defaultValue: 'Profile and personal preferences that do not affect other users.' }),
      },
    }),
    [t],
  )

  const sectionOrder: SettingsSectionKey[] = ['workspace', 'crm_setup', 'team', 'automations', 'integrations', 'billing', 'personal']

  const allCards: CardDef[] = useMemo(
    () => [
      {
        key: 'team',
        label: t('admin.settings.cards.users.label'),
        description: t('admin.settings.cards.users.description'),
        target: CRM_APP_PATHS.settingsUsers,
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'team',
      },
      {
        key: 'tenants',
        label: t('admin.settings.cards.tenants.label'),
        description: t('admin.settings.cards.tenants.description'),
        target: CRM_APP_PATHS.settingsTenants,
        roles: ['administrator'],
        section: 'workspace',
        superadminOnly: true,
      },
      {
        key: 'my_company',
        label: t('app.nav.items.my_company'),
        description: t('admin.settings.cards.my_company.description'),
        target: CRM_APP_PATHS.myCompany,
        roles: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor', 'compliance_officer', 'hr_officer', 'viewer'],
        section: 'workspace',
        requiresCompaniesView: true,
      },
      {
        key: 'company_access',
        label: t('admin.settings.cards.company_access.label', { defaultValue: 'Company access' }),
        description: t('admin.settings.cards.company_access.description', { defaultValue: 'Control which companies are visible for selected tenant users.' }),
        target: CRM_APP_PATHS.settingsCompanyAccess,
        roles: ['administrator'],
        section: 'team',
      },
      {
        key: 'notifications',
        label: t('admin.settings.cards.notifications.label'),
        description: t('admin.settings.cards.notifications.description'),
        target: CRM_APP_PATHS.tasks,
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'automations',
        requiresModules: ['candidates'],
      },
      {
        key: 'integrations_hub',
        label: t('admin.settings.cards.integrations_hub.label'),
        description: t('admin.settings.cards.integrations_hub.description'),
        target: CRM_APP_PATHS.settingsIntegrations,
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'integrations',
        integrationsHubEntry: true,
      },
      {
        key: 'communications_queue',
        label: t('admin.settings.cards.communications_queue.label', { defaultValue: 'Queue settings' }),
        description: t('admin.settings.cards.communications_queue.description', { defaultValue: 'Routing strategy and manager allocation queue controls.' }),
        target: CRM_APP_PATHS.settingsCommunicationsQueue,
        roles: ['administrator', 'supervisor'],
        section: 'automations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'communications_sla',
        label: t('admin.settings.cards.communications_sla.label', { defaultValue: 'SLA settings' }),
        description: t('admin.settings.cards.communications_sla.description', { defaultValue: 'Escalation policy for overdue communication threads.' }),
        target: CRM_APP_PATHS.settingsCommunicationsSla,
        roles: ['administrator', 'supervisor'],
        section: 'automations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'documents',
        label: t('admin.settings.cards.documents.label'),
        description: t('admin.settings.cards.documents.description'),
        target: CRM_APP_PATHS.settingsDocs,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['documents'],
      },
      {
        key: 'merge_templates',
        label: t('admin.settings.cards.merge_templates.label'),
        description: t('admin.settings.cards.merge_templates.description'),
        target: CRM_APP_PATHS.settingsMergeTemplates,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['documents'],
      },
      {
        key: 'funnels',
        label: t('admin.settings.cards.funnels.label', {
          defaultValue: 'Recruitment Pipelines',
        }),
        description: t('admin.settings.cards.funnels.description', {
          defaultValue:
            'Process catalog. Assign on Vacancy. ★ = default for new vacancies only.',
        }),
        target: CRM_APP_PATHS.settingsFunnels,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'settings-hiring-gates',
        label: t('admin.settings.cards.hiring_gates.label'),
        description: t('admin.settings.cards.hiring_gates.description'),
        target: CRM_APP_PATHS.settingsHiringPipelineGates,
        roles: ['administrator', 'supervisor', 'recruiter', 'compliance_officer', 'hr_officer', 'viewer'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'transfer_policy',
        label: t('admin.settings.cards.transfer_policy.label', { defaultValue: 'Transfer Policy' }),
        description: t('admin.settings.cards.transfer_policy.description', {
          defaultValue: 'Aggregated handoff rules, destinations, and governance in one place.',
        }),
        target: CRM_APP_PATHS.settingsTransferPolicy,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'risk_intel',
        label: t('admin.settings.cards.risk_intel.label'),
        description: t('admin.settings.cards.risk_intel.description'),
        target: CRM_APP_PATHS.settingsRiskIntel,
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'candidate_profiles',
        label: t('admin.settings.cards.candidate_profiles.label'),
        description: t('admin.settings.cards.candidate_profiles.description'),
        target: CRM_APP_PATHS.settingsCandidateProfiles,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'custom_fields',
        label: t('admin.settings.cards.custom_fields.label'),
        description: t('admin.settings.cards.custom_fields.description'),
        target: CRM_APP_PATHS.settingsCustomFields,
        roles: ['administrator'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'message_templates',
        label: t('admin.settings.cards.message_templates.label', { defaultValue: 'Message templates' }),
        description: t('admin.settings.cards.message_templates.description', { defaultValue: 'Shared templates for lead operational emails and RODO notices.' }),
        target: CRM_APP_PATHS.settingsMessageTemplates,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
      },
      {
        key: 'lead_forms',
        label: t('admin.settings.cards.lead_forms.label'),
        description: t('admin.settings.cards.lead_forms.description'),
        target: CRM_APP_PATHS.marketingForms,
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['leads'],
      },
      {
        key: 'billing',
        label: t('app.nav.items.settings_billing'),
        description: t('admin.settings.cards.billing.description'),
        target: CRM_APP_PATHS.settingsBilling,
        roles: ['administrator'],
        section: 'billing',
      },
      {
        key: 'legal',
        label: t('admin.settings.cards.legal.label'),
        description: t('admin.settings.cards.legal.description'),
        target: CRM_APP_PATHS.settingsLegal,
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'tenant_links',
        label: t('admin.settings.cards.tenant_links.label'),
        description: t('admin.settings.cards.tenant_links.description'),
        target: CRM_APP_PATHS.settingsTenantLinks,
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'ruleset',
        label: t('admin.settings.cards.ruleset.label'),
        description: t('admin.settings.cards.ruleset.description'),
        target: CRM_APP_PATHS.settingsRuleset,
        roles: ['administrator', 'supervisor'],
        section: 'automations',
      },
      {
        key: 'audit',
        label: t('admin.settings.cards.audit.label'),
        description: t('admin.settings.cards.audit.description'),
        target: CRM_APP_PATHS.settingsAudit,
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'profile',
        label: t('admin.settings.cards.profile.label', { defaultValue: 'My profile' }),
        description: t('admin.settings.cards.profile.description', { defaultValue: 'Personal profile, language, security and local preferences.' }),
        target: CRM_APP_PATHS.profile,
        roles: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor', 'compliance_officer', 'hr_officer', 'viewer'],
        section: 'personal',
      },
    ],
    [t],
  )

  const cards = useMemo(
    () =>
      allCards.filter((c) => {
        if (c.superadminOnly && !isSuperAdmin) return false
        if (c.requiresCompaniesView && !can('companies.view')) return false
        if (c.integrationsHubEntry) {
          const hubOk =
            can('admin.metaLeads') ||
            can('admin.users') ||
            can('settings.view') ||
            (can('notifications.view') &&
              (canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email')))
          if (!hubOk) return false
        }
        if (!c.roles.includes(role)) return false
        if (c.requiresModules && modules) {
          for (const mk of c.requiresModules) {
            if (!modules[mk]) return false
          }
        }
        if (c.requiresCommFeatures && c.requiresCommFeatures.length > 0) {
          const allowed = c.requiresCommFeatures.some((f) => canUseCommunicationsFeature(f))
          if (!allowed) return false
        }
        return true
      }),
    [allCards, can, canUseCommunicationsFeature, isSuperAdmin, modules, role],
  )

  const grouped = useMemo(
    () =>
      sectionOrder
        .map((section) => ({
          key: section,
          label: sectionMeta[section].label,
          description: sectionMeta[section].description,
          items: cards.filter((card) => card.section === section),
        }))
        .filter((section) => section.items.length > 0),
    [cards, sectionMeta],
  )

  const renderCard = (item: CardDef) => (
    <li key={item.target} className="rounded-xl border border-brand-100 bg-brand-50/30 p-4">
      <div className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
        {(() => {
          const CardIcon = CARD_ICONS[item.key] || DEFAULT_CARD_ICON
          return <CardIcon size={18} stroke={1.9} />
        })()}
        <span>{item.label}</span>
      </div>
      <p className="mt-1 text-sm text-slate-500">{item.description}</p>
      <Link className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline" to={item.target}>
        <IconLink size={15} stroke={2} />
        {t('admin.settings.actions.open')}
      </Link>
    </li>
  )

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('admin.settings.title')}
          subtitle={t('admin.settings.subtitle')}
          kind="browse"
        />
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
      <section className="card p-6">
        <div className="space-y-6">
          <p className="text-sm text-slate-600">{t('admin.settings.areas_intro')}</p>
          {grouped.map((section) => (
            <section key={section.key} className="space-y-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{section.label}</h3>
                <p className="mt-1 text-sm text-slate-500">{section.description}</p>
              </div>
              <ul className="grid gap-4 md:grid-cols-2">{section.items.map((item) => renderCard(item))}</ul>
            </section>
          ))}
        </div>
      </section>
      </div>
    </PageShell>
  )
}
