import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-md px-3 py-2 text-sm font-medium transition',
    isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  )

export default function HrWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const p = CRM_APP_PATHS

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="border-b border-slate-200 bg-white px-4 py-4 lg:px-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-3">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">
              {t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' })}
            </h1>
            <p className="text-sm text-slate-500">
              {t('app.nav.hr.workspace.subtitle', {
                defaultValue:
                  'Operational HR: dashboard, workforce employees, inbox, tasks, and compliance (workforce + HR APIs).',
              })}
            </p>
          </div>
          <nav className="flex flex-wrap gap-1" aria-label={t('app.nav.hr.workspace.nav_aria', { defaultValue: 'HR sections' })}>
            <NavLink to={p.hr} end className={tabClass}>
              {t('app.nav.hr.workspace.nav.dashboard', { defaultValue: 'Dashboard' })}
            </NavLink>
            <NavLink to={p.hrEmployees} className={tabClass}>
              {t('app.nav.hr.workspace.nav.employees', { defaultValue: 'Employees' })}
            </NavLink>
            <NavLink to={p.hrInbox} className={tabClass}>
              {t('app.nav.hr.workspace.nav.inbox', { defaultValue: 'Inbox' })}
            </NavLink>
            <NavLink to={p.hrTasks} className={tabClass}>
              {t('app.nav.hr.workspace.nav.tasks', { defaultValue: 'Tasks' })}
            </NavLink>
            <NavLink to={p.hrDocuments} className={tabClass}>
              {t('app.nav.hr.workspace.nav.documents', { defaultValue: 'Documents hub' })}
            </NavLink>
            <NavLink to={p.hrCompliance} className={tabClass}>
              {t('app.nav.hr.workspace.nav.compliance', { defaultValue: 'Compliance' })}
            </NavLink>
            <NavLink to={p.hrZusWorkspace} className={tabClass}>
              {t('app.nav.hr.workspace.nav.zus_workspace', { defaultValue: 'ZUS' })}
            </NavLink>
          </nav>
        </div>
      </header>
      <div className="flex-1 overflow-auto bg-slate-50/80 px-4 py-6 lg:px-6">
        <div className="mx-auto max-w-6xl">
          <Outlet key={location.pathname} />
        </div>
      </div>
    </div>
  )
}
