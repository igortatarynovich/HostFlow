import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { IconFilter, IconRefresh, IconTable } from '@tabler/icons-react'

import {
  completeActivity,
  createActivity,
  createBulkActivities,
  createInvoiceFromServiceOrder,
  createLeadServiceOrder,
  bulkUpdateLeads,
  getLeadTimeline,
  getOnboardingStatus,
  listVacancies,
  listLeads,
  listReminders,
  processLead,
  type OnboardingStatus,
} from '../api/client'
import { retryLeads, rerouteMetaLead } from '../api/metaLeads'
import type { Lead, LeadListResponse, LeadStatus, LeadStage } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
import { recordPerfMeasurement } from '../api/analytics'
import { useI18n } from '../i18n'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { BulkActivitiesModal } from '../modules/candidates/components'
import { useToast } from '../components/Toast'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { getLeadErrorSuggestion } from '../utils/leadErrorSuggestion'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { serviceOrderWorkspacePath } from '../modules/services/utils'

const STATUS_FILTERS: Array<'' | LeadStatus> = ['', 'new', 'processed', 'duplicated', 'needs_routing', 'failed']
const STAGE_FILTERS: Array<'' | LeadStage> = ['', 'new', 'contacted', 'qualified', 'converted', 'lost']
const NEXT_ACTION_FILTERS: Array<'' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'> = [
  '',
  'no_next_action',
  'overdue',
  'scheduled',
  'stuck',
]
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
  const location = useLocation()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'' | LeadStatus>('')
  const [stage, setStage] = useState<'' | LeadStage>('')
  const [nextAction, setNextAction] = useState<'' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'>('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [data, setData] = useState<LeadListResponse>({ items: [], total: 0, limit: 20, offset: 0 })
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null)
  const [creatingOrderLeadId, setCreatingOrderLeadId] = useState<string | null>(null)
  const [creatingInvoiceOrderId, setCreatingInvoiceOrderId] = useState<string | null>(null)
  const [processingLeadId, setProcessingLeadId] = useState<string | null>(null)
  const [retryingLeadId, setRetryingLeadId] = useState<string | null>(null)
  const [bulkRetryingMetaLeads, setBulkRetryingMetaLeads] = useState(false)
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null)
  const [vacanciesLoading, setVacanciesLoading] = useState(false)
  const [vacanciesError, setVacanciesError] = useState<string | null>(null)
  const [vacancyOptions, setVacancyOptions] = useState<Array<{ id: string; title: string }>>([])
  const [rerouteVacancyId, setRerouteVacancyId] = useState<string>('')
  const [reroutingLeadId, setReroutingLeadId] = useState<string | null>(null)

  // Lead Inbox side panel (Pipedrive-like: Composer / Focus / History)
  const [panelTab, setPanelTab] = useState<'composer' | 'fix' | 'focus' | 'history'>('composer')
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [remindersError, setRemindersError] = useState<string | null>(null)
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderDueAt, setReminderDueAt] = useState(() => new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
  const [reminderOffset, setReminderOffset] = useState<number>(15)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [timelineError, setTimelineError] = useState<string | null>(null)
  const [timelineItems, setTimelineItems] = useState<
    { at: string; kind: string; source: string; title?: string | null; description?: string | null }[]
  >([])

  // Bulk activities (reminders) for selected leads
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const selectedCount = useMemo(() => Object.values(checked).filter(Boolean).length, [checked])
  const allSelectedLeadIds = useMemo(() => data.items.filter((l) => checked[l.id]).map((l) => l.id), [checked, data.items])
  const selectedMetaProblemLeadIds = useMemo(() => {
    return data.items
      .filter((l) => checked[l.id])
      .filter((lead) => {
        const metaSource = String(lead.source || '').toLowerCase() === 'meta'
        const metaErrorCode = (lead.error ?? '').trim()
        return metaSource && metaErrorCode.length > 0 && (lead.status === 'failed' || lead.status === 'needs_routing')
      })
      .map((l) => l.id)
  }, [checked, data.items])
  const toggleChecked = useCallback((id: string) => setChecked((s) => ({ ...s, [id]: !s[id] })), [])

  const [bulkActivitiesOpen, setBulkActivitiesOpen] = useState(false)
  const [bulkActivityTitle, setBulkActivityTitle] = useState('')
  const [bulkActivityDueAt, setBulkActivityDueAt] = useState(() =>
    new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [bulkActivityOffsetMinutes, setBulkActivityOffsetMinutes] = useState(60)
  const [bulkActivityType, setBulkActivityType] = useState('custom')
  const [bulkActivitiesLoading, setBulkActivitiesLoading] = useState(false)
  const [bulkStage, setBulkStage] = useState<'' | LeadStage>('')
  const [bulkStatus, setBulkStatus] = useState<'' | LeadStatus>('')
  const [bulkUpdating, setBulkUpdating] = useState(false)

  const doBulkActivities = useCallback(async () => {
    const ids = allSelectedLeadIds
    if (ids.length === 0 || !bulkActivityTitle.trim() || !bulkActivityDueAt) return
    setBulkActivitiesLoading(true)
    try {
      const due = new Date(bulkActivityDueAt)
      const remindAt = new Date(due.getTime() - bulkActivityOffsetMinutes * 60 * 1000)
      const res = await createBulkActivities({
        title: bulkActivityTitle.trim(),
        description: '',
        type: bulkActivityType,
        entity_type: 'lead',
        entity_ids: ids,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        source: 'bulk',
        priority: 'normal',
      })
      const results: Array<{ entity_id?: string; ok?: boolean }> = Array.isArray(res?.results) ? res.results : []
      const failures = results.filter((r) => r && r.ok === false)
      setBulkActivitiesOpen(false)
      if (failures.length > 0) {
        notify({
          title: t('app.leads.bulk.activities.partial', { defaultValue: 'Some activities failed to create' }),
          description: `${failures.length} / ${ids.length}`,
          variant: 'error',
        })
      } else {
        notify({ title: t('app.leads.bulk.activities.created', { defaultValue: 'Activities created' }), variant: 'success' })
        setChecked({})
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed'
      notify({
        title: t('app.leads.bulk.activities.failed', { defaultValue: 'Failed to create activities' }),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setBulkActivitiesLoading(false)
    }
  }, [allSelectedLeadIds, bulkActivityDueAt, bulkActivityOffsetMinutes, bulkActivityTitle, bulkActivityType, notify, t])

  const limit = 20
  const offset = (page - 1) * limit

  // Drill-down support: /app/leads?status=needs_routing&stage=qualified
  useEffect(() => {
    const sp = new URLSearchParams(location.search || '')
    const nextStatus = (sp.get('status') || '').trim()
    const nextStage = (sp.get('stage') || '').trim()
    const nextNextAction = (sp.get('next_action') || '').trim()
    if (nextStatus && (STATUS_FILTERS as string[]).includes(nextStatus) && nextStatus !== status) {
      setStatus(nextStatus as any)
      setPage(1)
    }
    if (nextStage && (STAGE_FILTERS as string[]).includes(nextStage) && nextStage !== stage) {
      setStage(nextStage as any)
      setPage(1)
    }
    if (nextNextAction && (NEXT_ACTION_FILTERS as string[]).includes(nextNextAction) && nextNextAction !== nextAction) {
      setNextAction(nextNextAction as any)
      setPage(1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search])

  const drilldownInfo = useMemo(() => {
    const sp = new URLSearchParams(location.search || '')
    const nextStatus = (sp.get('status') || '').trim()
    const nextStage = (sp.get('stage') || '').trim()
    const nextNextAction = (sp.get('next_action') || '').trim()
    return {
      status: nextStatus,
      stage: nextStage,
      nextAction: nextNextAction,
      hasFilters: Boolean(nextStatus || nextStage || nextNextAction),
    }
  }, [location.search])

  const loadLeads = useCallback(
    async (nextOffset: number = offset) => {
      setLoading(true)
      setError(null)
      const perfT0 = typeof performance !== 'undefined' ? performance.now() : Date.now()
      let perfOk = true
      try {
        const payload = await listLeads({
          status: status || undefined,
          stage: stage || undefined,
          nextAction: nextAction || undefined,
          limit,
          offset: nextOffset,
        })
        const items = Array.isArray((payload as any)?.items) ? ((payload as any).items as Lead[]) : []
        const problemFirstItems = [...items].sort((a, b) => {
          const aMetaSource = String(a.source || '').toLowerCase() === 'meta'
          const bMetaSource = String(b.source || '').toLowerCase() === 'meta'
          const aErrorCode = (a.error ?? '').trim()
          const bErrorCode = (b.error ?? '').trim()
          const aIsProblem = aMetaSource && aErrorCode.length > 0 && (a.status === 'failed' || a.status === 'needs_routing')
          const bIsProblem = bMetaSource && bErrorCode.length > 0 && (b.status === 'failed' || b.status === 'needs_routing')
          if (aIsProblem !== bIsProblem) return aIsProblem ? -1 : 1
          const ta = a.created_at ? new Date(a.created_at).getTime() : 0
          const tb = b.created_at ? new Date(b.created_at).getTime() : 0
          return tb - ta
        })
        setData({ ...(payload as LeadListResponse), items: problemFirstItems })
      } catch (err: any) {
        perfOk = false
        setError(getFriendlyErrorInfo(err, t('app.leads.messages.load_failed')))
      } finally {
        const durationMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - perfT0
        void recordPerfMeasurement({
          metricKey: 'leads.list.load',
          durationMs,
          route: typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : undefined,
          meta: { ok: perfOk, status: status || null, stage: stage || null, next_action: nextAction || null, limit, offset: nextOffset },
        }).catch(() => {})
        setLoading(false)
      }
    },
    [limit, nextAction, offset, stage, status, t],
  )

  const resetDrilldown = useCallback(() => {
    setStatus('')
    setStage('')
    setNextAction('')
    setPage(1)
    setSelectedLeadId(null)
    navigate('/app/leads', { replace: true })
    // Let state updates apply before re-loading the first page.
    setTimeout(() => {
      void loadLeads(0)
    }, 0)
  }, [loadLeads, navigate])

  const doBulkUpdateLeads = useCallback(async () => {
    const ids = allSelectedLeadIds
    if (ids.length === 0) return
    if (!bulkStage && !bulkStatus) return
    setBulkUpdating(true)
    try {
      await bulkUpdateLeads({
        lead_ids: ids,
        stage: bulkStage || null,
        status: bulkStatus || null,
      })
      await loadLeads(offset)
      notify({
        title: t('app.leads.bulk.updated', { defaultValue: 'Leads updated' }),
        description: `${ids.length}`,
        variant: 'success',
      })
      setChecked({})
      setBulkStage('')
      setBulkStatus('')
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed'
      notify({
        title: t('app.leads.bulk.update_failed', { defaultValue: 'Bulk update failed' }),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setBulkUpdating(false)
    }
  }, [allSelectedLeadIds, bulkStage, bulkStatus, loadLeads, notify, offset, t])

  const doBulkRetryMetaLeads = useCallback(async () => {
    const ids = selectedMetaProblemLeadIds
    if (!ids.length) return

    setBulkRetryingMetaLeads(true)
    try {
      const result = await retryLeads({ lead_ids: ids, refresh_graph: true })

      if (result.processed > 0) {
        notify({
          title: t('app.leads.messages.processed', { defaultValue: 'Lead processed' }),
          description: `${result.processed} / ${ids.length}`,
          variant: 'success',
        })
      }
      if (result.failed > 0) {
        notify({
          title: t('app.leads.messages.process_failed', { defaultValue: 'Failed to process lead' }),
          description: `${result.failed} failed, ${result.skipped} skipped`,
          variant: 'error',
        })
      }

      await loadLeads(offset)
      setChecked({})
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
      notify({
        title: t('app.admin.meta_leads.errors.retry', { defaultValue: 'Retry failed' }),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setBulkRetryingMetaLeads(false)
    }
  }, [loadLeads, notify, offset, retryLeads, selectedMetaProblemLeadIds, t])

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

  useEffect(() => {
    // Drop selection when list changes (filters/paging).
    setChecked({})
  }, [nextAction, offset, stage, status])

  const selectedLead = useMemo(() => (selectedLeadId ? items.find((item) => item.id === selectedLeadId) ?? null : null), [items, selectedLeadId])
  const selectedIsMetaProblemLead = useMemo(() => {
    if (!selectedLead) return false
    const metaSource = String(selectedLead.source || '').toLowerCase() === 'meta'
    const metaErrorCode = (selectedLead.error ?? '').trim()
    return metaSource && metaErrorCode.length > 0 && (selectedLead.status === 'failed' || selectedLead.status === 'needs_routing')
  }, [selectedLead])

  const selectedLeadSuggestion = useMemo(() => {
    if (!selectedIsMetaProblemLead) return null
    return getLeadErrorSuggestion(selectedLead?.error, t)
  }, [selectedIsMetaProblemLead, selectedLead, t])

  const loadRerouteVacancies = useCallback(async () => {
    setVacanciesLoading(true)
    setVacanciesError(null)
    try {
      const res = await listVacancies({ limit: 200, offset: 0 })
      const items = Array.isArray((res as any)?.items)
        ? (res as any).items
        : Array.isArray(res as any)
          ? (res as any)
          : []
      const normalized = items
        .map((v: any) => ({
          id: String(v?.id ?? ''),
          title: String(v?.title ?? v?.vacancy_title ?? ''),
        }))
        .filter((v: any) => v.id && v.title)
      setVacancyOptions(normalized)
    } catch (err: any) {
      setVacanciesError(String(err?.response?.data?.detail ?? err?.message ?? 'Failed to load vacancies'))
      notify({
        title: t('app.vacancies.load_failed', { defaultValue: 'Failed to load vacancies' }),
        description: String(err?.response?.data?.detail ?? err?.message ?? 'Failed to load vacancies'),
        variant: 'error',
      })
    } finally {
      setVacanciesLoading(false)
    }
  }, [listVacancies, notify, t])

  useEffect(() => {
    const needsVacancies = panelTab === 'fix' && selectedIsMetaProblemLead && selectedLeadSuggestion?.tab === 'mapping'
    if (!needsVacancies) return
    if (vacancyOptions.length > 0) return
    if (vacanciesLoading) return
    void loadRerouteVacancies()
  }, [panelTab, selectedIsMetaProblemLead, selectedLeadSuggestion?.tab, vacancyOptions.length, vacanciesLoading, loadRerouteVacancies])

  useEffect(() => {
    const shouldReset = panelTab === 'fix' && selectedIsMetaProblemLead && selectedLeadSuggestion?.tab === 'mapping'
    if (!shouldReset) return
    const pre = selectedLead?.vacancy_id ? String(selectedLead.vacancy_id) : ''
    setRerouteVacancyId(pre)
  }, [panelTab, selectedIsMetaProblemLead, selectedLeadSuggestion?.tab, selectedLeadId, selectedLead])

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
  const nextActionOptions = useMemo<Array<{ value: '' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'; label: string }>>(
    () =>
      NEXT_ACTION_FILTERS.map((value) => ({
        value,
        label:
          value === ''
            ? t('common.filters.all', { defaultValue: 'All' })
            : value === 'no_next_action'
            ? t('app.leads.next_action.no_next_action', { defaultValue: 'No next action' })
            : value === 'overdue'
            ? t('app.leads.next_action.overdue', { defaultValue: 'Overdue' })
            : value === 'stuck'
            ? t('app.leads.next_action.stuck', { defaultValue: 'Stuck' })
            : t('app.leads.next_action.scheduled', { defaultValue: 'Scheduled' }),
      })),
    [t],
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

  useEffect(() => {
    if (panelTab === 'history' && selectedLeadId) {
      void loadLeadTimeline(selectedLeadId)
    }
  // Intentionally omit `loadLeadTimeline` to avoid TDZ at render-time.
  // The callback is executed after component initialization.
  }, [panelTab, selectedLeadId])
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
        await createActivity({
        title: reminderTitle,
        description: '',
        type: 'custom',
        entity_type: 'lead',
        entity_id: selectedLeadId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
          source: 'manual',
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
        await completeActivity(id)
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

  const loadLeadTimeline = useCallback(
    async (leadId: string) => {
      setTimelineLoading(true)
      setTimelineError(null)
      try {
        const res = await getLeadTimeline(leadId)
        const items = Array.isArray(res?.items) ? res.items : []
        setTimelineItems(
          items.map((item: any) => ({
            at: item.at,
            kind: String(item.kind || ''),
            source: String(item.source || ''),
            title: item.title,
            description: item.description,
          })),
        )
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed'
        setTimelineError(String(detail))
      } finally {
        setTimelineLoading(false)
      }
    },
    [],
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

  const handleProcessLead = useCallback(
    async (leadId: string) => {
      setProcessingLeadId(leadId)
      try {
        const result = await processLead(leadId)
        await loadLeads(offset)
        if (result?.status === 'needs_routing') {
          notify({
            title: t('app.leads.messages.needs_routing', { defaultValue: 'Lead needs routing' }),
            description:
              typeof result?.error === 'string' && result.error.trim()
                ? result.error
                : t('app.leads.messages.needs_routing_desc', {
                    defaultValue: 'Please choose a vacancy (or re-route the lead) to continue.',
                  }),
            variant: 'success',
          })
        } else if (result?.status === 'processed' || result?.status === 'duplicated') {
          notify({
            title: t('app.leads.messages.processed', { defaultValue: 'Lead processed' }),
            description: t('app.leads.messages.processed_desc', { defaultValue: 'Lead was processed and routed.' }),
            variant: 'success',
          })
        } else if (result?.status === 'failed') {
          notify({
            title: t('app.leads.messages.process_failed', { defaultValue: 'Failed to process lead' }),
            description:
              typeof result?.error === 'string' && result.error.trim()
                ? result.error
                : t('app.leads.messages.process_failed', { defaultValue: 'Try again.' }),
            variant: 'error',
          })
        } else {
          notify({
            title: t('app.leads.messages.processed', { defaultValue: 'Lead processed' }),
            description: t('app.leads.messages.processed_desc', { defaultValue: 'Lead was processed.' }),
            variant: 'success',
          })
        }
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.process_failed', {
            defaultValue: 'Failed to process lead',
          })
        notify({
          title: t('app.leads.messages.process_failed', { defaultValue: 'Failed to process lead' }),
          description: typeof detail === 'string' ? detail : JSON.stringify(detail),
          variant: 'error',
        })
      } finally {
        setProcessingLeadId(null)
      }
    },
    [loadLeads, notify, offset, t],
  )

  const handleRetryMetaLead = useCallback(
    async (leadId: string) => {
      setRetryingLeadId(leadId)
      try {
        const result = await retryLeads({ lead_ids: [String(leadId)], refresh_graph: true })
        const item = result.items?.[0]
        if (item?.processed) {
          notify({
            title: t('app.leads.messages.processed', { defaultValue: 'Lead processed' }),
            variant: 'success',
          })
        } else if (item?.message) {
          notify({
            title: t('app.leads.messages.process_failed', { defaultValue: 'Failed to process lead' }),
            description: item.message,
            variant: 'error',
          })
        } else {
          notify({
            title: t('app.leads.messages.process_failed', { defaultValue: 'Failed to process lead' }),
            variant: 'error',
          })
        }
        await loadLeads(offset)
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
        notify({
          title: t('app.admin.meta_leads.errors.retry', { defaultValue: 'Retry failed' }),
          description: String(detail),
          variant: 'error',
        })
      } finally {
        setRetryingLeadId(null)
      }
    },
    [loadLeads, notify, offset, t],
  )

  const handleRerouteSelectedLead = useCallback(async () => {
    if (!selectedLead) return
    if (!rerouteVacancyId.trim()) return
    setReroutingLeadId(selectedLead.id)
    try {
      await rerouteMetaLead(selectedLead.id, {
        vacancy_id: rerouteVacancyId.trim() as any,
        company_id: (selectedLead.company_id as any) || undefined,
        force_process: true,
      })
      notify({
        title: t('app.admin.meta_leads.notices.lead_rerouted', { defaultValue: 'Lead sent for processing' }),
        variant: 'success',
      })
      await loadLeads(offset)
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Reroute failed'
      notify({
        title: t('app.admin.meta_leads.errors.reroute', { defaultValue: 'Could not reroute lead' }),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setReroutingLeadId(null)
    }
  }, [selectedLead, rerouteVacancyId, rerouteMetaLead, notify, t, loadLeads, offset])

  const handleRerouteMetaLeadFromError = useCallback(
    (leadId: string, _leadCompanyId?: string) => {
      // No `window.prompt`: we open Fix tab where user can pick vacancy from dropdown.
      setSelectedLeadId(leadId)
      setPanelTab('fix')
    },
    [],
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
    <div className="flex min-h-0 w-full flex-1 flex-col space-y-0 gap-0">
      <header className="rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white px-3 py-2.5 shadow-none">
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
          <label className="min-w-[190px] text-xs font-medium text-slate-600">
            <span className="mb-1 inline-flex items-center gap-1">
              <IconFilter size={12} />
              {t('app.leads.filters.next_action', { defaultValue: 'Next action' })}
            </span>
            <select
              className="input h-9 rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              value={nextAction}
              onChange={(event) => {
                setNextAction(event.target.value as any)
                setPage(1)
              }}
            >
              {nextActionOptions.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
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

      {drilldownInfo.hasFilters && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-700">
              <span className="font-medium">{t('app.leads.inbox.banner.filtered', { defaultValue: 'Filtered leads:' })}</span>{' '}
              {[
                drilldownInfo.status ? statusLabels[drilldownInfo.status as any] ?? drilldownInfo.status : null,
                drilldownInfo.stage ? stageLabels[drilldownInfo.stage as any] ?? drilldownInfo.stage : null,
                drilldownInfo.nextAction
                  ? nextActionOptions.find((o) => o.value === (drilldownInfo.nextAction as any))?.label ?? drilldownInfo.nextAction
                  : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </div>
            <button
              type="button"
              className="btn-secondary h-8 rounded-lg px-2 text-xs"
              onClick={() => resetDrilldown()}
            >
              {t('app.leads.inbox.banner.reset', { defaultValue: 'All leads' })}
            </button>
          </div>
        </div>
      )}

      <section className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {selectedCount > 0 && (
            <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700 flex flex-wrap items-center gap-2">
              <div className="font-medium">
                {t('app.leads.bulk.selected', { defaultValue: 'Selected: {{count}}', values: { count: selectedCount } })}
              </div>
              <select
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                value={bulkStage}
                onChange={(e) => setBulkStage(e.target.value as any)}
                disabled={bulkUpdating}
              >
                <option value="">{t('app.leads.bulk.stage', { defaultValue: 'Set stage…' })}</option>
                {STAGE_FILTERS.filter((s) => s).map((s) => (
                  <option key={s} value={s}>
                    {String(s)}
                  </option>
                ))}
              </select>
              <select
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value as any)}
                disabled={bulkUpdating}
              >
                <option value="">{t('app.leads.bulk.status', { defaultValue: 'Set status…' })}</option>
                {STATUS_FILTERS.filter((s) => s).map((s) => (
                  <option key={s} value={s}>
                    {String(s)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-secondary rounded-lg px-2.5 py-1 text-xs"
                onClick={() => void doBulkUpdateLeads()}
                disabled={bulkUpdating || (!bulkStage && !bulkStatus)}
              >
                {bulkUpdating ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.leads.bulk.apply', { defaultValue: 'Apply' })}
              </button>
              {selectedMetaProblemLeadIds.length > 0 && (
                <button
                  type="button"
                  className="btn-secondary rounded-lg px-2.5 py-1 text-xs"
                  onClick={() => void doBulkRetryMetaLeads()}
                  disabled={bulkRetryingMetaLeads}
                >
                  {bulkRetryingMetaLeads
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.leads.bulk.retry_meta', {
                        defaultValue: 'Retry meta errors ({{count}})',
                        values: { count: selectedMetaProblemLeadIds.length },
                      })}
                </button>
              )}
              <button
                type="button"
                className="btn-secondary rounded-lg px-2.5 py-1 text-xs"
                onClick={() => {
                  setBulkActivityTitle(t('app.leads.bulk.activities.default_title', { defaultValue: 'Follow up' }))
                  setBulkActivityDueAt(new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
                  setBulkActivityOffsetMinutes(60)
                  setBulkActivitiesOpen(true)
                }}
              >
                {t('app.leads.bulk.activities.action', { defaultValue: 'Create activity' })}
              </button>
              <button type="button" className="btn-secondary rounded-lg px-2.5 py-1 text-xs" onClick={() => setChecked({})}>
                {t('app.leads.bulk.clear', { defaultValue: 'Clear' })}
              </button>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="table min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="w-[44px]">
                    <input
                      type="checkbox"
                      checked={items.length > 0 && items.every((l) => checked[l.id])}
                      onChange={(e) => {
                        const next: Record<string, boolean> = {}
                        if (e.target.checked) {
                          items.forEach((l) => (next[l.id] = true))
                        }
                        setChecked(next)
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </th>
                  <th>{t('app.leads.table.created')}</th>
                  <th>{t('app.leads.table.status')}</th>
                  <th>{t('app.leads.table.stage', { defaultValue: 'Stage' })}</th>
                  <th>{t('app.leads.table.next_action', { defaultValue: 'Next action' })}</th>
                  <th>{companyColumnLabel}</th>
                  <th>{vacancyColumnLabel}</th>
                  <th>{t('app.leads.table.contact')}</th>
                  <th>{t('app.leads.table.source')}</th>
                  <th>{t('app.leads.table.fit', { defaultValue: 'Fit' })}</th>
                  <th>{ownerColumnLabel}</th>
                  <th>{t('app.leads.table.error')}</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={12} className="px-3 py-5 text-center text-slate-500">
                      {t('common.loading')}
                    </td>
                  </tr>
                )}
                {error && !loading && (
                  <tr>
                    <td colSpan={12} className="px-3 py-4">
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
                    <td colSpan={12} className="px-3 py-6">
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
                          to: '/app/clients/directory',
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
                    const metaSource = String(lead.source || '').toLowerCase() === 'meta'
                    const metaErrorCode = (lead.error ?? '').trim()
                    const isMetaProblemLead =
                      metaSource && metaErrorCode.length > 0 && (lead.status === 'failed' || lead.status === 'needs_routing')
                    const leadSuggestion = isMetaProblemLead ? getLeadErrorSuggestion(lead.error, t) : null
                    const openCredentialsHref = '/app/settings/integrations?tab=credentials'
                    const openMappingHref = '/app/settings/integrations?tab=mapping'
                    const openSettingsHref = '/app/settings/integrations?tab=settings'
                    const fitStatus = (lead as any).fit_status as string | undefined
                    const fitReasons = Array.isArray((lead as any).fit_reasons) ? ((lead as any).fit_reasons as string[]) : []
                    const fitLabel =
                      fitStatus === 'fit'
                        ? 'Fit'
                        : fitStatus === 'no_fit'
                          ? 'No fit'
                          : fitStatus === 'needs_info'
                            ? 'Needs info'
                            : '—'
                    const fitClass =
                      fitStatus === 'fit'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : fitStatus === 'no_fit'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : fitStatus === 'needs_info'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-slate-50 text-slate-600 border-slate-200'

                    return (
                      <tr
                        key={lead.id}
                        className={isSelected ? 'bg-brand-50 hover:bg-brand-50' : 'hover:bg-slate-50'}
                        role="button"
                        tabIndex={0}
                        onClick={() => {
                          setSelectedLeadId(lead.id)
                          setPanelTab(isMetaProblemLead ? 'fix' : 'composer')
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedLeadId(lead.id)
                            setPanelTab(isMetaProblemLead ? 'fix' : 'composer')
                          }
                        }}
                      >
                        <td onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={!!checked[lead.id]}
                            onChange={() => toggleChecked(lead.id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
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
                        <td>
                          {lead.next_action_status === 'overdue' ? (
                            <div className="flex flex-col items-start gap-0.5">
                              <span className="inline-flex items-center rounded-md bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-800">
                                {t('app.leads.next_action.overdue', { defaultValue: 'Overdue' })}
                              </span>
                              {lead.next_action_due_at ? (
                                <span className="text-[11px] text-rose-700">{formatDateValue(lead.next_action_due_at)}</span>
                              ) : null}
                            </div>
                          ) : lead.next_action_status === 'scheduled' ? (
                            <div className="flex flex-col items-start gap-0.5">
                              <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                                {t('app.leads.next_action.scheduled', { defaultValue: 'Scheduled' })}
                              </span>
                              {lead.next_action_due_at ? (
                                <span className="text-[11px] text-slate-600">{formatDateValue(lead.next_action_due_at)}</span>
                              ) : null}
                            </div>
                          ) : (
                            <span className="inline-flex items-center rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                              {t('app.leads.next_action.no_next_action', { defaultValue: 'No next action' })}
                            </span>
                          )}
                        </td>
                        <td className="text-slate-800">{lead.company_name || lead.company_id}</td>
                        <td className="text-slate-800">{lead.vacancy_title || lead.vacancy_id || '—'}</td>
                        <td className="text-slate-700">{contact || '—'}</td>
                        <td className="text-slate-700">{lead.source}</td>
                        <td className="text-slate-700">
                          <span
                            className={['inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold', fitClass].join(' ')}
                            title={fitReasons.length ? fitReasons.join('\n') : ''}
                          >
                            {fitLabel}
                          </span>
                        </td>
                        <td className="text-brand-700">
                          {isMetaProblemLead ? (
                            <div className="flex flex-col items-start gap-1">
                              <div className="text-xs text-red-500">{metaErrorCode}</div>
                              <div className="flex flex-wrap items-center gap-2">
                                <button
                                  type="button"
                                  className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                  disabled={retryingLeadId === lead.id}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    void handleRetryMetaLead(lead.id)
                                  }}
                                >
                                  {retryingLeadId === lead.id
                                    ? t('common.loading', { defaultValue: 'Loading...' })
                                    : t('app.admin.meta_leads.logs.actions.retry', { defaultValue: 'Retry' })}
                                </button>

                                {leadSuggestion?.tab === 'mapping' ? (
                                  <>
                                    <button
                                      type="button"
                                      className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        void handleRerouteMetaLeadFromError(lead.id, lead.company_id)
                                      }}
                                    >
                                      {t('app.admin.meta_leads.logs.actions.reroute', { defaultValue: 'Reroute' })}
                                    </button>
                                    <Link
                                      to={openMappingHref}
                                      className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {t('app.admin.meta_leads.tabs.mapping', { defaultValue: 'Mapping' })}
                                    </Link>
                                  </>
                                ) : null}

                                {leadSuggestion?.tab === 'credentials' ? (
                                  <Link
                                    to={openCredentialsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('app.admin.meta_leads.tabs.credentials', { defaultValue: 'Credentials' })}
                                  </Link>
                                ) : null}

                                {leadSuggestion?.tab === 'settings' ? (
                                  <Link
                                    to={openSettingsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('app.admin.meta_leads.tabs.settings', { defaultValue: 'Settings' })}
                                  </Link>
                                ) : null}
                              </div>
                            </div>
                          ) : isServicesTenant ? (
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
                                    to={serviceOrderWorkspacePath(String(lead.service_order_id), lead.company_id)}
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
                            <div className="flex items-center gap-2">
                              <span>—</span>
                              {String(lead.source || '').toLowerCase() === 'meta' ? (
                                <button
                                  type="button"
                                  className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                  disabled={processingLeadId === lead.id}
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    void handleProcessLead(lead.id)
                                  }}
                                >
                                  {processingLeadId === lead.id
                                    ? t('common.loading', { defaultValue: 'Loading...' })
                                    : t('app.leads.actions.process', { defaultValue: 'Process' })}
                                </button>
                              ) : null}
                            </div>
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

        <BulkActivitiesModal
          open={bulkActivitiesOpen}
          onClose={() => !bulkActivitiesLoading && setBulkActivitiesOpen(false)}
          title={bulkActivityTitle}
          dueAt={bulkActivityDueAt}
          offsetMinutes={bulkActivityOffsetMinutes}
          onTitleChange={setBulkActivityTitle}
          onDueAtChange={setBulkActivityDueAt}
          onOffsetMinutesChange={setBulkActivityOffsetMinutes}
          onApply={doBulkActivities}
          loading={bulkActivitiesLoading}
          activityType={bulkActivityType}
          onActivityTypeChange={setBulkActivityType}
        />

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
                  {selectedIsMetaProblemLead && (
                    <button
                      type="button"
                      className={panelTab === 'fix' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                      onClick={() => setPanelTab('fix')}
                    >
                      {t('app.leads.inbox.tabs.fix', { defaultValue: 'Fix' })}
                    </button>
                  )}
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
                {panelTab === 'fix' && selectedLead && selectedIsMetaProblemLead && (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                      <div className="text-xs font-semibold text-rose-700">
                        {t('app.leads.inbox.fix.title', { defaultValue: 'Fix / Troubleshoot' })}
                      </div>
                      <div className="mt-1 text-xs text-red-500">{(selectedLead.error ?? '').trim() || '—'}</div>
                      {selectedLeadSuggestion?.hint ? (
                        <div className="mt-2 text-sm text-slate-800">{selectedLeadSuggestion.hint}</div>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="btn-primary rounded-lg px-2 py-1 text-[11px] disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={retryingLeadId === selectedLead.id}
                        onClick={() => void handleRetryMetaLead(selectedLead.id)}
                      >
                        {retryingLeadId === selectedLead.id
                          ? t('common.loading', { defaultValue: 'Loading...' })
                          : t('app.admin.meta_leads.logs.actions.retry', { defaultValue: 'Retry' })}
                      </button>

                      <Link
                        to="/app/automations"
                        className="text-[11px] text-slate-500 hover:text-brand-700 hover:underline"
                      >
                        {t('app.admin.meta_leads.tabs.automation_rules', { defaultValue: 'Automation Rules' })}
                      </Link>
                    </div>

                    {selectedLeadSuggestion?.tab === 'mapping' ? (
                      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
                        <div className="text-xs font-semibold text-slate-700">
                          {t('app.admin.meta_leads.logs.actions.reroute', { defaultValue: 'Reroute' })}
                        </div>

                        {vacanciesError ? (
                          <div className="text-xs text-rose-600">{vacanciesError}</div>
                        ) : null}

                        <label className="text-xs font-medium text-slate-600">
                          <div className="mb-1">{t('app.admin.meta_leads.logs.table.vacancy', { defaultValue: 'Vacancy' })}</div>
                          <select
                            className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                            value={rerouteVacancyId}
                            onChange={(e) => setRerouteVacancyId(e.target.value)}
                            disabled={vacanciesLoading}
                          >
                            <option value="">
                              {vacanciesLoading
                                ? t('common.loading', { defaultValue: 'Loading...' })
                                : t('app.admin.meta_leads.prompts.reroute_vacancy', { defaultValue: 'Select vacancy_id' })}
                            </option>
                            {vacancyOptions.map((v) => (
                              <option key={v.id} value={v.id}>
                                {v.title}
                              </option>
                            ))}
                          </select>
                        </label>

                        {vacancyOptions.length === 0 && !vacanciesLoading ? (
                          <Link
                            to="/app/vacancies"
                            className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                          >
                            {t('app.vacancies.actions.create', { defaultValue: 'Create vacancy' })}
                          </Link>
                        ) : null}

                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            className="btn-primary rounded-lg px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={!rerouteVacancyId || reroutingLeadId === selectedLead.id || vacanciesLoading}
                            onClick={() => void handleRerouteSelectedLead()}
                          >
                            {reroutingLeadId === selectedLead.id
                              ? t('common.loading', { defaultValue: 'Routing...' })
                              : t('app.admin.meta_leads.logs.actions.reroute', { defaultValue: 'Reroute' })}
                          </button>
                        </div>
                      </div>
                    ) : null}

                    {selectedLeadSuggestion ? (
                      <div className="flex flex-wrap items-center gap-2">
                        {selectedLeadSuggestion.tab === 'credentials' ? (
                          <Link
                            to="/app/settings/integrations?tab=credentials"
                            className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                          >
                            {selectedLeadSuggestion.actionLabel}
                          </Link>
                        ) : null}
                        {selectedLeadSuggestion.tab === 'mapping' ? (
                          <Link
                            to="/app/settings/integrations?tab=mapping"
                            className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                          >
                            {selectedLeadSuggestion.actionLabel}
                          </Link>
                        ) : null}
                        {selectedLeadSuggestion.tab === 'settings' ? (
                          <Link
                            to="/app/settings/integrations?tab=settings"
                            className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                          >
                            {selectedLeadSuggestion.actionLabel}
                          </Link>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )}
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
                      </div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-white p-3">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-semibold text-slate-700">
                          {t('app.leads.inbox.history.timeline_title', { defaultValue: 'Timeline' })}
                        </div>
                        <button
                          type="button"
                          className="btn-secondary h-7 rounded-lg px-2 text-[11px]"
                          onClick={() => selectedLeadId && void loadLeadTimeline(selectedLeadId)}
                        >
                          {t('common.actions.refresh', { defaultValue: 'Refresh' })}
                        </button>
                      </div>
                      {timelineLoading ? (
                        <div className="py-3 text-center text-[11px] text-slate-500">{t('common.loading')}</div>
                      ) : timelineError ? (
                        <div className="mt-2 rounded border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-700">
                          {timelineError}
                        </div>
                      ) : timelineItems.length === 0 ? (
                        <div className="mt-2 rounded border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-500">
                          {t('app.leads.inbox.history.empty', { defaultValue: 'No events yet.' })}
                        </div>
                      ) : (
                        <ul className="mt-2 space-y-1.5">
                          {timelineItems.map((ev, idx) => (
                            <li key={`${ev.at}-${ev.kind}-${idx}`} className="flex items-start gap-2">
                              <div className="mt-[3px] h-1.5 w-1.5 rounded-full bg-slate-400" />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="truncate text-[11px] font-medium text-slate-800">
                                    {ev.title || ev.kind || t('app.leads.inbox.history.event', { defaultValue: 'Event' })}
                                  </div>
                                  <div className="shrink-0 text-[10px] text-slate-500">{formatDateValue(ev.at)}</div>
                                </div>
                                {ev.description ? (
                                  <div className="mt-0.5 text-[11px] text-slate-600 truncate">{ev.description}</div>
                                ) : null}
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
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
