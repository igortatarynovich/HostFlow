import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  cancelInvoice,
  createPayment,
  createReminder,
  getInvoiceActivity,
  getInvoice,
  getInvoicePdf,
  listReminders,
  sendInvoice,
  updateInvoice,
} from '../api/client'
import type { Invoice, InvoiceActivity, InvoiceStatus, ReminderRecord } from '../api/types'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

const currencyFormatter = new Intl.NumberFormat('pl-PL', {
  style: 'currency',
  currency: 'PLN',
})

function formatAmount(value: number | null | undefined, fallback = '-') {
  if (value == null || Number.isNaN(value)) return fallback
  try {
    return currencyFormatter.format(value)
  } catch {
    return value.toFixed(2)
  }
}

function formatDate(value: string | null | undefined) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleDateString('pl-PL')
  } catch {
    return value
  }
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('pl-PL')
  } catch {
    return value
  }
}

function formatAddress(value: Record<string, any> | null | undefined) {
  if (!value) return '-'
  return [value.country, value.city, value.street, value.zip].filter(Boolean).join(', ') || '-'
}

function statusBadgeClass(status: InvoiceStatus): string {
  const classes: Record<InvoiceStatus, string> = {
    draft: 'bg-slate-100 text-slate-700',
    issued: 'bg-blue-100 text-blue-700',
    sent: 'bg-indigo-100 text-indigo-700',
    paid: 'bg-green-100 text-green-700',
    overdue: 'bg-red-100 text-red-700',
    cancelled: 'bg-slate-100 text-slate-700',
    refunded: 'bg-amber-100 text-amber-700',
  }
  return classes[status] || 'bg-slate-100 text-slate-700'
}

type TimelineItem = {
  key: string
  ts: string
  title: string
  detail?: string | null
  tone?: 'default' | 'success' | 'warning'
}

