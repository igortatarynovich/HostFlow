import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { IconArrowRight, IconInbox, IconPhone, IconSearch } from '@tabler/icons-react'
import type { Application, ApplicationTab } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import {
  advanceSalesWorkSession,
  getSalesWorkSession,
  startSalesWorkSession,
} from '../../services/salesWorkSession'
import {
  APPLICATION_CALL_OUTCOME_CODES,
  APPLICATION_STATUS_BADGE,
  applicationCallOutcome,
  applicationCallOutcomeLabel,
  applicationMatchesSearch,
  applicationNeedsFirstContact,
  applicationStatusLabel,
  applicationTabBucket,
  formatApplicationRelativeTime,
  sortApplicationsByCreatedDesc,
} from './applicationDisplay'
import type { ApplicationWorkspaceConfig } from './types'
import { DEFAULT_DETAIL_RAIL_WIDTH_PX } from '../detail-rail/detailRailTypes'

type ApplicationWorkspaceProps = {
  config: ApplicationWorkspaceConfig
  /** Route param name for selected application id */
  routeParam?: string
}

export function ApplicationWorkspace({ config, routeParam = 'applicationId' }: ApplicationWorkspaceProps) {
  const params = useParams<Record<string, string | undefined>>()
  const selectedId = params[routeParam] || params.inquiryId || params.leadId || null
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()

  const [allApplications, setAllApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<ApplicationTab>('all')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [callResultFilter, setCallResultFilter] = useState('')
  const [tabCounts, setTabCounts] = useState<Record<ApplicationTab, number>>({
    all: 0,
    new: 0,
    in_progress: 0,
    waiting: 0,
    completed: 0,
  })
  const [listTotal, setListTotal] = useState(0)
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const allApplicationsRef = useRef(allApplications)
  allApplicationsRef.current = allApplications

  const splitView = Boolean(selectedId)
  const serverTabs = Boolean(config.serverTabPagination)
  const showCallOutcome = Boolean(config.showCallOutcome)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [search])

  const loadList = useCallback(
    async (opts?: { tab?: ApplicationTab; offset?: number; append?: boolean }) => {
      const targetTab = opts?.tab ?? tab
      const offset = opts?.offset ?? 0
      const append = Boolean(opts?.append)
      if (append) setLoadingMore(true)
      else setLoading(true)
      setError(null)
      try {
        const res = await config.listApplications({
          limit: 200,
          offset,
          tab: serverTabs ? targetTab : undefined,
          scope: 'all',
          includeCounts: serverTabs && offset === 0,
          callResult: showCallOutcome ? callResultFilter || undefined : undefined,
          q: debouncedSearch || undefined,
        })
        const sorted = [...res.items].sort(sortApplicationsByCreatedDesc)
        setAllApplications((prev) => (append ? [...prev, ...sorted] : sorted))
        setListTotal(res.total)
        if (serverTabs && res.counts) {
          setTabCounts((prev) => ({
            ...prev,
            all: res.counts?.all ?? prev.all,
            new: res.counts?.new ?? prev.new,
            in_progress: res.counts?.in_progress ?? prev.in_progress,
            waiting: res.counts?.waiting ?? prev.waiting,
            completed: res.counts?.completed ?? prev.completed,
          }))
        }
      } catch {
        setError(t('common.load_failed'))
        if (!append) setAllApplications([])
      } finally {
        if (append) setLoadingMore(false)
        else setLoading(false)
      }
    },
    [config, serverTabs, showCallOutcome, t, tab, callResultFilter, debouncedSearch],
  )

  useEffect(() => {
    void loadList({ tab, offset: 0 })
  }, [loadList, tab])

  const derivedTabCounts = useMemo(() => {
    if (serverTabs) return tabCounts
    const counts: Record<ApplicationTab, number> = {
      all: allApplications.length,
      new: 0,
      in_progress: 0,
      waiting: 0,
      completed: 0,
    }
    for (const app of allApplications) {
      const bucket = applicationTabBucket(app)
      if (bucket !== 'all') counts[bucket] += 1
    }
    return counts
  }, [allApplications, serverTabs, tabCounts])

  const filteredApplications = useMemo(() => {
    let rows = serverTabs
      ? allApplications
      : tab === 'all'
        ? allApplications
        : allApplications.filter((app) => applicationTabBucket(app) === tab)
    if (!serverTabs && callResultFilter) {
      rows = rows.filter((app) => applicationCallOutcome(app) === callResultFilter)
    }
    if (!serverTabs && debouncedSearch) {
      rows = rows.filter((app) => applicationMatchesSearch(app, debouncedSearch))
    }
    return rows
  }, [allApplications, callResultFilter, debouncedSearch, serverTabs, tab])

  const newToContactCount = serverTabs ? derivedTabCounts.new : allApplications.filter(applicationNeedsFirstContact).length
  const newToContact = useMemo(
    () => (serverTabs ? [] : allApplications.filter(applicationNeedsFirstContact)),
    [allApplications, serverTabs],
  )

  const hasMore = serverTabs && allApplications.length < listTotal

  const loadDetail = useCallback(
    async (id: string) => {
      setDetailLoading(true)
      try {
        let row
        try {
          row = await config.getApplication(id)
        } catch {
          const cached = allApplicationsRef.current.find((item) => item.id === id)
          const transportId = String(cached?.transport_lead_id || '').trim()
          if (!transportId || transportId === id) throw new Error('application not found')
          row = await config.getApplication(transportId)
        }
        if (row.module !== config.module) {
          setSelectedApplication(null)
          navigate(config.homePath, { replace: true })
          return
        }
        setSelectedApplication(row)
      } catch {
        setSelectedApplication(null)
        navigate(config.homePath, { replace: true })
      } finally {
        setDetailLoading(false)
      }
    },
    [config, navigate],
  )

  useEffect(() => {
    if (!selectedId) {
      setSelectedApplication(null)
      return
    }
    void loadDetail(selectedId)
  }, [loadDetail, selectedId])

  const refreshApplication = useCallback(
    async (id: string) => {
      const updated = await config.getApplication(id)
      setSelectedApplication((prev) => (prev?.id === updated.id ? updated : prev))
      if (serverTabs) {
        await loadList({ tab, offset: 0 })
        return
      }
      setAllApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
    },
    [config, loadList, serverTabs, tab],
  )

  const startCallSession = async () => {
    let queue = newToContact
    if (serverTabs) {
      try {
        const res = await config.listApplications({ tab: 'new', limit: 200, scope: 'all' })
        queue = res.items.filter(applicationNeedsFirstContact)
      } catch {
        notify({ title: t('common.load_failed'), variant: 'error' })
        return
      }
    }
    if (queue.length === 0) return
    startSalesWorkSession({
      surface: config.workSessionSurface,
      kind: config.workSessionKind,
      queue: queue.map((a) => a.id),
      returnPath: config.homePath,
    })
    navigate(config.applicationPath(queue[0].id))
  }

  useEffect(() => {
    if (!selectedId) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return
      e.preventDefault()
      navigate(config.homePath)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [config.homePath, navigate, selectedId])

  const selectApplication = (id: string) => {
    if (selectedId === id) {
      navigate(config.homePath)
      return
    }
    navigate(config.applicationPath(id))
  }

  const renderListItem = (app: Application) => {
    const status = app.status
    const badge = config.extensionBadge?.(app)
    const isSelected = app.id === selectedId
    const entityPath = config.primaryEntityPath?.(app)
    const callOutcome = showCallOutcome ? applicationCallOutcome(app) : null

    return (
      <tr
        key={app.id}
        onClick={() => selectApplication(app.id)}
        className={clsx(
          'cursor-pointer border-b border-slate-100 transition hover:bg-slate-50',
          isSelected &&
            'border-l-[3px] border-l-brand-600 bg-brand-50/90 shadow-[inset_0_0_0_1px_rgb(191_219_254_/_0.35)] hover:bg-brand-50/90',
        )}
        aria-current={isSelected ? 'true' : undefined}
      >
        <td className="px-3 py-2">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-100 text-xs font-bold text-brand-800">
              {(app.title || app.contact.name).charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0">
              {entityPath ? (
                <Link
                  to={entityPath}
                  className="block truncate font-semibold text-brand-700 hover:text-brand-800 hover:underline"
                  data-entity-link="primary"
                  onClick={(e) => e.stopPropagation()}
                  title={config.primaryEntityLabel ?? t('app.platform.application_workspace.open_card')}
                >
                  {app.title}
                </Link>
              ) : (
                <p className="truncate font-semibold text-slate-900">{app.title}</p>
              )}
              <p className="text-xs text-slate-500">{config.listKindLabel}</p>
            </div>
          </div>
        </td>
        <td className="px-3 py-2 text-sm text-slate-600">
          <p>{app.contact.name}</p>
          {app.contact.phone ? <p className="text-xs text-slate-400">{app.contact.phone}</p> : null}
        </td>
        <td className="px-3 py-2 text-sm text-slate-600">{app.source || '—'}</td>
        <td className="px-3 py-2 text-sm text-slate-600">{badge || '—'}</td>
        {showCallOutcome ? (
          <td className="px-3 py-2">
            {callOutcome ? (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                {applicationCallOutcomeLabel(callOutcome, t)}
              </span>
            ) : (
              <span className="text-xs text-slate-400">—</span>
            )}
          </td>
        ) : null}
        <td className="px-3 py-2">
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[status as keyof typeof APPLICATION_STATUS_BADGE]}`}>
            {applicationStatusLabel(status, t)}
          </span>
        </td>
        <td className="px-3 py-2 text-sm text-slate-500">{formatApplicationRelativeTime(app.created_at, t, locale)}</td>
      </tr>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-slate-50/80">
      <div className="shrink-0 space-y-2 border-b border-slate-200 bg-white px-3 py-2">
        <h1 className="sr-only">{config.objectNamePlural}</h1>

        {newToContactCount > 0 ? (
          <section className="flex items-center gap-2 border border-brand-200 bg-brand-50/70 px-2.5 py-1.5" title={config.heroCallHint}>
            <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center bg-brand-100 text-brand-700">
              <IconPhone size={16} stroke={1.9} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-700">
                {t('app.platform.application_workspace.next_action')}
              </p>
              <p className="truncate text-sm font-semibold text-slate-900">{config.heroCallTitle(newToContactCount)}</p>
            </div>
            <button
              type="button"
              onClick={() => void startCallSession()}
              className="inline-flex shrink-0 items-center gap-1.5 bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-800"
            >
              {t('app.platform.application_workspace.start_work')}
              <IconArrowRight size={14} stroke={2} />
            </button>
          </section>
        ) : (
          <section className="flex items-center gap-2 border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600">
            <IconInbox size={16} stroke={1.9} className="shrink-0 text-slate-400" />
            <span className="truncate">{config.heroEmptyText}</span>
          </section>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1">
            {config.tabs.map((def) => (
              <button
                key={def.id}
                type="button"
                onClick={() => setTab(def.id)}
                className={clsx(
                  'rounded-md px-2.5 py-1 text-xs font-medium transition',
                  tab === def.id ? 'bg-brand-700 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50',
                )}
              >
                {def.label} ({derivedTabCounts[def.id]})
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative">
              <IconSearch size={12} stroke={1.9} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t('app.platform.application_workspace.search_placeholder')}
                className="w-44 rounded-md border border-slate-200 bg-white py-1 pl-6 pr-2 text-xs text-slate-700 placeholder:text-slate-400"
                aria-label={t('app.platform.application_workspace.search_placeholder')}
              />
            </label>
            {showCallOutcome ? (
              <select
                value={callResultFilter}
                onChange={(event) => setCallResultFilter(event.target.value)}
                className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                aria-label={t('app.platform.application_workspace.filter_call_result')}
              >
                <option value="">{t('app.platform.application_workspace.filter_call_all')}</option>
                {APPLICATION_CALL_OUTCOME_CODES.map((code) => (
                  <option key={code} value={code}>
                    {applicationCallOutcomeLabel(code, t)}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
        </div>
      </div>

      {loading ? (
        <p className="p-6 text-sm text-slate-500">{t('common.loading')}</p>
      ) : error ? (
        <section className="m-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</section>
      ) : (
        <div
          className={clsx(
            'grid min-h-0 min-w-0 flex-1',
            splitView
              ? 'max-lg:auto-rows-min max-lg:grid-cols-1 max-lg:overflow-y-auto lg:overflow-hidden lg:grid-cols-[minmax(0,1fr)_var(--hf-detail-rail-width)] lg:grid-rows-[minmax(0,1fr)]'
              : 'grid-cols-1 grid-rows-[minmax(0,1fr)] overflow-hidden',
          )}
          data-hf-decision-mode={splitView ? 'context' : 'table'}
          style={{ ['--hf-detail-rail-width' as string]: `${DEFAULT_DETAIL_RAIL_WIDTH_PX}px` }}
        >
          <div
            className={clsx(
              'min-h-0 min-w-0 overflow-auto bg-white',
              splitView && 'max-lg:max-h-[min(45dvh,24rem)]',
            )}
          >
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_contact')}</th>
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_details')}</th>
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_source')}</th>
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_extra')}</th>
                  {showCallOutcome ? (
                    <th className="px-3 py-2">{t('app.platform.application_workspace.col_call_result')}</th>
                  ) : null}
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_status')}</th>
                  <th className="px-3 py-2">{t('app.platform.application_workspace.col_time')}</th>
                </tr>
              </thead>
              <tbody>{filteredApplications.map((app) => renderListItem(app))}</tbody>
            </table>
            {filteredApplications.length === 0 ? (
              <p className="p-8 text-center text-sm text-slate-500">
                {t('app.platform.application_workspace.empty_tab')}
              </p>
            ) : null}
            {hasMore ? (
              <div className="border-t border-slate-100 p-4 text-center">
                <button
                  type="button"
                  disabled={loadingMore}
                  onClick={() => void loadList({ tab, offset: allApplications.length, append: true })}
                  className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  {loadingMore
                    ? t('common.loading')
                    : t('app.platform.application_workspace.load_more', {
                        values: { loaded: allApplications.length, total: listTotal },
                      })}
                </button>
              </div>
            ) : null}
          </div>

          {splitView ? (
            <aside
              className="flex min-h-0 w-full shrink-0 flex-col overflow-hidden border-t border-slate-200 bg-slate-50 shadow-[inset_1px_0_0_rgb(226_232_240)] max-lg:max-h-[min(70dvh,32rem)] lg:h-full lg:w-[var(--hf-detail-rail-width)] lg:min-w-[var(--hf-detail-rail-width)] lg:max-w-[var(--hf-detail-rail-width)] lg:border-l lg:border-t-0"
              data-detail-rail="application-context"
            >
              {detailLoading || !selectedApplication ? (
                <p className="p-6 text-sm text-slate-500">{t('common.loading')}</p>
              ) : (
                <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
                  {config.renderDetail({
                    application: selectedApplication,
                    onRefresh: () => void refreshApplication(selectedApplication.id),
                    onClose: () => navigate(config.homePath),
                  })}
                </div>
              )}
            </aside>
          ) : null}
        </div>
      )}
    </div>
  )
}

export { advanceSalesWorkSession, getSalesWorkSession }
