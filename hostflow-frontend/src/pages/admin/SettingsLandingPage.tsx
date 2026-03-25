import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconAlertTriangle,
  IconBell,
  IconBrandTelegram,
  IconChecklist,
  IconCreditCard,
  IconFileText,
  IconFilter,
  IconLink,
  IconMail,
  IconMessage2Cog,
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
}
const DEFAULT_CARD_ICON: TablerIcon = IconSettings
const CARD_ICONS: Partial<Record<string, TablerIcon>> = {
  team: IconUsersGroup,
  tenants: IconShield,
  notifications: IconBell,
  communications_setup: IconChecklist,
  communications: IconMessage2Cog,
  communications_messengers: IconBrandTelegram,
  communications_queue: IconFilter,
  communications_sla: IconBell,
  email: IconMail,
  documents: IconFileText,
  funnels: IconFilter,
  'settings-hiring-gates': IconChecklist,
  risk_intel: IconAlertTriangle,
  candidate_profiles: IconUsersGroup,
  custom_fields: IconSettings,
  company_access: IconShield,
  legal: IconShield,
  tenant_links: IconLink,
  billing: IconCreditCard,
  integrations: IconPlugConnected,
  ruleset: IconSettings,
  audit: IconShield,
  profile: IconUsersGroup,
}

