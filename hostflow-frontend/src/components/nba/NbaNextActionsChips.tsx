import { IconLock } from '@tabler/icons-react'

import { nbaGroupHref, type NextActionGroup } from '../../api/nextActions'
import { useI18n } from '../../i18n'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { Chip } from '../ui/Chip'
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

function nbaChipTitle(t: (key: string, options?: { defaultValue?: string; values?: Record<string, string | number> }) => string, g: NextActionGroup) {
  const d = g.nba_detail || {}
  const rootCode = typeof d.conversion_root === 'string' ? d.conversion_root : ''
  const rootLabel = rootCode ? t(`app.leads.conversion_funnel.roots.${rootCode}`) : ''
  const key = `app.leads.nba.groups.${g.id}`
  const translated = t(key, {
    defaultValue: '',
    values: {
      root: rootLabel || rootCode,
      pct: d.pct != null ? d.pct : '',
      days: d.days != null ? d.days : '',
      count: g.count,
    },
  })
  return translated && translated !== key ? translated : g.title
}

const ENTITY_CHIP_CLASS = {
  candidate:
    'rounded-lg border-brand-200 bg-brand-50/90 text-left text-brand-950 hover:bg-brand-100',
  lead: 'rounded-lg border-amber-200 bg-amber-50/90 text-left text-amber-950 hover:bg-amber-100',
} as const

const ENTITY_COUNT_CLASS = {
  candidate: 'tabular-nums text-brand-800',
  lead: 'tabular-nums text-amber-800',
} as const

const ENTITY_ACTION_CLASS = {
  candidate:
    'rounded-md border-brand-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-900 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-60',
  lead: 'rounded-md border-amber-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60',
} as const

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
      {visible.map((g) => {
        const chipTitle = nbaChipTitle(t, g)
        const entity = g.entity === 'candidate' ? 'candidate' : 'lead'

        if (g.locked) {
          const lockedHint = t('app.leads.nba.locked_hint')
          return (
            <Chip
              key={g.id}
              behavior="action"
              href={`${ACTIVATION_PATHS.billing}?focus=plan`}
              title={lockedHint}
              ariaLabel={`${chipTitle}: ${lockedHint}`}
              size="md"
              className="rounded-lg border-slate-300 bg-slate-100/90 text-left text-slate-600 hover:bg-slate-200"
              label={
                <>
                  <IconLock size={12} className="shrink-0 text-slate-500" aria-hidden />
                  <span className="font-medium">{chipTitle}</span>
                  <span className="tabular-nums text-slate-500">({g.count})</span>
                  <span className="text-[10px] font-medium uppercase text-slate-500">
                    {String(g.required_plan || '').toLowerCase() === 'pro'
                      ? t('app.leads.nba.badge_pro')
                      : t('app.leads.nba.badge_team')}
                  </span>
                </>
              }
            />
          )
        }

        const loading = nbaQuickLoadingGroupId === g.id

        return (
          <div key={g.id} className="inline-flex max-w-full flex-wrap items-center gap-1">
            <Chip
              behavior="action"
              href={nbaGroupHref(g)}
              size="md"
              className={ENTITY_CHIP_CLASS[entity]}
              label={
                <>
                  <span className="font-medium">{chipTitle}</span>
                  <span className={ENTITY_COUNT_CLASS[entity]}>({g.count})</span>
                </>
              }
            />
            {NBA_QUICK_REMINDER_GROUP_IDS.has(g.id) ? (
              <Chip
                behavior="action"
                size="sm"
                disabled={loading}
                className={ENTITY_ACTION_CLASS[entity]}
                onClick={() => void onQuickFollowUp(g)}
                label={loading ? t('common.loading') : t('app.leads.nba.do_now')}
              />
            ) : null}
            {NBA_QUICK_PROCESS_NEW_GROUP_IDS.has(g.id) ? (
              teamTierFeatures ? (
                <Chip
                  behavior="action"
                  size="sm"
                  disabled={loading}
                  className="rounded-md border-emerald-300 bg-white px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => void onQuickProcessNew(g)}
                  label={loading ? t('common.loading') : t('app.leads.nba.process_new')}
                />
              ) : (
                <Chip
                  behavior="action"
                  href={`${ACTIVATION_PATHS.billing}?focus=plan`}
                  title={t('app.leads.nba.process_new_upgrade_hint')}
                  size="sm"
                  className="inline-flex items-center gap-0.5 rounded-md border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700 hover:bg-slate-100"
                  label={
                    <>
                      <IconLock size={11} className="shrink-0 text-slate-500" aria-hidden />
                      {t('app.leads.nba.process_new')}
                    </>
                  }
                />
              )
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
