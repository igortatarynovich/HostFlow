import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

/** CRM standard tabs (see `components.css`: `.tabs`, `.tab`, `.tab-active`). */
const tabClass = ({ isActive }: { isActive: boolean }) => clsx('tab', isActive && 'tab-active')

export default function HrWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const p = CRM_APP_PATHS

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="border-b border-brand-100 bg-white/95 px-4 py-4 shadow-sm ring-1 ring-black/5 lg:px-6">
        <div className="flex w-full max-w-none flex-col gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-900">
              {t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' })}
            </h1>
            <p className="text-sm text-slate-600">
              {t('app.nav.hr.workspace.subtitle', {
                defaultValue:
                  'Operational HR: dashboard, workforce employees, inbox, tasks, and compliance (workforce + HR APIs).',
              })}
            </p>
          </div>
          <nav className="tabs flex-wrap" aria-label={t('app.nav.hr.workspace.nav_aria', { defaultValue: 'HR sections' })}>
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
      <div className="flex-1 overflow-auto bg-gradient-to-b from-brand-50/40 to-slate-50/90">
        <div className="crm-page-inset max-w-none pb-8 pt-6">
          <Outlet key={location.pathname} />
        </div>
      </div>
    </div>
  )
}
