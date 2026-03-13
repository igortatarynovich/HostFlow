import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { cancelInvoice, createPayment, getInvoicePdf, listInvoices, sendInvoice, updateInvoice } from '../api/client'
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [activeInvoiceAction, setActiveInvoiceAction] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('')
  const [reloadKey, setReloadKey] = useState(0)
  const companyIdFilter = searchParams.get('company_id') || ''
  const serviceOrderIdFilter = searchParams.get('service_order_id') || ''
  const urlStatusFilter = (searchParams.get('status') || '') as InvoiceStatus | ''
  const activeFilterChips = useMemo(
    () =>
      [
        companyIdFilter
          ? {
              key: 'company_id',
              label: t('app.invoices.drilldown.company', {
                defaultValue: 'Client: {{id}}',
                values: { id: companyIdFilter.slice(0, 8) },
              }),
            }
          : null,
        serviceOrderIdFilter
          ? {
              key: 'service_order_id',
              label: t('app.invoices.drilldown.service_order', {
                defaultValue: 'Service order: {{id}}',
                values: { id: serviceOrderIdFilter.slice(0, 8) },
              }),
            }
          : null,
        statusFilter
          ? {
              key: 'status',
              label: t('app.invoices.drilldown.status', {
                defaultValue: 'Status: {{status}}',
                values: { status: statusFilter },
              }),
            }
          : null,
      ].filter(Boolean) as Array<{ key: string; label: string }>,
    [companyIdFilter, serviceOrderIdFilter, statusFilter, t],
  )

  useEffect(() => {
    if (urlStatusFilter && urlStatusFilter !== statusFilter) {
      setStatusFilter(urlStatusFilter)
    }
  }, [urlStatusFilter, statusFilter])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listInvoices({
      company_id: companyIdFilter || undefined,
      service_order_id: serviceOrderIdFilter || undefined,
      status: statusFilter || undefined,
      limit: 100,
    })
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
  }, [companyIdFilter, serviceOrderIdFilter, statusFilter, reloadKey])

  const clearFilter = (key: 'company_id' | 'service_order_id' | 'status') => {
    const next = new URLSearchParams(searchParams)
    next.delete(key)
    if (key === 'status') {
      setStatusFilter('')
    }
    setSearchParams(next)
  }

  const clearAllFilters = () => {
    setStatusFilter('')
    setSearchParams(new URLSearchParams())
  }

  const replaceInvoice = (nextInvoice: Invoice) => {
    setInvoices((current) => current.map((invoice) => (invoice.id === nextInvoice.id ? nextInvoice : invoice)))
  }

  const withInvoiceAction = async (invoiceId: string, action: string, fn: () => Promise<void>) => {
    setActiveInvoiceAction(`${invoiceId}:${action}`)
    setActionError(null)
    setActionMessage(null)
    try {
      await fn()
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || err?.message || 'Invoice action failed')
    } finally {
      setActiveInvoiceAction(null)
    }
  }

  const handleIssue = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'issue', async () => {
      const updated = await updateInvoice(invoice.id, { status: 'issued' })
      replaceInvoice(updated as Invoice)
      setActionMessage(t('app.invoices.issue_success', { defaultValue: 'Invoice issued.' }))
    })

  const handleSend = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'send', async () => {
      const updated = await sendInvoice(invoice.id)
      replaceInvoice(updated as Invoice)
      setActionMessage(
        t('app.invoices.send_success', {
          defaultValue: invoice.status === 'sent' ? 'Invoice resent.' : 'Invoice sent.',
        }),
      )
    })

  const handleMarkPaid = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'mark-paid', async () => {
      const outstanding = Number(invoice.total_amount || 0) - Number(invoice.paid_amount || 0)
      if (outstanding <= 0) {
        setActionMessage(t('app.invoices.already_paid', { defaultValue: 'Invoice is already fully paid.' }))
        return
      }
      await createPayment(invoice.id, {
        amount: outstanding,
        currency: invoice.currency || 'PLN',
        payment_date: new Date().toISOString().slice(0, 10),
        method: 'bank_transfer',
        status: 'confirmed',
      })
      const updated = await updateInvoice(invoice.id, {})
      replaceInvoice(updated as Invoice)
      setActionMessage(t('app.invoices.mark_paid_success', { defaultValue: 'Payment recorded.' }))
    })

  const handleCancel = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'cancel', async () => {
      const updated = await cancelInvoice(invoice.id)
      replaceInvoice(updated as Invoice)
      setActionMessage(t('app.invoices.cancel_success', { defaultValue: 'Invoice cancelled.' }))
    })

  const handleDownloadPdf = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'pdf', async () => {
      const blob = await getInvoicePdf(invoice.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${invoice.invoice_number || 'invoice'}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    })

  const isActionBusy = (invoiceId: string, action: string) => activeInvoiceAction === `${invoiceId}:${action}`

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
          {activeFilterChips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {activeFilterChips.map((chip) => (
                <span key={chip.key} className="inline-flex items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-xs text-brand-800">
                  {chip.label}
                  <button type="button" className="btn-secondary btn-xs" onClick={() => clearFilter(chip.key as 'company_id' | 'service_order_id' | 'status')}>
                    {t('common.actions.clear', { defaultValue: 'Clear' })}
                  </button>
                </span>
              ))}
              <button type="button" className="btn-secondary btn-sm" onClick={clearAllFilters}>
                {t('app.invoices.clear_filters', { defaultValue: 'Clear filters' })}
              </button>
            </div>
          )}
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

        {actionError && (
          <ErrorRecoveryBanner
            info={{
              title: actionError,
              hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
            }}
            onRetry={() => setActionError(null)}
            retryLabel={t('common.actions.dismiss', { defaultValue: 'Dismiss' })}
            compact
          />
        )}

        {actionMessage && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {actionMessage}
          </div>
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
                    {t('app.invoices.context', { defaultValue: 'Context' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.paid', { defaultValue: 'Paid' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.status', { defaultValue: 'Status' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.actions', { defaultValue: 'Actions' })}
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
                    <td className="py-3 px-4 text-sm text-slate-700">
                      <div className="flex flex-wrap gap-2">
                        {invoice.company_id && (
                          <Link to={`/app/clients/${invoice.company_id}`} className="text-brand-700 hover:underline">
                            {t('app.invoices.open_client', { defaultValue: 'Open client' })}
                          </Link>
                        )}
                        {invoice.service_order_id && (
                          <Link to={`/app/services?order=${invoice.service_order_id}`} className="text-brand-700 hover:underline">
                            {t('app.invoices.open_service_order', { defaultValue: 'Open service order' })}
                          </Link>
                        )}
                      </div>
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
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-2">
                        {invoice.status === 'draft' && (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            disabled={isActionBusy(invoice.id, 'issue')}
                            onClick={() => void handleIssue(invoice)}
                          >
                            {isActionBusy(invoice.id, 'issue')
                              ? t('common.loading', { defaultValue: 'Loading...' })
                              : t('app.invoices.issue', { defaultValue: 'Issue' })}
                          </button>
                        )}
                        {(invoice.status === 'issued' || invoice.status === 'sent') && (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            disabled={isActionBusy(invoice.id, 'send')}
                            onClick={() => void handleSend(invoice)}
                          >
                            {isActionBusy(invoice.id, 'send')
                              ? t('common.loading', { defaultValue: 'Loading...' })
                              : t(
                                  invoice.status === 'sent' ? 'app.invoices.resend' : 'app.invoices.send',
                                  { defaultValue: invoice.status === 'sent' ? 'Resend' : 'Send' },
                                )}
                          </button>
                        )}
                        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            disabled={isActionBusy(invoice.id, 'mark-paid')}
                            onClick={() => void handleMarkPaid(invoice)}
                          >
                            {isActionBusy(invoice.id, 'mark-paid')
                              ? t('common.loading', { defaultValue: 'Loading...' })
                              : t('app.invoices.mark_paid', { defaultValue: 'Mark paid' })}
                          </button>
                        )}
                        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            disabled={isActionBusy(invoice.id, 'cancel')}
                            onClick={() => void handleCancel(invoice)}
                          >
                            {isActionBusy(invoice.id, 'cancel')
                              ? t('common.loading', { defaultValue: 'Loading...' })
                              : t('app.invoices.cancel', { defaultValue: 'Cancel' })}
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          disabled={isActionBusy(invoice.id, 'pdf')}
                          onClick={() => void handleDownloadPdf(invoice)}
                        >
                          {isActionBusy(invoice.id, 'pdf')
                            ? t('common.loading', { defaultValue: 'Loading...' })
                            : t('app.invoices.pdf', { defaultValue: 'PDF' })}
                        </button>
                      </div>
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
