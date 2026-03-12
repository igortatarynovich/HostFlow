import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  listInvoices,
  createInvoice,
  sendInvoice,
  getInvoicePdf,
} from '../../api/client'
import type { Invoice } from '../../api/types'
import { useI18n } from '../../i18n'
import { Modal } from '../Modal'

const STATUS_BADGE: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  issued: 'bg-blue-100 text-blue-700',
  sent: 'bg-indigo-100 text-indigo-700',
  paid: 'bg-emerald-100 text-emerald-700',
  overdue: 'bg-rose-100 text-rose-700',
  cancelled: 'bg-slate-100 text-slate-600',
}

function formatDate(s: string | null | undefined) {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleDateString()
  } catch {
    return s
  }
}

function formatAmount(val: number | null | undefined, currency = 'PLN') {
  if (val == null || Number.isNaN(val)) return '—'
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(val)
}

export function ClientInvoicesBlock({ companyId, companyName }: { companyId: string; companyName: string }) {
  const { t } = useI18n()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

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

  const handleSend = async (inv: Invoice) => {
    if (inv.status !== 'issued' && inv.status !== 'sent') return
    setSendingId(inv.id)
    try {
      await sendInvoice(inv.id)
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to send')
    } finally {
      setSendingId(null)
    }
  }

  const handleDownloadPdf = async (inv: Invoice) => {
    try {
      const blob = await getInvoicePdf(inv.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoice_${inv.invoice_number}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e?.message || 'Failed to download PDF')
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">{t('app.companies.invoices.title', { defaultValue: 'Счета' })}</h3>
          <p className="text-xs text-slate-500">{t('app.companies.invoices.subtitle', { defaultValue: 'Счета по клиенту' })}</p>
        </div>
        <button
          type="button"
          className="btn-primary text-sm"
          onClick={() => setCreateOpen(true)}
        >
          {t('app.companies.invoices.create', { defaultValue: 'Выставить счёт' })}
        </button>
      </div>
      {error && (
        <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      )}
      {loading ? (
        <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка…' })}</div>
      ) : invoices.length === 0 ? (
        <p className="text-sm text-slate-500">{t('app.companies.invoices.empty', { defaultValue: 'Счетов нет' })}</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-100">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80">
                <th className="px-3 py-2 text-left font-semibold text-slate-600">{t('app.invoices.number', { defaultValue: 'Номер' })}</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">{t('app.invoices.issue_date', { defaultValue: 'Дата' })}</th>
                <th className="px-3 py-2 text-right font-semibold text-slate-600">{t('app.invoices.total', { defaultValue: 'Сумма' })}</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">{t('app.invoices.status', { defaultValue: 'Статус' })}</th>
                <th className="px-3 py-2 text-right font-semibold text-slate-600">{t('common.actions.title', { defaultValue: 'Действия' })}</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-b border-slate-50 last:border-0">
                  <td className="px-3 py-2">
                    <Link to={`/app/invoices/${inv.id}`} className="text-brand-600 hover:underline font-medium">
                      {inv.invoice_number}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-slate-600">{formatDate(inv.issue_date)}</td>
                  <td className="px-3 py-2 text-right font-medium">{formatAmount(inv.total_amount, inv.currency)}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[inv.status] ?? 'bg-slate-100'}`}>
                      {t(`app.invoices.status.${inv.status}`, { defaultValue: inv.status })}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        className="text-brand-600 hover:underline text-xs"
                        onClick={() => handleDownloadPdf(inv)}
                      >
                        {t('app.companies.invoices.download_pdf', { defaultValue: 'PDF' })}
                      </button>
                      {(inv.status === 'issued' || inv.status === 'sent') && (
                        <button
                          type="button"
                          className="text-brand-600 hover:underline text-xs disabled:opacity-50"
                          onClick={() => handleSend(inv)}
                          disabled={!!sendingId}
                        >
                          {sendingId === inv.id ? t('common.sending', { defaultValue: 'Отправка…' }) : t('app.companies.invoices.send_email', { defaultValue: 'Отправить' })}
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
      <InvoiceCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        companyId={companyId}
        companyName={companyName}
        onCreated={() => {
          setCreateOpen(false)
          load()
        }}
        creating={creating}
        setCreating={setCreating}
      />
    </div>
  )
}

function InvoiceCreateModal({
  open,
  onClose,
  companyId,
  companyName,
  onCreated,
  creating,
  setCreating,
}: {
  open: boolean
  onClose: () => void
  companyId: string
  companyName: string
  onCreated: () => void
  creating: boolean
  setCreating: (v: boolean) => void
}) {
  const { t } = useI18n()
  const [issueDate, setIssueDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [dueDate, setDueDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() + 14)
    return d.toISOString().slice(0, 10)
  })
  const [items, setItems] = useState([{ description: '', qty: 1, unit_price: 0, vat_rate: 23 }])

  const addItem = () => setItems((prev) => [...prev, { description: '', qty: 1, unit_price: 0, vat_rate: 23 }])
  const removeItem = (i: number) => setItems((prev) => prev.filter((_, idx) => idx !== i))
  const setItem = (i: number, patch: Partial<typeof items[0]>) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const valid = items.every((it) => it.description.trim() && it.qty > 0 && it.unit_price >= 0)
    if (!valid) return
    setCreating(true)
    try {
      await createInvoice({
        company_id: companyId,
        issue_date: issueDate,
        due_date: dueDate,
        currency: 'PLN',
        status: 'issued',
        items: items.map((it) => ({
          description: it.description.trim(),
          qty: Number(it.qty),
          unit_price: Number(it.unit_price),
          vat_rate: Number(it.vat_rate) || 23,
        })),
        billing_details: { company_name: companyName },
      })
      onCreated()
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || 'Failed to create invoice')
    } finally {
      setCreating(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('app.companies.invoices.create_modal_title', { defaultValue: 'Выставить счёт' })}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm text-slate-600">{companyName}</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.invoices.issue_date', { defaultValue: 'Дата выставления' })}</span>
            <input
              type="date"
              className="input"
              value={issueDate}
              onChange={(e) => setIssueDate(e.target.value)}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t('app.invoices.due_date', { defaultValue: 'Срок оплаты' })}</span>
            <input
              type="date"
              className="input"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              required
            />
          </label>
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">{t('app.invoices.items', { defaultValue: 'Позиции' })}</span>
            <button type="button" onClick={addItem} className="text-xs text-brand-600 hover:underline">
              + {t('common.add', { defaultValue: 'Добавить' })}
            </button>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {items.map((it, i) => (
              <div key={i} className="flex gap-2 items-start p-2 rounded border border-slate-100">
                <input
                  className="input flex-1 text-sm"
                  placeholder={t('app.invoices.item_description', { defaultValue: 'Описание' })}
                  value={it.description}
                  onChange={(e) => setItem(i, { description: e.target.value })}
                  required
                />
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  className="input w-20 text-sm"
                  placeholder="Цена"
                  value={it.unit_price || ''}
                  onChange={(e) => setItem(i, { unit_price: Number(e.target.value) || 0 })}
                />
                <input
                  type="number"
                  min="1"
                  className="input w-14 text-sm"
                  value={it.qty}
                  onChange={(e) => setItem(i, { qty: Number(e.target.value) || 1 })}
                />
                <input
                  type="number"
                  min="0"
                  max="100"
                  className="input w-14 text-sm"
                  placeholder="VAT"
                  value={it.vat_rate}
                  onChange={(e) => setItem(i, { vat_rate: Number(e.target.value) || 23 })}
                />
                {items.length > 1 && (
                  <button type="button" onClick={() => removeItem(i)} className="text-rose-500 hover:underline text-xs">
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            {t('common.actions.cancel')}
          </button>
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? t('common.saving') : t('app.companies.invoices.create_submit', { defaultValue: 'Создать счёт' })}
          </button>
        </div>
      </form>
    </Modal>
  )
}
