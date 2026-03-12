import { useEffect, useState } from 'react'
import { listInvoices } from '../api/client'
import type { Invoice, InvoiceStatus } from '../api/types'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

const STATUS_OPTIONS: InvoiceStatus[] = ['draft', 'issued', 'sent', 'paid', 'overdue', 'cancelled']

const currency = new Intl.NumberFormat('pl-PL', {
  style: 'currency',
  currency: 'PLN',
})

function formatAmount(value: number | null | undefined, fallback = '-') {
  if (value == null || Number.isNaN(value)) {
    return fallback
  }
  try {
    return currency.format(value)
  } catch (err) {
    return value.toFixed(2)
  }
}

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleDateString('pl-PL')
  } catch {
    return dateStr
  }
}

function statusBadgeClass(status: InvoiceStatus): string {
  const classes: Record<InvoiceStatus, string> = {
    draft: 'bg-slate-100 text-slate-700',
    issued: 'bg-blue-100 text-blue-700',
    sent: 'bg-indigo-100 text-indigo-700',
    paid: 'bg-green-100 text-green-700',
    overdue: 'bg-red-100 text-red-700',
    cancelled: 'bg-slate-100 text-slate-700',
  }
  return classes[status] || 'bg-slate-100 text-slate-700'
}

export default function InvoicesPage() {
  const { t } = useI18n()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listInvoices({ status: statusFilter || undefined, limit: 100 })
      .then((data: Invoice[]) => {
        if (!cancelled) {
          setInvoices(Array.isArray(data) ? data : [])
        }
      })
      .catch((err: any) => {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err?.message || 'Failed to load invoices')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [statusFilter, reloadKey])

  return (
    <div className="h-full w-full flex flex-col space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">{t('app.invoices.title', { defaultValue: 'Invoices' })}</h1>
        <button
          className="btn-primary"
          onClick={() => {
            // TODO: Open create invoice form
            alert('Create invoice form - coming soon')
          }}
        >
          {t('app.invoices.create', { defaultValue: 'Create Invoice' })}
        </button>
      </div>

      <div className="app-surface space-y-4 p-6">
        <div className="flex items-center gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.invoices.filter_status', { defaultValue: 'Status' })}
            </span>
            <select
              className="input"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | '')}
            >
              <option value="">{t('app.invoices.all_statuses', { defaultValue: 'All statuses' })}</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {t(`app.invoices.status.${status}`, { defaultValue: status })}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
            }}
            onRetry={() => setReloadKey((prev) => prev + 1)}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            compact
          />
        )}

        {loading ? (
          <div className="text-center py-8 text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
        ) : invoices.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            {t('app.invoices.empty', { defaultValue: 'No invoices found' })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.number', { defaultValue: 'Number' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.issue_date', { defaultValue: 'Issue Date' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.due_date', { defaultValue: 'Due Date' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.total', { defaultValue: 'Total' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.paid', { defaultValue: 'Paid' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.status', { defaultValue: 'Status' })}
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <a
                        href={`/app/invoices/${invoice.id}`}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {invoice.invoice_number}
                      </a>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatDate(invoice.issue_date)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatDate(invoice.due_date)}</td>
                    <td className="py-3 px-4 text-sm font-semibold text-slate-900">
                      {formatAmount(invoice.total_amount)}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatAmount(invoice.paid_amount)}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(
                          invoice.status
                        )}`}
                      >
                        {t(`app.invoices.status.${invoice.status}`, { defaultValue: invoice.status })}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
