import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  fetchHrHandoffsAccepted,
  fetchHrHandoffsPending,
  fetchHrInboxContext,
  type HrHandoffInboxItem,
  type HrOperationalQueue,
} from '../../api/hrWorkspace'
import { acceptHandoff } from '../../api/handoffs'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'

const tabBtn = (active: boolean) =>
  clsx('tab cursor-pointer border-0 bg-transparent', active && 'tab-active')

type InboxTab = 'all' | 'pending' | 'accepted'

const TERMINAL_QUEUES = new Set<HrOperationalQueue>([
  'approved_for_employment',
  'returned_to_recruitment',
  'rejected_by_hr',
])

export default function HrInboxPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [tab, setTab] = useState<InboxTab>('all')
  const [queueFilter, setQueueFilter] = useState<HrOperationalQueue | 'all'>('all')
  const [pending, setPending] = useState<{ total: number; items: HrHandoffInboxItem[] } | null>(null)
  const [accepted, setAccepted] = useState<{ total: number; items: HrHandoffInboxItem[] } | null>(null)
  const [delayedFlag, setDelayedFlag] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [acceptedUnavailable, setAcceptedUnavailable] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [acceptingId, setAcceptingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    setAcceptedUnavailable(null)
    try {
      const ctx = await fetchHrInboxContext()
      setDelayedFlag(Boolean(ctx.delayed_hr_workforce_creation))
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
      setLoading(false)
      return
    }

    try {
      setPending(await fetchHrHandoffsPending())
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
      setPending(null)
    }

    try {
      setAccepted(await fetchHrHandoffsAccepted())
    } catch (e: unknown) {
      const ex = e as { response?: { status?: number; data?: { detail?: string } }; message?: string }
      if (ex?.response?.status === 404) {
        setAccepted({ total: 0, items: [] })
        setAcceptedUnavailable(
          t('app.nav.hr.inbox.accepted_unavailable', {
            defaultValue:
              'Accepted handoff queue is unavailable (backend version mismatch). Pending pickup still loads below.',
          }),
        )
      } else {
        setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
        setAccepted(null)
      }
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const allItems = useMemo(() => {
    const p = pending?.items ?? []
    const a = accepted?.items ?? []
    return [...p, ...a]
  }, [pending, accepted])

  const tabItems = useMemo(() => {
    if (tab === 'pending') return pending?.items ?? []
    if (tab === 'accepted') return accepted?.items ?? []
    return allItems.filter((row) => !TERMINAL_QUEUES.has(row.operational_queue as HrOperationalQueue))
  }, [tab, pending, accepted, allItems])

  const items = useMemo(() => {
    if (queueFilter === 'all') return tabItems
    return tabItems.filter((row) => row.operational_queue === queueFilter)
  }, [tabItems, queueFilter])

  const queueLabel = (q: string) => {
    const key = `app.nav.hr.inbox.queue_${q}`
    const tr = t(key, { defaultValue: '' })
    return tr && tr !== key ? tr : q.replace(/_/g, ' ')
  }

  const handleAcceptPickup = async (handoffId: string) => {
    setAcceptingId(handoffId)
    try {
      await acceptHandoff(handoffId)
      notify({
        variant: 'success',
        title: t('app.nav.hr.inbox.accept_pickup', { defaultValue: 'Take into HR review' }),
      })
      await load()
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      notify({
        variant: 'error',
        title: ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'),
      })
    } finally {
      setAcceptingId(null)
    }
  }

  const empHref = (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}`
  const handoffHref = (id: string) => `${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(id)}`

  const lanes = useMemo(
    () => [
      {
        key: 'awaiting_documents',
        title: t('app.hr.inbox.lane.awaiting_documents', { defaultValue: 'Awaiting documents' }),
        match: (q: string) => q === 'awaiting_documents' || q === 'awaiting_work_permit' || q === 'awaiting_red_paper',
      },
      {
        key: 'ready_for_review',
        title: t('app.hr.inbox.lane.ready_for_review', { defaultValue: 'Ready for review' }),
        match: (q: string) => q === 'hr_review_in_progress' || q === 'awaiting_hr_pickup',
      },
      {
        key: 'blocked',
        title: t('app.hr.inbox.lane.blocked', { defaultValue: 'Blocked' }),
        match: (q: string) => q === 'returned_to_recruitment' || q === 'rejected_by_hr',
      },
      {
        key: 'ready_for_activation',
        title: t('app.hr.inbox.lane.ready_for_activation', { defaultValue: 'Ready for activation' }),
        match: (q: string) => q === 'approved_for_employment',
      },
    ],
    [t],
  )

  const queueChips: Array<HrOperationalQueue | 'all'> = [
    'all',
    'awaiting_hr_pickup',
    'hr_review_in_progress',
    'awaiting_documents',
    'awaiting_payments',
    'awaiting_work_permit',
    'awaiting_red_paper',
    'approved_for_employment',
    'returned_to_recruitment',
    'rejected_by_hr',
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-base font-semibold tracking-tight text-slate-900">
          {t('app.nav.hr.inbox.heading', { defaultValue: 'Inbox' })}
        </h2>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrDocuments}>
            {t('app.nav.hr.inbox.quick_hub', { defaultValue: 'Documents hub' })}
          </Link>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </div>

      {delayedFlag ? (
        <p className="rounded-lg border border-indigo-200 bg-indigo-50/80 px-3 py-2 text-xs text-indigo-950">
          {t('app.nav.hr.inbox.delayed_hint', {
            defaultValue: 'Workforce is created only after employment approval.',
          })}
        </p>
      ) : null}

      <div className="sticky top-0 z-20 -mx-1 space-y-4 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
        {!loading && !err ? (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.inbox.stat_pending', {
                defaultValue: 'Awaiting pickup: {n}',
                values: { n: pending?.total ?? 0 },
              })}
            </span>
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.inbox.stat_accepted', {
                defaultValue: 'In review: {n}',
                values: { n: accepted?.total ?? 0 },
              })}
            </span>
            <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
              {t('app.nav.hr.inbox.stat_tab', {
                defaultValue: 'This tab: {n}',
                values: { n: items.length },
              })}
            </span>
          </div>
        ) : null}

        <div className="tabs flex-wrap gap-x-1 gap-y-0" role="tablist">
          {(['all', 'pending', 'accepted'] as const).map((k) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              className={tabBtn(tab === k)}
              onClick={() => setTab(k)}
            >
              {k === 'all'
                ? t('app.nav.hr.inbox.tab_all', { defaultValue: 'All active' })
                : k === 'pending'
                  ? t('app.nav.hr.inbox.tab_pending', { defaultValue: 'Awaiting pickup' })
                  : t('app.nav.hr.inbox.tab_accepted', { defaultValue: 'In HR review' })}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-1.5">
          <span className="self-center text-[10px] font-semibold uppercase text-slate-500">
            {t('app.nav.hr.inbox.filter_queue', { defaultValue: 'Filter by queue' })}
          </span>
          {queueChips.map((q) => (
            <button
              key={q}
              type="button"
              className={clsx(
                'rounded-full border px-2 py-0.5 text-[11px] font-medium',
                queueFilter === q
                  ? 'border-indigo-300 bg-indigo-50 text-indigo-950'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300',
              )}
              onClick={() => setQueueFilter(q)}
            >
              {q === 'all' ? t('common.all', { defaultValue: 'All' }) : queueLabel(q)}
            </button>
          ))}
        </div>
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {acceptedUnavailable ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2 text-xs text-amber-950">
          {acceptedUnavailable}
        </p>
      ) : null}
      {err ? <div className="alert-error">{err}</div> : null}

      <div className="space-y-4">
        {loading ? (
          <div className="card p-6 text-sm text-slate-600">{t('common.loading')}</div>
        ) : (
          <>
            {lanes.map((lane) => {
              const laneItems = items.filter((row) => lane.match(String(row.operational_queue)))
              return (
                <section key={lane.key} className="card p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-900">{lane.title}</h3>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {laneItems.length}
                    </span>
                  </div>
                  {!laneItems.length ? (
                    <p className="text-xs text-slate-500">{t('app.nav.hr.inbox.empty', { defaultValue: 'No handoffs in this queue.' })}</p>
                  ) : (
                    <ul className="space-y-2">
                      {laneItems.map((row) => {
                        const h = row.handoff
                        const id = h?.id
                        const wf = row.workforce_employee_id
                        const isPickup = row.operational_queue === 'awaiting_hr_pickup'
                        return (
                          <li key={id || `${row.candidate_display_name}-${lane.key}`} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="font-medium text-slate-900">{row.candidate_display_name || '—'}</div>
                                <div className="mt-0.5 text-xs text-slate-600">
                                  {queueLabel(String(row.operational_queue))}
                                  {row.awaiting_employment_approval ? ` · ${t('app.hr.review.approve', { defaultValue: 'Approve for employment' })}` : ''}
                                </div>
                                {id ? <div className="mt-0.5 font-mono text-[10px] text-slate-400">handoff:{id.slice(0, 8)}…</div> : null}
                              </div>
                              <div className="flex flex-col items-end gap-1">
                                {isPickup && id ? (
                                  <button
                                    type="button"
                                    className="btn-primary btn-sm text-left"
                                    disabled={acceptingId === id}
                                    onClick={() => void handleAcceptPickup(id)}
                                  >
                                    {t('app.nav.hr.inbox.accept_pickup', { defaultValue: 'Take into HR review' })}
                                  </button>
                                ) : null}
                                {id ? (
                                  <Link className="text-sm font-medium text-brand-700 hover:underline" to={handoffHref(id)}>
                                    {isPickup
                                      ? t('app.nav.hr.inbox.view_snapshot', { defaultValue: 'Open case' })
                                      : t('app.nav.hr.inbox.view_review', { defaultValue: 'HR review' })}
                                  </Link>
                                ) : null}
                                {wf && row.hr_review_status === 'approved_for_employment' ? (
                                  <Link className="text-xs font-medium text-brand-700 hover:underline" to={empHref(wf)}>
                                    {t('app.hr.review_case.open_employee_profile', { defaultValue: 'Open employee profile' })}
                                  </Link>
                                ) : null}
                              </div>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </section>
              )
            })}
            {!items.length && !loading ? (
              <div className="card p-6 text-center text-sm text-slate-600">
                {t('app.nav.hr.inbox.empty', { defaultValue: 'No handoffs in this queue.' })}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  )
}
