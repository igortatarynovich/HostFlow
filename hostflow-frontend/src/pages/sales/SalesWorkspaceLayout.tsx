import { Outlet, useLocation } from 'react-router-dom'
import { SALES_HOME_PATH, SALES_ORDERS_PATH } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

export default function SalesWorkspaceLayout() {
  const { t } = useI18n()
  const location = useLocation()
  const onInquiries =
    location.pathname === SALES_HOME_PATH || location.pathname.startsWith(`${SALES_HOME_PATH}/inquiries`)
  const onOrders = location.pathname === SALES_ORDERS_PATH || location.pathname.startsWith(`${SALES_ORDERS_PATH}/`)

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-slate-200 bg-slate-50/80 px-3 py-2 sm:px-4">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-700">
          {t('app.sales_workspace.eyebrow', { defaultValue: 'Продажи' })}
        </p>
        <h1 className="mt-0.5 text-lg font-semibold text-slate-900">
          {onOrders
            ? t('app.sales_workspace.orders_title', { defaultValue: 'Заказы' })
            : onInquiries
              ? t('app.sales_workspace.inquiries_title', { defaultValue: 'Обращения' })
              : t('app.sales_workspace.title', { defaultValue: 'Продажи' })}
        </h1>
      </header>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
