import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconPlus } from '@tabler/icons-react'
import { listSalesOrders, type SalesOrder } from '../../api/salesOrders'
import { listCompanies } from '../../api/client'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SALES_ORDERS_PATH, salesOrderNewPath, salesOrderPath } from '../../app/salesPaths'
import { useI18n } from '../../i18n'
import { ContextHelp } from '../../components/help/ContextHelp'

function statusLabel(status: string, t: ReturnType<typeof useI18n>['t']) {
  const key = `app.sales_orders.status.${status}`
  return t(key, { defaultValue: status })
}

export default function SalesOrdersListPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [rows, setRows] = useState<SalesOrder[]>([])
  const [companyNames, setCompanyNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [orders, companiesRaw] = await Promise.all([
        listSalesOrders({
          status: statusFilter || undefined,
          limit: 200,
        }),
        listCompanies({ limit: 500 }).catch(() => []),
      ])
      setRows(orders)
      const companies = Array.isArray((companiesRaw as { items?: unknown })?.items)
        ? (companiesRaw as { items: Array<{ id?: string; name?: string }> }).items
        : Array.isArray(companiesRaw)
          ? (companiesRaw as Array<{ id?: string; name?: string }>)
          : []
      const map: Record<string, string> = {}
      for (const c of companies) {
        if (c?.id) map[String(c.id)] = String(c.name || c.id)
      }
      setCompanyNames(map)
    } catch (e) {
      setRows([])
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="mx-auto max-w-4xl space-y-4 overflow-y-auto px-4 py-4 sm:px-6" data-testid="sales-orders-list">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="inline-flex items-center gap-1.5 text-lg font-semibold text-slate-900">
            {t('app.sales_orders.list.title', { defaultValue: 'Service Orders' })}
            <ContextHelp term="order" />
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.sales_orders.list.subtitle', {
              defaultValue: 'Коммерческие заказы клиента: снимок сделки и линии спроса (ADR-032).',
            })}
          </p>
        </div>
        <button
          type="button"
          className="btn-primary inline-flex items-center gap-2"
          data-testid="sales-orders-create"
          onClick={() => navigate(salesOrderNewPath())}
        >
          <IconPlus size={16} stroke={1.9} />
          {t('app.sales_orders.list.create', { defaultValue: 'Новый заказ' })}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-slate-600">
          {t('app.sales_orders.list.filter_status', { defaultValue: 'Статус' })}
          <select
            className="input ml-2 w-auto"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            data-testid="sales-orders-status-filter"
          >
            <option value="">{t('app.sales_orders.list.filter_all', { defaultValue: 'Все' })}</option>
            <option value="open">open</option>
            <option value="in_progress">in_progress</option>
            <option value="completed">completed</option>
            <option value="cancelled">cancelled</option>
          </select>
        </label>
      </div>

      {error ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</p>
      ) : rows.length === 0 ? (
        <section className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
          <h3 className="text-base font-semibold text-slate-900">
            {t('app.sales_orders.list.empty_title', { defaultValue: 'Пока нет заказов' })}
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.sales_orders.list.empty_body', {
              defaultValue: 'Создайте Service Order для клиента, затем добавьте Order Lines под вакансии.',
            })}
          </p>
          <button
            type="button"
            className="btn-primary mt-4"
            onClick={() => navigate(salesOrderNewPath())}
          >
            {t('app.sales_orders.list.create', { defaultValue: 'Новый заказ' })}
          </button>
        </section>
      ) : (
        <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {rows.map((order) => (
            <li key={order.id}>
              <Link
                to={salesOrderPath(order.id)}
                className="flex items-center justify-between gap-3 px-4 py-3 transition hover:bg-slate-50"
                data-testid={`sales-order-row-${order.id}`}
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-900">{order.title}</p>
                  <p className="mt-0.5 truncate text-sm text-slate-500">
                    {companyNames[order.company_id] || order.company_id.slice(0, 8)}
                    {' · '}
                    {order.lines?.length ?? 0}{' '}
                    {t('app.sales_orders.list.lines', { defaultValue: 'линий' })}
                    {order.currency ? ` · ${order.currency}` : ''}
                  </p>
                </div>
                <span className="shrink-0 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
                  {statusLabel(String(order.status), t)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-slate-400">
        {t('app.sales_orders.list.services_note', {
          defaultValue: 'Не путать с услугами доп. сервисов — они остаются на',
        })}{' '}
        <Link to={CRM_APP_PATHS.orders} className="underline hover:text-brand-700">
          {CRM_APP_PATHS.orders}
        </Link>
        . SoT: {SALES_ORDERS_PATH}
      </p>
    </div>
  )
}
