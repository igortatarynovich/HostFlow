import type { ComponentType } from 'react'
import { Link } from 'react-router-dom'
import {
  IconAdjustments,
  IconCreditCard,
  IconLayoutGrid,
  IconPlugConnected,
  IconSettings,
  IconShield,
  IconUsers,
  IconUserCircle,
} from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'

type SettingsChromeProps = {
  pathname: string
  compactMode?: boolean
}

type NavItem = {
  key: string
  label: string
  to: string
  icon: ComponentType<{ size?: number; className?: string }>
  visible: boolean
}

const isActive = (pathname: string, target: string): boolean => {
  if (target === '/app/settings') return pathname === '/app/settings'
  return pathname.startsWith(target)
}

export function SettingsChrome({ pathname, compactMode = false }: SettingsChromeProps) {
  const { t } = useI18n()
  const { can } = usePermissions()

  const items: NavItem[] = [
    {
      key: 'overview',
      label: t('app.settings.chrome.overview', { defaultValue: 'Overview' }),
      to: '/app/settings',
      icon: IconLayoutGrid,
      visible: can('settings.view') || can('admin.users'),
    },
    {
      key: 'workspace',
      label: t('app.settings.chrome.workspace', { defaultValue: 'Workspace' }),
      to: '/app/settings/company-access',
      icon: IconSettings,
      visible: can('admin.companyAcl') || can('admin.users'),
    },
    {
      key: 'crm',
      label: t('app.settings.chrome.crm_setup', { defaultValue: 'CRM setup' }),
      to: '/app/settings/funnels',
      icon: IconAdjustments,
      visible: can('admin.users') || can('users.manage'),
    },
    {
      key: 'team',
      label: t('app.settings.chrome.team', { defaultValue: 'Team' }),
      to: '/app/settings/users',
      icon: IconUsers,
      visible: can('admin.users') || can('users.manage') || can('users.view'),
    },
    {
      key: 'billing',
      label: t('app.settings.chrome.billing', { defaultValue: 'Billing' }),
      to: '/app/settings/billing',
      icon: IconCreditCard,
      visible: can('admin.users'),
    },
    {
      key: 'integrations',
      label: t('app.settings.chrome.integrations', { defaultValue: 'Integrations' }),
      to: '/app/settings/integrations',
      icon: IconPlugConnected,
      visible: can('admin.metaLeads') || can('admin.users'),
    },
    {
      key: 'security',
      label: t('app.settings.chrome.security', { defaultValue: 'Security' }),
      to: '/app/settings/audit',
      icon: IconShield,
      visible: can('admin.deletionQueue') || can('admin.users'),
    },
    {
      key: 'personal',
      label: t('app.settings.chrome.personal', { defaultValue: 'Personal' }),
      to: '/app/profile',
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
    <section className="mb-4 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            {t('app.settings.chrome.title', { defaultValue: 'Settings' })}
          </h1>
          <p className="text-xs text-slate-500">
            {t('app.settings.chrome.subtitle', {
              defaultValue: 'Responsibility-first setup: workspace, CRM, team, billing, integrations, personal.',
            })}
          </p>
        </div>
      </div>

      <nav className="mt-3 flex flex-wrap gap-2">
        {visibleItems.map((item) => {
          const active = isActive(pathname, item.to)
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
