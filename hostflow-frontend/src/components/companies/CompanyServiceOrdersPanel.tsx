import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listServiceOrders } from '../../api/additionalServices'
import type { AdditionalServiceOrder } from '../../api/types'
import { useI18n } from '../../i18n'
import { formatAmount } from '../../modules/services/utils'

export function CompanyServiceOrdersPanel({ companyId }: { companyId: string }) {
  const { t } = useI18n()
  const [orders, setOrders] = useState<AdditionalServiceOrder[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!companyId) return
    setLoading(true)
    setError(null)
    try {
      const data = await listServiceOrders({ companyId })
      setOrders(Array.isArray(data) ? data : [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load orders')
      setOrders([])
    } finally {
      setLoading(false)
    }
  }, [companyId])

  useEffect(() => {
    void load()
  }, [load])

  if (!companyId) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-sm text-slate-500">
        {t('common.loading')}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">
            {t('app.companies.detail.workspace.orders.service_title')}
          </h3>
          <p className="text-xs text-slate-500">{t('app.companies.detail.workspace.orders.service_subtitle')}</p>
        </div>
        <Link
          to={
            companyId
              ? `/app/services?tab=orders&company_id=${encodeURIComponent(companyId)}`
              : '/app/services?tab=orders'
          }
          className="btn-secondary btn-sm shrink-0 text-center text-sm"
        >
          {t('app.companies.detail.workspace.orders.open_services')}
        </Link>
      </div>
      {error && <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">{error}</div>}
      <div className="overflow-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50/90 text-left">
            <tr>
              <th className="border-b border-r border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600">
                {t('app.companies.detail.workspace.orders.col_status')}
              </th>
              <th className="border-b border-r border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600">
                {t('app.companies.detail.workspace.orders.col_amount')}
              </th>
              <th className="border-b border-r border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600">
                {t('app.companies.detail.workspace.orders.col_items')}
              </th>
              <th className="border-b border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600">
                {t('app.companies.detail.workspace.orders.col_open')}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-slate-500">
                  {t('common.loading')}
                </td>
              </tr>
            ) : orders.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-slate-500">
                  {t('app.companies.detail.workspace.orders.empty')}
                </td>
              </tr>
            ) : (
              orders.map((ord) => (
                <tr key={ord.id} className="border-t border-slate-100">
                  <td className="border-r border-slate-200 px-3 py-2">
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-800">
                      {t(`app.services.status.order.${ord.status}`, { defaultValue: ord.status })}
                    </span>
                  </td>
                  <td className="border-r border-slate-200 px-3 py-2 tabular-nums">{formatAmount(ord.total_amount)}</td>
                  <td className="border-r border-slate-200 px-3 py-2 tabular-nums">{ord.items?.length ?? 0}</td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/app/services?tab=orders&company_id=${encodeURIComponent(companyId)}&order_id=${encodeURIComponent(ord.id)}`}
                      className="text-sm font-medium text-brand-600 hover:underline"
                    >
                      {t('app.companies.detail.workspace.orders.open')}
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
