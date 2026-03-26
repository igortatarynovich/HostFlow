import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconSparkles } from '@tabler/icons-react'

import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import { fetchLeadNextActions, type LeadNextActionsResponse } from '../../api/nextActions'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { BulkActivitiesModal } from '../../modules/candidates/components'
import { NbaNextActionsChips } from './NbaNextActionsChips'
import { useNbaQuickBulkFlow } from './useNbaQuickBulkFlow'

export function TopbarNbaMenu() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const [open, setOpen] = useState(false)
  const [nba, setNba] = useState<LeadNextActionsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const wrapRef = useRef<HTMLDivElement | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetchLeadNextActions()
      setNba(r)
    } catch {
      setNba(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (!open) return
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  const nbaBulk = useNbaQuickBulkFlow({
    onNbaSuccess: load,
  })

  const actionableSum = useMemo(() => {
    if (!nba?.groups?.length) return 0
    return nba.groups.filter((g) => !g.locked).reduce((acc, g) => acc + (g.count > 0 ? g.count : 0), 0)
  }, [nba])

  const hasQueues = Boolean(nba?.groups?.some((g) => g.count > 0))

  if (!can('leads.view')) return null

  return (
    <>
      <div className="relative" ref={wrapRef}>
        <button
          type="button"
          className={[
            'relative inline-flex items-center gap-1 rounded-md border px-2.5 text-sm font-semibold transition sm:gap-2 sm:px-3',
            hasQueues
              ? 'border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100'
              : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
          ].join(' ')}
          aria-haspopup="dialog"
          aria-expanded={open}
          title={t('app.topbar.nba.button_title')}
          onClick={() => {
            setOpen((v) => !v)
            void load()
          }}
        >
          <IconSparkles size={18} stroke={1.85} className="shrink-0" aria-hidden />
          <span className="hidden sm:inline">
            {t('app.topbar.nba.button')}
          </span>
          {actionableSum > 0 ? (
            <span className="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-amber-600 px-1 text-[11px] font-bold text-white tabular-nums">
              {actionableSum > 99 ? '99+' : actionableSum}
            </span>
          ) : null}
        </button>

        {open ? (
          <div
            className="absolute right-0 top-10 z-50 w-[min(calc(100vw-1.5rem),22rem)] max-h-[min(70vh,28rem)] overflow-y-auto rounded-xl border border-slate-200 bg-white py-3 shadow-2xl"
            role="dialog"
            aria-label={t('app.topbar.nba.panel_title')}
          >
            <div className="border-b border-slate-100 px-3 pb-2">
              <div className="text-sm font-semibold text-slate-900">
                {t('app.topbar.nba.panel_title')}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">
                {loading ? t('common.loading') : t('app.topbar.nba.panel_hint')}
              </p>
              {!loading ? (
                <p className="mt-1.5 text-[11px] leading-snug text-slate-500">
                  <span>{t('app.dashboard.nba.playbook_hint_before')}</span>{' '}
                  <Link
                    className="font-medium text-brand-700 hover:underline"
                    to={ACTIVATION_PATHS.leads}
                    onClick={() => setOpen(false)}
                  >
                    {t('app.dashboard.nba.playbook_hint_link')}
                  </Link>
                  <span>{t('app.dashboard.nba.playbook_hint_after')}</span>
                </p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <Link
                  className="text-xs font-medium text-brand-700 hover:underline"
                  to={ACTIVATION_PATHS.leads}
                  onClick={() => setOpen(false)}
                >
                  {t('app.topbar.nba.open_leads')}
                </Link>
                <span className="text-slate-300">·</span>
                <Link
                  className="text-xs font-medium text-brand-700 hover:underline"
                  to={ACTIVATION_PATHS.overview}
                  onClick={() => setOpen(false)}
                >
                  {t('app.topbar.nba.open_dashboard')}
                </Link>
              </div>
            </div>
            <div className="px-3 pt-2">
              {nba && hasQueues ? (
                <NbaNextActionsChips
                  groups={nba.groups}
                  nbaQuickLoadingGroupId={nbaBulk.nbaQuickLoadingGroupId}
                  onQuickFollowUp={async (g) => {
                    await nbaBulk.openNbaQuickFollowUp(g)
                    setOpen(false)
                  }}
                  teamTierFeatures={nba.nba_tier === 'team'}
                  onQuickProcessNew={async (g) => {
                    await nbaBulk.openNbaQuickProcessNewLeads(g)
                    setOpen(false)
                  }}
                  className="flex flex-col gap-2"
                />
              ) : !loading ? (
                <p className="text-xs text-slate-500">
                  {t('app.topbar.nba.empty')}
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      <BulkActivitiesModal
        open={nbaBulk.bulkActivitiesOpen}
        onClose={() => !nbaBulk.bulkActivitiesLoading && nbaBulk.closeBulkActivitiesModal()}
        hint={nbaBulk.bulkActivitiesHint}
        title={nbaBulk.bulkActivityTitle}
        dueAt={nbaBulk.bulkActivityDueAt}
        offsetMinutes={nbaBulk.bulkActivityOffsetMinutes}
        onTitleChange={nbaBulk.setBulkActivityTitle}
        onDueAtChange={nbaBulk.setBulkActivityDueAt}
        onOffsetMinutesChange={nbaBulk.setBulkActivityOffsetMinutes}
        onApply={() => void nbaBulk.applyBulkActivities([])}
        loading={nbaBulk.bulkActivitiesLoading}
        activityType={nbaBulk.bulkActivityType}
        onActivityTypeChange={nbaBulk.setBulkActivityType}
      />
    </>
  )
}
