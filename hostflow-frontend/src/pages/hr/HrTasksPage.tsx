import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ReminderRecord } from '../../api/types/notification'
import { fetchHrTasks, type HrAssigneeScope } from '../../api/hrWorkspace'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { Toolbar } from '../../components/layout'
import { useI18n } from '../../i18n'

function formatDue(iso: string | null | undefined): string {
  if (!iso) return '—'
  const ms = Date.parse(iso)
  if (Number.isNaN(ms)) return String(iso)
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(ms)
  } catch {
    return String(iso)
  }
}

export default function HrTasksPage() {
  const { t } = useI18n()
  const [assigneeScope, setAssigneeScope] = useState<HrAssigneeScope>('team')
  const [data, setData] = useState<{ items: ReminderRecord[] } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const d = await fetchHrTasks({ assignee_scope: assigneeScope, limit: 200 })
      setData(d)
    } catch (e: unknown) {
      const ex = e as { response?: { data?: { detail?: string } }; message?: string }
      setErr(ex?.response?.data?.detail || ex?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [assigneeScope, t])

  useEffect(() => {
    void load()
  }, [load])

  const items = data?.items ?? []

  const stats = useMemo(() => {
    const overdue = items.filter((r) => (r.status || '').toLowerCase() === 'overdue').length
    return { n: items.length, overdue }
  }, [items])

  const entityHref = (r: ReminderRecord): string | null => {
    const payload = r.payload && typeof r.payload === 'object' ? r.payload : {}
    const wfId = String(payload.workforce_employee_id || '').trim()
    if (wfId) {
      return `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(wfId)}#hr-verification`
    }
    const et = String(r.entity_type || '').toLowerCase()
    const id = String(r.entity_id || '').trim()
    if (!id) return null
    if (et === 'workforce_employee') {
      return `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}#hr-verification`
    }
    if (et === 'candidate') return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(id)}`
    if (et === 'lead') return `${CRM_APP_PATHS.leads}/${encodeURIComponent(id)}`
    return null
  }

  const entityLabel = (r: ReminderRecord): string => {
    const payload = r.payload && typeof r.payload === 'object' ? r.payload : {}
    if (payload.workforce_employee_id) return 'workforce_employee'
    return String(r.entity_type || '')
  }

  return (
    <div className="space-y-4">
      <Toolbar>
        <div className="flex w-full flex-wrap items-center justify-end gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrZusWorkspace}>
            {t('app.nav.hr.tasks.quick_zus', { defaultValue: 'ZUS workspace' })}
          </Link>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </Toolbar>

      <div className="sticky top-0 z-20 -mx-1 space-y-4 border-b border-slate-200/90 bg-gradient-to-b from-brand-50/95 via-white/95 to-white pb-4 pt-1 backdrop-blur-sm">
        {!loading && !err ? (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.tasks.stat_rows', { defaultValue: 'Rows: {n}', values: { n: stats.n } })}
            </span>
            <span className="badge border border-rose-100 bg-rose-50/90 font-medium tabular-nums text-rose-900">
              {t('app.nav.hr.tasks.stat_overdue', { defaultValue: 'Overdue status: {n}', values: { n: stats.overdue } })}
            </span>
          </div>
        ) : null}

        <section className="card p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.nav.hr.tasks.filters', { defaultValue: 'Scope' })}
          </div>
          <div className="mt-2 flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.tasks.assignee', { defaultValue: 'Assignee scope' })}</span>
              <select className="input text-sm" value={assigneeScope} onChange={(e) => setAssigneeScope(e.target.value as HrAssigneeScope)}>
                <option value="team">{t('app.nav.hr.tasks.scope_team', { defaultValue: 'Team' })}</option>
                <option value="mine">{t('app.nav.hr.tasks.scope_mine', { defaultValue: 'Mine' })}</option>
              </select>
            </label>
          </div>
        </section>
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table w-full min-w-[1100px] text-left text-sm">
            <thead>
              <tr>
                <th>{t('app.nav.hr.tasks.col_title', { defaultValue: 'Title' })}</th>
                <th>{t('app.nav.hr.tasks.col_type', { defaultValue: 'Type' })}</th>
                <th>{t('app.nav.hr.tasks.col_status', { defaultValue: 'Status' })}</th>
                <th>{t('app.nav.hr.tasks.col_due', { defaultValue: 'Due' })}</th>
                <th>{t('app.nav.hr.tasks.col_entity', { defaultValue: 'Entity' })}</th>
                <th>{t('app.nav.hr.tasks.col_sla', { defaultValue: 'SLA' })}</th>
                <th className="w-32">{t('app.nav.hr.tasks.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => {
                const href = entityHref(r)
                return (
                  <tr key={String(r.id)}>
                    <td className="font-medium text-slate-900">{r.title || r.type || String(r.id)}</td>
                    <td className="font-mono text-xs text-slate-700">{r.type}</td>
                    <td className="text-slate-700">{r.status}</td>
                    <td className="whitespace-nowrap text-xs text-slate-600">{formatDue(r.due_at)}</td>
                    <td className="max-w-[14rem] truncate font-mono text-xs text-slate-600" title={`${entityLabel(r)}:${r.entity_id}`}>
                      {r.entity_id ? `${entityLabel(r)}:${r.entity_id}` : '—'}
                    </td>
                    <td className="text-xs text-slate-600">{r.sla_status || '—'}</td>
                    <td>
                      {href ? (
                        <Link className="text-sm font-medium text-brand-700 hover:underline" to={href}>
                          {t('app.nav.hr.tasks.open_entity', { defaultValue: 'Open' })}
                        </Link>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-600">
                    {t('app.nav.hr.tasks.empty', { defaultValue: 'No HR tasks.' })}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
