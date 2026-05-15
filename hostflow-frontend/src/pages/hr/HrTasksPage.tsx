import { useCallback, useEffect, useState } from 'react'
import { fetchHrTasks } from '../../api/hrWorkspace'
import { useI18n } from '../../i18n'

export default function HrTasksPage() {
  const { t } = useI18n()
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const d = await fetchHrTasks({ assignee_scope: 'team', limit: 200 })
      setData(d)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const items = data?.items ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">{t('app.nav.hr.tasks.heading', { defaultValue: 'HR tasks' })}</h2>
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
          onClick={() => void load()}
        >
          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
        </button>
      </div>
      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>
      )}
      <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        {items.map((r: any) => (
          <li key={r.id} className="px-4 py-3">
            <div className="text-sm font-medium text-slate-900">{r.title || r.type || r.id}</div>
            {r.due_at ? <div className="text-xs text-slate-500">{r.due_at}</div> : null}
          </li>
        ))}
        {!items.length && !loading ? (
          <li className="px-4 py-8 text-center text-sm text-slate-500">
            {t('app.nav.hr.tasks.empty', { defaultValue: 'No HR tasks.' })}
          </li>
        ) : null}
      </ul>
    </div>
  )
}
