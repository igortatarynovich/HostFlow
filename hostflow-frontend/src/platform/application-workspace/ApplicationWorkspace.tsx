import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import clsx from 'clsx'
import { IconArrowRight, IconFilter, IconInbox, IconPhone } from '@tabler/icons-react'
import type { Application, ApplicationStatus, ApplicationTab } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import {
  advanceSalesWorkSession,
  getSalesWorkSession,
  startSalesWorkSession,
} from '../../services/salesWorkSession'
import {
  APPLICATION_STATUS_BADGE,
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
  const selectedId = params[routeParam] || params.leadId || null
  const { t } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()

  const [allApplications, setAllApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<ApplicationTab>('all')
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

  const splitView = Boolean(selectedId)
  const serverTabs = Boolean(config.serverTabPagination)

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
        setError(t('app.application_workspace.load_failed', { defaultValue: 'Failed to load data' }))
        if (!append) setAllApplications([])
      } finally {
        if (append) setLoadingMore(false)
        else setLoading(false)
      }
    },
    [config, serverTabs, t, tab],
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
    if (serverTabs) return allApplications
    if (tab === 'all') return allApplications
    return allApplications.filter((app) => applicationTabBucket(app) === tab)
  }, [allApplications, serverTabs, tab])

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
        const row = await config.getApplication(id)
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
      setAllApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
      setSelectedApplication((prev) => (prev?.id === updated.id ? updated : prev))
    },
    [config],
  )

  const startCallSession = async () => {
    let queue = newToContact
    if (serverTabs) {
      try {
        const res = await config.listApplications({ tab: 'new', limit: 200, scope: 'all' })
        queue = res.items.filter(applicationNeedsFirstContact)
      } catch {
        notify({
          title: t('app.application_workspace.load_failed', { defaultValue: 'Failed to load data' }),
          variant: 'error',
        })
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
    const status: ApplicationStatus = app.status === 'rejected' ? 'completed' : app.status
    const badge = config.extensionBadge?.(app)
    const isSelected = app.id === selectedId
    const entityPath = config.primaryEntityPath?.(app)

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
        <td className="px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-sm font-bold text-brand-800">
              {(app.title || app.contact.name).charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0">
              {entityPath ? (
                <Link
                  to={entityPath}
                  className="block truncate font-semibold text-brand-700 hover:text-brand-800 hover:underline"
                  data-entity-link="primary"
                  onClick={(e) => e.stopPropagation()}
                  title={
                    config.primaryEntityLabel ??
                    t('app.application_workspace.open_card', { defaultValue: 'Open card' })
                  }
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
        <td className="px-4 py-3 text-sm text-slate-600">
          <p>{app.contact.name}</p>
          {app.contact.phone ? <p className="text-xs text-slate-400">{app.contact.phone}</p> : null}
        </td>
        <td className="px-4 py-3 text-sm text-slate-600">{app.source || '—'}</td>
        <td className="px-4 py-3 text-sm text-slate-600">{badge || '—'}</td>
        <td className="px-4 py-3">
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${APPLICATION_STATUS_BADGE[status]}`}>
            {applicationStatusLabel(status, t)}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-slate-500">{formatApplicationRelativeTime(app.created_at, t)}</td>
      </tr>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-slate-50/80">
      <div className="shrink-0 space-y-4 border-b border-slate-200 bg-white px-4 py-4">
        <h1 className="text-lg font-bold text-slate-900">{config.objectNamePlural}</h1>

        {newToContactCount > 0 ? (
          <section className="rounded-xl border border-brand-200 bg-gradient-to-r from-brand-50/80 to-white px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700">
                  <IconPhone size={20} stroke={1.9} />
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                    {t('app.application_workspace.next_action', { defaultValue: 'Next action' })}
                  </p>
                  <p className="mt-1 text-lg font-bold text-slate-900">{config.heroCallTitle(newToContactCount)}</p>
                  <p className="mt-1 text-sm text-slate-600">{config.heroCallHint}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void startCallSession()}
                className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-brand-700 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800"
              >
                {t('app.application_workspace.start_work', { defaultValue: 'Start work' })}
                <IconArrowRight size={16} stroke={2} />
              </button>
            </div>
          </section>
        ) : (
          <section className="rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600">
            <span className="inline-flex items-center gap-2">
              <IconInbox size={18} stroke={1.9} className="text-slate-400" />
              {config.heroEmptyText}
            </span>
          </section>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1">
            {config.tabs.map((def) => (
              <button
                key={def.id}
                type="button"
                onClick={() => setTab(def.id)}
                className={clsx(
                  'rounded-lg px-3 py-2 text-sm font-medium transition',
                  tab === def.id ? 'bg-brand-700 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50',
                )}
              >
                {def.label} ({derivedTabCounts[def.id]})
              </button>
            ))}
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
          >
            <IconFilter size={14} stroke={1.9} />
            {t('app.application_workspace.sort_newest_first', { defaultValue: 'Newest first' })}
          </button>
        </div>
      </div>

      {loading ? (
        <p className="p-6 text-sm text-slate-500">{t('common.loading')}</p>
      ) : error ? (
        <section className="m-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</section>
      ) : (
        <div
          className="grid min-h-0 flex-1"
          data-hf-decision-mode={splitView ? 'context' : 'table'}
          style={{
            gridTemplateColumns: splitView
              ? `minmax(0, 1fr) ${DEFAULT_DETAIL_RAIL_WIDTH_PX}px`
              : 'minmax(0, 1fr)',
          }}
        >
          <div className="min-h-0 min-w-0 overflow-auto bg-white">
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.contact', { defaultValue: 'Contact' })}
                  </th>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.details', { defaultValue: 'Details' })}
                  </th>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.source', { defaultValue: 'Source' })}
                  </th>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.extra', { defaultValue: 'Extra' })}
                  </th>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.status', { defaultValue: 'Status' })}
                  </th>
                  <th className="px-4 py-3">
                    {t('app.application_workspace.columns.time', { defaultValue: 'Time' })}
                  </th>
                </tr>
              </thead>
              <tbody>{filteredApplications.map((app) => renderListItem(app))}</tbody>
            </table>
            {filteredApplications.length === 0 ? (
              <p className="p-8 text-center text-sm text-slate-500">
                {t('app.application_workspace.empty_tab', { defaultValue: 'No records in this tab' })}
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
                    : t('app.application_workspace.load_more', {
                        defaultValue: 'Load more ({loaded} of {total})',
                        values: { loaded: allApplications.length, total: listTotal },
                      })}
                </button>
              </div>
            ) : null}
          </div>

          {splitView ? (
            <aside
              className="flex min-h-0 shrink-0 flex-col overflow-hidden border-l border-slate-200 bg-slate-50 shadow-[inset_1px_0_0_rgb(226_232_240)]"
              style={{
                width: DEFAULT_DETAIL_RAIL_WIDTH_PX,
                minWidth: DEFAULT_DETAIL_RAIL_WIDTH_PX,
                maxWidth: DEFAULT_DETAIL_RAIL_WIDTH_PX,
              }}
              data-detail-rail="application-context"
            >
              {detailLoading || !selectedApplication ? (
                <p className="p-6 text-sm text-slate-500">{t('common.loading')}</p>
              ) : (
                <div className="flex min-h-0 flex-1 flex-col">
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
