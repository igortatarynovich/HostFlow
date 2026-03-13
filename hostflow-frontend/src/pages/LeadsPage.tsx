import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconFilter, IconRefresh, IconTable } from '@tabler/icons-react'

import { createInvoiceFromServiceOrder, createLeadServiceOrder, getOnboardingStatus, listLeads, type OnboardingStatus } from '../api/client'
import type { Lead, LeadListResponse, LeadStatus, LeadStage } from '../api/types'
import { useI18n } from '../i18n'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useToast } from '../components/Toast'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'

const STATUS_FILTERS: Array<'' | LeadStatus> = ['', 'new', 'processed', 'duplicated', 'needs_routing', 'failed']
const STAGE_FILTERS: Array<'' | LeadStage> = ['', 'new', 'contacted', 'qualified', 'converted', 'lost']
const DATE_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
}

const LOCALE_TO_DATE = {
  en: 'en-US',
  ru: 'ru-RU',
  pl: 'pl-PL',
} as const

export default function LeadsPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const { entitySingular, openEntityLabel } = useBusinessTerminology()
  const [status, setStatus] = useState<'' | LeadStatus>('')
  const [stage, setStage] = useState<'' | LeadStage>('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [data, setData] = useState<LeadListResponse>({ items: [], total: 0, limit: 20, offset: 0 })
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null)
  const [creatingOrderLeadId, setCreatingOrderLeadId] = useState<string | null>(null)
  const [creatingInvoiceOrderId, setCreatingInvoiceOrderId] = useState<string | null>(null)

  const limit = 20
  const offset = (page - 1) * limit

  const loadLeads = useCallback(
    async (nextOffset: number = offset) => {
      setLoading(true)
      setError(null)
      try {
        const payload = await listLeads({ status: status || undefined, stage: stage || undefined, limit, offset: nextOffset })
        setData(payload as LeadListResponse)
      } catch (err: any) {
        setError(getFriendlyErrorInfo(err, t('app.leads.messages.load_failed')))
      } finally {
        setLoading(false)
      }
    },
    [limit, offset, stage, status, t],
  )

  useEffect(() => {
    void loadLeads(offset)
  }, [loadLeads, offset])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const payload = await getOnboardingStatus()
        if (!cancelled) setOnboardingStatus(payload)
      } catch {
        if (!cancelled) setOnboardingStatus(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const businessType = onboardingStatus?.business_type ?? 'agency'
  const isServicesTenant = businessType === 'services'
  const isEmployerTenant = businessType === 'employer'
  const leadWorkspaceTitle = isServicesTenant
    ? t('app.leads.title_services', { defaultValue: 'Client Leads' })
    : t('app.leads.title')
  const leadWorkspaceSubtitle = isServicesTenant
    ? t('app.leads.subtitle_services', {
        defaultValue: 'Track potential clients from first contact to qualification, service order, and invoicing.',
      })
    : t('app.leads.subtitle')
  const ownerColumnLabel = isServicesTenant
    ? t('app.leads.table.client', { defaultValue: 'Client' })
    : t('app.leads.table.candidate')
  const companyColumnLabel = isEmployerTenant
    ? t('app.dashboard.terms.companies_singular', { defaultValue: 'Company' })
    : entitySingular
  const vacancyColumnLabel = isServicesTenant
    ? t('app.leads.table.service_order', { defaultValue: 'Service order' })
    : t('app.leads.table.vacancy')
  const emptyTitle = isServicesTenant
    ? t('app.leads.states.empty_title_services', { defaultValue: 'No client leads yet' })
    : t('app.leads.states.empty_title', { defaultValue: 'No leads yet' })
  const emptyDescription = isServicesTenant
    ? t('app.leads.states.empty_desc_services', {
        defaultValue: 'Connect lead sources or add your first client to start service sales and follow-up.',
      })
    : t('app.leads.states.empty_desc', {
        defaultValue: 'Connect ad sources or import leads to start routing and assignment.',
      })
  const secondaryEmptyLabel = isServicesTenant
    ? t('app.leads.states.empty_cta_clients', { defaultValue: 'Open clients' })
    : openEntityLabel

  const totalPages = useMemo(() => {
    if (!data.limit) return 1
    return Math.max(1, Math.ceil((data.total || 0) / data.limit))
  }, [data.total, data.limit])

  const canPrev = page > 1
  const canNext = page < totalPages

  const items: Lead[] = useMemo(() => (Array.isArray(data.items) ? data.items : []), [data.items])
  const statusOptions = useMemo<Array<{ value: '' | LeadStatus; label: string }>>(
    () =>
      STATUS_FILTERS.map((value) => ({
        value,
        label: value ? t(`app.leads.statuses.${value}`) : t('app.leads.filters.status_all'),
      })),
    [t]
  )
  const stageOptions = useMemo<Array<{ value: '' | LeadStage; label: string }>>(
    () =>
      STAGE_FILTERS.map((value) => ({
        value,
        label: value ? t(`app.leads.stages.${value}`) : t('app.leads.filters.stage_all', { defaultValue: 'All stages' }),
      })),
    [t]
  )
  const stageLabels = useMemo(() => {
    const map: Record<string, string> = {}
    STAGE_FILTERS.forEach((value) => {
      if (!value) return
      map[value] = t(`app.leads.stages.${value}`)
    })
    return map
  }, [t])
  const statusLabels = useMemo(() => {
    const map: Record<string, string> = {}
    STATUS_FILTERS.forEach((value) => {
      if (!value) return
      map[value] = t(`app.leads.statuses.${value}`)
    })
    return map
  }, [t])
  const dateFormatter = useMemo(() => {
    const localeCode = LOCALE_TO_DATE[locale as keyof typeof LOCALE_TO_DATE] || 'en-US'
    try {
      return new Intl.DateTimeFormat(localeCode, DATE_FORMAT_OPTIONS)
    } catch (err) {
      return new Intl.DateTimeFormat('en-US', DATE_FORMAT_OPTIONS)
    }
  }, [locale])
  const formatDateValue = (value?: string) => {
    if (!value) return '—'
    try {
      return dateFormatter.format(new Date(value))
    } catch (err) {
      return value
    }
  }

  const handleCreateServiceOrder = useCallback(
    async (leadId: string) => {
      setCreatingOrderLeadId(leadId)
      try {
        await createLeadServiceOrder(leadId)
        await loadLeads(offset)
        notify({
          title: t('app.leads.messages.service_order_created', { defaultValue: 'Service order created' }),
          description: t('app.leads.messages.service_order_created_desc', {
            defaultValue: 'Draft service order was created from this lead.',
          }),
          variant: 'success',
        })
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.service_order_create_failed', {
            defaultValue: 'Failed to create service order',
          })
        notify({
          title: t('app.leads.messages.service_order_create_failed', { defaultValue: 'Failed to create service order' }),
          description: typeof detail === 'string' ? detail : JSON.stringify(detail),
          variant: 'error',
        })
      } finally {
        setCreatingOrderLeadId(null)
      }
    },
    [loadLeads, notify, offset, t],
  )

  const handleCreateInvoice = useCallback(
    async (orderId: string) => {
      setCreatingInvoiceOrderId(orderId)
      try {
        const invoice = await createInvoiceFromServiceOrder(orderId)
        notify({
          title: t('app.leads.messages.invoice_created', { defaultValue: 'Invoice ready' }),
          description: t('app.leads.messages.invoice_created_desc', {
            defaultValue: 'Draft invoice was created and is now available in Invoices.',
          }),
          variant: 'success',
        })
        window.location.assign(`/app/invoices`)
        return invoice
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.invoice_create_failed', {
            defaultValue: 'Failed to create invoice',
          })
        notify({
          title: t('app.leads.messages.invoice_create_failed', { defaultValue: 'Failed to create invoice' }),
          description: typeof detail === 'string' ? detail : JSON.stringify(detail),
          variant: 'error',
        })
      } finally {
        setCreatingInvoiceOrderId(null)
      }
    },
    [notify, t],
  )

  return (
    <div className="space-y-3">
      <header className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">{leadWorkspaceTitle}</h1>
            <p className="text-xs text-slate-500">{leadWorkspaceSubtitle}</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">
            <IconTable size={14} />
            <span>{t('app.leads.pagination.shown', { values: { count: items.length, total: data.total } })}</span>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-[170px] text-xs font-medium text-slate-600">
            <span className="mb-1 inline-flex items-center gap-1">
              <IconFilter size={12} />
              {t('app.leads.filters.status')}
            </span>
            <select
              className="input h-9 rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as '' | LeadStatus)
                setPage(1)
              }}
            >
              {statusOptions.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label className="min-w-[170px] text-xs font-medium text-slate-600">
            <span className="mb-1 inline-flex items-center gap-1">
              <IconFilter size={12} />
              {t('app.leads.filters.stage', { defaultValue: 'Stage' })}
            </span>
            <select
              className="input h-9 rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              value={stage}
              onChange={(event) => {
                setStage(event.target.value as '' | LeadStage)
                setPage(1)
              }}
            >
              {stageOptions.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => {
              setPage(1)
              void loadLeads(0)
            }}
            className="btn-secondary h-9 rounded-lg px-3 text-xs"
          >
            <IconRefresh size={14} />
            {t('app.candidates.actions.refresh')}
          </button>
        </div>
      </header>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="table min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th>{t('app.leads.table.created')}</th>
                <th>{t('app.leads.table.status')}</th>
                <th>{t('app.leads.table.stage', { defaultValue: 'Stage' })}</th>
                <th>{companyColumnLabel}</th>
                <th>{vacancyColumnLabel}</th>
                <th>{t('app.leads.table.contact')}</th>
                <th>{t('app.leads.table.source')}</th>
                <th>{ownerColumnLabel}</th>
                <th>{t('app.leads.table.error')}</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={9} className="px-3 py-5 text-center text-slate-500">
                    {t('common.loading')}
                  </td>
                </tr>
              )}
              {error && !loading && (
                <tr>
                  <td colSpan={9} className="px-3 py-4">
                    <ErrorRecoveryBanner
                      compact
                      info={error}
                      onRetry={() => void loadLeads(offset)}
                      retryLabel={t('common.retry', { defaultValue: 'Retry' })}
                      secondaryTo="/app/settings/leads"
                      secondaryLabel={t('app.leads.states.empty_cta_connect', { defaultValue: 'Connect sources' })}
                    />
                  </td>
                </tr>
              )}
              {!loading && !error && items.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-3 py-6">
                    <EmptyStatePanel
                      compact
                      title={emptyTitle}
                      description={emptyDescription}
                      primaryAction={{
                        label: t('app.leads.states.empty_cta_connect', { defaultValue: 'Connect sources' }),
                        to: '/app/settings/leads',
                      }}
                      secondaryAction={{
                        label: secondaryEmptyLabel,
                        to: '/app/clients',
                      }}
                    />
                  </td>
                </tr>
              )}
              {!loading && !error && items.map((lead) => {
                const normalized = lead.normalized || {}
                const contactName = normalized.full_name || `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
                const contactEmail = normalized.email
                const contactPhone = normalized.phone
                const contact = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ')

                return (
                  <tr key={lead.id} className="hover:bg-slate-50">
                    <td className="text-slate-600">{formatDateValue(lead.created_at)}</td>
                    <td>
                      <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                        {statusLabels[lead.status] ?? lead.status}
                      </span>
                    </td>
                    <td>
                      {lead.stage ? (
                        <span className="inline-flex items-center rounded-md bg-brand-100 px-2 py-0.5 text-[11px] font-medium text-brand-800">
                          {stageLabels[lead.stage] ?? lead.stage}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="text-slate-800">{lead.company_name || lead.company_id}</td>
                    <td className="text-slate-800">{lead.vacancy_title || lead.vacancy_id || '—'}</td>
                    <td className="text-slate-700">
                      {contact || '—'}
                    </td>
                    <td className="text-slate-700">{lead.source}</td>
                    <td className="text-brand-700">
                      {isServicesTenant ? (
                        <div className="flex flex-col items-start gap-1">
                          {lead.outcome_entity_id ? (
                            <Link to={`/app/clients/${lead.outcome_entity_id}`}>{lead.outcome_entity_name || lead.company_name || lead.outcome_entity_id}</Link>
                          ) : (
                            <span>—</span>
                          )}
                          {lead.service_order_id ? (
                            <div className="flex flex-wrap items-center gap-2">
                              <Link
                                to={`/app/services?order=${lead.service_order_id}`}
                                className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                              >
                                {t('app.leads.actions.open_service_order', { defaultValue: 'Open service order' })}
                              </Link>
                              <button
                                type="button"
                                className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                disabled={creatingInvoiceOrderId === lead.service_order_id}
                                onClick={() => void handleCreateInvoice(String(lead.service_order_id))}
                              >
                                {creatingInvoiceOrderId === lead.service_order_id
                                  ? t('common.loading', { defaultValue: 'Loading...' })
                                  : t('app.leads.actions.create_invoice', { defaultValue: 'Create invoice' })}
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                              disabled={creatingOrderLeadId === lead.id}
                              onClick={() => void handleCreateServiceOrder(lead.id)}
                            >
                              {creatingOrderLeadId === lead.id
                                ? t('common.loading', { defaultValue: 'Loading...' })
                                : t('app.leads.actions.create_service_order', { defaultValue: 'Create service order' })}
                            </button>
                          )}
                        </div>
                      ) : lead.candidate_id ? (
                        <Link to={`/app/candidates/${lead.candidate_id}`}>{lead.candidate_name || lead.candidate_id}</Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="text-sm text-red-500">{lead.error || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <footer className="flex items-center justify-between border-t border-slate-200 px-3 py-2 text-xs text-slate-600">
          <div>
            {t('app.leads.pagination.shown', { values: { count: items.length, total: data.total } })}
          </div>
          <div className="space-x-2">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => canPrev && setPage((prev) => prev - 1)}
              className="btn-secondary rounded-lg px-2.5 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('app.leads.pagination.prev')}
            </button>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => canNext && setPage((prev) => prev + 1)}
              className="btn-secondary rounded-lg px-2.5 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('app.leads.pagination.next')}
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
