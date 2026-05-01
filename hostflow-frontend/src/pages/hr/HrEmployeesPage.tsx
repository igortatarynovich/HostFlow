import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { listWorkforceEmployees, createWorkforceEmployee, type WorkforceEmployee } from '../../api/workforce'
import { usePermissions } from '../../hooks/usePermissions'
import { useToast } from '../../components/Toast'
import { PageBreadcrumb } from '../../components/nav/PageBreadcrumb'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../../app/crmAppPaths'

const hrEmployeePath = (id: string) => `${CRM_APP_PATHS.hrEmployees}/${encodeURIComponent(id)}`

export default function HrEmployeesPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { notify } = useToast()
  const [rows, setRows] = useState<WorkforceEmployee[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [nameDraft, setNameDraft] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listWorkforceEmployees()
      setRows(data)
    } catch (e: unknown) {
      notify({
        variant: 'error',
        title: t('app.hr.employees.load_error', { defaultValue: 'Could not load employees' }),
      })
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [t, notify])

  useEffect(() => {
    if (can('workforce.view')) void load()
  }, [can, load])

  const onCreate = async () => {
    const display_name = nameDraft.trim()
    if (!display_name) {
      notify({
        variant: 'error',
        title: t('app.hr.employees.name_required', { defaultValue: 'Enter a name' }),
      })
      return
    }
    setCreating(true)
    try {
      await createWorkforceEmployee({ display_name, status: 'onboarding' })
      setNameDraft('')
      notify({
        variant: 'success',
        title: t('app.hr.employees.created', { defaultValue: 'Employee created' }),
      })
      await load()
    } catch {
      notify({
        variant: 'error',
        title: t('app.hr.employees.create_error', { defaultValue: 'Could not create employee' }),
      })
    } finally {
      setCreating(false)
    }
  }

  if (!can('workforce.view')) {
    return (
      <div className="p-6 text-sm text-slate-600">
        {t('app.hr.employees.forbidden', { defaultValue: 'You do not have access to the HR workspace.' })}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4 md:p-6 max-w-6xl mx-auto w-full">
      <PageBreadcrumb
        items={[
          { to: CRM_APP_PATHS.overview, label: t('app.nav.items.overview', { defaultValue: 'Insights' }) },
          { label: t('app.nav.items.hr_employees', { defaultValue: 'HR · Employees' }) },
        ]}
      />
      <div>
        <h1 className="text-xl font-semibold text-slate-900">
          {t('app.hr.employees.title', { defaultValue: 'Employees (HR workspace)' })}
        </h1>
        <p className="text-sm text-slate-500 mt-1 max-w-2xl">{t('app.hr.employees.subtitle')}</p>
        <p className="text-sm text-slate-600 mt-2">
          <Link className="text-sky-700 hover:underline" to={CRM_APP_DRILLDOWN_HREFS.candidatesStageEmploymentPending}>
            {t('app.hr.employees.link_pending')}
          </Link>
        </p>
      </div>

      {can('workforce.manage') && (
        <div className="flex flex-wrap items-end gap-2 border border-slate-200 rounded-lg p-3 bg-slate-50/80">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-500" htmlFor="hr-emp-name">
              {t('app.hr.employees.add_manual', { defaultValue: 'Add without candidate link' })}
            </label>
            <input
              id="hr-emp-name"
              className="border border-slate-200 rounded px-2 py-1.5 text-sm min-w-[220px]"
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              placeholder={t('app.hr.employees.display_name', { defaultValue: 'Full name' })}
            />
          </div>
          <button
            type="button"
            className="px-3 py-1.5 rounded text-sm font-medium bg-slate-900 text-white disabled:opacity-50"
            disabled={creating}
            onClick={() => void onCreate()}
          >
            {t('app.hr.employees.create', { defaultValue: 'Create' })}
          </button>
        </div>
      )}

      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
        {loading ? (
          <div className="p-6 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</div>
        ) : !rows || rows.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">
            {t('app.hr.employees.empty', { defaultValue: 'No employees yet. Create one above or hand off from a candidate.' })}
          </div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-3 py-2 font-medium">{t('app.hr.employees.col_name', { defaultValue: 'Name' })}</th>
                <th className="px-3 py-2 font-medium">{t('app.hr.employees.col_status', { defaultValue: 'Status' })}</th>
                <th className="px-3 py-2 font-medium">{t('app.hr.employees.col_hire', { defaultValue: 'Hire date' })}</th>
                <th className="px-3 py-2 font-medium">{t('app.hr.employees.col_candidate', { defaultValue: 'From candidate' })}</th>
                <th className="px-3 py-2 font-medium w-28">{t('app.hr.employees.col_actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2 font-medium text-slate-900">{r.display_name}</td>
                  <td className="px-3 py-2 text-slate-700">{r.status}</td>
                  <td className="px-3 py-2 text-slate-600">{r.hire_date || '—'}</td>
                  <td className="px-3 py-2 text-slate-600 font-mono text-xs">{r.candidate_id || '—'}</td>
                  <td className="px-3 py-2">
                    <Link
                      className="text-sm text-brand-600 hover:underline"
                      to={hrEmployeePath(r.id)}
                    >
                      {t('app.hr.employees.open', { defaultValue: 'Open' })}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
