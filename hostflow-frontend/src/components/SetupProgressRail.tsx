import { Link } from 'react-router-dom'
import { IconCircle } from '@tabler/icons-react'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

type Props = {
  visible: boolean
  showClearDemo?: boolean
  clearDemoBusy?: boolean
  onClearDemo?: () => void | Promise<void>
}

/**
 * Non-blocking setup checklist (fixed right rail) — shown after demo onboarding seed.
 */
export function SetupProgressRail({ visible, showClearDemo, clearDemoBusy, onClearDemo }: Props) {
  const { t } = useI18n()
  if (!visible) return null

  const items = [
    { id: 'logo', label: t('app.setup_rail.logo'), href: CRM_APP_PATHS.settingsTenants },
    { id: 'hours', label: t('app.setup_rail.hours'), href: CRM_APP_PATHS.myAvailability },
    { id: 'team', label: t('app.setup_rail.team'), href: CRM_APP_PATHS.settingsUsers },
    {
      id: 'tg',
      label: t('app.setup_rail.telegram'),
      href: CRM_APP_PATHS.settingsIntegrations,
    },
  ]

  return (
    <aside
      className="pointer-events-auto fixed right-4 top-24 z-30 hidden w-56 rounded-xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur-sm lg:block"
      aria-label={t('app.setup_rail.title')}
    >
      <div className="text-xs font-semibold text-slate-900">
        {t('app.setup_rail.title')}
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-full w-[40%] rounded-full bg-brand-500" />
      </div>
      <div className="mt-1 text-[10px] font-medium text-slate-500">40%</div>
      <ul className="mt-3 space-y-2">
        {items.map((it) => (
          <li key={it.id}>
            <Link
              to={it.href}
              className="flex items-start gap-2 rounded-lg px-1 py-1 text-xs text-slate-700 hover:bg-slate-50 hover:text-brand-800"
            >
              <IconCircle size={14} stroke={1.6} className="mt-0.5 shrink-0 text-slate-400" />
              <span>{it.label}</span>
            </Link>
          </li>
        ))}
      </ul>
      {showClearDemo && typeof onClearDemo === 'function' ? (
        <div className="mt-3 border-t border-slate-100 pt-2">
          <button
            type="button"
            className="w-full rounded-lg border border-rose-200 bg-rose-50 px-2 py-1.5 text-left text-[11px] font-medium text-rose-900 hover:bg-rose-100 disabled:opacity-60"
            disabled={clearDemoBusy}
            onClick={() => {
              void onClearDemo()
            }}
          >
            {t('app.setup_rail.clear_demo')}
          </button>
          <p className="mt-1 text-[10px] leading-snug text-slate-500">
            {t('app.setup_rail.clear_demo_hint')}
          </p>
        </div>
      ) : null}
      <p className="mt-3 border-t border-slate-100 pt-2 text-[10px] leading-snug text-slate-500">
        {t('app.setup_rail.footer')}
      </p>
    </aside>
  )
}
