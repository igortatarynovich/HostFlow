import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { createInvoice, getCompany, listCompanies } from '../api/client'
import type { Company } from '../api/types'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

type InvoiceItemDraft = {
  line_no: number
  description: string
  qty: string
  unit_price: string
  vat_rate: string
}

function isoDate(offsetDays = 0) {
  const dt = new Date()
  dt.setDate(dt.getDate() + offsetDays)
  return dt.toISOString().slice(0, 10)
}

const initialItem = (): InvoiceItemDraft => ({
  line_no: 1,
  description: '',
  qty: '1',
  unit_price: '0',
  vat_rate: '23',
})

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === 'object' ? (value as Record<string, any>) : {}
}

function asArray(value: unknown): any[] {
  return Array.isArray(value) ? value : []
}

function extractBilling(company: Company | null) {
  const extra = asRecord(company?.extra)
  const billing = asRecord(extra.billing)
  return billing
}

function extractPrimaryBankAccount(company: Company | null) {
  const billing = extractBilling(company)
  const accounts = asArray(billing.bank_accounts).map((entry) => asRecord(entry))
  return accounts.find((account) => Boolean(account.is_primary)) || accounts[0] || null
}

function extractIssuerAddress(company: Company | null) {
  const billing = extractBilling(company)
  const billingAddress = asRecord(billing.billing_address)
  const raw = {
    country: billingAddress.country || company?.country || company?.country_code || '',
    city: billingAddress.city || company?.city || '',
    street: billingAddress.street || company?.address || '',
    zip: billingAddress.zip || '',
  }
  return Object.values(raw).some(Boolean) ? raw : null
}

