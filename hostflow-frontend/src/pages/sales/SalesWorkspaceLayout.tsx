import { NavLink, Outlet, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SALES_HOME_PATH } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'rounded-lg px-3 py-1.5 text-sm font-medium transition',
    isActive ? 'bg-white text-brand-900 shadow-sm' : 'text-slate-600 hover:bg-white/60 hover:text-slate-900',
  )

export default function SalesWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const onInquiries = location.pathname === SALES_HOME_PATH || location.pathname.startsWith(`${SALES_HOME_PATH}/inquiries`)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-slate-200 bg-slate-50/80 px-4 py-4 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
          {t('app.sales_workspace.eyebrow', { defaultValue: 'Продажи' })}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-slate-900 sm:text-2xl">
          {onInquiries
            ? t('app.sales_workspace.inquiries_title', { defaultValue: 'Обращения' })
            : t('app.sales_workspace.title', { defaultValue: 'Продажи' })}
        </h1>
        <nav
          className="mt-3 inline-flex flex-wrap gap-1 rounded-xl bg-slate-100/80 p-1"
          aria-label={t('app.sales_workspace.nav_aria', { defaultValue: 'Разделы продаж' })}
        >
          <NavLink to={SALES_HOME_PATH} end className={tabClass}>
            {t('app.sales_workspace.nav.inquiries', { defaultValue: 'Обращения' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.clientsDirectory} className={tabClass}>
            {t('app.sales_workspace.nav.clients', { defaultValue: 'Клиенты' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.services} className={tabClass}>
            {t('app.sales_workspace.nav.services', { defaultValue: 'Услуги' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.orders} className={tabClass}>
            {t('app.sales_workspace.nav.orders', { defaultValue: 'Заказы' })}
          </NavLink>
          <NavLink to={CRM_APP_PATHS.invoices} className={tabClass}>
            {t('app.sales_workspace.nav.invoices', { defaultValue: 'Счета' })}
          </NavLink>
        </nav>
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
