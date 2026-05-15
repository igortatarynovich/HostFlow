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
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-slate-900">
          {t('app.nav.hr.zus_workspace.heading', { defaultValue: 'ZUS workspace' })}
        </h2>
        <p className="text-sm text-slate-600 mt-1">
          {t('app.nav.hr.zus_workspace.subtitle', {
            defaultValue:
              'Operational queue: registrations, deregistrations, ZUA/ZZA/ZWUA, monthly settlement, export placeholders. No ZUS API or Płatnik export in this MVP.',
          })}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.nav.hr.zus_workspace.filters', { defaultValue: 'Filters' })}
        </div>
        <div className="flex flex-wrap gap-3 items-end">
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_status', { defaultValue: 'Status' })}
            <input
              className="border border-slate-200 rounded px-2 py-1.5 text-sm w-36"
              value={fStatus}
              onChange={(e) => setFStatus(e.target.value)}
              placeholder="open"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_lane', { defaultValue: 'Lane' })}
            <select
              className="border border-slate-200 rounded px-2 py-1.5 text-sm min-w-[11rem]"
              value={fLane}
              onChange={(e) => setFLane(e.target.value)}
            >
              <option value="">{t('app.nav.hr.zus_workspace.f_all', { defaultValue: 'All' })}</option>
              {LANES.map((l) => (
                <option key={l.value} value={l.value}>
                  {t(`app.nav.hr.zus_workspace.${l.i18n}`, { defaultValue: l.value })}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_form', { defaultValue: 'Form (ZUA/ZZA/ZWUA)' })}
            <select className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={fFormKind} onChange={(e) => setFFormKind(e.target.value)}>
              <option value="">{t('app.nav.hr.zus_workspace.f_all', { defaultValue: 'All' })}</option>
              {FORM_KINDS.map((fk) => (
                <option key={fk} value={fk}>
                  {fk}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_assignee', { defaultValue: 'Assigned HR (user id)' })}
            <input
              className="border border-slate-200 rounded px-2 py-1.5 text-sm font-mono w-44"
              value={fAssignee}
              onChange={(e) => setFAssignee(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_due_after', { defaultValue: 'Due from (date)' })}
            <input type="date" className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={fDueAfter} onChange={(e) => setFDueAfter(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            {t('app.nav.hr.zus_workspace.f_due_before', { defaultValue: 'Due to (date)' })}
            <input type="date" className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={fDueBefore} onChange={(e) => setFDueBefore(e.target.value)} />
          </label>
          <button
            type="button"
            className="rounded-md border border-slate-200 bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
            onClick={() => void load()}
          >
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
      {err && <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{err}</div>}

      {manage ? (
        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.zus_workspace.create_heading', { defaultValue: 'Add queue row' })}
          </h3>
          <div className="flex flex-wrap gap-3 items-end">
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.nav.hr.zus_workspace.col_employee', { defaultValue: 'Employee' })}
              <select
                className="border border-slate-200 rounded px-2 py-1.5 text-sm min-w-[14rem]"
                value={cEmployee}
                onChange={(e) => setCEmployee(e.target.value)}
              >
                <option value="">{t('app.nav.hr.zus_workspace.pick_employee', { defaultValue: 'Select…' })}</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.nav.hr.zus_workspace.f_lane', { defaultValue: 'Lane' })}
              <select className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={cLane} onChange={(e) => setCLane(e.target.value as ZusWorkspaceLane)}>
                {LANES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {t(`app.nav.hr.zus_workspace.${l.i18n}`, { defaultValue: l.value })}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.nav.hr.zus_workspace.col_kind', { defaultValue: 'Task kind' })}
              <input className="border border-slate-200 rounded px-2 py-1.5 text-sm w-52" value={cTaskKind} onChange={(e) => setCTaskKind(e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs text-slate-600">
              {t('app.nav.hr.zus_workspace.col_title', { defaultValue: 'Title' })}
              <input className="border border-slate-200 rounded px-2 py-1.5 text-sm w-56" value={cTitle} onChange={(e) => setCTitle(e.target.value)} placeholder="e.g. Zgłoszenie do ZUS" />
            </label>
            <button
              type="button"
              disabled={cSaving || !cEmployee}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              onClick={() => void onCreate()}
            >
              {t('app.nav.hr.zus_workspace.create_btn', { defaultValue: 'Create' })}
            </button>
          </div>
        </section>
      ) : null}

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-slate-100 px-4 py-3 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.nav.hr.zus_workspace.table_heading', { defaultValue: 'Queue ({{n}})', values: { n: total } })}
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-xs text-slate-600">
              <tr>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_employee', { defaultValue: 'Employee' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_lane', { defaultValue: 'Lane' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_kind', { defaultValue: 'Task kind' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_forms', { defaultValue: 'Form' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_status', { defaultValue: 'Status' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_due', { defaultValue: 'Due' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_export', { defaultValue: 'Export' })}</th>
                <th className="px-3 py-2">{t('app.nav.hr.zus_workspace.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/80">
                  <td className="px-3 py-2">
                    <Link className="font-medium text-brand-700 hover:underline" to={employeeHref(row.employee_id)}>
                      {row.employee_display_name || row.employee_id}
                    </Link>
                    <div className="text-[10px] font-mono text-slate-400">{row.employee_id}</div>
                  </td>
                  <td className="px-3 py-2 text-xs">{laneLabel(row.workspace_lane)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.task_kind}</td>
                  <td className="px-3 py-2 text-xs">
                    {row.form_kind ? `${row.form_kind}${row.form_status ? ` · ${row.form_status}` : ''}` : '—'}
                  </td>
                  <td className="px-3 py-2">
                    {manage ? (
                      <select
                        className="border border-slate-200 rounded px-1 py-0.5 text-xs"
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
                  <td className="px-3 py-2 text-xs whitespace-nowrap">{formatDue(row.due_at)}</td>
                  <td className="px-3 py-2 text-xs">{row.export_status || '—'}</td>
                  <td className="px-3 py-2">
                    <Link to={employeeHref(row.employee_id)} className="text-xs text-brand-700 hover:underline">
                      {t('app.nav.hr.zus_workspace.open_employee', { defaultValue: 'Profile' })}
                    </Link>
                  </td>
                </tr>
              ))}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-slate-500">
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
