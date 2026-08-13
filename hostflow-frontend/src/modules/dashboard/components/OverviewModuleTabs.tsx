import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'

import { getTenantModules } from '../../../api/tenants'
import type { TenantModuleSettings } from '../../../api/types'
import { usePermissions } from '../../../hooks/usePermissions'
import { useI18n } from '../../../i18n'

/** Analytics hub tabs — system summary + licensed business modules (module-owned content). */
export type OverviewModuleTab =
  | 'summary'
  | 'recruitment'
  | 'marketing'
  | 'sales'
  | 'hr'
  | 'finance'
  | 'fleet'

export type OverviewModuleTabsProps = {
  active: OverviewModuleTab
  onChange: (tab: OverviewModuleTab) => void
  /** Called when available tabs resolve (for default selection). */
  onTabsReady?: (tabs: OverviewModuleTab[]) => void
}

type TabDef = {
  key: OverviewModuleTab
  label: string
}

const MODULE_DEFAULTS: TenantModuleSettings = {
  candidates: true,
  companies: true,
  vacancies: true,
  documents: true,
  leads: true,
  services: true,
  client_portal: true,
  hr: true,
}

function moduleOn(mods: TenantModuleSettings | null, key: keyof TenantModuleSettings): boolean {
  if (mods && Object.prototype.hasOwnProperty.call(mods, key)) return Boolean(mods[key])
  return Boolean(MODULE_DEFAULTS[key])
}

/**
 * Tabs for the system Analytics host (`overview.*`).
 * Shows system «Сводка» always, plus licensed/connected business modules only.
 */
export function OverviewModuleTabs({ active, onChange, onTabsReady }: OverviewModuleTabsProps) {
  const { t } = useI18n()
  const { can } = usePermissions()
  const [mods, setMods] = useState<TenantModuleSettings | null>(null)

  useEffect(() => {
    let mounted = true
    void getTenantModules()
      .then((data) => {
        if (mounted) setMods(data)
      })
      .catch(() => {
        if (mounted) setMods(null)
      })
    return () => {
      mounted = false
    }
  }, [])

  const tabs = useMemo(() => {
    const out: TabDef[] = [
      {
        key: 'summary',
        label: t('app.dashboard.tabs.summary', { defaultValue: 'Summary' }),
      },
    ]

    const recruitmentLicensed =
      moduleOn(mods, 'candidates') || moduleOn(mods, 'vacancies') || moduleOn(mods, 'leads')
    if (recruitmentLicensed && (can('candidates.view') || can('leads.view') || can('vacancies.view'))) {
      out.push({
        key: 'recruitment',
        label: t('app.dashboard.tabs.recruitment', { defaultValue: 'Recruitment' }),
      })
    }

    // Marketing = Acquisition under Sales host (ADR-023); not a 6th product deploy host.
    const marketingLicensed = moduleOn(mods, 'companies') || moduleOn(mods, 'leads')
    if (marketingLicensed && (can('companies.view') || can('leads.view'))) {
      out.push({
        key: 'marketing',
        label: t('app.dashboard.tabs.marketing', { defaultValue: 'Marketing' }),
      })
    }

    const salesLicensed = moduleOn(mods, 'companies') || moduleOn(mods, 'services')
    if (salesLicensed && (can('companies.view') || can('services.view'))) {
      out.push({
        key: 'sales',
        label: t('app.dashboard.tabs.sales', { defaultValue: 'Sales' }),
      })
    }

    if (moduleOn(mods, 'hr') && can('workforce.view')) {
      out.push({
        key: 'hr',
        label: t('app.dashboard.tabs.hr', { defaultValue: 'HR' }),
      })
    }

    // Finance UI is gated by services today (invoices). Show only when services is on.
    if (moduleOn(mods, 'services') && can('services.view')) {
      out.push({
        key: 'finance',
        label: t('app.dashboard.tabs.finance', { defaultValue: 'Finance' }),
      })
    }

    // Fleet: same surface gate as Topbar (companies.view); API confirms module status.
    if (can('companies.view')) {
      out.push({
        key: 'fleet',
        label: t('app.dashboard.tabs.fleet', { defaultValue: 'Fleet' }),
      })
    }

    return out
  }, [can, mods, t])

  useEffect(() => {
    onTabsReady?.(tabs.map((tab) => tab.key))
  }, [tabs, onTabsReady])

  if (tabs.length === 0) return null

  return (
    <div className="border-b border-slate-200 bg-white px-4 pt-2 sm:px-4 lg:px-8">
      <nav
        className="flex max-w-full flex-wrap items-center gap-1 overflow-x-auto pb-0 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label={t('app.dashboard.tabs.aria', { defaultValue: 'Analytics modules' })}
        role="tablist"
      >
        {tabs.map((tab) => {
          const selected = active === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={selected}
              className={clsx(
                'shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition',
                selected
                  ? 'bg-slate-100 text-brand-800 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
              )}
              onClick={() => onChange(tab.key)}
            >
              {tab.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}

export function parseOverviewModuleTab(raw: string | null | undefined): OverviewModuleTab | null {
  const v = String(raw || '')
    .trim()
    .toLowerCase()
  if (v === 'summary' || v === 'general' || v === 'overview' || v === 'platform') return 'summary'
  if (v === 'recruitment' || v === 'recruit') return 'recruitment'
  if (v === 'marketing' || v === 'acquisition' || v === 'ads') return 'marketing'
  if (v === 'sales' || v === 'commercial') return 'sales'
  if (v === 'hr' || v === 'workforce') return 'hr'
  if (v === 'finance' || v === 'invoices') return 'finance'
  if (v === 'fleet') return 'fleet'
  return null
}
