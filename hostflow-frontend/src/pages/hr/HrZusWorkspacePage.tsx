import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  createZusWorkspaceTask,
  listZusWorkspaceTasks,
  patchZusWorkspaceTask,
  type ZusWorkspaceLane,
  type ZusWorkspaceTask,
} from '../../api/zusWorkspace'
import { listWorkforceEmployees, type WorkforceEmployee } from '../../api/workforce'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'

const LANES: { value: ZusWorkspaceLane; i18n: string }[] = [
  { value: 'task_queue', i18n: 'lane_task_queue' },
  { value: 'form_status', i18n: 'lane_form_status' },
  { value: 'checklist_register', i18n: 'lane_checklist_register' },
  { value: 'checklist_deregister', i18n: 'lane_checklist_deregister' },
  { value: 'monthly_settlement', i18n: 'lane_monthly_settlement' },
  { value: 'export_queue', i18n: 'lane_export_queue' },
]

const FORM_KINDS = ['ZUA', 'ZZA', 'ZWUA'] as const

function formatDue(iso: string | null | undefined): string {
  if (!iso) return '—'
  const ms = Date.parse(iso)
  if (Number.isNaN(ms)) return iso
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(ms)
  } catch {
    return iso
  }
}

export default function HrZusWorkspacePage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const manage = can('workforce.manage')
  const [items, setItems] = useState<ZusWorkspaceTask[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [employees, setEmployees] = useState<WorkforceEmployee[]>([])

  const [fStatus, setFStatus] = useState('')
  const [fLane, setFLane] = useState('')
  const [fFormKind, setFFormKind] = useState('')
  const [fAssignee, setFAssignee] = useState('')
  const [fDueBefore, setFDueBefore] = useState('')
  const [fDueAfter, setFDueAfter] = useState('')

  const [cEmployee, setCEmployee] = useState('')
  const [cLane, setCLane] = useState<ZusWorkspaceLane>('task_queue')
  const [cTaskKind, setCTaskKind] = useState('zus_registration_review')
  const [cTitle, setCTitle] = useState('')
  const [cSaving, setCSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const page = await listZusWorkspaceTasks({
        status: fStatus || undefined,
        workspace_lane: fLane || undefined,
        form_kind: fFormKind || undefined,
        assigned_hr_user_id: fAssignee || undefined,
        due_before: fDueBefore ? `${fDueBefore}T23:59:59` : undefined,
        due_after: fDueAfter ? `${fDueAfter}T00:00:00` : undefined,
        limit: 200,
        offset: 0,
      })
      setItems(page.items)
      setTotal(page.total)
    } catch (ex: unknown) {
      const e = ex as { response?: { data?: { detail?: string } }; message?: string }
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setLoading(false)
    }
  }, [fAssignee, fDueAfter, fDueBefore, fFormKind, fLane, fStatus, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const rows = await listWorkforceEmployees({ status: undefined })
        if (!cancelled) setEmployees(rows)
      } catch {
        if (!cancelled) setEmployees([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const laneLabel = useCallback(
    (lane: string) => {
      const hit = LANES.find((l) => l.value === lane)
      return hit ? t(`app.nav.hr.zus_workspace.${hit.i18n}`, { defaultValue: lane }) : lane
    },
    [t],
  )

  const stats = useMemo(() => {
    const open = items.filter((r) => r.status === 'open').length
    const inProg = items.filter((r) => r.status === 'in_progress').length
    const blocked = items.filter((r) => r.status === 'blocked').length
    const done = items.filter((r) => r.status === 'done').length
    return { open, inProg, blocked, done, loaded: items.length, total }
  }, [items, total])

  const onCreate = async () => {
    if (!cEmployee.trim()) return
    setCSaving(true)
    setErr(null)
    try {
      await createZusWorkspaceTask({
        employee_id: cEmployee.trim(),
        workspace_lane: cLane,
        task_kind: cTaskKind.trim() || 'custom',
        title: cTitle.trim(),
      })
      setCTitle('')
      await load()
    } catch (ex: unknown) {
      const e = ex as { response?: { data?: { detail?: string } }; message?: string }
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    } finally {
      setCSaving(false)
    }
  }

  const onPatchStatus = async (task: ZusWorkspaceTask, status: string) => {
    setErr(null)
    try {
      await patchZusWorkspaceTask(task.id, { status })
      await load()
    } catch (ex: unknown) {
      const e = ex as { response?: { data?: { detail?: string } }; message?: string }
      setErr(e?.response?.data?.detail || e?.message || t('common.errors.request_failed'))
    }
  }

  const employeeHref = useMemo(() => (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}`, [])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-900">
            {t('app.nav.hr.zus_workspace.heading', { defaultValue: 'ZUS workspace' })}
          </h2>
          <p className="mt-1 max-w-4xl text-sm text-slate-600">
            {t('app.nav.hr.zus_workspace.subtitle', {
              defaultValue:
                'Operational queue: registrations, deregistrations, ZUA/ZZA/ZWUA, monthly settlement, export placeholders. No ZUS API or Płatnik export in this MVP.',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.hrTasks}>
            {t('app.nav.hr.zus_workspace.quick_tasks', { defaultValue: 'HR tasks' })}
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
              {t('app.nav.hr.zus_workspace.stat_total', { defaultValue: 'API total: {n}', values: { n: stats.total } })}
            </span>
            <span className="badge border border-slate-200 font-medium tabular-nums">
              {t('app.nav.hr.zus_workspace.stat_loaded', { defaultValue: 'Loaded: {n}', values: { n: stats.loaded } })}
            </span>
            <span className="badge border border-emerald-100 bg-emerald-50/90 font-medium tabular-nums text-emerald-900">
              {t('app.nav.hr.zus_workspace.stat_open', { defaultValue: 'Open: {n}', values: { n: stats.open } })}
            </span>
            <span className="badge border border-brand-100 bg-brand-50/90 font-medium tabular-nums text-brand-900">
              {t('app.nav.hr.zus_workspace.stat_in_progress', { defaultValue: 'In progress: {n}', values: { n: stats.inProg } })}
            </span>
            <span className="badge border border-rose-100 bg-rose-50/90 font-medium tabular-nums text-rose-900">
              {t('app.nav.hr.zus_workspace.stat_blocked', { defaultValue: 'Blocked: {n}', values: { n: stats.blocked } })}
            </span>
            <span className="badge border border-slate-200 font-medium tabular-nums text-slate-700">
              {t('app.nav.hr.zus_workspace.stat_done', { defaultValue: 'Done: {n}', values: { n: stats.done } })}
            </span>
          </div>
        ) : null}

        <section className="card p-4 sm:p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.nav.hr.zus_workspace.filters', { defaultValue: 'Filters' })}
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_status', { defaultValue: 'Status' })}</span>
              <input
                className="input w-36 text-sm"
                value={fStatus}
                onChange={(e) => setFStatus(e.target.value)}
                placeholder="open"
              />
            </label>
            <label className="flex min-w-[11rem] flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_lane', { defaultValue: 'Lane' })}</span>
              <select className="input text-sm" value={fLane} onChange={(e) => setFLane(e.target.value)}>
                <option value="">{t('app.nav.hr.zus_workspace.f_all', { defaultValue: 'All' })}</option>
                {LANES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {t(`app.nav.hr.zus_workspace.${l.i18n}`, { defaultValue: l.value })}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_form', { defaultValue: 'Form (ZUA/ZZA/ZWUA)' })}</span>
              <select className="input text-sm" value={fFormKind} onChange={(e) => setFFormKind(e.target.value)}>
                <option value="">{t('app.nav.hr.zus_workspace.f_all', { defaultValue: 'All' })}</option>
                {FORM_KINDS.map((fk) => (
                  <option key={fk} value={fk}>
                    {fk}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_assignee', { defaultValue: 'Assigned HR (user id)' })}</span>
              <input className="input w-44 font-mono text-sm" value={fAssignee} onChange={(e) => setFAssignee(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_due_after', { defaultValue: 'Due from (date)' })}</span>
              <input type="date" className="input text-sm" value={fDueAfter} onChange={(e) => setFDueAfter(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_due_before', { defaultValue: 'Due to (date)' })}</span>
              <input type="date" className="input text-sm" value={fDueBefore} onChange={(e) => setFDueBefore(e.target.value)} />
            </label>
            <button type="button" className="btn-primary btn-sm" onClick={() => void load()}>
              {t('app.nav.hr.zus_workspace.apply_filters', { defaultValue: 'Apply' })}
            </button>
          </div>
        </section>
      </div>

      {loading ? <p className="text-sm text-slate-600">{t('common.loading')}</p> : null}
      {err ? <div className="alert-error">{err}</div> : null}

      {manage ? (
        <section className="card space-y-3 p-4">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.zus_workspace.create_heading', { defaultValue: 'Add queue row' })}
          </h3>
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex min-w-[14rem] flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.col_employee', { defaultValue: 'Employee' })}</span>
              <select className="input text-sm" value={cEmployee} onChange={(e) => setCEmployee(e.target.value)}>
                <option value="">{t('app.nav.hr.zus_workspace.pick_employee', { defaultValue: 'Select…' })}</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.f_lane', { defaultValue: 'Lane' })}</span>
              <select className="input text-sm" value={cLane} onChange={(e) => setCLane(e.target.value as ZusWorkspaceLane)}>
                {LANES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {t(`app.nav.hr.zus_workspace.${l.i18n}`, { defaultValue: l.value })}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.col_kind', { defaultValue: 'Task kind' })}</span>
              <input className="input w-52 text-sm" value={cTaskKind} onChange={(e) => setCTaskKind(e.target.value)} />
            </label>
            <label className="flex min-w-[14rem] flex-1 flex-col gap-1.5">
              <span className="label mb-0 text-xs text-slate-600">{t('app.nav.hr.zus_workspace.col_title', { defaultValue: 'Title' })}</span>
              <input
                className="input text-sm"
                value={cTitle}
                onChange={(e) => setCTitle(e.target.value)}
                placeholder="e.g. Zgłoszenie do ZUS"
              />
            </label>
            <button type="button" disabled={cSaving || !cEmployee} className="btn-primary btn-sm" onClick={() => void onCreate()}>
              {t('app.nav.hr.zus_workspace.create_btn', { defaultValue: 'Create' })}
            </button>
          </div>
        </section>
      ) : null}

      <section className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.zus_workspace.table_heading', { defaultValue: 'Queue ({{n}})', values: { n: total } })}
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="table w-full min-w-[1280px] text-left text-sm">
            <thead>
              <tr>
                <th>{t('app.nav.hr.zus_workspace.col_employee', { defaultValue: 'Employee' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_lane', { defaultValue: 'Lane' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_kind', { defaultValue: 'Task kind' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_forms', { defaultValue: 'Form' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_status', { defaultValue: 'Status' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_due', { defaultValue: 'Due' })}</th>
                <th>{t('app.nav.hr.zus_workspace.col_export', { defaultValue: 'Export' })}</th>
                <th className="w-36">{t('app.nav.hr.zus_workspace.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Link className="font-medium text-brand-700 hover:underline" to={employeeHref(row.employee_id)}>
                      {row.employee_display_name || row.employee_id}
                    </Link>
                    <div className="text-[10px] font-mono text-slate-400">{row.employee_id}</div>
                  </td>
                  <td className="text-xs">{laneLabel(row.workspace_lane)}</td>
                  <td className="font-mono text-xs">{row.task_kind}</td>
                  <td className="text-xs">
                    {row.form_kind ? `${row.form_kind}${row.form_status ? ` · ${row.form_status}` : ''}` : '—'}
                  </td>
                  <td>
                    {manage ? (
                      <select
                        className="input py-1 text-xs"
                        value={row.status}
                        onChange={(e) => void onPatchStatus(row, e.target.value)}
                      >
                        {['open', 'in_progress', 'blocked', 'done', 'cancelled'].map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    ) : (
                      row.status
                    )}
                  </td>
                  <td className="whitespace-nowrap text-xs">{formatDue(row.due_at)}</td>
                  <td className="text-xs">{row.export_status || '—'}</td>
                  <td>
                    <Link to={employeeHref(row.employee_id)} className="text-xs font-medium text-brand-700 hover:underline">
                      {t('app.nav.hr.zus_workspace.open_employee', { defaultValue: 'Profile' })}
                    </Link>
                  </td>
                </tr>
              ))}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-600">
                    {t('app.nav.hr.zus_workspace.empty', { defaultValue: 'No tasks match filters.' })}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
