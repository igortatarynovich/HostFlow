import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'

/** CRM standard tabs (see `components.css`: `.tabs`, `.tab`, `.tab-active`). */
const tabClass = ({ isActive }: { isActive: boolean }) => clsx('tab', isActive && 'tab-active')

export default function HrWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const p = CRM_APP_PATHS

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.nav.hr.workspace.title', { defaultValue: 'HR workspace' })}
          subtitle={t('app.nav.hr.workspace.subtitle', {
            defaultValue:
              'Operational HR: dashboard, workforce employees, inbox, tasks, and compliance (workforce + HR APIs).',
          })}
          kind="browse"
        />
        <nav
          className="tabs mt-1.5 flex-wrap"
          aria-label={t('app.nav.hr.workspace.nav_aria', { defaultValue: 'HR sections' })}
        >
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
      </PageShellHeader>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-gradient-to-b from-brand-50/40 to-slate-50/90 pb-8 pt-4">
        <Outlet key={location.pathname} />
      </div>
    </PageShell>
  )
}
