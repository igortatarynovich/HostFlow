import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrHandoffsAccepted, fetchHrHandoffsPending } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

const tabBtn = (active: boolean) =>
  clsx('tab cursor-pointer border-0 bg-transparent', active && 'tab-active')

export default function HrInboxPage() {
  const { t } = useI18n()
  const [tab, setTab] = useState<'pending' | 'accepted'>('pending')
  const [pending, setPending] = useState<any>(null)
  const [accepted, setAccepted] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const [p, a] = await Promise.all([fetchHrHandoffsPending(), fetchHrHandoffsAccepted()])
      setPending(p)
      setAccepted(a)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const data = tab === 'pending' ? pending : accepted
  const items = data?.items ?? []
  const total = data?.total ?? 0
  const pendingTotal = pending?.total ?? 0
  const acceptedTotal = accepted?.total ?? 0

  const empHref = useMemo(() => (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}`, [])

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

      <div className="sticky top-0 z-20 -mx-1 space-y-4 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
        {!loading && !err ? (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.inbox.stat_pending', { defaultValue: 'Pending: {n}', values: { n: pendingTotal } })}
            </span>
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.inbox.stat_accepted', { defaultValue: 'Accepted: {n}', values: { n: acceptedTotal } })}
            </span>
            <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
              {t('app.nav.hr.inbox.stat_tab', { defaultValue: 'This tab: {n}', values: { n: total } })}
            </span>
          </div>
        ) : null}

        <div className="tabs flex-wrap gap-x-1 gap-y-0" role="tablist" aria-label={t('app.nav.hr.inbox.tabs_aria', { defaultValue: 'Inbox queues' })}>
          {(['pending', 'accepted'] as const).map((k) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              className={tabBtn(tab === k)}
              onClick={() => setTab(k)}
            >
              {k === 'pending'
                ? t('app.nav.hr.inbox.tab_pending', { defaultValue: 'Pending' })
                : t('app.nav.hr.inbox.tab_accepted', { defaultValue: 'Accepted' })}
            </button>
          ))}
        </div>
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-6 text-sm text-slate-600">{t('common.loading')}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table w-full min-w-[960px] text-left text-sm">
              <thead>
                <tr>
                  <th>{t('app.nav.hr.inbox.col_handoff', { defaultValue: 'Handoff' })}</th>
                  <th>{t('app.nav.hr.inbox.col_status', { defaultValue: 'Status' })}</th>
                  <th>{t('app.nav.hr.inbox.col_candidate', { defaultValue: 'Candidate' })}</th>
                  <th>{t('app.nav.hr.inbox.col_employee', { defaultValue: 'Workforce' })}</th>
                  <th className="w-40">{t('app.nav.hr.inbox.col_actions', { defaultValue: 'Actions' })}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row: any) => {
                  const h = row.handoff
                  const id = h?.id as string | undefined
                  const wf = row.workforce_employee_id as string | undefined
                  const cand = h?.candidate_id as string | undefined
                  return (
                    <tr key={id || Math.random().toString(36)}>
                      <td className="font-mono text-xs text-slate-800">{id || '—'}</td>
                      <td className="text-slate-700">{h?.status ?? '—'}</td>
                      <td className="font-mono text-xs text-slate-600">{cand || '—'}</td>
                      <td className="font-mono text-xs text-slate-600">{wf || '—'}</td>
                      <td>
                        <div className="flex flex-col gap-1">
                          {id ? (
                            <Link className="text-sm font-medium text-brand-700 hover:underline" to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(id)}`}>
                              {t('app.nav.hr.inbox.view_snapshot', { defaultValue: 'Snapshot' })}
                            </Link>
                          ) : null}
                          {wf ? (
                            <Link className="text-xs font-medium text-brand-700 hover:underline" to={empHref(wf)}>
                              {t('app.nav.hr.inbox.open_employee', { defaultValue: 'Employee' })}
                            </Link>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {!items.length && !loading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-sm text-slate-600">
                      {t('app.nav.hr.inbox.empty', { defaultValue: 'No handoffs in this queue.' })}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
