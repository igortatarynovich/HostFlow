import { Link } from 'react-router-dom'
import { IconLock } from '@tabler/icons-react'

import { nbaGroupHref, type NextActionGroup } from '../../api/nextActions'
import { useI18n } from '../../i18n'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { NBA_QUICK_PROCESS_NEW_GROUP_IDS, NBA_QUICK_REMINDER_GROUP_IDS } from './nbaQuickConstants'

type NbaNextActionsChipsProps = {
  groups: NextActionGroup[]
  nbaQuickLoadingGroupId: string | null
  onQuickFollowUp: (g: NextActionGroup) => void | Promise<void>
  /** Team-tier (automation / bulk process); solo shows upgrade link for process-new. */
  teamTierFeatures: boolean
  onQuickProcessNew: (g: NextActionGroup) => void | Promise<void>
  /** Extra wrapper classes for the flex row (e.g. mt-2). */
  className?: string
}

export function NbaNextActionsChips({
  groups,
  nbaQuickLoadingGroupId,
  onQuickFollowUp,
  teamTierFeatures,
  onQuickProcessNew,
  className = 'mt-2 flex flex-wrap gap-2',
}: NbaNextActionsChipsProps) {
  const { t } = useI18n()
  const visible = groups.filter((g) => g.count > 0)
  if (!visible.length) return null

  return (
    <div className={className}>
      {visible.map((g) =>
        g.locked ? (
          <Link
            key={g.id}
            to={`${ACTIVATION_PATHS.billing}?focus=plan`}
            title={t('app.leads.nba.locked_hint')}
            aria-label={`${g.title}: ${t('app.leads.nba.locked_hint')}`}
            className="inline-flex max-w-full items-center gap-1 rounded-lg border border-slate-300 bg-slate-100/90 px-2.5 py-1 text-left text-xs text-slate-600 hover:bg-slate-200"
          >
            <IconLock size={12} className="shrink-0 text-slate-500" aria-hidden />
            <span className="font-medium">{g.title}</span>
            <span className="tabular-nums text-slate-500">({g.count})</span>
            <span className="text-[10px] font-medium uppercase text-slate-500">
              {String(g.required_plan || '').toLowerCase() === 'pro' ? t('app.leads.nba.badge_pro') : t('app.leads.nba.badge_team')}
            </span>
          </Link>
        ) : (
          <div key={g.id} className="inline-flex max-w-full flex-wrap items-center gap-1">
            <Link
              to={nbaGroupHref(g)}
              className={
                g.entity === 'candidate'
                  ? 'inline-flex max-w-full items-center gap-1 rounded-lg border border-indigo-200 bg-indigo-50/90 px-2.5 py-1 text-left text-xs text-indigo-950 hover:bg-indigo-100'
                  : 'inline-flex max-w-full items-center gap-1 rounded-lg border border-amber-200 bg-amber-50/90 px-2.5 py-1 text-left text-xs text-amber-950 hover:bg-amber-100'
              }
            >
              <span className="font-medium">{g.title}</span>
              <span
                className={g.entity === 'candidate' ? 'tabular-nums text-indigo-800' : 'tabular-nums text-amber-800'}
              >
                ({g.count})
              </span>
            </Link>
            {NBA_QUICK_REMINDER_GROUP_IDS.has(g.id) ? (
              <button
                type="button"
                className={
                  g.entity === 'candidate'
                    ? 'rounded-md border border-indigo-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-900 hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60'
                    : 'rounded-md border border-amber-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60'
                }
                disabled={nbaQuickLoadingGroupId === g.id}
                onClick={() => void onQuickFollowUp(g)}
              >
                {nbaQuickLoadingGroupId === g.id ? t('common.loading') : t('app.leads.nba.do_now')}
              </button>
            ) : null}
            {NBA_QUICK_PROCESS_NEW_GROUP_IDS.has(g.id) ? (
              teamTierFeatures ? (
                <button
                  type="button"
                  className="rounded-md border border-emerald-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={nbaQuickLoadingGroupId === g.id}
                  onClick={() => void onQuickProcessNew(g)}
                >
                  {nbaQuickLoadingGroupId === g.id ? t('common.loading') : t('app.leads.nba.process_new')}
                </button>
              ) : (
                <Link
                  to={`${ACTIVATION_PATHS.billing}?focus=plan`}
                  title={t('app.leads.nba.process_new_upgrade_hint')}
                  className="inline-flex items-center gap-0.5 rounded-md border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-100"
                >
                  <IconLock size={11} className="shrink-0 text-slate-500" aria-hidden />
                  {t('app.leads.nba.process_new')}
                </Link>
              )
            ) : null}
          </div>
        ),
      )}
    </div>
  )
}
