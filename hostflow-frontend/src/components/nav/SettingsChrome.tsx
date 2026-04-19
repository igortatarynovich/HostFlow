import { Link } from 'react-router-dom'
import {
  type Icon as TablerIcon,
  IconAdjustments,
  IconCreditCard,
  IconLayoutGrid,
  IconPlugConnected,
  IconRobot,
  IconSettings,
  IconShield,
  IconUsers,
  IconUserCircle,
} from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  isSettingsChromeTabActive,
  settingsChromeTabHref,
  type SettingsChromeTabKey,
} from '../../nav/settingsChromeNav'
import { PageBreadcrumb } from './PageBreadcrumb'
type SettingsChromeProps = {
  pathname: string
  search: string
  compactMode?: boolean
}

type NavItem = {
  key: SettingsChromeTabKey
  label: string
  to: string
  icon: TablerIcon
  visible: boolean
}

export function SettingsChrome({ pathname, search, compactMode = false }: SettingsChromeProps) {
  const { t } = useI18n()
  const { can } = usePermissions()

  const items: NavItem[] = [
    {
      key: 'overview',
      label: t('app.settings.chrome.overview', { defaultValue: 'Overview' }),
      to: settingsChromeTabHref('overview'),
      icon: IconLayoutGrid,
      visible: can('settings.view') || can('admin.users'),
    },
    {
      key: 'workspace',
      label: t('app.settings.chrome.workspace', { defaultValue: 'Workspace' }),
      to: settingsChromeTabHref('workspace'),
      icon: IconSettings,
      visible: can('admin.companyAcl') || can('admin.users'),
    },
    {
      key: 'crm_setup',
      label: t('app.settings.chrome.crm_setup', { defaultValue: 'CRM setup' }),
      to: settingsChromeTabHref('crm_setup'),
      icon: IconAdjustments,
      visible: can('admin.users') || can('users.manage'),
    },
    {
      key: 'team',
      label: t('app.settings.chrome.team', { defaultValue: 'Team' }),
      to: settingsChromeTabHref('team'),
      icon: IconUsers,
      visible: can('admin.users') || can('users.manage') || can('users.view'),
    },
    {
      key: 'automations',
      label: t('app.settings.chrome.automations', { defaultValue: 'Automations' }),
      to: settingsChromeTabHref('automations'),
      icon: IconRobot,
      visible: can('notifications.view') || can('admin.ruleset') || can('admin.users'),
    },
    {
      key: 'integrations',
      label: t('app.settings.chrome.integrations', { defaultValue: 'Integrations' }),
      to: settingsChromeTabHref('integrations'),
      icon: IconPlugConnected,
      visible: can('admin.metaLeads') || can('admin.users'),
    },
    {
      key: 'billing',
      label: t('app.settings.chrome.billing', { defaultValue: 'Billing' }),
      to: settingsChromeTabHref('billing'),
      icon: IconCreditCard,
      visible: can('admin.users'),
    },
    {
      key: 'security',
      label: t('app.settings.chrome.security', { defaultValue: 'Security' }),
      to: settingsChromeTabHref('security'),
      icon: IconShield,
      visible: can('admin.deletionQueue') || can('admin.users'),
    },
    {
      key: 'personal',
      label: t('app.settings.chrome.personal', { defaultValue: 'Personal' }),
      to: settingsChromeTabHref('personal'),
      icon: IconUserCircle,
      visible: true,
    },
  ]

  const visibleItems = items.filter((item) => {
    if (!item.visible) return false
    if (!compactMode) return true
    return item.key === 'billing' || item.key === 'personal'
  })

  const settingsRoot = CRM_APP_PATHS.settings.replace(/\/+$/, '') || '/'
  const pathNorm = pathname.replace(/\/+$/, '') || '/'
  /** Root `/app/settings` already has a full CRM contours grid on the landing; avoid duplicating the strip there. */
  const showCrmWayfinding = pathNorm !== settingsRoot

  return (
    <section className="mb-0 rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white px-3 py-2.5 shadow-none">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            {t('app.settings.chrome.title', { defaultValue: 'Settings' })}
          </h1>
          <p className="text-xs text-slate-500">
            {t('app.settings.chrome.subtitle', {
              defaultValue: 'Responsibility-first setup: workspace, CRM, team, automations, integrations, billing, personal.',
            })}
          </p>
        </div>
      </div>

      <nav className="mt-3 flex flex-wrap gap-2">
        {visibleItems.map((item) => {
          const active = isSettingsChromeTabActive(item.key, pathname, search)
          const Icon = item.icon
          return (
            <Link
              key={item.key}
              to={item.to}
              className={[
                'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition',
                active
                  ? 'border-brand-300 bg-brand-50 text-brand-800'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
              ].join(' ')}
            >
              <Icon size={14} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {showCrmWayfinding ? (
        <div className="mt-3">
          <PageBreadcrumb />
        </div>
      ) : null}
    </section>
  )
}
