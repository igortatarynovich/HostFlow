import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { cancelInvoice, createPayment, createReminder, getInvoicePdf, listInvoices, sendInvoice, updateInvoice } from '../api/client'
import type { Invoice, InvoiceStatus } from '../api/types'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { invoiceDaysPastDue, invoiceOutstandingAmount, serviceOrderWorkspacePath } from '../modules/services/utils'

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

function formatDateTime(dateStr: string | null | undefined) {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString('pl-PL')
  } catch {
    return dateStr
  }
}

function invoiceKindLabel(invoice: Invoice, t: ReturnType<typeof useI18n>['t']) {
  const kind = String(invoice.billing_details?.invoice_kind || '').trim().toLowerCase()
  if (kind === 'vat') return t('app.invoices.kind.vat', { defaultValue: 'VAT invoice' })
  if (kind === 'proforma') return t('app.invoices.kind.proforma', { defaultValue: 'Proforma' })
  if (kind === 'correction') return t('app.invoices.kind.correction', { defaultValue: 'Correction' })
  return t('app.invoices.kind.invoice', { defaultValue: 'Invoice' })
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

function deliveryBadgeClass(status: string | null | undefined): string {
  switch (status) {
    case 'sent':
      return 'bg-emerald-100 text-emerald-700'
    case 'skipped':
      return 'bg-amber-100 text-amber-700'
    case 'failed':
      return 'bg-red-100 text-red-700'
    default:
      return 'bg-slate-100 text-slate-600'
  }
}

function isLockedForCompliance(status: InvoiceStatus): boolean {
  return status === 'sent' || status === 'paid' || status === 'overdue'
}

export default function InvoicesPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<FriendlyErrorInfo | null>(null)
  const [activeInvoiceAction, setActiveInvoiceAction] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | ''>('')
  const [queueFilter, setQueueFilter] = useState<'all' | 'delivery_failed' | 'missing_recipient' | 'overdue_unpaid' | 'needs_correction'>('all')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [reloadKey, setReloadKey] = useState(0)
  const companyIdFilter = searchParams.get('company_id') || ''
  const serviceOrderIdFilter = searchParams.get('service_order_id') || ''
  const urlStatusFilter = (searchParams.get('status') || '') as InvoiceStatus | ''
  const urlQueueFilter = searchParams.get('queue') || ''
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
  const invoiceSnapshot = useMemo(() => {
    const staleThreshold = Date.now() - 7 * 24 * 60 * 60 * 1000
    return invoices.reduce(
      (acc, invoice) => {
        const recipient = String(invoice.billing_details?.email || '').trim()
        const outstanding = Number(invoice.total_amount || 0) - Number(invoice.paid_amount || 0)
        acc.totalOutstanding += Math.max(0, outstanding)
        if (!recipient) acc.missingRecipient += 1
        if (invoice.status === 'overdue') acc.overdue += 1
        if (invoice.status === 'paid') acc.paid += 1
        if (isLockedForCompliance(invoice.status)) acc.locked += 1
        if ((invoice.status === 'sent' || invoice.status === 'issued') && new Date(invoice.updated_at).getTime() <= staleThreshold) {
          acc.needsFollowUp += 1
        }
        return acc
      },
      { totalOutstanding: 0, missingRecipient: 0, overdue: 0, paid: 0, locked: 0, needsFollowUp: 0 },
    )
  }, [invoices])

  const queueCounts = useMemo(() => {
    const counts = {
      all: invoices.length,
      delivery_failed: 0,
      missing_recipient: 0,
      overdue_unpaid: 0,
      needs_correction: 0,
    }
    for (const invoice of invoices) {
      if (invoice.latest_delivery_status === 'failed') counts.delivery_failed += 1
      if (!String(invoice.billing_details?.email || '').trim()) counts.missing_recipient += 1
      if (invoice.status === 'overdue' && Number(invoice.total_amount || 0) > Number(invoice.paid_amount || 0)) counts.overdue_unpaid += 1
      if (isLockedForCompliance(invoice.status)) counts.needs_correction += 1
    }
    return counts
  }, [invoices])
  const visibleInvoices = useMemo(() => {
    return invoices.filter((invoice) => {
      if (queueFilter === 'delivery_failed') {
        return invoice.latest_delivery_status === 'failed'
      }
      if (queueFilter === 'missing_recipient') {
        return !String(invoice.billing_details?.email || '').trim()
      }
      if (queueFilter === 'overdue_unpaid') {
        return invoice.status === 'overdue' && Number(invoice.total_amount || 0) > Number(invoice.paid_amount || 0)
      }
      if (queueFilter === 'needs_correction') {
        return isLockedForCompliance(invoice.status)
      }
      return true
    })
  }, [invoices, queueFilter])
  const allVisibleSelected = useMemo(
    () => visibleInvoices.length > 0 && visibleInvoices.every((invoice) => selectedIds.includes(invoice.id)),
    [selectedIds, visibleInvoices],
  )

  useEffect(() => {
    if (urlStatusFilter && urlStatusFilter !== statusFilter) {
      setStatusFilter(urlStatusFilter)
    }
  }, [urlStatusFilter, statusFilter])

  useEffect(() => {
    const allowed: Array<typeof queueFilter> = [
      'all',
      'delivery_failed',
      'missing_recipient',
      'overdue_unpaid',
      'needs_correction',
    ]
    if (urlQueueFilter && allowed.includes(urlQueueFilter as typeof queueFilter)) {
      setQueueFilter(urlQueueFilter as typeof queueFilter)
    }
  }, [urlQueueFilter])

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
          if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.invoices.errors.load_failed'))) {
            setError(getFriendlyErrorInfo(err, t('app.invoices.errors.load_failed'), t))
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [companyIdFilter, planLimitModal, serviceOrderIdFilter, statusFilter, reloadKey, t])

  useEffect(() => {
    setSelectedIds((current) => current.filter((id) => visibleInvoices.some((invoice) => invoice.id === id)))
  }, [visibleInvoices])

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
    setQueueFilter('all')
    setSearchParams(new URLSearchParams())
  }

  const toggleOne = (invoiceId: string) => {
    setSelectedIds((current) => (current.includes(invoiceId) ? current.filter((id) => id !== invoiceId) : [...current, invoiceId]))
  }

  const toggleAllVisible = () => {
    if (allVisibleSelected) {
      setSelectedIds((current) => current.filter((id) => !visibleInvoices.some((invoice) => invoice.id === id)))
      return
    }
    setSelectedIds((current) => Array.from(new Set([...current, ...visibleInvoices.map((invoice) => invoice.id)])))
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
      if (!planLimitModal?.showPlanLimitIfNeeded(err, t('app.invoices.errors.action_failed'))) {
        setActionError(getFriendlyErrorInfo(err, t('app.invoices.errors.action_failed'), t))
      }
    } finally {
      setActiveInvoiceAction(null)
    }
  }

  const handleIssue = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'issue', async () => {
      const updated = await updateInvoice(invoice.id, { status: 'issued' })
      replaceInvoice(updated as Invoice)
      setReloadKey((prev) => prev + 1)
      setActionMessage(t('app.invoices.issue_success', { defaultValue: 'Invoice issued.' }))
    })

  const handleSend = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'send', async () => {
      const updated = await sendInvoice(invoice.id)
      replaceInvoice(updated as Invoice)
      setReloadKey((prev) => prev + 1)
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
      setReloadKey((prev) => prev + 1)
      setActionMessage(t('app.invoices.mark_paid_success', { defaultValue: 'Payment recorded.' }))
    })

  const handleCancel = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'cancel', async () => {
      const updated = await cancelInvoice(invoice.id)
      replaceInvoice(updated as Invoice)
      setReloadKey((prev) => prev + 1)
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

  const handleRemind = async (invoice: Invoice) =>
    withInvoiceAction(invoice.id, 'remind', async () => {
      const dueAt = new Date(Date.now() + 24 * 60 * 60 * 1000)
      const remindAt = new Date(Date.now() + 60 * 60 * 1000)
      await createReminder({
        title: `Invoice follow-up: ${invoice.invoice_number}`,
        description: invoice.billing_details?.email
          ? `Follow up with ${invoice.billing_details.email} about invoice ${invoice.invoice_number}.`
          : `Follow up on invoice ${invoice.invoice_number}.`,
        type: 'invoice_followup',
        entity_type: 'invoice',
        entity_id: invoice.id,
        due_at: dueAt.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: invoice.status === 'overdue' ? 'high' : 'normal',
        channel: 'internal',
        payload: {
          invoice_id: invoice.id,
          invoice_number: invoice.invoice_number,
          company_id: invoice.company_id,
          service_order_id: invoice.service_order_id,
          recipient_email: invoice.billing_details?.email || null,
          status: invoice.status,
        },
      })
      setActionMessage(t('app.invoices.remind_success', { defaultValue: 'Follow-up reminder created.' }))
    })

  const isActionBusy = (invoiceId: string, action: string) => activeInvoiceAction === `${invoiceId}:${action}`

  const runBulkAction = async (
    actionKey: string,
    predicate: (invoice: Invoice) => boolean,
    runner: (invoice: Invoice) => Promise<void>,
    successMessage: string,
  ) => {
    const selectedInvoices = visibleInvoices.filter((invoice) => selectedIds.includes(invoice.id)).filter(predicate)
    if (selectedInvoices.length === 0) {
      setActionError({
        title: t('app.invoices.bulk_none', { defaultValue: 'No matching invoices selected for this action.' }),
        hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
      })
      return
    }
    setActiveInvoiceAction(`bulk:${actionKey}`)
    setActionError(null)
    setActionMessage(null)
    const results = await Promise.allSettled(selectedInvoices.map((invoice) => runner(invoice)))
    const failed = results.filter((result) => result.status === 'rejected').length
    setActiveInvoiceAction(null)
    setReloadKey((prev) => prev + 1)
    if (failed > 0) {
      setActionError({
        title: t('app.invoices.bulk_partial_error', {
          defaultValue: 'Some bulk actions failed ({{failed}} of {{total}}).',
          values: { failed, total: selectedInvoices.length },
        }),
        hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
      })
    } else {
      setActionMessage(
        t('app.invoices.bulk_success', {
          defaultValue: '{{message}} ({{count}})',
          values: { message: successMessage, count: selectedInvoices.length },
        }),
      )
    }
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-1 flex-col space-y-0 gap-0 p-0">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">{t('app.invoices.title', { defaultValue: 'Invoices' })}</h1>
        <button
          className="btn-primary"
          onClick={() => navigate(CRM_APP_PATHS.invoiceNew)}
        >
          {t('app.invoices.create', { defaultValue: 'Create Invoice' })}
        </button>
      </div>

      <div className="app-surface space-y-0 gap-0 border-x-0 border-t-0 p-3">
        <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-6">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.invoices.snapshot.outstanding', { defaultValue: 'Outstanding' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-slate-900">{formatAmount(invoiceSnapshot.totalOutstanding, '0')}</div>
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              {t('app.invoices.snapshot.follow_up', { defaultValue: 'Needs follow-up' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-amber-900">{invoiceSnapshot.needsFollowUp}</div>
          </div>
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-red-700">
              {t('app.invoices.snapshot.overdue', { defaultValue: 'Overdue' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-red-900">{invoiceSnapshot.overdue}</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              {t('app.invoices.snapshot.paid', { defaultValue: 'Paid' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-emerald-900">{invoiceSnapshot.paid}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.invoices.snapshot.missing_recipient', { defaultValue: 'Missing recipient' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-slate-900">{invoiceSnapshot.missingRecipient}</div>
          </div>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              {t('app.invoices.snapshot.locked', { defaultValue: 'Locked' })}
            </div>
            <div className="mt-2 text-xl font-semibold text-amber-900">{invoiceSnapshot.locked}</div>
          </div>
        </div>

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

        <div className="flex flex-wrap items-center gap-2">
          {[
            { key: 'all', label: t('app.invoices.queue.all', { defaultValue: 'All queue' }) },
            { key: 'delivery_failed', label: t('app.invoices.queue.delivery_failed', { defaultValue: 'Delivery failed' }) },
            { key: 'missing_recipient', label: t('app.invoices.queue.missing_recipient', { defaultValue: 'Missing recipient' }) },
            { key: 'overdue_unpaid', label: t('app.invoices.queue.overdue_unpaid', { defaultValue: 'Overdue unpaid' }) },
            { key: 'needs_correction', label: t('app.invoices.queue.needs_correction', { defaultValue: 'Needs correction' }) },
          ].map((item) => {
            const active = queueFilter === item.key
            return (
              <button
                key={item.key}
                type="button"
                className={active ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                onClick={() => setQueueFilter(item.key as typeof queueFilter)}
              >
                {item.label} ({queueCounts[item.key as keyof typeof queueCounts]})
              </button>
            )
          })}
        </div>

        {selectedIds.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <span>
              {t('app.invoices.bulk_selected', {
                defaultValue: 'Selected: {{count}}',
                values: { count: selectedIds.length },
              })}
            </span>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={activeInvoiceAction === 'bulk:send'}
              onClick={() =>
                void runBulkAction(
                  'send',
                  (invoice) => invoice.status === 'issued' || invoice.status === 'sent',
                  async (invoice) => {
                    await sendInvoice(invoice.id)
                  },
                  t('app.invoices.bulk_send_success', { defaultValue: 'Invoices sent' }),
                )
              }
            >
              {t('app.invoices.bulk_send', { defaultValue: 'Bulk send' })}
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={activeInvoiceAction === 'bulk:remind'}
              onClick={() =>
                void runBulkAction(
                  'remind',
                  (invoice) => invoice.status !== 'paid' && invoice.status !== 'cancelled',
                  async (invoice) => {
                    const dueAt = new Date(Date.now() + 24 * 60 * 60 * 1000)
                    const remindAt = new Date(Date.now() + 60 * 60 * 1000)
                    await createReminder({
                      title: `Invoice follow-up: ${invoice.invoice_number}`,
                      description: invoice.billing_details?.email
                        ? `Follow up with ${invoice.billing_details.email} about invoice ${invoice.invoice_number}.`
                        : `Follow up on invoice ${invoice.invoice_number}.`,
                      type: 'invoice_followup',
                      entity_type: 'invoice',
                      entity_id: invoice.id,
                      due_at: dueAt.toISOString(),
                      remind_at: remindAt.toISOString(),
                      priority: invoice.status === 'overdue' ? 'high' : 'normal',
                      channel: 'internal',
                      payload: {
                        invoice_id: invoice.id,
                        invoice_number: invoice.invoice_number,
                        company_id: invoice.company_id,
                        service_order_id: invoice.service_order_id,
                        recipient_email: invoice.billing_details?.email || null,
                        status: invoice.status,
                      },
                    })
                  },
                  t('app.invoices.bulk_remind_success', { defaultValue: 'Reminders created' }),
                )
              }
            >
              {t('app.invoices.bulk_remind', { defaultValue: 'Bulk remind' })}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={() => setSelectedIds([])}>
              {t('common.actions.clear', { defaultValue: 'Clear' })}
            </button>
          </div>
        )}

        {error && (
          <ErrorRecoveryBanner
            info={error}
            onRetry={() => setReloadKey((prev) => prev + 1)}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            {...friendlyErrorBannerSecondary(
              error,
              CRM_APP_PATHS.invoices,
              t('app.invoices.title', { defaultValue: 'Invoices' }),
            )}
            compact
          />
        )}

        {actionError && (
          <ErrorRecoveryBanner
            info={actionError}
            onRetry={() => setActionError(null)}
            retryLabel={t('common.actions.dismiss', { defaultValue: 'Dismiss' })}
            {...friendlyErrorBannerSecondary(
              actionError,
              CRM_APP_PATHS.invoices,
              t('app.invoices.title', { defaultValue: 'Invoices' }),
            )}
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
        ) : visibleInvoices.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            {t('app.invoices.empty', { defaultValue: 'No invoices found' })}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-3 px-4">
                    <input type="checkbox" checked={allVisibleSelected} onChange={toggleAllVisible} />
                  </th>
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
                    {t('app.invoices.col_days_overdue', { defaultValue: 'Days overdue' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.total', { defaultValue: 'Total' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.fields.outstanding', { defaultValue: 'Outstanding' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.context', { defaultValue: 'Context' })}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.invoices.delivery', { defaultValue: 'Delivery' })}
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
                {visibleInvoices.map((invoice) => {
                  const outstanding = invoiceOutstandingAmount(invoice.total_amount, invoice.paid_amount)
                  const daysOverdue = invoiceDaysPastDue(invoice.due_date, outstanding)
                  return (
                  <tr key={invoice.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <input type="checkbox" checked={selectedIds.includes(invoice.id)} onChange={() => toggleOne(invoice.id)} />
                    </td>
                    <td className="py-3 px-4">
                      <a
                        href={`${CRM_APP_PATHS.invoices}/${invoice.id}`}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {invoice.invoice_number}
                      </a>
                      <div className="mt-1 flex flex-wrap gap-2 text-xs">
                        <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
                          {invoiceKindLabel(invoice, t)}
                        </span>
                        {invoice.billing_details?.correction_of_invoice_number && (
                          <span className="text-slate-500">
                            {t('app.invoices.correction_of', { defaultValue: 'Correction of' })}:{' '}
                            {String(invoice.billing_details?.correction_of_invoice_number)}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {invoice.billing_details?.email || t('app.invoices.no_recipient', { defaultValue: 'No recipient email' })}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatDate(invoice.issue_date)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatDate(invoice.due_date)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">
                      {daysOverdue != null ? (
                        <span className="font-semibold text-red-700">{daysOverdue}</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm font-semibold text-slate-900">
                      {formatAmount(invoice.total_amount)}
                    </td>
                    <td className="py-3 px-4 text-sm font-semibold text-slate-900">
                      {outstanding > 0 ? (
                        <span className="text-amber-800">{formatAmount(outstanding)}</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">
                      <div className="flex flex-wrap gap-2">
                        {invoice.company_id && (
                          <Link
                            to={`${CRM_APP_PATHS.agencyClients}/${invoice.company_id}`}
                            className="text-brand-700 hover:underline"
                          >
                            {t('app.invoices.open_client', { defaultValue: 'Open client' })}
                          </Link>
                        )}
                        {invoice.service_order_id && (
                          <Link
                            to={serviceOrderWorkspacePath(String(invoice.service_order_id), invoice.company_id)}
                            className="text-brand-700 hover:underline"
                          >
                            {t('app.invoices.open_service_order', { defaultValue: 'Open service order' })}
                          </Link>
                        )}
                      </div>
                      <div className="mt-2 text-xs text-slate-500">
                        {t('app.invoices.last_activity', { defaultValue: 'Last activity' })}: {formatDateTime(invoice.payment_date || invoice.updated_at)}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">
                      {invoice.latest_delivery_status ? (
                        <div className="space-y-1">
                          <span
                            className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium ${deliveryBadgeClass(
                              invoice.latest_delivery_status,
                            )}`}
                          >
                            {invoice.latest_delivery_status}
                          </span>
                          {invoice.latest_delivery_recipient && (
                            <div className="text-xs text-slate-700">{invoice.latest_delivery_recipient}</div>
                          )}
                          {invoice.latest_delivery_subject && (
                            <div className="line-clamp-2 text-xs text-slate-500">{invoice.latest_delivery_subject}</div>
                          )}
                          <div className="text-xs text-slate-500">
                            {invoice.latest_delivery_reason || formatDateTime(invoice.latest_delivery_at)}
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">
                          {invoice.billing_details?.email
                            ? t('app.invoices.delivery_not_sent', { defaultValue: 'Not sent yet' })
                            : t('app.invoices.delivery_missing_recipient', { defaultValue: 'Recipient missing' })}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{formatAmount(invoice.paid_amount)}</td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap items-center gap-1">
                        <span
                          className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(
                            invoice.status
                          )}`}
                        >
                          {t(`app.invoices.status.${invoice.status}`, { defaultValue: invoice.status })}
                        </span>
                        {isLockedForCompliance(invoice.status) && (
                          <span className="inline-flex items-center rounded-md bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
                            {t('app.invoices.locked', { defaultValue: 'LOCKED' })}
                          </span>
                        )}
                      </div>
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
                        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && !isLockedForCompliance(invoice.status) && (
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
                        {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            disabled={isActionBusy(invoice.id, 'remind')}
                            onClick={() => void handleRemind(invoice)}
                          >
                            {isActionBusy(invoice.id, 'remind')
                              ? t('common.loading', { defaultValue: 'Loading...' })
                              : t('app.invoices.remind', { defaultValue: 'Remind' })}
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() =>
                            navigate(
                              invoice.status === 'draft'
                                ? `${CRM_APP_PATHS.invoiceNew}?source_invoice_id=${invoice.id}`
                                : `${CRM_APP_PATHS.invoiceNew}?source_invoice_id=${invoice.id}&invoice_kind=correction&correction_of_invoice_id=${invoice.id}&correction_of_invoice_number=${encodeURIComponent(invoice.invoice_number)}`,
                            )
                          }
                        >
                          {t(
                            invoice.status === 'draft' ? 'app.invoices.duplicate' : 'app.invoices.create_correction',
                            { defaultValue: invoice.status === 'draft' ? 'Duplicate' : 'Create correction' },
                          )}
                        </button>
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
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