export default function SettingsLandingPage() {
  const { t } = useI18n()
  const { role } = usePermissions()
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
        target: '/app/settings/users',
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'team',
      },
      {
        key: 'tenants',
        label: t('admin.settings.cards.tenants.label'),
        description: t('admin.settings.cards.tenants.description'),
        target: '/app/settings/tenants',
        roles: ['administrator'],
        section: 'workspace',
        superadminOnly: true,
      },
      {
        key: 'company_access',
        label: t('admin.settings.cards.company_access.label', { defaultValue: 'Company access' }),
        description: t('admin.settings.cards.company_access.description', { defaultValue: 'Control which companies are visible for selected tenant users.' }),
        target: '/app/settings/company-access',
        roles: ['administrator'],
        section: 'team',
      },
      {
        key: 'notifications',
        label: t('admin.settings.cards.notifications.label', { defaultValue: 'Notifications' }),
        description: t('admin.settings.cards.notifications.description', { defaultValue: 'Reminder and notification behavior.' }),
        target: '/app/tasks',
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'automations',
        requiresModules: ['candidates'],
      },
      {
        key: 'communications_setup',
        label: t('app.nav.items.communications_setup', { defaultValue: 'Comms setup' }),
        description: t('admin.settings.cards.communications_setup.description', { defaultValue: 'Guided first-run setup: connect channels, verify inbound, prepare queue.' }),
        target: '/app/setup/communications',
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'integrations',
        requiresModules: ['candidates'],
        requiresCommFeatures: ['messages', 'email'],
      },
      {
        key: 'communications',
        label: t('app.nav.items.settings_communications', { defaultValue: 'Communications settings' }),
        description: t('admin.settings.cards.communications.description', { defaultValue: 'Main communication settings menu with separated domains.' }),
        target: '/app/settings/communications',
        roles: ['administrator', 'supervisor'],
        section: 'integrations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'communications_messengers',
        label: t('admin.settings.cards.communications_messengers.label', { defaultValue: 'Messenger settings' }),
        description: t('admin.settings.cards.communications_messengers.description', { defaultValue: 'Telegram/WhatsApp channels, templates and command presets.' }),
        target: '/app/settings/communications/messengers',
        roles: ['administrator', 'supervisor'],
        section: 'integrations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'communications_queue',
        label: t('admin.settings.cards.communications_queue.label', { defaultValue: 'Queue settings' }),
        description: t('admin.settings.cards.communications_queue.description', { defaultValue: 'Routing strategy and manager allocation queue controls.' }),
        target: '/app/settings/communications/queue',
        roles: ['administrator', 'supervisor'],
        section: 'automations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'communications_sla',
        label: t('admin.settings.cards.communications_sla.label', { defaultValue: 'SLA settings' }),
        description: t('admin.settings.cards.communications_sla.description', { defaultValue: 'Escalation policy for overdue communication threads.' }),
        target: '/app/settings/communications/sla',
        roles: ['administrator', 'supervisor'],
        section: 'automations',
        requiresCommFeatures: ['communicationsAdmin'],
      },
      {
        key: 'email',
        label: t('admin.settings.cards.email.label'),
        description: t('admin.settings.cards.email.description'),
        target: '/app/settings/email',
        roles: ['administrator'],
        section: 'integrations',
      },
      {
        key: 'documents',
        label: t('admin.settings.cards.documents.label'),
        description: t('admin.settings.cards.documents.description'),
        target: '/app/settings/docs',
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['documents'],
      },
      {
        key: 'funnels',
        label: t('admin.settings.cards.funnels.label', { defaultValue: 'Funnels' }),
        description: t('admin.settings.cards.funnels.description', { defaultValue: 'Candidate and lead stages.' }),
        target: '/app/settings/funnels',
        roles: ['administrator', 'supervisor'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'settings-hiring-gates',
        label: t('admin.settings.cards.hiring_gates.label'),
        description: t('admin.settings.cards.hiring_gates.description'),
        target: '/app/settings/hiring-pipeline-gates',
        roles: ['administrator', 'supervisor', 'recruiter', 'viewer'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'risk_intel',
        label: t('admin.settings.cards.risk_intel.label'),
        description: t('admin.settings.cards.risk_intel.description'),
        target: '/app/settings/risk-intel',
        roles: ['administrator', 'supervisor', 'client_manager'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'candidate_profiles',
        label: t('admin.settings.cards.candidate_profiles.label'),
        description: t('admin.settings.cards.candidate_profiles.description'),
        target: '/app/settings/candidate-profiles',
        roles: ['administrator'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'custom_fields',
        label: t('admin.settings.cards.custom_fields.label'),
        description: t('admin.settings.cards.custom_fields.description'),
        target: '/app/settings/custom-fields',
        roles: ['administrator'],
        section: 'crm_setup',
        requiresModules: ['candidates'],
      },
      {
        key: 'billing',
        label: t('admin.settings.cards.billing.label', { defaultValue: 'Billing & subscription' }),
        description: t('admin.settings.cards.billing.description', { defaultValue: 'Plan, payment scenarios and subscription status.' }),
        target: '/app/settings/billing',
        roles: ['administrator'],
        section: 'billing',
      },
      {
        key: 'legal',
        label: t('admin.settings.cards.legal.label'),
        description: t('admin.settings.cards.legal.description'),
        target: '/app/settings/legal',
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'tenant_links',
        label: t('admin.settings.cards.tenant_links.label'),
        description: t('admin.settings.cards.tenant_links.description'),
        target: '/app/settings/tenant-links',
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'integrations',
        label: t('admin.settings.cards.integrations.label'),
        description: t('admin.settings.cards.integrations.description'),
        target: '/app/settings/integrations',
        roles: ['administrator', 'supervisor'],
        section: 'integrations',
        requiresModules: ['leads'],
      },
      {
        key: 'ruleset',
        label: t('admin.settings.cards.ruleset.label'),
        description: t('admin.settings.cards.ruleset.description'),
        target: '/app/settings/ruleset',
        roles: ['administrator', 'supervisor'],
        section: 'automations',
      },
      {
        key: 'audit',
        label: t('admin.settings.cards.audit.label'),
        description: t('admin.settings.cards.audit.description'),
        target: '/app/settings/audit',
        roles: ['administrator'],
        section: 'workspace',
      },
      {
        key: 'profile',
        label: t('admin.settings.cards.profile.label', { defaultValue: 'My profile' }),
        description: t('admin.settings.cards.profile.description', { defaultValue: 'Personal profile, language, security and local preferences.' }),
        target: '/app/profile',
        roles: ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor', 'viewer'],
        section: 'personal',
      },
    ],
    [t],
  )

  const cards = useMemo(
    () =>
      allCards.filter((c) => {
        if (c.superadminOnly && !isSuperAdmin) return false
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
    [allCards, canUseCommunicationsFeature, isSuperAdmin, modules, role],
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

  return (
    <div className="space-y-4">
      <section className="card p-6">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-slate-900">{t('admin.settings.title')}</h2>
          <p className="text-sm text-slate-500">{t('admin.settings.subtitle')}</p>
        </header>
        <div className="space-y-4">
          {grouped.map((section) => (
            <section key={section.key} className="space-y-3">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{section.label}</h3>
                <p className="mt-1 text-sm text-slate-500">{section.description}</p>
              </div>
              <ul className="grid gap-4 md:grid-cols-2">
                {section.items.map((item) => (
                  <li key={item.target} className="rounded-2xl border border-brand-100 bg-brand-50/30 p-4">
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
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>
    </div>
  )
}
