import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { fetchHrHandoffsAccepted, fetchHrHandoffsPending } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">{t('app.nav.hr.inbox.heading', { defaultValue: 'Inbox' })}</h2>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => void load()}
        >
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>

      <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
        {(['pending', 'accepted'] as const).map((k) => (
          <button
            key={k}
            type="button"
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              tab === k ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
            onClick={() => setTab(k)}
          >
            {k === 'pending'
              ? t('app.nav.hr.inbox.tab_pending', { defaultValue: 'Pending' })
              : t('app.nav.hr.inbox.tab_accepted', { defaultValue: 'Accepted' })}
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}

      {!loading && !err && (
        <p className="text-xs text-slate-500">
          {t('app.nav.hr.inbox.total', { defaultValue: 'Total: {{n}}', n: data?.total ?? 0 })}
        </p>
      )}

      <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        {items.map((row: any) => {
          const h = row.handoff
          const id = h?.id
          return (
            <li key={id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <div className="text-sm font-medium text-slate-900">
                  {t('app.nav.hr.inbox.handoff_row', { defaultValue: 'Handoff {{id}}', id: id ?? '—' })}
                </div>
                <div className="text-xs text-slate-500">
                  {h?.status} · {h?.candidate_id ? `candidate ${h.candidate_id}` : ''}
                </div>
              </div>
              {id ? (
                <Link
                  to={`${CRM_APP_PATHS.hrHandoffs}/${encodeURIComponent(id)}`}
                  className="text-sm font-medium text-brand-700 hover:text-brand-900"
                >
                  {t('app.nav.hr.inbox.view_snapshot', { defaultValue: 'Snapshot' })}
                </Link>
              ) : null}
            </li>
          )
        })}
        {!items.length && !loading ? (
          <li className="px-4 py-8 text-center text-sm text-slate-500">
            {t('app.nav.hr.inbox.empty', { defaultValue: 'No handoffs in this queue.' })}
          </li>
        ) : null}
      </ul>
    </div>
  )
}
