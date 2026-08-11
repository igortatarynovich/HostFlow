import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SALES_HOME_PATH, SALES_ORDERS_PATH } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-lg px-3 py-2 text-sm font-medium transition',
    isActive ? 'bg-white text-brand-900 shadow-sm' : 'text-slate-600 hover:bg-white/60 hover:text-slate-900',
  )

export default function SalesWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const onInquiries =
    location.pathname === SALES_HOME_PATH || location.pathname.startsWith(`${SALES_HOME_PATH}/inquiries`)
  const onOrders = location.pathname === SALES_ORDERS_PATH || location.pathname.startsWith(`${SALES_ORDERS_PATH}/`)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-slate-200 bg-slate-50/80 px-4 py-4 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
          {t('app.sales_workspace.eyebrow', { defaultValue: 'Sales' })}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-slate-900 sm:text-2xl">
          {onOrders
            ? t('app.sales_workspace.orders_title', { defaultValue: 'Orders' })
            : onInquiries
              ? t('app.sales_workspace.inquiries_title', { defaultValue: 'Inquiries' })
              : t('app.sales_workspace.title', { defaultValue: 'Sales' })}
        </h1>
        <nav
          className="mt-3 inline-flex flex-wrap gap-1 rounded-xl bg-slate-100/80 p-1"
          aria-label={t('app.sales_workspace.nav_aria', { defaultValue: 'Sales sections' })}
        >
          <NavLink to={SALES_HOME_PATH} end className={tabClass}>
            {t('app.sales_workspace.nav.inquiries', { defaultValue: 'Inquiries' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.clientsDirectory} className={tabClass}>
            {t('app.sales_workspace.nav.clients', { defaultValue: 'Clients' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.services} className={tabClass}>
            {t('app.sales_workspace.nav.services', { defaultValue: 'Services' })}
          </NavLink>
          <NavLink to={SALES_ORDERS_PATH} className={tabClass}>
            {t('app.sales_workspace.nav.orders', { defaultValue: 'Orders' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.invoices} className={tabClass}>
            {t('app.sales_workspace.nav.invoices', { defaultValue: 'Invoices' })}
          </NavLink>
        </nav>
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
