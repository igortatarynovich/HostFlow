import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconRefresh } from '@tabler/icons-react'

import { listLeads } from '../../api/client'
import type { Lead, LeadListResponse } from '../../api/types'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'
import {
  fetchLeadNextActions,
  type LeadNextActionsResponse,
  type NextActionGroup,
} from '../../api/nextActions'
import LeadNextActionPlaybook from '../leads/LeadNextActionPlaybook'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { BulkActivitiesModal } from '../../modules/candidates/components'
import { NbaNextActionsChips } from './NbaNextActionsChips'
import { useNbaQuickBulkFlow } from './useNbaQuickBulkFlow'

const DATE_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
}

const LOCALE_TO_DATE = {
  en: 'en-US',
  ru: 'ru-RU',
  pl: 'pl-PL',
} as const

function isLeadsWorkspacePath(path: string | undefined): boolean {
  const defaultPath = ACTIVATION_PATHS.leads
  const p = (path || defaultPath).replace(/\/+$/, '') || defaultPath
  return p === defaultPath || p.endsWith('/leads')
}

/** First non-empty lead NBA group: prefer unlocked (same sort as API: unlocked before locked). */
function pickPlaybookLeadGroup(groups: NextActionGroup[] | undefined): NextActionGroup | null {
  const candidates = (groups || []).filter(
    (g) => g.entity === 'lead' && g.count > 0 && isLeadsWorkspacePath(g.path),
  )
  const unlocked = candidates.find((g) => !g.locked)
  return unlocked ?? candidates[0] ?? null
}

export function DashboardNbaSection() {
  const { t, locale } = useI18n()
  const { can } = usePermissions()
  const [nba, setNba] = useState<LeadNextActionsResponse | null>(null)
  /** Start true so the first paint mounts the section and `useEffect` can load (avoids flash-null). */
  const [nbaLoading, setNbaLoading] = useState(true)
  const [playbookLead, setPlaybookLead] = useState<Lead | null>(null)
  const [playbookLoading, setPlaybookLoading] = useState(false)

  const dateFormatter = useMemo(() => {
    const localeCode = LOCALE_TO_DATE[locale as keyof typeof LOCALE_TO_DATE] || 'en-US'
    try {
      return new Intl.DateTimeFormat(localeCode, DATE_FORMAT_OPTIONS)
    } catch {
      return new Intl.DateTimeFormat('en-US', DATE_FORMAT_OPTIONS)
    }
  }, [locale])

  const formatDueAt = useCallback(
    (value?: string | null) => {
      if (!value) return '—'
      try {
        return dateFormatter.format(new Date(value))
      } catch {
        return String(value)
      }
    },
    [dateFormatter],
  )

  const refreshNba = useCallback(async () => {
    setNbaLoading(true)
    try {
      const r = await fetchLeadNextActions()
      setNba(r)
    } catch {
      setNba(null)
    } finally {
      setNbaLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshNba()
  }, [refreshNba])

  useEffect(() => {
    if (nbaLoading || !nba) return
    const group = pickPlaybookLeadGroup(nba.groups)
    if (!group) {
      setPlaybookLead(null)
      setPlaybookLoading(false)
      return
    }
    let cancelled = false
    setPlaybookLoading(true)
    void (async () => {
      try {
        const res = (await listLeads({
          status: group.query.status || undefined,
          stage: group.query.stage || undefined,
          nextAction: group.query.next_action || undefined,
          limit: 1,
          offset: 0,
        })) as LeadListResponse
        const first = res.items?.[0] ?? null
        if (!cancelled) setPlaybookLead(first)
      } catch {
        if (!cancelled) setPlaybookLead(null)
      } finally {
        if (!cancelled) setPlaybookLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [nba, nbaLoading])

  const nbaBulk = useNbaQuickBulkFlow({
    onNbaSuccess: refreshNba,
  })

  if (!can('leads.view')) return null

  const hasAny = Boolean(nba?.groups?.some((g) => g.count > 0))

  return (
    <>
      <div className="mb-4 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-slate-900">
              {t('app.dashboard.nba.title')}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">
              {t('app.dashboard.nba.subtitle')}
            </div>
            <p className="mt-1 max-w-xl text-[11px] leading-snug text-slate-500">
              <span>{t('app.dashboard.nba.playbook_hint_before')}</span>{' '}
              <Link to={ACTIVATION_PATHS.leads} className="font-medium text-brand-700 hover:underline">
                {t('app.dashboard.nba.playbook_hint_link')}
              </Link>
              <span>{t('app.dashboard.nba.playbook_hint_after')}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex items-center gap-1 btn-sm"
              disabled={nbaLoading}
              onClick={() => void refreshNba()}
              title={t('common.actions.refresh')}
            >
              <IconRefresh size={14} className={nbaLoading ? 'animate-spin' : ''} aria-hidden />
              {nbaLoading ? t('common.loading') : t('common.actions.refresh')}
            </button>
            <Link className="btn-secondary btn-sm" to={ACTIVATION_PATHS.leads}>
              {t('app.dashboard.nba.open_leads')}
            </Link>
          </div>
        </div>
        {nbaLoading ? (
          <div className="mt-2 text-xs text-slate-500">{t('app.dashboard.nba.loading')}</div>
        ) : !nba ? (
          <div className="mt-2 text-xs text-rose-700">{t('app.dashboard.nba.load_error')}</div>
        ) : hasAny ? (
          <>
            <NbaNextActionsChips
              groups={nba.groups}
              nbaQuickLoadingGroupId={nbaBulk.nbaQuickLoadingGroupId}
              onQuickFollowUp={nbaBulk.openNbaQuickFollowUp}
              teamTierFeatures={nba.nba_tier === 'team'}
              onQuickProcessNew={nbaBulk.openNbaQuickProcessNewLeads}
            />
            {playbookLoading ? (
              <div className="mt-2 text-xs text-slate-500">{t('app.dashboard.nba.playbook_loading')}</div>
            ) : playbookLead ? (
              <LeadNextActionPlaybook
                lead={playbookLead}
                formatDueAt={formatDueAt}
                className="mt-2"
              />
            ) : null}
          </>
        ) : (
          <div className="mt-2 rounded-lg border border-emerald-100 bg-emerald-50/60 px-3 py-2 text-xs text-emerald-950">
            <div className="font-medium">{t('app.dashboard.nba.all_clear_title')}</div>
            <p className="mt-0.5 text-emerald-900/90">{t('app.dashboard.nba.all_clear_subtitle')}</p>
          </div>
        )}
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
