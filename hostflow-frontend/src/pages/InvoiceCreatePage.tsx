import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { listAdditionalServices } from '../api/additionalServices'
import { createInvoice, getCompany, getInvoice, listCompanies, listInvoices, sendInvoice, updateInvoice } from '../api/client'
import type { AdditionalService, Company, Invoice } from '../api/types'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

type InvoiceItemDraft = {
  line_no: number
  service_id?: string
  description: string
  qty: string
  unit_price: string
  vat_rate: string
}

type CompanyContact = {
  id: string
  full_name?: string
  email?: string
  phone?: string
  role?: string
  is_primary?: boolean
}

function isoDate(offsetDays = 0) {
  const dt = new Date()
  dt.setDate(dt.getDate() + offsetDays)
  return dt.toISOString().slice(0, 10)
}

const initialItem = (): InvoiceItemDraft => ({
  line_no: 1,
  service_id: '',
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

function extractBankAccounts(company: Company | null) {
  const billing = extractBilling(company)
  return asArray(billing.bank_accounts).map((entry) => asRecord(entry)).filter((entry) => Object.keys(entry).length > 0)
}

function extractCompanyContacts(company: Company | null): CompanyContact[] {
  const contactsRaw = asRecord(company?.contacts)
  const entries = Object.entries(contactsRaw)
    .map(([id, value]) => {
      const data = asRecord(value)
      return {
        id,
        full_name: String(data.full_name || '').trim() || undefined,
        email: String(data.email || '').trim() || undefined,
        phone: String(data.phone || '').trim() || undefined,
        role: String(data.role || '').trim() || undefined,
        is_primary: Boolean(data.is_primary),
      }
    })
    .filter((entry) => entry.email || entry.phone || entry.full_name)
  entries.sort((left, right) => Number(Boolean(right.is_primary)) - Number(Boolean(left.is_primary)))
  return entries
}

function bankAccountKey(account: Record<string, any> | null | undefined) {
  if (!account) return ''
  return String(account.id || account.iban || account.label || '').trim()
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

function extractCompanyBillingSnapshot(company: Company | null) {
  const billing = extractBilling(company)
  const billingAddress = asRecord(billing.billing_address)
  const address = [
    billingAddress.country || company?.country || company?.country_code || '',
    billingAddress.city || company?.city || '',
    billingAddress.street || company?.address || '',
    billingAddress.zip || '',
  ]
    .filter(Boolean)
    .join(', ')

  return {
    company_name: company?.legal_name || company?.name || undefined,
    email: String(billing.invoice_email || company?.email || '').trim() || undefined,
    tax_id: company?.tax_id || undefined,
    address: address || undefined,
    payment_terms_days: Number(billing.payment_terms_days || 0) || undefined,
  }
}

function addDays(isoValue: string, days: number) {
  const dt = new Date(isoValue)
  if (Number.isNaN(dt.getTime())) return isoValue
  dt.setDate(dt.getDate() + days)
  return dt.toISOString().slice(0, 10)
}

function invoicePrefix(invoiceKind: string, taxMode: string) {
  if (invoiceKind === 'correction') return 'KOR'
  if (invoiceKind === 'proforma') return 'PRO'
  if (invoiceKind === 'invoice') return 'INV'
  if (invoiceKind === 'vat' || taxMode === 'standard_vat') return 'FV'
  return 'INV'
}

function buildSuggestedInvoiceNumber(invoiceKind: string, taxMode: string, issueDate: string, existingNumbers: string[]) {
  const dt = new Date(issueDate)
  if (Number.isNaN(dt.getTime())) return ''
  const year = dt.getFullYear()
  const month = `${dt.getMonth() + 1}`.padStart(2, '0')
  const prefix = invoicePrefix(invoiceKind, taxMode)
  const pattern = new RegExp(`^${prefix}/${year}/${month}/(\\d{4,})$`)
  let maxSeq = 0
  for (const number of existingNumbers) {
    const match = pattern.exec(String(number || '').trim())
    if (!match) continue
    maxSeq = Math.max(maxSeq, Number.parseInt(match[1], 10) || 0)
  }
  return `${prefix}/${year}/${month}/${String(maxSeq + 1).padStart(4, '0')}`
}

function isManagedIssuerCompany(company: Company, userId: string) {
  const actor = String(userId || '').trim()
  if (!actor) return false
  const companyRole = String((company.extra as Record<string, any> | undefined)?.company_role || '').trim().toLowerCase()
  if (companyRole !== 'operating') return false
  return [company.owner_user_id, company.manager_user_id].some((value) => String(value || '').trim() === actor)
}

export default function InvoiceCreatePage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const navigate = useNavigate()
  const { id: invoiceId } = useParams<{ id?: string }>()
  const [searchParams] = useSearchParams()
  const isEditMode = Boolean(invoiceId)
  const correctionOfInvoiceId = String(searchParams.get('correction_of_invoice_id') || '').trim()
  const correctionOfInvoiceNumber = String(searchParams.get('correction_of_invoice_number') || '').trim()
  const [companies, setCompanies] = useState<Company[]>([])
  const [serviceCatalog, setServiceCatalog] = useState<AdditionalService[]>([])
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [loadingServices, setLoadingServices] = useState(true)
  const [loadingInvoice, setLoadingInvoice] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [knownInvoiceNumbers, setKnownInvoiceNumbers] = useState<string[]>([])

  const [companyId, setCompanyId] = useState('')
  const [issuerCompanyId, setIssuerCompanyId] = useState('')
  const [invoiceKind, setInvoiceKind] = useState('vat')
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [issueDate, setIssueDate] = useState(isoDate(0))
  const [dueDate, setDueDate] = useState(isoDate(14))
  const [paymentTermsDays, setPaymentTermsDays] = useState('14')
  const [taxMode, setTaxMode] = useState('standard_vat')
  const [currency, setCurrency] = useState('PLN')
  const [billingEmail, setBillingEmail] = useState('')
  const [recipientContactId, setRecipientContactId] = useState('')
  const [issuerBankAccountKey, setIssuerBankAccountKey] = useState('')
  const [notes, setNotes] = useState('')
  const [correctionReason, setCorrectionReason] = useState('')
  const [items, setItems] = useState<InvoiceItemDraft[]>([initialItem()])
  const [issuerCompany, setIssuerCompany] = useState<Company | null>(null)
  const [clientCompany, setClientCompany] = useState<Company | null>(null)
  const [sourceInvoice, setSourceInvoice] = useState<Invoice | null>(null)
  const clientContacts = extractCompanyContacts(clientCompany)
  const selfId = String((me as any)?.sub || '').trim()
  const issuerCompanies = useMemo(
    () => companies.filter((company) => isManagedIssuerCompany(company, selfId)),
    [companies, selfId],
  )
  const issuerBankAccounts = extractBankAccounts(issuerCompany)

  const draftTotals = useMemo(() => {
    const subtotal = items.reduce((sum, item) => {
      const qty = Number.parseFloat(item.qty || '0')
      const unitPrice = Number.parseFloat(item.unit_price || '0')
      if (!Number.isFinite(qty) || !Number.isFinite(unitPrice)) return sum
      return sum + qty * unitPrice
    }, 0)
    const vatTotal = items.reduce((sum, item) => {
      const qty = Number.parseFloat(item.qty || '0')
      const unitPrice = Number.parseFloat(item.unit_price || '0')
      const vatRate = Number.parseFloat(item.vat_rate || '0')
      if (!Number.isFinite(qty) || !Number.isFinite(unitPrice) || !Number.isFinite(vatRate)) return sum
      return sum + qty * unitPrice * (vatRate / 100)
    }, 0)
    return { subtotal, vatTotal, total: subtotal + vatTotal }
  }, [items])

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
    let cancelled = false
    listInvoices({ limit: 1000 })
      .then((data) => {
        if (!cancelled) {
          setKnownInvoiceNumbers(
            (Array.isArray(data) ? data : [])
              .map((entry: any) => String(entry?.invoice_number || '').trim())
              .filter(Boolean),
          )
        }
      })
      .catch(() => {
        if (!cancelled) setKnownInvoiceNumbers([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoadingServices(true)
    listAdditionalServices(false)
      .then((data) => {
        if (!cancelled) setServiceCatalog(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (!cancelled) setServiceCatalog([])
      })
      .finally(() => {
        if (!cancelled) setLoadingServices(false)
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
    const contacts = extractCompanyContacts(clientCompany)
    if (!contacts.length) {
      setRecipientContactId('')
      return
    }
    setRecipientContactId((current) => {
      if (current && contacts.some((entry) => entry.id === current)) return current
      return contacts.find((entry) => entry.is_primary)?.id || contacts[0].id
    })
  }, [clientCompany])

  useEffect(() => {
    if (!recipientContactId) return
    const contact = extractCompanyContacts(clientCompany).find((entry) => entry.id === recipientContactId)
    if (!contact?.email) return
    setBillingEmail(contact.email)
  }, [clientCompany, recipientContactId])

  useEffect(() => {
    if (!companyId) {
      setClientCompany(null)
      return
    }
    let cancelled = false
    getCompany(companyId)
      .then((company) => {
        if (!cancelled) setClientCompany(company as Company)
      })
      .catch((err: any) => {
        if (!cancelled) {
          setClientCompany(null)
          setError(err?.response?.data?.detail || err?.message || 'Failed to load client billing details')
        }
      })
    return () => {
      cancelled = true
    }
  }, [companyId])

  useEffect(() => {
    const billing = extractCompanyBillingSnapshot(clientCompany)
    if (!billing.payment_terms_days) return
    setPaymentTermsDays(String(billing.payment_terms_days))
  }, [clientCompany])

  useEffect(() => {
    const days = Number.parseInt(paymentTermsDays || '0', 10)
    if (days > 0) {
      setDueDate(addDays(issueDate, days))
    }
  }, [issueDate, paymentTermsDays])

  useEffect(() => {
    if (isEditMode || companies.length === 0) return
    const prefCompanyId = String(searchParams.get('company_id') || '').trim()
    const prefBillingEmail = String(searchParams.get('billing_email') || '').trim()
    const prefInvoiceKind = String(searchParams.get('invoice_kind') || '').trim()
    if (prefCompanyId && !companyId) {
      const matchedCompany = companies.find((entry) => entry.id === prefCompanyId)
      if (matchedCompany) {
        setCompanyId(matchedCompany.id)
      }
    }
    if (prefBillingEmail && !billingEmail) {
      setBillingEmail(prefBillingEmail)
    }
    if (prefInvoiceKind && invoiceKind !== prefInvoiceKind) {
      setInvoiceKind(prefInvoiceKind)
    }
  }, [billingEmail, companies, companyId, invoiceKind, isEditMode, searchParams])

  useEffect(() => {
    if (isEditMode) return
    const sourceInvoiceId = String(searchParams.get('source_invoice_id') || '').trim()
    const prefInvoiceKind = String(searchParams.get('invoice_kind') || '').trim()
    if (!sourceInvoiceId) return
    let cancelled = false
    setLoadingInvoice(true)
    getInvoice(sourceInvoiceId)
      .then((data) => {
        if (cancelled) return
        const invoice = data as Invoice
        setSourceInvoice(invoice)
        setCompanyId((current) => current || invoice.company_id || '')
        setIssuerCompanyId((current) => current || String(invoice.billing_details?.issuer_company_id || ''))
        setInvoiceKind(prefInvoiceKind || String(invoice.billing_details?.invoice_kind || 'vat'))
        setInvoiceNumber('')
        setCurrency((current) => (current === 'PLN' ? invoice.currency || current : current))
        setBillingEmail((current) => current || String(invoice.billing_details?.email || ''))
        setCorrectionReason((current) => current || String(invoice.billing_details?.correction_reason || ''))
        setNotes((current) =>
          current ||
          (prefInvoiceKind === 'correction'
            ? `Correction for invoice ${invoice.invoice_number}\n${String(invoice.notes || '').trim()}`.trim()
            : String(invoice.notes || '')),
        )
        if (Array.isArray(invoice.items) && invoice.items.length > 0) {
          setItems(
            invoice.items.map((item, index) => ({
              line_no: index + 1,
              service_id: '',
              description: String(item.description || ''),
              qty: String((item as any).quantity ?? (item as any).qty ?? 1),
              unit_price: String(item.unit_price ?? 0),
              vat_rate: String(item.vat_rate ?? 0),
            })),
          )
        }
      })
      .catch((err: any) => {
        if (!cancelled) {
          setSourceInvoice(null)
          setError(err?.response?.data?.detail || err?.message || 'Failed to load source invoice')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingInvoice(false)
      })
    return () => {
      cancelled = true
    }
  }, [isEditMode, searchParams])

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
    const accounts = extractBankAccounts(issuerCompany)
    if (!accounts.length) {
      setIssuerBankAccountKey('')
      return
    }
    setIssuerBankAccountKey((current) => {
      if (current && accounts.some((entry) => bankAccountKey(entry) === current)) return current
      return bankAccountKey(extractPrimaryBankAccount(issuerCompany)) || bankAccountKey(accounts[0])
    })
  }, [issuerCompany])

  useEffect(() => {
    if (!issuerCompanies.length) {
      setIssuerCompanyId('')
      return
    }
    setIssuerCompanyId((current) => {
      if (current && issuerCompanies.some((company) => company.id === current)) return current
      const ownerMatch = issuerCompanies.find((company) => String(company.owner_user_id || '').trim() === selfId)
      return ownerMatch?.id || issuerCompanies[0].id
    })
  }, [issuerCompanies, selfId])

  useEffect(() => {
    if (!invoiceId) return
    let cancelled = false
    setLoadingInvoice(true)
    getInvoice(invoiceId)
      .then((data) => {
        if (cancelled) return
        const invoice = data as Invoice
        if (invoice.status !== 'draft') {
          setError(t('app.invoices.edit_only_draft', { defaultValue: 'Only draft invoices can be edited.' }))
          return
        }
        setCompanyId(invoice.company_id || '')
        setIssuerCompanyId(String(invoice.billing_details?.issuer_company_id || ''))
        setInvoiceKind(String(invoice.billing_details?.invoice_kind || 'vat'))
        setInvoiceNumber(String(invoice.invoice_number || ''))
        setIssueDate(invoice.issue_date || isoDate(0))
        setDueDate(invoice.due_date || isoDate(14))
        setPaymentTermsDays(String(invoice.billing_details?.payment_terms_days || 14))
        setTaxMode(String(invoice.billing_details?.tax_mode || 'standard_vat'))
        setCurrency(invoice.currency || 'PLN')
        setBillingEmail(String(invoice.billing_details?.email || ''))
        setCorrectionReason(String(invoice.billing_details?.correction_reason || ''))
        setIssuerBankAccountKey(
          bankAccountKey((invoice.billing_details?.issuer_bank_account as Record<string, any> | undefined) || null),
        )
        setNotes(String(invoice.notes || ''))
        setItems(
          Array.isArray(invoice.items) && invoice.items.length > 0
            ? invoice.items.map((item, index) => ({
                line_no: index + 1,
                service_id: '',
                description: String(item.description || ''),
                qty: String((item as any).quantity ?? (item as any).qty ?? 1),
                unit_price: String(item.unit_price ?? 0),
                vat_rate: String(item.vat_rate ?? 0),
              }))
            : [initialItem()],
        )
      })
      .catch((err: any) => {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err?.message || 'Failed to load invoice')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingInvoice(false)
      })
    return () => {
      cancelled = true
    }
  }, [invoiceId, t])

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

  const applyCatalogService = (index: number, serviceId: string) => {
    const selected = serviceCatalog.find((entry) => entry.id === serviceId)
    if (!selected) {
      updateItem(index, { service_id: '', description: '' })
      return
    }
    updateItem(index, {
      service_id: selected.id,
      description: selected.name || selected.code,
      unit_price: String(selected.base_price ?? 0),
      vat_rate: String(selected.vat_rate ?? 0),
    })
    setCurrency((current) => (current ? current : selected.currency || 'PLN'))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nativeEvent = event.nativeEvent as SubmitEvent | undefined
    const submitter = nativeEvent?.submitter as HTMLButtonElement | null
    const submitMode = submitter?.value === 'save_and_send' ? 'save_and_send' : 'save_draft'
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
    if (invoiceKind === 'correction' && !correctionOfInvoiceId) {
      setError(t('app.invoices.correction_original_required', { defaultValue: 'Correction invoice must reference the original invoice.' }))
      return
    }
    if (invoiceKind === 'correction' && !correctionReason.trim()) {
      setError(t('app.invoices.correction_reason_required', { defaultValue: 'Correction reason is required.' }))
      return
    }

    setSaving(true)
    try {
      const issuerBankAccount = extractPrimaryBankAccount(issuerCompany)
      const selectedIssuerBankAccount =
        extractBankAccounts(issuerCompany).find((entry) => bankAccountKey(entry) === issuerBankAccountKey) ||
        issuerBankAccount
      const issuerAddress = extractIssuerAddress(issuerCompany)
      const clientBilling = extractCompanyBillingSnapshot(clientCompany)

      if (!issuerCompany?.id) {
        setError(t('app.invoices.issuer_required', { defaultValue: 'Your own issuer company is required.' }))
        setSaving(false)
        return
      }
      if (!issuerCompany?.tax_id) {
        setError(t('app.invoices.issuer_tax_id_required', { defaultValue: 'Issuer tax ID/NIP is required for invoices.' }))
        setSaving(false)
        return
      }
      if (!issuerAddress) {
        setError(t('app.invoices.issuer_address_required', { defaultValue: 'Issuer legal address is required for invoices.' }))
        setSaving(false)
        return
      }
      if (!selectedIssuerBankAccount?.iban) {
        setError(t('app.invoices.issuer_bank_required', { defaultValue: 'Issuer bank account is required for invoices.' }))
        setSaving(false)
        return
      }
      if (!clientBilling.company_name) {
        setError(t('app.invoices.client_legal_name_required', { defaultValue: 'Client legal name is required for invoices.' }))
        setSaving(false)
        return
      }
      if (!clientBilling.tax_id) {
        setError(t('app.invoices.client_tax_id_required', { defaultValue: 'Client tax ID/NIP is required for invoices.' }))
        setSaving(false)
        return
      }
      if (!clientBilling.address) {
        setError(t('app.invoices.client_address_required', { defaultValue: 'Client legal address is required for invoices.' }))
        setSaving(false)
        return
      }

      const payload = {
        company_id: companyId,
        invoice_number: invoiceNumber.trim() || undefined,
        issue_date: issueDate,
        due_date: dueDate,
        currency,
        notes: notes.trim() || undefined,
        billing_details: {
          company_name: clientBilling.company_name,
          email: billingEmail.trim() || clientBilling.email,
          tax_id: clientBilling.tax_id,
          address: clientBilling.address,
          invoice_kind: invoiceKind,
          correction_of_invoice_id: correctionOfInvoiceId || undefined,
          correction_of_invoice_number: correctionOfInvoiceNumber || undefined,
          correction_reason: correctionReason.trim() || undefined,
          payment_terms_days: Number.parseInt(paymentTermsDays || '0', 10) || clientBilling.payment_terms_days,
          tax_mode: taxMode,
          issuer_company_id: issuerCompany?.id || undefined,
          issuer_name: issuerCompany?.legal_name || issuerCompany?.name || undefined,
          issuer_tax_id: issuerCompany?.tax_id || undefined,
          issuer_address: issuerAddress || undefined,
          issuer_bank_account: selectedIssuerBankAccount
            ? {
                bank_name: selectedIssuerBankAccount.bank_name || undefined,
                iban: selectedIssuerBankAccount.iban || undefined,
                swift_bic: selectedIssuerBankAccount.swift_bic || selectedIssuerBankAccount.swift || undefined,
                country: selectedIssuerBankAccount.country || undefined,
                label: selectedIssuerBankAccount.label || undefined,
              }
            : undefined,
        },
        items: normalizedItems,
        status: 'draft',
      }
      let invoice = (isEditMode && invoiceId ? await updateInvoice(invoiceId, payload) : await createInvoice(payload)) as Invoice
      if (submitMode === 'save_and_send') {
        if (String(invoice.status || '').toLowerCase() === 'draft') {
          invoice = (await updateInvoice(invoice.id, { status: 'issued' })) as Invoice
        }
        await sendInvoice(invoice.id, {
          recipient_email: String(payload.billing_details?.email || '').trim() || undefined,
        })
      }
      navigate(`/app/invoices/${invoice.id}`)
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          (isEditMode ? 'Failed to update invoice' : 'Failed to create invoice'),
      )
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
        <h1 className="text-2xl font-bold text-slate-900">
          {isEditMode
            ? t('app.invoices.edit', { defaultValue: 'Edit Draft Invoice' })
            : t('app.invoices.create', { defaultValue: 'Create Invoice' })}
        </h1>
        <p className="text-sm text-slate-500">
          {isEditMode
            ? t('app.invoices.edit_subtitle', {
                defaultValue: 'Update draft invoice details, issuer information and line items.',
              })
            : invoiceKind === 'correction'
              ? t('app.invoices.create_correction_subtitle', {
                  defaultValue: 'Create a correction invoice linked to the original tax document.',
                })
            : t('app.invoices.create_subtitle', {
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

      {(loadingCompanies || loadingInvoice) && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          {t('common.loading', { defaultValue: 'Loading...' })}
        </div>
      )}

      {invoiceKind === 'correction' && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {t(
            'app.invoices.correction_notice',
            { defaultValue: 'Correction invoices preserve the original document. Adjust only the fields that must change for tax reporting.' },
          )}
        </div>
      )}

      <form className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_360px]" onSubmit={handleSubmit}>
        <section className="app-surface space-y-4 p-6">
          {invoiceKind === 'correction' && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                {t('app.invoices.correction_context', { defaultValue: 'Correction context' })}
              </div>
              <div className="mt-2 grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-amber-200 bg-white px-3 py-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    {t('app.invoices.correction_of', { defaultValue: 'Correction of' })}
                  </div>
                  <div className="mt-1 font-medium text-slate-900">{correctionOfInvoiceNumber || sourceInvoice?.invoice_number || '-'}</div>
                </div>
                <div className="rounded-xl border border-amber-200 bg-white px-3 py-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">
                    {t('app.invoices.original_total', { defaultValue: 'Original total' })}
                  </div>
                  <div className="mt-1 font-medium text-slate-900">
                    {sourceInvoice ? `${Number(sourceInvoice.total_amount || 0).toFixed(2)} ${sourceInvoice.currency || currency}` : '-'}
                  </div>
                </div>
              </div>
              <label className="mt-3 flex flex-col gap-1 text-sm">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.invoices.correction_reason', { defaultValue: 'Correction reason' })}
                </span>
                <textarea
                  className="input min-h-24"
                  value={correctionReason}
                  onChange={(event) => setCorrectionReason(event.target.value)}
                  placeholder={t('app.invoices.correction_reason_placeholder', {
                    defaultValue: 'Example: corrected NIP, legal address, quantity or billed amount.',
                  })}
                />
              </label>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.client', { defaultValue: 'Client' })}
              </span>
              <select
                className="input"
                value={companyId}
                onChange={(event) => setCompanyId(event.target.value)}
                disabled={loadingCompanies || loadingInvoice || saving}
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
                disabled={loadingCompanies || loadingInvoice || saving}
              >
                <option value="">{t('app.invoices.select_issuer', { defaultValue: 'Select your company' })}</option>
                {issuerCompanies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {[company.legal_name || company.name, String(company.owner_user_id || '').trim() === selfId ? 'owner' : 'manager'].filter(Boolean).join(' · ')}
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-500">
                {t(
                  'app.invoices.issuer_help',
                  { defaultValue: 'Only your own companies can issue invoices. Client companies are not available here.' },
                )}
              </span>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.recipient', { defaultValue: 'Recipient' })}
              </span>
              <input className="input" value={billingEmail} onChange={(event) => setBillingEmail(event.target.value)} placeholder="billing@client.com" />
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.recipient_contact', { defaultValue: 'Recipient contact' })}
              </span>
              <select
                className="input"
                value={recipientContactId}
                onChange={(event) => setRecipientContactId(event.target.value)}
                disabled={!clientContacts.length}
              >
                <option value="">{t('app.invoices.recipient_contact_none', { defaultValue: 'Manual recipient' })}</option>
                {clientContacts.map((contact) => (
                  <option key={contact.id} value={contact.id}>
                    {[contact.full_name, contact.role, contact.email].filter(Boolean).join(' · ')}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.kind', { defaultValue: 'Invoice type' })}
              </span>
              <select className="input" value={invoiceKind} onChange={(event) => setInvoiceKind(event.target.value)}>
                <option value="vat">{t('app.invoices.kind_vat', { defaultValue: 'VAT invoice' })}</option>
                <option value="invoice">{t('app.invoices.kind_invoice', { defaultValue: 'Invoice' })}</option>
                <option value="proforma">{t('app.invoices.kind_proforma', { defaultValue: 'Proforma' })}</option>
                <option value="correction">{t('app.invoices.kind_correction', { defaultValue: 'Correction invoice' })}</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.number', { defaultValue: 'Number' })}
              </span>
              <input
                className="input"
                value={invoiceNumber}
                onChange={(event) => setInvoiceNumber(event.target.value)}
                placeholder={buildSuggestedInvoiceNumber(invoiceKind, taxMode, issueDate, knownInvoiceNumbers)}
              />
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
                {t('app.invoices.payment_terms', { defaultValue: 'Payment terms (days)' })}
              </span>
              <input
                className="input"
                type="number"
                min="1"
                max="120"
                value={paymentTermsDays}
                onChange={(event) => setPaymentTermsDays(event.target.value)}
              />
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

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.tax_mode', { defaultValue: 'Tax mode' })}
              </span>
              <select className="input" value={taxMode} onChange={(event) => setTaxMode(event.target.value)}>
                <option value="standard_vat">{t('app.invoices.tax_mode_standard', { defaultValue: 'Standard VAT' })}</option>
                <option value="reverse_charge">{t('app.invoices.tax_mode_reverse', { defaultValue: 'Reverse charge' })}</option>
                <option value="vat_exempt">{t('app.invoices.tax_mode_exempt', { defaultValue: 'VAT exempt' })}</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('app.invoices.bank_account', { defaultValue: 'Bank account' })}
              </span>
              <select
                className="input"
                value={issuerBankAccountKey}
                onChange={(event) => setIssuerBankAccountKey(event.target.value)}
                disabled={!issuerBankAccounts.length}
              >
                <option value="">{t('app.invoices.bank_account_missing', { defaultValue: 'No primary bank account' })}</option>
                {issuerBankAccounts.map((account) => (
                  <option key={bankAccountKey(account)} value={bankAccountKey(account)}>
                    {[account.label, account.bank_name, account.iban].filter(Boolean).join(' · ')}
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
              <div key={item.line_no} className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1.5fr)_100px_120px_100px_auto]">
                <select
                  className="input"
                  value={item.service_id || ''}
                  onChange={(event) => applyCatalogService(index, event.target.value)}
                  disabled={loadingServices}
                >
                  <option value="">{t('app.invoices.catalog_item', { defaultValue: 'Catalog item' })}</option>
                  {serviceCatalog.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.code} · {service.name}
                    </option>
                  ))}
                </select>
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
                {item.service_id && (
                  <div className="text-xs text-slate-500 md:col-span-6">
                    {t('app.invoices.catalog_hint', {
                      defaultValue: 'Price and VAT were prefilled from the services catalog. You can still override them for this invoice.',
                    })}
                  </div>
                )}
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
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.kind', { defaultValue: 'Invoice type' })}</dt>
              <dd className="mt-1 text-slate-900">{invoiceKind || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.number', { defaultValue: 'Number' })}</dt>
              <dd className="mt-1 text-slate-900">{invoiceNumber || buildSuggestedInvoiceNumber(invoiceKind, taxMode, issueDate, knownInvoiceNumbers) || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.correction_of', { defaultValue: 'Correction of' })}</dt>
              <dd className="mt-1 text-slate-900">{correctionOfInvoiceNumber || sourceInvoice?.invoice_number || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.correction_reason', { defaultValue: 'Correction reason' })}</dt>
              <dd className="mt-1 text-slate-900">{correctionReason.trim() || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.client', { defaultValue: 'Client' })}</dt>
              <dd className="mt-1 text-slate-900">{companies.find((company) => company.id === companyId)?.name || '-'}</dd>
              <div className="mt-1 text-xs text-slate-500">
                {extractCompanyBillingSnapshot(clientCompany).tax_id || t('app.invoices.client_tax_id_required', { defaultValue: 'Client tax ID/NIP is required for invoices.' })}
              </div>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.issuer', { defaultValue: 'Issuer company' })}</dt>
              <dd className="mt-1 text-slate-900">{issuerCompany?.legal_name || issuerCompany?.name || '-'}</dd>
              <div className="mt-1 text-xs text-slate-500">
                {issuerCompany?.tax_id || t('app.invoices.issuer_tax_id_required', { defaultValue: 'Issuer tax ID/NIP is required for invoices.' })}
              </div>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.recipient', { defaultValue: 'Recipient' })}</dt>
              <dd className="mt-1 text-slate-900">{billingEmail || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.recipient_contact', { defaultValue: 'Recipient contact' })}</dt>
              <dd className="mt-1 text-slate-900">
                {clientContacts.find((contact) => contact.id === recipientContactId)?.full_name ||
                  clientContacts.find((contact) => contact.id === recipientContactId)?.email ||
                  '-'}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.bank_account', { defaultValue: 'Bank account' })}</dt>
              <dd className="mt-1 text-slate-900">
                {issuerBankAccounts.find((account) => bankAccountKey(account) === issuerBankAccountKey)?.iban ||
                  extractPrimaryBankAccount(issuerCompany)?.iban ||
                  t('app.invoices.bank_account_missing', { defaultValue: 'No primary bank account' })}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.payment_terms', { defaultValue: 'Payment terms (days)' })}</dt>
              <dd className="mt-1 text-slate-900">{paymentTermsDays || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.tax_mode', { defaultValue: 'Tax mode' })}</dt>
              <dd className="mt-1 text-slate-900">{taxMode || '-'}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.items', { defaultValue: 'Items' })}</dt>
              <dd className="mt-1 text-slate-900">{items.length}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.total', { defaultValue: 'Total' })}</dt>
              <dd className="mt-1 text-slate-900">{draftTotals.total.toFixed(2)} {currency}</dd>
            </div>
            {invoiceKind === 'correction' && sourceInvoice && (
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.invoices.delta_total', { defaultValue: 'Delta vs original' })}</dt>
                <dd className="mt-1 text-slate-900">{(draftTotals.total - Number(sourceInvoice.total_amount || 0)).toFixed(2)} {currency}</dd>
              </div>
            )}
          </dl>
          <div className="flex flex-col gap-2">
            <button type="submit" value="save_draft" className="btn-primary" disabled={saving || loadingCompanies}>
              {saving
                ? t('common.loading', { defaultValue: 'Loading...' })
                : isEditMode
                  ? t('app.invoices.save_draft', { defaultValue: 'Save Draft' })
                  : t('app.invoices.create', { defaultValue: 'Create Invoice' })}
            </button>
            <button type="submit" value="save_and_send" className="btn-secondary" disabled={saving || loadingCompanies}>
              {saving
                ? t('common.loading', { defaultValue: 'Loading...' })
                : t('app.invoices.save_and_send', { defaultValue: 'Save and send' })}
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
