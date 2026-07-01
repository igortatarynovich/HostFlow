import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listInvoices } from '../../api/client'
import type { Invoice } from '../../api/types'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { invoiceDaysPastDue, invoiceOutstandingAmount } from '../../modules/services/utils'

type InvoiceWithPaid = Invoice & { paid_amount?: number | null }

export function CompanyReceivablesOverview({ companyId }: { companyId: string }) {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [invoices, setInvoices] = useState<InvoiceWithPaid[]>([])

  useEffect(() => {
    if (!companyId) return
    let cancelled = false
    setLoading(true)
    setFailed(false)
    void listInvoices({ company_id: companyId, limit: 100 })
      .then((data) => {
        if (cancelled) return
        setInvoices(Array.isArray(data) ? (data as InvoiceWithPaid[]) : [])
      })
      .catch(() => {
        if (cancelled) return
        setFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [companyId])

  const { totalOutstanding, overdueCount, maxDaysPastDue, currency } = useMemo(() => {
    let totalOutstanding = 0
    let overdueCount = 0
    let maxDaysPastDue: number | null = null
    let currency = 'PLN'
    for (const inv of invoices) {
      const st = String(inv.status || '').toLowerCase()
      if (st === 'cancelled' || st === 'paid') continue
      const out = invoiceOutstandingAmount(inv.total_amount, inv.paid_amount)
      if (out <= 0) continue
      currency = inv.currency || currency
      totalOutstanding += out
      const days = invoiceDaysPastDue(inv.due_date, out)
      if (days != null) {
        overdueCount += 1
        maxDaysPastDue = maxDaysPastDue == null ? days : Math.max(maxDaysPastDue, days)
      }
    }
    return { totalOutstanding, overdueCount, maxDaysPastDue, currency }
  }, [invoices])

  const formatAmount = (v: number) =>
    new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(v)

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }
  if (failed) {
    return <p className="text-xs text-slate-500">{t('app.companies.detail.overview.receivables.unavailable')}</p>
  }

  const invHref = `${CRM_APP_PATHS.invoices}?company_id=${encodeURIComponent(companyId)}`

  return (
    <div className="space-y-2">
      <p className="text-2xl font-semibold text-slate-900">{formatAmount(totalOutstanding)}</p>
      <p className="text-xs text-slate-500">{t('app.companies.detail.overview.receivables.outstanding_label')}</p>
      {overdueCount > 0 && (
        <p className="text-sm font-medium text-rose-700">
          {t('app.companies.detail.overview.receivables.overdue_line', {
            count: overdueCount,
            days: maxDaysPastDue ?? 0,
          })}
        </p>
      )}
      <Link to={invHref} className="text-sm text-brand-600 hover:underline">
        {t('app.companies.detail.overview.receivables.open_invoices')}
      </Link>
    </div>
  )
}
