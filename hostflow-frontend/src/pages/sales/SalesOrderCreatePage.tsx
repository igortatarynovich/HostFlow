import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createSalesOrder } from '../../api/salesOrders'
import { listCompanies } from '../../api/client'
import { listClientAccounts, type ClientAccount } from '../../api/clientAccounts'
import { SALES_ORDERS_PATH, salesOrderPath } from '../../app/salesPaths'
import { useI18n } from '../../i18n'

type CompanyOpt = { id: string; name: string }

export default function SalesOrderCreatePage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<CompanyOpt[]>([])
  const [accounts, setAccounts] = useState<ClientAccount[]>([])
  const [companyId, setCompanyId] = useState('')
  const [clientAccountId, setClientAccountId] = useState('')
  const [title, setTitle] = useState('')
  const [currency, setCurrency] = useState('PLN')
  const [paymentTermDays, setPaymentTermDays] = useState('14')
  const [paymentModel, setPaymentModel] = useState('')
  const [vatRate, setVatRate] = useState('')
  const [guaranteeDays, setGuaranteeDays] = useState('')
  const [billingNotes, setBillingNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void Promise.all([
      listCompanies({ limit: 500 }).catch(() => []),
      listClientAccounts({ limit: 200 }).catch(() => []),
    ]).then(([cosRaw, cas]) => {
      if (cancelled) return
      const cos = Array.isArray((cosRaw as { items?: unknown })?.items)
        ? (cosRaw as { items: Array<{ id?: string; name?: string }> }).items
        : Array.isArray(cosRaw)
          ? (cosRaw as Array<{ id?: string; name?: string }>)
          : []
      setCompanies(
        cos
          .filter((c) => c?.id)
          .map((c) => ({ id: String(c.id), name: String(c.name || c.id) })),
      )
      setAccounts(cas)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!clientAccountId) return
    const acc = accounts.find((a) => a.id === clientAccountId)
    if (acc?.primary_company_id) setCompanyId(String(acc.primary_company_id))
  }, [clientAccountId, accounts])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!companyId || !title.trim()) {
      setError(t('app.sales_orders.create.required', { defaultValue: 'Клиент и название обязательны' }))
      return
    }
    setSaving(true)
    setError(null)
    try {
      const order = await createSalesOrder({
        company_id: companyId,
        title: title.trim(),
        client_account_id: clientAccountId || undefined,
        currency: currency.trim() || undefined,
        payment_term_days: paymentTermDays ? Number(paymentTermDays) : undefined,
        payment_model: paymentModel.trim() || undefined,
        vat_rate: vatRate !== '' ? Number(vatRate) : undefined,
        guarantee_days: guaranteeDays !== '' ? Number(guaranteeDays) : undefined,
        billing_notes: billingNotes.trim() || undefined,
      })
      navigate(salesOrderPath(order.id), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl overflow-y-auto px-4 py-4 sm:px-6" data-testid="sales-order-create">
      <Link to={SALES_ORDERS_PATH} className="text-sm text-slate-600 hover:text-brand-700">
        ← {t('app.sales_orders.create.back', { defaultValue: 'К списку заказов' })}
      </Link>
      <h2 className="mt-3 text-lg font-semibold text-slate-900">
        {t('app.sales_orders.create.title', { defaultValue: 'Новый Service Order' })}
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        {t('app.sales_orders.create.subtitle', {
          defaultValue: 'Снимок коммерческих условий сделки. Defaults клиента сюда не подтягиваются автоматически (V1).',
        })}
      </p>

      <form className="mt-4 space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <div className="label">
            {t('app.sales_orders.create.client_account', { defaultValue: 'Client Account (опц.)' })}
          </div>
          <select
            className="input"
            value={clientAccountId}
            onChange={(e) => setClientAccountId(e.target.value)}
            data-testid="sales-order-client-account"
          >
            <option value="">—</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <div className="label">
            {t('app.sales_orders.create.company', { defaultValue: 'Компания клиента' })} *
          </div>
          <select
            className="input"
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            required
            data-testid="sales-order-company"
          >
            <option value="">—</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <div className="label">{t('app.sales_orders.create.name', { defaultValue: 'Название заказа' })} *</div>
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            data-testid="sales-order-title"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <div className="label">{t('app.sales_orders.create.currency', { defaultValue: 'Валюта' })}</div>
            <input className="input" value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </label>
          <label className="block">
            <div className="label">
              {t('app.sales_orders.create.payment_term', { defaultValue: 'Отсрочка, дней' })}
            </div>
            <input
              className="input"
              type="number"
              min={0}
              max={365}
              value={paymentTermDays}
              onChange={(e) => setPaymentTermDays(e.target.value)}
            />
          </label>
          <label className="block">
            <div className="label">
              {t('app.sales_orders.create.payment_model', { defaultValue: 'Модель оплаты' })}
            </div>
            <input
              className="input"
              value={paymentModel}
              onChange={(e) => setPaymentModel(e.target.value)}
              placeholder="per_hire / monthly / …"
            />
          </label>
          <label className="block">
            <div className="label">{t('app.sales_orders.create.vat', { defaultValue: 'VAT %' })}</div>
            <input
              className="input"
              type="number"
              step="0.01"
              value={vatRate}
              onChange={(e) => setVatRate(e.target.value)}
            />
          </label>
          <label className="block">
            <div className="label">
              {t('app.sales_orders.create.guarantee', { defaultValue: 'Гарантия, дней' })}
            </div>
            <input
              className="input"
              type="number"
              min={0}
              value={guaranteeDays}
              onChange={(e) => setGuaranteeDays(e.target.value)}
            />
          </label>
        </div>

        <label className="block">
          <div className="label">{t('app.sales_orders.create.notes', { defaultValue: 'Коммерческие заметки' })}</div>
          <textarea
            className="input min-h-[80px]"
            value={billingNotes}
            onChange={(e) => setBillingNotes(e.target.value)}
          />
        </label>

        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <button type="submit" className="btn-primary" disabled={saving} data-testid="sales-order-submit">
            {saving
              ? t('common.saving', { defaultValue: 'Сохранение…' })
              : t('app.sales_orders.create.submit', { defaultValue: 'Создать заказ' })}
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={saving}
            onClick={() => navigate(SALES_ORDERS_PATH)}
          >
            {t('common.cancel', { defaultValue: 'Отмена' })}
          </button>
        </div>
      </form>
    </div>
  )
}
