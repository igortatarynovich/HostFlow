import { Link } from 'react-router-dom'
import {
  type Icon as TablerIcon,
  IconBriefcase,
  IconBuildingStore,
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
      visible: can('companies.view') || can('admin.companyAcl') || can('admin.users') || can('settings.view'),
    },
    {
      key: 'recruitment_setup',
      label: t('app.settings.chrome.recruitment_setup', { defaultValue: 'Recruitment' }),
      to: settingsChromeTabHref('recruitment_setup'),
      icon: IconBriefcase,
      visible: can('admin.users') || can('users.manage'),
    },
    {
      key: 'sales_setup',
      label: t('app.settings.chrome.sales_setup', { defaultValue: 'Sales' }),
      to: settingsChromeTabHref('sales_setup'),
      icon: IconBuildingStore,
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
      visible: can('admin.metaLeads') || can('admin.users') || can('settings.view') || can('notifications.view'),
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

  return (
    <section className="mb-0 shrink-0 rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white px-3 py-2.5 shadow-none">
      <nav className="flex flex-wrap gap-2">
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
    </section>
  )
}
