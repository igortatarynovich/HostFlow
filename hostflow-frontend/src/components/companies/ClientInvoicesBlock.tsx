import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getInvoicePdf, listInvoices, sendInvoice } from '../../api/client'
import type { Invoice } from '../../api/types'
import { recordTtvStepCompleted } from '../../api/analytics'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

const STATUS_BADGE: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  issued: 'bg-blue-100 text-blue-700',
  sent: 'bg-indigo-100 text-indigo-700',
  paid: 'bg-emerald-100 text-emerald-700',
  overdue: 'bg-rose-100 text-rose-700',
  cancelled: 'bg-slate-100 text-slate-600',
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}

function formatAmount(value: number | null | undefined, currency = 'PLN') {
  if (value == null || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value)
}

export function ClientInvoicesBlock({
  companyId,
  companyName,
}: {
  companyId: string
  companyName: string
}) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const firstInvoiceSentRecordedRef = useRef(false)
  useEffect(() => {
    try {
      firstInvoiceSentRecordedRef.current = window.localStorage.getItem('hf:ttv:first_invoice_sent') === '1'
    } catch {
      firstInvoiceSentRecordedRef.current = false
    }
  }, [])

  const load = useCallback(async () => {
    if (!companyId) return
    setLoading(true)
    setError(null)
    try {
      const data = await listInvoices({ company_id: companyId, limit: 50 })
      setInvoices(Array.isArray(data) ? data : [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load invoices')
    } finally {
      setLoading(false)
    }
  }, [companyId])

  useEffect(() => {
    load()
  }, [load])

  const handleSend = async (invoice: Invoice) => {
    if (invoice.status !== 'issued' && invoice.status !== 'sent') return
    setSendingId(invoice.id)
    try {
      await sendInvoice(invoice.id)
      if (!firstInvoiceSentRecordedRef.current) {
        firstInvoiceSentRecordedRef.current = true
        try {
          window.localStorage.setItem('hf:ttv:first_invoice_sent', '1')
        } catch {}
        void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'first_invoice_sent' })
      }
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to send')
    } finally {
      setSendingId(null)
    }
  }

  const handleDownloadPdf = async (invoice: Invoice) => {
    try {
      const blob = await getInvoicePdf(invoice.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `invoice_${invoice.invoice_number}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to download PDF')
    }
  }

  const openCreateInvoice = () => {
    const params = new URLSearchParams()
    params.set('company_id', companyId)
    navigate(`${CRM_APP_PATHS.invoiceNew}?${params.toString()}`)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">
            {t('app.companies.invoices.title', { defaultValue: 'Счета' })}
          </h3>
          <p className="text-xs text-slate-500">
            {t('app.companies.invoices.subtitle', {
              defaultValue: 'Счета по клиенту',
            })}
          </p>
        </div>
        <button type="button" className="btn-primary text-sm" onClick={openCreateInvoice}>
          {t('app.companies.invoices.create', { defaultValue: 'Выставить счёт' })}
        </button>
      </div>
      {error && <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
      {loading ? (
        <div className="text-sm text-slate-500">
          {t('common.loading', { defaultValue: 'Загрузка…' })}
        </div>
      ) : invoices.length === 0 ? (
        <p className="text-sm text-slate-500">
          {t('app.companies.invoices.empty', { defaultValue: 'Счетов нет' })}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-100">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80">
                <th className="px-3 py-2 text-left font-semibold text-slate-600">
                  {t('app.invoices.number', { defaultValue: 'Номер' })}
                </th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">
                  {t('app.invoices.issue_date', { defaultValue: 'Дата' })}
                </th>
                <th className="px-3 py-2 text-right font-semibold text-slate-600">
                  {t('app.invoices.total', { defaultValue: 'Сумма' })}
                </th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">
                  {t('app.invoices.status', { defaultValue: 'Статус' })}
                </th>
                <th className="px-3 py-2 text-right font-semibold text-slate-600">
                  {t('common.actions.title', { defaultValue: 'Действия' })}
                </th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} className="border-b border-slate-50 last:border-0">
                  <td className="px-3 py-2">
                    <Link
                      to={`${CRM_APP_PATHS.invoices}/${invoice.id}`}
                      className="font-medium text-brand-600 hover:underline"
                    >
                      {invoice.invoice_number}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-slate-600">{formatDate(invoice.issue_date)}</td>
                  <td className="px-3 py-2 text-right font-medium">
                    {formatAmount(invoice.total_amount, invoice.currency)}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[invoice.status] ?? 'bg-slate-100'}`}
                    >
                      {t(`app.invoices.status.${invoice.status}`, { defaultValue: invoice.status })}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        className="text-xs text-brand-600 hover:underline"
                        onClick={() => handleDownloadPdf(invoice)}
                      >
                        {t('app.companies.invoices.download_pdf', { defaultValue: 'PDF' })}
                      </button>
                      {(invoice.status === 'issued' || invoice.status === 'sent') && (
                        <button
                          type="button"
                          className="text-xs text-brand-600 hover:underline disabled:opacity-50"
                          onClick={() => handleSend(invoice)}
                          disabled={Boolean(sendingId)}
                        >
                          {sendingId === invoice.id
                            ? t('common.sending', { defaultValue: 'Отправка…' })
                            : t('app.companies.invoices.send_email', { defaultValue: 'Отправить' })}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