export default function InvoiceCreatePage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [companyId, setCompanyId] = useState('')
  const [issuerCompanyId, setIssuerCompanyId] = useState('')
  const [issueDate, setIssueDate] = useState(isoDate(0))
  const [dueDate, setDueDate] = useState(isoDate(14))
  const [currency, setCurrency] = useState('PLN')
  const [billingEmail, setBillingEmail] = useState('')
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<InvoiceItemDraft[]>([initialItem()])
  const [issuerCompany, setIssuerCompany] = useState<Company | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoadingCompanies(true)
    listCompanies({ limit: 500 })
      .then((data) => {
        if (!cancelled) setCompanies(Array.isArray(data) ? data : [])
      })
      .catch((err: any) => {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err?.message || 'Failed to load companies')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingCompanies(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!companyId) return
    const company = companies.find((entry) => entry.id === companyId)
    if (!company) return
    setBillingEmail((current) => current || String(company.email || ''))
  }, [companies, companyId])

  useEffect(() => {
    if (!issuerCompanyId) {
      setIssuerCompany(null)
      return
    }
    let cancelled = false
    getCompany(issuerCompanyId)
      .then((company) => {
        if (!cancelled) setIssuerCompany(company as Company)
      })
      .catch((err: any) => {
        if (!cancelled) {
          setIssuerCompany(null)
          setError(err?.response?.data?.detail || err?.message || 'Failed to load issuer details')
        }
      })
    return () => {
      cancelled = true
    }
  }, [issuerCompanyId])

  useEffect(() => {
    if (!issuerCompanyId && companies.length > 0) {
      setIssuerCompanyId(companies[0].id)
    }
  }, [companies, issuerCompanyId])

  const updateItem = (index: number, patch: Partial<InvoiceItemDraft>) => {
    setItems((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)).map((item, itemIndex) => ({
        ...item,
        line_no: itemIndex + 1,
      })),
    )
  }

  const addItem = () => {
    setItems((current) => [...current, { ...initialItem(), line_no: current.length + 1 }])
  }

  const removeItem = (index: number) => {
    setItems((current) =>
      current
        .filter((_, itemIndex) => itemIndex !== index)
        .map((item, itemIndex) => ({ ...item, line_no: itemIndex + 1 })),
    )
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!companyId) {
      setError(t('app.invoices.create_company_required', { defaultValue: 'Client is required.' }))
      return
    }
    const normalizedItems = items
      .map((item, index) => ({
        line_no: index + 1,
        description: item.description.trim(),
        qty: Number.parseFloat(item.qty || '0'),
        unit_price: Number.parseFloat(item.unit_price || '0'),
        vat_rate: Number.parseFloat(item.vat_rate || '0'),
      }))
      .filter((item) => item.description && item.qty > 0)

    if (normalizedItems.length === 0) {
      setError(t('app.invoices.create_items_required', { defaultValue: 'Add at least one valid invoice item.' }))
      return
    }

    setSaving(true)
    try {
      const issuerBankAccount = extractPrimaryBankAccount(issuerCompany)
      const issuerAddress = extractIssuerAddress(issuerCompany)
      const invoice = await createInvoice({
        company_id: companyId,
        issue_date: issueDate,
        due_date: dueDate,
        currency,
        notes: notes.trim() || undefined,
        billing_details: {
          email: billingEmail.trim() || undefined,
          issuer_company_id: issuerCompany?.id || undefined,
          issuer_name: issuerCompany?.legal_name || issuerCompany?.name || undefined,
          issuer_tax_id: issuerCompany?.tax_id || undefined,
          issuer_address: issuerAddress || undefined,
          issuer_bank_account: issuerBankAccount
            ? {
                bank_name: issuerBankAccount.bank_name || undefined,
                iban: issuerBankAccount.iban || undefined,
                swift_bic: issuerBankAccount.swift_bic || issuerBankAccount.swift || undefined,
                country: issuerBankAccount.country || undefined,
                label: issuerBankAccount.label || undefined,
              }
            : undefined,
        },
        items: normalizedItems,
        status: 'draft',
      })
      navigate(`/app/invoices/${invoice.id}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create invoice')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-4 p-6">
      <div className="space-y-2">
        <button type="button" className="text-sm text-brand-700 hover:underline" onClick={() => navigate('/app/invoices')}>
          {t('app.invoices.back', { defaultValue: 'Back to invoices' })}
        </button>
        <h1 className="text-2xl font-bold text-slate-900">{t('app.invoices.create', { defaultValue: 'Create Invoice' })}</h1>
        <p className="text-sm text-slate-500">
          {t('app.invoices.create_subtitle', {
            defaultValue: 'Create a draft invoice with client, billing recipient and line items.',
          })}
        </p>
      </div>

      {error && (
        <ErrorRecoveryBanner
          info={{
            title: error,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => setError(null)}
          retryLabel={t('common.actions.dismiss', { defaultValue: 'Dismiss' })}
        />
      )}

      <form className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]" onSubmit={handleSubmit}>
        <section className="app-surface space-y-4 p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.client', { defaultValue: 'Client' })}
              </span>
              <select
                className="input"
                value={companyId}
                onChange={(event) => setCompanyId(event.target.value)}
                disabled={loadingCompanies || saving}
              >
                <option value="">{t('app.invoices.select_client', { defaultValue: 'Select client' })}</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.issuer', { defaultValue: 'Issuer company' })}
              </span>
              <select
                className="input"
                value={issuerCompanyId}
                onChange={(event) => setIssuerCompanyId(event.target.value)}
                disabled={loadingCompanies || saving}
              >
                <option value="">{t('app.invoices.select_issuer', { defaultValue: 'Select issuer' })}</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.legal_name || company.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.recipient', { defaultValue: 'Recipient' })}
              </span>
              <input className="input" value={billingEmail} onChange={(event) => setBillingEmail(event.target.value)} placeholder="billing@client.com" />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.issue_date', { defaultValue: 'Issue Date' })}
              </span>
              <input className="input" type="date" value={issueDate} onChange={(event) => setIssueDate(event.target.value)} />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.due_date', { defaultValue: 'Due Date' })}
              </span>
              <input className="input" type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.currency', { defaultValue: 'Currency' })}
              </span>
              <select className="input" value={currency} onChange={(event) => setCurrency(event.target.value)}>
                {['PLN', 'EUR', 'USD', 'GBP'].map((entry) => (
                  <option key={entry} value={entry}>
                    {entry}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm md:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.notes', { defaultValue: 'Notes' })}
              </span>
              <textarea className="input min-h-28" value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{t('app.invoices.items', { defaultValue: 'Items' })}</h2>
                <p className="text-sm text-slate-500">
                  {t('app.invoices.items_subtitle', { defaultValue: 'Billable lines included in this invoice.' })}
                </p>
              </div>
              <button type="button" className="btn-secondary btn-sm" onClick={addItem}>
                {t('app.invoices.add_item', { defaultValue: 'Add item' })}
              </button>
            </div>

            {items.map((item, index) => (
              <div key={item.line_no} className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-[minmax(0,1.6fr)_120px_140px_120px_auto]">
                <input
                  className="input"
                  value={item.description}
                  onChange={(event) => updateItem(index, { description: event.target.value })}
                  placeholder={t('app.invoices.item_description', { defaultValue: 'Description' })}
                />
                <input className="input" type="number" min="0.01" step="0.01" value={item.qty} onChange={(event) => updateItem(index, { qty: event.target.value })} />
                <input
                  className="input"
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.unit_price}
                  onChange={(event) => updateItem(index, { unit_price: event.target.value })}
                />
                <input
                  className="input"
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.vat_rate}
                  onChange={(event) => updateItem(index, { vat_rate: event.target.value })}
                />
                <button type="button" className="btn-secondary btn-sm" onClick={() => removeItem(index)} disabled={items.length === 1}>
                  {t('common.actions.remove', { defaultValue: 'Remove' })}
                </button>
              </div>
            ))}
          </div>
        </section>

        <aside className="app-surface space-y-4 p-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{t('app.invoices.summary', { defaultValue: 'Summary' })}</h2>
            <p className="text-sm text-slate-500">
              {t('app.invoices.create_summary', { defaultValue: 'Invoice will be created as draft and opened in detail view.' })}
            </p>
          </div>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.client', { defaultValue: 'Client' })}</dt>
              <dd className="mt-1 text-slate-900">{companies.find((company) => company.id === companyId)?.name || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issuer', { defaultValue: 'Issuer company' })}</dt>
              <dd className="mt-1 text-slate-900">{issuerCompany?.legal_name || issuerCompany?.name || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.recipient', { defaultValue: 'Recipient' })}</dt>
              <dd className="mt-1 text-slate-900">{billingEmail || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.bank_account', { defaultValue: 'Bank account' })}</dt>
              <dd className="mt-1 text-slate-900">
                {extractPrimaryBankAccount(issuerCompany)?.iban || t('app.invoices.bank_account_missing', { defaultValue: 'No primary bank account' })}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.items', { defaultValue: 'Items' })}</dt>
              <dd className="mt-1 text-slate-900">{items.length}</dd>
            </div>
          </dl>
          <div className="flex flex-col gap-2">
            <button type="submit" className="btn-primary" disabled={saving || loadingCompanies}>
              {saving ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.invoices.create', { defaultValue: 'Create Invoice' })}
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate('/app/invoices')}>
              {t('common.actions.cancel', { defaultValue: 'Cancel' })}
            </button>
          </div>
        </aside>
      </form>
    </div>
  )
}