function invoiceActionMeta(action: string, t: ReturnType<typeof useI18n>['t']): Pick<TimelineItem, 'title' | 'tone'> {
  switch (action) {
    case 'invoice.created':
      return { title: t('app.invoices.timeline.created', { defaultValue: 'Invoice created' }), tone: 'default' }
    case 'invoice.issued':
      return { title: t('app.invoices.timeline.issued', { defaultValue: 'Invoice issued' }), tone: 'default' }
    case 'invoice.sent':
      return { title: t('app.invoices.timeline.sent', { defaultValue: 'Invoice sent' }), tone: 'default' }
    case 'invoice.send_failed':
      return { title: t('app.invoices.timeline.send_failed', { defaultValue: 'Invoice delivery failed' }), tone: 'warning' }
    case 'invoice.payment_recorded':
      return { title: t('app.invoices.timeline.paid', { defaultValue: 'Payment recorded' }), tone: 'success' }
    case 'invoice.reminder_created':
      return { title: t('app.invoices.timeline.reminder', { defaultValue: 'Follow-up reminder' }), tone: 'default' }
    case 'invoice.reminder_completed':
      return { title: t('app.invoices.timeline.reminder_completed', { defaultValue: 'Reminder completed' }), tone: 'success' }
    case 'invoice.cancelled':
      return { title: t('app.invoices.timeline.cancelled', { defaultValue: 'Invoice cancelled' }), tone: 'warning' }
    case 'invoice.status_changed':
      return { title: t('app.invoices.timeline.status', { defaultValue: 'Status updated' }), tone: 'default' }
    default:
      return { title: action, tone: 'default' }
  }
}

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useI18n()
  const navigate = useNavigate()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [activities, setActivities] = useState<InvoiceActivity[]>([])
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      getInvoice(id),
      getInvoiceActivity(id, { limit: 100 }),
      listReminders({ entityType: 'invoice', entityId: id, status: ['new', 'pending', 'sent', 'overdue', 'done'] }),
    ])
      .then(([invoiceData, activityData, reminderData]) => {
        if (cancelled) return
        setInvoice(invoiceData as Invoice)
        setActivities(Array.isArray(activityData) ? (activityData as InvoiceActivity[]) : [])
        setReminders(Array.isArray((reminderData as any)?.items) ? (reminderData as any).items : [])
      })
      .catch((err: any) => {
        if (cancelled) return
        setError(err?.response?.data?.detail || err?.message || 'Failed to load invoice')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, reloadKey])

  const timelineItems = useMemo(() => {
    if (!invoice) return []
    const items: TimelineItem[] = activities.map((activity) => {
      const meta = invoiceActionMeta(activity.action, t)
      const nextStatus = activity.payload?.next_status
      const detail =
        activity.action === 'invoice.payment_recorded'
          ? `${formatAmount(Number(activity.payload?.amount || 0))} • ${String(activity.payload?.method || '-')}`
          : activity.action === 'invoice.reminder_created'
            ? `${String(activity.payload?.title || '-')} • due ${formatDateTime(activity.payload?.due_at || null)}`
            : activity.action === 'invoice.reminder_completed'
              ? `${String(activity.payload?.title || '-')} • ${formatDateTime(activity.payload?.completed_at || null)}`
          : activity.action === 'invoice.sent'
            ? `${String(activity.payload?.recipient_email || invoice.billing_details?.email || '-')} • ${String(activity.payload?.delivery_status || 'sent')}`
            : activity.action === 'invoice.send_failed'
              ? `${String(activity.payload?.recipient_email || invoice.billing_details?.email || '-')} • ${String(activity.payload?.reason || 'failed')}`
            : nextStatus
              ? `${String(activity.payload?.previous_status || '-')} → ${String(nextStatus)}`
              : String(activity.payload?.source || activity.payload?.invoice_number || '').trim() || null
      return {
        key: `activity:${activity.id}`,
        ts: activity.created_at,
        title: meta.title,
        detail,
        tone: meta.tone,
      }
    })
    return items.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())
  }, [activities, invoice, t])

  const outstandingAmount = useMemo(() => {
    if (!invoice) return 0
    return Math.max(0, Number(invoice.total_amount || 0) - Number(invoice.paid_amount || 0))
  }, [invoice])

  const withAction = async (action: string, fn: () => Promise<void>) => {
    setBusyAction(action)
    setActionError(null)
    setActionMessage(null)
    try {
      await fn()
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || err?.message || 'Invoice action failed')
    } finally {
      setBusyAction(null)
    }
  }

  const refreshInvoice = async () => {
    if (!id) return
    const [invoiceData, activityData, reminderData] = await Promise.all([
      getInvoice(id),
      getInvoiceActivity(id, { limit: 100 }),
      listReminders({ entityType: 'invoice', entityId: id, status: ['new', 'pending', 'sent', 'overdue', 'done'] }),
    ])
    setInvoice(invoiceData as Invoice)
    setActivities(Array.isArray(activityData) ? (activityData as InvoiceActivity[]) : [])
    setReminders(Array.isArray((reminderData as any)?.items) ? (reminderData as any).items : [])
  }

  const handleIssue = async () => {
    if (!invoice) return
    await withAction('issue', async () => {
      const updated = await updateInvoice(invoice.id, { status: 'issued' })
      setInvoice(updated as Invoice)
      await refreshInvoice()
      setActionMessage(t('app.invoices.issue_success', { defaultValue: 'Invoice issued.' }))
    })
  }

  const handleSend = async () => {
    if (!invoice) return
    await withAction('send', async () => {
      const updated = await sendInvoice(invoice.id)
      setInvoice(updated as Invoice)
      await refreshInvoice()
      setActionMessage(
        t('app.invoices.send_success', {
          defaultValue: invoice.status === 'sent' ? 'Invoice resent.' : 'Invoice sent.',
        }),
      )
    })
  }

  const handleMarkPaid = async () => {
    if (!invoice || outstandingAmount <= 0) return
    await withAction('paid', async () => {
      await createPayment(invoice.id, {
        amount: outstandingAmount,
        currency: invoice.currency || 'PLN',
        payment_date: new Date().toISOString().slice(0, 10),
        method: 'bank_transfer',
        status: 'confirmed',
      })
      await refreshInvoice()
      setActionMessage(t('app.invoices.mark_paid_success', { defaultValue: 'Payment recorded.' }))
    })
  }

  const handleCancel = async () => {
    if (!invoice) return
    await withAction('cancel', async () => {
      const updated = await cancelInvoice(invoice.id)
      setInvoice(updated as Invoice)
      await refreshInvoice()
      setActionMessage(t('app.invoices.cancel_success', { defaultValue: 'Invoice cancelled.' }))
    })
  }

  const handlePdf = async () => {
    if (!invoice) return
    await withAction('pdf', async () => {
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
  }

  const handleRemind = async () => {
    if (!invoice) return
    await withAction('remind', async () => {
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
      await refreshInvoice()
      setActionMessage(t('app.invoices.remind_success', { defaultValue: 'Follow-up reminder created.' }))
    })
  }

  if (loading) {
    return <div className="p-6 text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>
  }

  if (error || !invoice) {
    return (
      <div className="p-6">
        <ErrorRecoveryBanner
          info={{
            title: error || t('app.invoices.not_found', { defaultValue: 'Invoice not found' }),
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => setReloadKey((prev) => prev + 1)}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
        />
      </div>
    )
  }

  return (
    <div className="flex h-full w-full flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-2">
          <button type="button" className="text-sm text-brand-700 hover:underline" onClick={() => navigate('/app/invoices')}>
            {t('app.invoices.back', { defaultValue: 'Back to invoices' })}
          </button>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{invoice.invoice_number}</h1>
            <span className={`inline-flex rounded-md px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(invoice.status)}`}>
              {t(`app.invoices.status.${invoice.status}`, { defaultValue: invoice.status })}
            </span>
          </div>
          <p className="text-sm text-slate-500">
            {invoice.billing_details?.email || t('app.invoices.no_recipient', { defaultValue: 'No recipient email' })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => navigate(`/app/invoices/new?source_invoice_id=${invoice.id}`)}
          >
            {t('app.invoices.duplicate', { defaultValue: 'Duplicate' })}
          </button>
          {invoice.status === 'draft' && (
            <button type="button" className="btn-secondary btn-sm" onClick={() => navigate(`/app/invoices/${invoice.id}/edit`)}>
              {t('app.invoices.edit', { defaultValue: 'Edit Draft' })}
            </button>
          )}
          {invoice.status === 'draft' && (
            <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'issue'} onClick={() => void handleIssue()}>
              {busyAction === 'issue' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.invoices.issue', { defaultValue: 'Issue' })}
            </button>
          )}
          {(invoice.status === 'issued' || invoice.status === 'sent') && (
            <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'send'} onClick={() => void handleSend()}>
              {busyAction === 'send'
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t(invoice.status === 'sent' ? 'app.invoices.resend' : 'app.invoices.send', {
                    defaultValue: invoice.status === 'sent' ? 'Resend' : 'Send',
                  })}
            </button>
          )}
          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
            <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'paid'} onClick={() => void handleMarkPaid()}>
              {busyAction === 'paid'
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('app.invoices.mark_paid', { defaultValue: 'Mark paid' })}
            </button>
          )}
          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
            <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'remind'} onClick={() => void handleRemind()}>
              {busyAction === 'remind'
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('app.invoices.remind', { defaultValue: 'Remind' })}
            </button>
          )}
          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
            <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'cancel'} onClick={() => void handleCancel()}>
              {busyAction === 'cancel'
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('app.invoices.cancel', { defaultValue: 'Cancel' })}
            </button>
          )}
          <button type="button" className="btn-secondary btn-sm" disabled={busyAction === 'pdf'} onClick={() => void handlePdf()}>
            {busyAction === 'pdf' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.invoices.pdf', { defaultValue: 'PDF' })}
          </button>
        </div>
      </div>

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

      {actionMessage && <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{actionMessage}</div>}

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.total', { defaultValue: 'Total' })}</div>
          <div className="mt-2 text-xl font-semibold text-slate-900">{formatAmount(Number(invoice.total_amount || 0))}</div>
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">{t('app.invoices.paid', { defaultValue: 'Paid' })}</div>
          <div className="mt-2 text-xl font-semibold text-emerald-900">{formatAmount(Number(invoice.paid_amount || 0))}</div>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">{t('app.invoices.snapshot.outstanding', { defaultValue: 'Outstanding' })}</div>
          <div className="mt-2 text-xl font-semibold text-amber-900">{formatAmount(outstandingAmount)}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.last_activity', { defaultValue: 'Last activity' })}</div>
          <div className="mt-2 text-sm font-medium text-slate-900">{formatDateTime(invoice.payment_date || invoice.updated_at)}</div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)]">
        <section className="app-surface space-y-4 p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('app.invoices.timeline.title', { defaultValue: 'Timeline' })}</h2>
              <p className="text-sm text-slate-500">{t('app.invoices.timeline.subtitle', { defaultValue: 'Status, reminders and payment activity.' })}</p>
            </div>
            <Link to="/app/reminders" className="text-sm text-brand-700 hover:underline">
              {t('app.invoices.open_reminders', { defaultValue: 'Open reminders' })}
            </Link>
          </div>
          <div className="space-y-3">
            {timelineItems.map((item) => (
              <div key={item.key} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div
                      className={`text-sm font-semibold ${
                        item.tone === 'success'
                          ? 'text-emerald-700'
                          : item.tone === 'warning'
                            ? 'text-amber-700'
                            : 'text-slate-900'
                      }`}
                    >
                      {item.title}
                    </div>
                    {item.detail && <div className="mt-1 text-sm text-slate-600">{item.detail}</div>}
                  </div>
                  <div className="text-xs text-slate-500">{formatDateTime(item.ts)}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="app-surface space-y-4 p-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('app.invoices.items', { defaultValue: 'Items' })}</h2>
              <p className="text-sm text-slate-500">{t('app.invoices.items_subtitle', { defaultValue: 'Billable lines included in this invoice.' })}</p>
            </div>
            <div className="space-y-3">
              {invoice.items.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-900">{item.description}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.quantity} × {formatAmount(Number(item.unit_price || 0))} • VAT {item.vat_rate}%
                      </div>
                    </div>
                    <div className="text-sm font-semibold text-slate-900">{formatAmount(Number(item.amount || 0))}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="app-surface space-y-4 p-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('app.invoices.context', { defaultValue: 'Context' })}</h2>
              <p className="text-sm text-slate-500">{t('app.invoices.context_subtitle', { defaultValue: 'Related client, service order and billing data.' })}</p>
            </div>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issue_date', { defaultValue: 'Issue Date' })}</dt>
                <dd className="mt-1 text-slate-900">{formatDate(invoice.issue_date)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.due_date', { defaultValue: 'Due Date' })}</dt>
                <dd className="mt-1 text-slate-900">{formatDate(invoice.due_date)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issuer', { defaultValue: 'Issuer company' })}</dt>
                <dd className="mt-1 text-slate-900">{String(invoice.billing_details?.issuer_name || '-')}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issuer_tax_id', { defaultValue: 'Issuer tax ID' })}</dt>
                <dd className="mt-1 text-slate-900">{String(invoice.billing_details?.issuer_tax_id || '-')}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issuer_address', { defaultValue: 'Issuer address' })}</dt>
                <dd className="mt-1 text-slate-900">{formatAddress((invoice.billing_details?.issuer_address as Record<string, any> | null | undefined) || null)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.recipient', { defaultValue: 'Recipient' })}</dt>
                <dd className="mt-1 text-slate-900">{invoice.billing_details?.email || '-'}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.currency', { defaultValue: 'Currency' })}</dt>
                <dd className="mt-1 text-slate-900">{invoice.currency || '-'}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.payment_terms', { defaultValue: 'Payment terms (days)' })}</dt>
                <dd className="mt-1 text-slate-900">{String(invoice.billing_details?.payment_terms_days || '-')}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.tax_mode', { defaultValue: 'Tax mode' })}</dt>
                <dd className="mt-1 text-slate-900">{String(invoice.billing_details?.tax_mode || '-')}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.bank_account', { defaultValue: 'Bank account' })}</dt>
                <dd className="mt-1 text-slate-900">
                  {String((invoice.billing_details?.issuer_bank_account as Record<string, any> | undefined)?.iban || '-')}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.bank_name', { defaultValue: 'Bank name' })}</dt>
                <dd className="mt-1 text-slate-900">
                  {String((invoice.billing_details?.issuer_bank_account as Record<string, any> | undefined)?.bank_name || '-')}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.swift', { defaultValue: 'SWIFT/BIC' })}</dt>
                <dd className="mt-1 text-slate-900">
                  {String((invoice.billing_details?.issuer_bank_account as Record<string, any> | undefined)?.swift_bic || '-')}
                </dd>
              </div>
            </dl>
            <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
              {invoice.company_id && (
                <Link to={`/app/clients/${invoice.company_id}`} className="text-sm text-brand-700 hover:underline">
                  {t('app.invoices.open_client', { defaultValue: 'Open client' })}
                </Link>
              )}
              {invoice.service_order_id && (
                <Link to={`/app/services?order=${invoice.service_order_id}`} className="text-sm text-brand-700 hover:underline">
                  {t('app.invoices.open_service_order', { defaultValue: 'Open service order' })}
                </Link>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
