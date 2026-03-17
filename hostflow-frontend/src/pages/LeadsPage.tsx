import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconFilter, IconRefresh, IconTable } from '@tabler/icons-react'

import {
  completeReminder,
  createInvoiceFromServiceOrder,
  createLeadServiceOrder,
  createReminder,
  getOnboardingStatus,
  listLeads,
  listReminders,
  type OnboardingStatus,
} from '../api/client'
import type { Lead, LeadListResponse, LeadStatus, LeadStage } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
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
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)

  // Lead Inbox side panel (Pipedrive-like: Composer / Focus / History)
  const [panelTab, setPanelTab] = useState<'composer' | 'focus' | 'history'>('composer')
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [remindersError, setRemindersError] = useState<string | null>(null)
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderDueAt, setReminderDueAt] = useState(() => new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
  const [reminderOffset, setReminderOffset] = useState<number>(15)

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
  const selectedLead = useMemo(() => (selectedLeadId ? items.find((item) => item.id === selectedLeadId) ?? null : null), [items, selectedLeadId])
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

  const loadLeadReminders = useCallback(
    async (leadId: string) => {
      setRemindersLoading(true)
      setRemindersError(null)
      try {
        const res = await listReminders({ entityType: 'lead', entityId: leadId, status: ['pending', 'new', 'overdue'] })
        const list = Array.isArray(res?.items) ? (res.items as ReminderRecord[]) : []
        setReminders(list)
      } catch (err: any) {
        setRemindersError(
          err?.response?.data?.detail ??
            err?.message ??
            t('app.reminders.errors.load', { defaultValue: 'Failed to load reminders' }),
        )
        setReminders([])
      } finally {
        setRemindersLoading(false)
      }
    },
    [t],
  )

  useEffect(() => {
    if (!selectedLeadId) {
      setReminders([])
      setRemindersError(null)
      setRemindersLoading(false)
      return
    }
    void loadLeadReminders(selectedLeadId)
  }, [loadLeadReminders, selectedLeadId])

  const handleCreateLeadReminder = useCallback(async () => {
    if (!selectedLeadId || !reminderTitle || !reminderDueAt) return
    try {
      const due = new Date(reminderDueAt)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createReminder({
        title: reminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'lead',
        entity_id: selectedLeadId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
      })
      setReminderTitle('')
      setReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      await loadLeadReminders(selectedLeadId)
      notify({ title: t('app.reminders.messages.created', { defaultValue: 'Reminder created' }), variant: 'success' })
      setPanelTab('focus')
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ??
        err?.message ??
        t('app.reminders.errors.create', { defaultValue: 'Failed to create reminder' })
      setRemindersError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      notify({ title: typeof detail === 'string' ? detail : t('app.reminders.errors.create'), variant: 'error' })
    }
  }, [loadLeadReminders, notify, panelTab, reminderDueAt, reminderOffset, reminderTitle, selectedLeadId, t])

  const handleCompleteReminder = useCallback(
    async (id: string) => {
      try {
        await completeReminder(id)
        if (selectedLeadId) await loadLeadReminders(selectedLeadId)
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.reminders.errors.complete', { defaultValue: 'Failed to complete reminder' })
        notify({ title: typeof detail === 'string' ? detail : t('app.reminders.errors.complete'), variant: 'error' })
      }
    },
    [loadLeadReminders, notify, selectedLeadId, t],
  )

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

      <section className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
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
                {!loading &&
                  !error &&
                  items.map((lead) => {
                    const normalized = lead.normalized || {}
                    const contactName = normalized.full_name || `${normalized.first_name || ''} ${normalized.last_name || ''}`.trim()
                    const contactEmail = normalized.email
                    const contactPhone = normalized.phone
                    const contact = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ')
                    const isSelected = selectedLeadId === lead.id

                    return (
                      <tr
                        key={lead.id}
                        className={isSelected ? 'bg-brand-50 hover:bg-brand-50' : 'hover:bg-slate-50'}
                        role="button"
                        tabIndex={0}
                        onClick={() => {
                          setSelectedLeadId(lead.id)
                          setPanelTab('composer')
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedLeadId(lead.id)
                            setPanelTab('composer')
                          }
                        }}
                      >
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
                        <td className="text-slate-700">{contact || '—'}</td>
                        <td className="text-slate-700">{lead.source}</td>
                        <td className="text-brand-700">
                          {isServicesTenant ? (
                            <div className="flex flex-col items-start gap-1">
                              {lead.outcome_entity_id ? (
                                <Link to={`/app/clients/${lead.outcome_entity_id}`} onClick={(e) => e.stopPropagation()}>
                                  {lead.outcome_entity_name || lead.company_name || lead.outcome_entity_id}
                                </Link>
                              ) : (
                                <span>—</span>
                              )}
                              {lead.service_order_id ? (
                                <div className="flex flex-wrap items-center gap-2">
                                  <Link
                                    to={`/app/services?order=${lead.service_order_id}`}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('app.leads.actions.open_service_order', { defaultValue: 'Open service order' })}
                                  </Link>
                                  <button
                                    type="button"
                                    className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                    disabled={creatingInvoiceOrderId === lead.service_order_id}
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      void handleCreateInvoice(String(lead.service_order_id))
                                    }}
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
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    void handleCreateServiceOrder(lead.id)
                                  }}
                                >
                                  {creatingOrderLeadId === lead.id
                                    ? t('common.loading', { defaultValue: 'Loading...' })
                                    : t('app.leads.actions.create_service_order', { defaultValue: 'Create service order' })}
                                </button>
                              )}
                            </div>
                          ) : lead.candidate_id ? (
                            <Link to={`/app/candidates/${lead.candidate_id}`} onClick={(e) => e.stopPropagation()}>
                              {lead.candidate_name || lead.candidate_id}
                            </Link>
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
            <div>{t('app.leads.pagination.shown', { values: { count: items.length, total: data.total } })}</div>
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
        </div>

        <aside className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {!selectedLead ? (
            <div className="p-4 text-sm text-slate-500">
              {t('app.leads.inbox.select_hint', { defaultValue: 'Select a lead to work it from the side panel.' })}
            </div>
          ) : (
            <div className="flex h-full flex-col">
              <div className="border-b border-slate-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-900">
                      {selectedLead.normalized?.full_name ||
                        `${selectedLead.normalized?.first_name || ''} ${selectedLead.normalized?.last_name || ''}`.trim() ||
                        selectedLead.company_name ||
                        t('app.leads.inbox.lead', { defaultValue: 'Lead' })}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-600">
                      <span className="font-medium">{t('app.leads.table.status')}:</span> {statusLabels[selectedLead.status] ?? selectedLead.status}
                      {selectedLead.stage ? (
                        <>
                          <span className="mx-1">·</span>
                          <span className="font-medium">{t('app.leads.table.stage', { defaultValue: 'Stage' })}:</span>{' '}
                          {stageLabels[selectedLead.stage] ?? selectedLead.stage}
                        </>
                      ) : null}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary h-8 rounded-lg px-2 text-xs"
                    onClick={() => setSelectedLeadId(null)}
                  >
                    {t('common.actions.close', { defaultValue: 'Close' })}
                  </button>
                </div>

                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    className={panelTab === 'composer' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('composer')}
                  >
                    {t('app.leads.inbox.tabs.composer', { defaultValue: 'Composer' })}
                  </button>
                  <button
                    type="button"
                    className={panelTab === 'focus' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('focus')}
                  >
                    {t('app.leads.inbox.tabs.focus', { defaultValue: 'Focus' })}
                  </button>
                  <button
                    type="button"
                    className={panelTab === 'history' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('history')}
                  >
                    {t('app.leads.inbox.tabs.history', { defaultValue: 'History' })}
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-auto p-3">
                {panelTab === 'composer' && (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-semibold text-slate-700">
                        {t('app.leads.inbox.composer.followup', { defaultValue: 'Create follow-up' })}
                      </div>
                      <div className="mt-2 space-y-2">
                        <input
                          className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                          value={reminderTitle}
                          onChange={(e) => setReminderTitle(e.target.value)}
                          placeholder={t('app.reminders.fields.title', { defaultValue: 'Title' })}
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <label className="text-xs font-medium text-slate-600">
                            <div className="mb-1">{t('app.reminders.fields.due_at', { defaultValue: 'Due' })}</div>
                            <input
                              type="datetime-local"
                              className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                              value={reminderDueAt}
                              onChange={(e) => setReminderDueAt(e.target.value)}
                            />
                          </label>
                          <label className="text-xs font-medium text-slate-600">
                            <div className="mb-1">{t('app.reminders.fields.remind_before', { defaultValue: 'Remind before (min)' })}</div>
                            <input
                              type="number"
                              min={0}
                              className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                              value={reminderOffset}
                              onChange={(e) => setReminderOffset(Number(e.target.value) || 0)}
                            />
                          </label>
                        </div>
                        <button
                          type="button"
                          className="btn-primary h-9 w-full rounded-lg text-sm disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={!reminderTitle || !reminderDueAt}
                          onClick={() => void handleCreateLeadReminder()}
                        >
                          {t('app.reminders.actions.create', { defaultValue: 'Create reminder' })}
                        </button>
                        {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
                      </div>
                    </div>
                    <div className="text-xs text-slate-500">
                      {t('app.leads.inbox.composer.hint', {
                        defaultValue: 'This panel is designed to “work the lead” without leaving the list.',
                      })}
                    </div>
                  </div>
                )}

                {panelTab === 'focus' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-semibold text-slate-700">
                        {t('app.reminders.title', { defaultValue: 'Reminders' })}
                      </div>
                      <button
                        type="button"
                        className="btn-secondary h-8 rounded-lg px-2 text-xs"
                        onClick={() => selectedLeadId && void loadLeadReminders(selectedLeadId)}
                      >
                        {t('common.actions.refresh', { defaultValue: 'Refresh' })}
                      </button>
                    </div>
                    {remindersLoading ? (
                      <div className="py-4 text-center text-xs text-slate-500">{t('common.loading')}</div>
                    ) : reminders.length === 0 ? (
                      <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-500">
                        {t('app.reminders.states.empty', { defaultValue: 'No reminders yet.' })}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {reminders.slice(0, 20).map((r) => (
                          <div key={r.id} className="rounded-lg border border-slate-200 bg-white p-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-medium text-slate-900">{r.title || t('app.reminders.item.untitled', { defaultValue: 'Untitled' })}</div>
                                <div className="mt-0.5 text-xs text-slate-600">
                                  <span className="font-medium">{t('app.reminders.fields.due_at', { defaultValue: 'Due' })}:</span> {formatDateValue(r.due_at)}
                                </div>
                              </div>
                              <button
                                type="button"
                                className="btn-secondary h-8 rounded-lg px-2 text-xs"
                                onClick={() => void handleCompleteReminder(r.id)}
                              >
                                {t('app.reminders.actions.complete', { defaultValue: 'Done' })}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
                  </div>
                )}

                {panelTab === 'history' && (
                  <div className="space-y-2 text-xs">
                    <div className="rounded-lg border border-slate-200 bg-white p-3">
                      <div className="grid grid-cols-1 gap-2">
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.created')}:</span>{' '}
                          <span className="font-medium text-slate-800">{formatDateValue(selectedLead.created_at)}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.source')}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.source}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{companyColumnLabel}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.company_name || selectedLead.company_id}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{vacancyColumnLabel}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.vacancy_title || selectedLead.vacancy_id || '—'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.status')}:</span>{' '}
                          <span className="font-medium text-slate-800">{statusLabels[selectedLead.status] ?? selectedLead.status}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.stage', { defaultValue: 'Stage' })}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.stage ? stageLabels[selectedLead.stage] ?? selectedLead.stage : '—'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.error')}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.error || '—'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.table.contact')}:</span>{' '}
                          <span className="font-medium text-slate-800">
                            {[
                              selectedLead.normalized?.full_name ||
                                `${selectedLead.normalized?.first_name || ''} ${selectedLead.normalized?.last_name || ''}`.trim(),
                              selectedLead.normalized?.email,
                              selectedLead.normalized?.phone,
                            ]
                              .filter(Boolean)
                              .join(' · ') || '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.inbox.history.last_routed', { defaultValue: 'Last routed' })}:</span>{' '}
                          <span className="font-medium text-slate-800">{selectedLead.last_routed_at ? formatDateValue(selectedLead.last_routed_at) : '—'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">{t('app.leads.inbox.history.outcome', { defaultValue: 'Outcome' })}:</span>{' '}
                          <span className="font-medium text-slate-800">
                            {selectedLead.outcome_entity_id ? `${selectedLead.outcome_entity_type || 'entity'}: ${selectedLead.outcome_entity_name || selectedLead.outcome_entity_id}` : '—'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-500">
                      {t('app.leads.inbox.history.note', {
                        defaultValue: 'History v1 shows lead metadata. We can extend it with event timeline once backend exposes lead events.',
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </aside>
      </section>
    </div>
  )
}
