import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { IconExternalLink, IconFilter, IconRefresh, IconSearch, IconTable } from '@tabler/icons-react'

import {
  completeActivity,
  createActivity,
  createInvoiceFromServiceOrder,
  createLeadServiceOrder,
  bulkUpdateLeads,
  getLeadTimeline,
  getOnboardingStatus,
  listLeads,
  listReminders,
  processLead,
  updateLeadStage,
  type OnboardingStatus,
} from '../api/client'
import { retryLeads } from '../api/metaLeads'
import type { Lead, LeadListResponse, LeadStatus, LeadStage } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
import { recordPerfMeasurement } from '../api/analytics'
import { useI18n } from '../i18n'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { NbaNextActionsChips } from '../components/nba/NbaNextActionsChips'
import { useNbaQuickBulkFlow } from '../components/nba/useNbaQuickBulkFlow'
import { BulkActivitiesModal } from '../modules/candidates/components'
import { useToast } from '../components/Toast'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import {
  fetchLeadConversionFunnel,
  type LeadConversionFunnelResponse,
  type LeadConversionFunnelSliceQuery,
} from '../api/leadConversionFunnel'
import { fetchLeadStageHealth, type LeadStageHealthResponse } from '../api/leadStageHealth'
import { fetchLeadNextActions, leadsNextActionHref, type LeadNextActionsResponse } from '../api/nextActions'
import { getLeadErrorSuggestion } from '../utils/leadErrorSuggestion'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { serviceOrderWorkspacePath } from '../modules/services/utils'
import { listCustomFieldDefinitions, type CustomFieldDefinition } from '../api/custom_fields'
import LeadMetaProblemPanel from '../components/leads/LeadMetaProblemPanel'
import LeadNextActionPlaybook from '../components/leads/LeadNextActionPlaybook'
import LeadLostReasonReadonly from '../components/leads/LeadLostReasonReadonly'
import LostReasonForLostStageModal from '../components/leads/LostReasonForLostStageModal'
import { ActiveOwnCompanyBadge } from '../components/shell/ActiveOwnCompanyBadge'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { CRM_STAGE_VALUES, isMetaProblemLead, leadAssignmentLocked } from '../utils/leadCrm'

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

function leadSearchFromSearchString(search: string): string {
  try {
    return (new URLSearchParams(search || '').get('q') || '').trim()
  } catch {
    return ''
  }
}

function initialLeadSearchFromLocation(): string {
  if (typeof window === 'undefined') return ''
  return leadSearchFromSearchString(window.location.search)
}

export default function LeadsPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const { entitySingular, openEntityLabel } = useBusinessTerminology()
  const location = useLocation()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'' | LeadStatus>('')
  const [stage, setStage] = useState<'' | LeadStage>('')
  const [nextAction, setNextAction] = useState<'' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'>('')
  const [customFieldKey, setCustomFieldKey] = useState('')
  const [customFieldValue, setCustomFieldValue] = useState('')
  const [leadSearch, setLeadSearch] = useState(initialLeadSearchFromLocation)
  const [leadCustomFieldDefs, setLeadCustomFieldDefs] = useState<CustomFieldDefinition[]>([])
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
  const [patchingLeadId, setPatchingLeadId] = useState<string | null>(null)

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
    return data.items.filter((l) => checked[l.id]).filter((lead) => isMetaProblemLead(lead)).map((l) => l.id)
  }, [checked, data.items])
  const toggleChecked = useCallback((id: string) => setChecked((s) => ({ ...s, [id]: !s[id] })), [])

  const [bulkStage, setBulkStage] = useState<'' | LeadStage>('')
  const [bulkStatus, setBulkStatus] = useState<'' | LeadStatus>('')
  const [bulkUpdating, setBulkUpdating] = useState(false)
  const [leadNba, setLeadNba] = useState<LeadNextActionsResponse | null>(null)
  const [leadStageHealth, setLeadStageHealth] = useState<LeadStageHealthResponse | null>(null)
  const [leadConversionFunnel, setLeadConversionFunnel] = useState<LeadConversionFunnelResponse | null>(
    null,
  )
  const [funnelSliceDraft, setFunnelSliceDraft] = useState({
    source: '',
    vacancyId: '',
    funnelId: '',
    assigneeUserId: '',
  })
  const [funnelSliceQuery, setFunnelSliceQuery] = useState<LeadConversionFunnelSliceQuery>({})
  const [lostStagePrompt, setLostStagePrompt] = useState<{ leadId: string; previousStage: string | null } | null>(
    null,
  )
  const [bulkLostModalOpen, setBulkLostModalOpen] = useState(false)

  useEffect(() => {
    if (lostStagePrompt && selectedLeadId && lostStagePrompt.leadId !== selectedLeadId) {
      setLostStagePrompt(null)
    }
  }, [lostStagePrompt, selectedLeadId])

  const applyFunnelSlices = useCallback(() => {
    const next: LeadConversionFunnelSliceQuery = {}
    if (funnelSliceDraft.source.trim()) next.source = funnelSliceDraft.source.trim()
    if (funnelSliceDraft.vacancyId.trim()) next.vacancyId = funnelSliceDraft.vacancyId.trim()
    if (funnelSliceDraft.funnelId.trim()) next.funnelId = funnelSliceDraft.funnelId.trim()
    if (funnelSliceDraft.assigneeUserId.trim()) next.assigneeUserId = funnelSliceDraft.assigneeUserId.trim()
    setFunnelSliceQuery(next)
  }, [funnelSliceDraft])

  const clearFunnelSlices = useCallback(() => {
    setFunnelSliceDraft({ source: '', vacancyId: '', funnelId: '', assigneeUserId: '' })
    setFunnelSliceQuery({})
  }, [])

  const refreshLeadInsights = useCallback(() => {
    void fetchLeadNextActions()
      .then((r) => setLeadNba(r))
      .catch(() => setLeadNba(null))
    void fetchLeadStageHealth()
      .then((r) => setLeadStageHealth(r))
      .catch(() => setLeadStageHealth(null))
    const hasSlices = Boolean(
      funnelSliceQuery.source?.trim() ||
        funnelSliceQuery.vacancyId?.trim() ||
        funnelSliceQuery.funnelId?.trim() ||
        funnelSliceQuery.assigneeUserId?.trim(),
    )
    void fetchLeadConversionFunnel(hasSlices ? funnelSliceQuery : null)
      .then((r) => setLeadConversionFunnel(r))
      .catch((err: any) => {
        const detail = err?.response?.data?.detail
        if (detail && typeof detail === 'object' && detail.code === 'plan_requires_team') {
          notify({
            title: t('app.leads.conversion_funnel.slices_team_required_title'),
            description: t('app.leads.conversion_funnel.slices_team_required_desc'),
            variant: 'error',
          })
        }
        setLeadConversionFunnel(null)
      })
  }, [funnelSliceQuery, notify, t])

  useEffect(() => {
    refreshLeadInsights()
  }, [refreshLeadInsights])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const defs = await listCustomFieldDefinitions({ scope: 'LEAD', is_active: true })
        if (!cancelled) setLeadCustomFieldDefs(defs)
      } catch {
        if (!cancelled) setLeadCustomFieldDefs([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const limit = 20
  const offset = (page - 1) * limit
  /** Last `q` we wrote to the URL (or loaded initially); avoids wiping in-progress input when we strip `q` for short queries. */
  const lastCommittedUrlQRef = useRef(leadSearchFromSearchString(typeof window !== 'undefined' ? window.location.search : ''))
  const prevExternalUrlQRef = useRef<string | null>(null)

  // Apply `?q=` from the URL when it changes without our debounced write (back/forward, external links).
  useEffect(() => {
    const nextQ = leadSearchFromSearchString(location.search || '')
    if (nextQ === lastCommittedUrlQRef.current) {
      prevExternalUrlQRef.current = nextQ
      return
    }
    lastCommittedUrlQRef.current = nextQ
    setLeadSearch(nextQ)
    if (prevExternalUrlQRef.current !== null && prevExternalUrlQRef.current !== nextQ) {
      setPage(1)
    }
    prevExternalUrlQRef.current = nextQ
  }, [location.search])

  // Drill-down support: /app/leads?status=needs_routing&stage=qualified
  useEffect(() => {
    const sp = new URLSearchParams(location.search || '')
    const nextStatus = (sp.get('status') || '').trim()
    const nextStage = (sp.get('stage') || '').trim()
    const nextNextAction = (sp.get('next_action') || '').trim()
    const nextCfKey = (sp.get('custom_field_key') || '').trim()
    const hasCfValParam = sp.has('custom_field_value')
    const nextCfVal = hasCfValParam ? sp.get('custom_field_value') ?? '' : null
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
    if (nextCfKey && hasCfValParam && nextCfVal !== null) {
      if (nextCfKey !== customFieldKey) setCustomFieldKey(nextCfKey)
      if (nextCfVal !== customFieldValue) setCustomFieldValue(nextCfVal)
      setPage(1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search])

  useEffect(() => {
    const id = window.setTimeout(() => {
      const sp = new URLSearchParams(location.search || '')
      const t = leadSearch.trim()
      const targetUrlQ = t.length >= 2 ? t : ''
      if (targetUrlQ) sp.set('q', targetUrlQ)
      else sp.delete('q')
      const next = sp.toString()
      const cur = (location.search || '').replace(/^\?/, '')
      lastCommittedUrlQRef.current = targetUrlQ
      if (next !== cur) {
        navigate({ pathname: CRM_APP_PATHS.leads, search: next ? `?${next}` : '' }, { replace: true })
      }
    }, 400)
    return () => window.clearTimeout(id)
  }, [leadSearch, location.search, navigate])

  const filterBannerVisible = Boolean(
    status || stage || nextAction || customFieldKey.trim() || leadSearch.trim().length >= 2,
  )

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
          q: leadSearch.trim().length >= 2 ? leadSearch.trim() : undefined,
          ...(customFieldKey.trim()
            ? { customFieldKey: customFieldKey.trim(), customFieldValue }
            : {}),
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
          meta: {
            ok: perfOk,
            status: status || null,
            stage: stage || null,
            next_action: nextAction || null,
            custom_field_key: customFieldKey.trim() || null,
            q: leadSearch.trim().length >= 2 ? leadSearch.trim() : null,
            limit,
            offset: nextOffset,
          },
        }).catch(() => {})
        setLoading(false)
      }
    },
    [customFieldKey, customFieldValue, leadSearch, limit, nextAction, offset, stage, status, t],
  )

  const handleNbaBulkSuccess = useCallback(async () => {
    void refreshLeadInsights()
    await loadLeads(offset)
  }, [refreshLeadInsights, loadLeads, offset])

  const clearLeadSelection = useCallback(() => setChecked({}), [])

  const nbaBulk = useNbaQuickBulkFlow({
    onNbaSuccess: handleNbaBulkSuccess,
    onSelectionSuccess: clearLeadSelection,
  })

  const resetDrilldown = useCallback(() => {
    setStatus('')
    setStage('')
    setNextAction('')
    setCustomFieldKey('')
    setCustomFieldValue('')
    setLeadSearch('')
    lastCommittedUrlQRef.current = ''
    setPage(1)
    setSelectedLeadId(null)
    navigate(CRM_APP_PATHS.leads, { replace: true })
    // Let state updates apply before re-loading the first page.
    setTimeout(() => {
      void loadLeads(0)
    }, 0)
  }, [loadLeads, navigate])

  const runBulkUpdateLeads = useCallback(
    async (lost?: { lost_reason_code: string; lost_reason_note: string }) => {
      const ids = allSelectedLeadIds
      if (ids.length === 0) return
      if (!bulkStage && !bulkStatus) return
      setBulkUpdating(true)
      try {
        await bulkUpdateLeads({
          lead_ids: ids,
          stage: bulkStage || null,
          status: bulkStatus || null,
          ...(bulkStage === 'lost' && lost
            ? {
                lost_reason_code: lost.lost_reason_code,
                lost_reason_note: lost.lost_reason_note || undefined,
              }
            : {}),
        })
        await loadLeads(offset)
        refreshLeadInsights()
        notify({
          title: t('app.leads.bulk.updated'),
          description: `${ids.length}`,
          variant: 'success',
        })
        setChecked({})
        setBulkStage('')
        setBulkStatus('')
        setBulkLostModalOpen(false)
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed'
        notify({
          title: t('app.leads.bulk.update_failed'),
          description: String(detail),
          variant: 'error',
        })
      } finally {
        setBulkUpdating(false)
      }
    },
    [allSelectedLeadIds, bulkStage, bulkStatus, loadLeads, notify, offset, refreshLeadInsights, t],
  )

  const doBulkUpdateLeads = useCallback(() => {
    if (bulkStage === 'lost') {
      setBulkLostModalOpen(true)
      return
    }
    void runBulkUpdateLeads()
  }, [bulkStage, runBulkUpdateLeads])

  const confirmBulkLostReason = useCallback(
    (p: { lost_reason_code: string; lost_reason_note: string }) => {
      void runBulkUpdateLeads(p)
    },
    [runBulkUpdateLeads],
  )

  const doBulkRetryMetaLeads = useCallback(async () => {
    const ids = selectedMetaProblemLeadIds
    if (!ids.length) return

    setBulkRetryingMetaLeads(true)
    try {
      const result = await retryLeads({ lead_ids: ids, refresh_graph: true })

      if (result.processed > 0) {
        notify({
          title: t('app.leads.messages.processed'),
          description: `${result.processed} / ${ids.length}`,
          variant: 'success',
        })
      }
      if (result.failed > 0) {
        notify({
          title: t('app.leads.messages.process_failed'),
          description: `${result.failed} failed, ${result.skipped} skipped`,
          variant: 'error',
        })
      }

      await loadLeads(offset)
      setChecked({})
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
      notify({
        title: t('app.admin.meta_leads.errors.retry'),
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
  const leadWorkspaceTitle = isServicesTenant ? t('app.leads.title_services') : t('app.leads.title')
  const leadWorkspaceSubtitle = isServicesTenant ? t('app.leads.subtitle_services') : t('app.leads.subtitle')
  const ownerColumnLabel = isServicesTenant ? t('app.leads.table.client') : t('app.leads.table.candidate')
  const companyColumnLabel = isEmployerTenant ? t('app.dashboard.terms.companies_singular') : entitySingular
  const vacancyColumnLabel = isServicesTenant ? t('app.leads.table.service_order') : t('app.leads.table.vacancy')
  const emptyTitle = isServicesTenant ? t('app.leads.states.empty_title_services') : t('app.leads.states.empty_title')
  const emptyDescription = isServicesTenant ? t('app.leads.states.empty_desc_services') : t('app.leads.states.empty_desc')
  const secondaryEmptyLabel = isServicesTenant ? t('app.leads.states.empty_cta_clients') : openEntityLabel

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

  const applyLeadPatchToList = useCallback((updated: Lead) => {
    setData((d) => ({
      ...d,
      items: d.items.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)),
    }))
  }, [])

  const handleInboxStageChange = useCallback(
    async (nextRaw: string) => {
      if (!selectedLeadId || !selectedLead) return
      const next = (nextRaw || null) as LeadStage | null
      const cur = selectedLead.stage ?? null
      if (String(cur || '') === String(next || '')) return
      setPatchingLeadId(selectedLeadId)
      try {
        const updated = (await updateLeadStage(selectedLeadId, { stage: next })) as Lead
        applyLeadPatchToList(updated)
        notify({
          title: t('app.leads.inbox.stage_updated'),
          variant: 'success',
        })
        await loadLeads(offset)
        refreshLeadInsights()
      } catch (err: unknown) {
        const info = getFriendlyErrorInfo(
          err,
          t('app.leads.detail.stage_update_failed'),
        )
        notify({ title: info.title, description: info.detail || info.hint, variant: 'error' })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [applyLeadPatchToList, loadLeads, notify, offset, refreshLeadInsights, selectedLead, selectedLeadId, t],
  )

  const handleInboxStageSelect = useCallback(
    (nextRaw: string) => {
      if (!selectedLeadId || !selectedLead) return
      const next = nextRaw || ''
      if (next === 'lost') {
        setLostStagePrompt({ leadId: selectedLeadId, previousStage: selectedLead.stage ?? null })
        return
      }
      void handleInboxStageChange(next)
    },
    [handleInboxStageChange, selectedLead, selectedLeadId],
  )

  const cancelLostStagePrompt = useCallback(() => setLostStagePrompt(null), [])

  const confirmLostStageFromModal = useCallback(
    async (p: { lost_reason_code: string; lost_reason_note: string }) => {
      if (!lostStagePrompt) return
      const { leadId } = lostStagePrompt
      setPatchingLeadId(leadId)
      try {
        const updated = (await updateLeadStage(leadId, {
          stage: 'lost',
          lost_reason_code: p.lost_reason_code,
          lost_reason_note: p.lost_reason_note || undefined,
        })) as Lead
        setLostStagePrompt(null)
        applyLeadPatchToList(updated)
        notify({
          title: t('app.leads.inbox.stage_updated'),
          variant: 'success',
        })
        await loadLeads(offset)
        refreshLeadInsights()
      } catch (err: unknown) {
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'))
        notify({ title: info.title, description: info.detail || info.hint, variant: 'error' })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [applyLeadPatchToList, loadLeads, lostStagePrompt, notify, offset, refreshLeadInsights, t],
  )

  const handleInboxAssignmentLockToggle = useCallback(
    async (locked: boolean) => {
      if (!selectedLeadId) return
      setPatchingLeadId(selectedLeadId)
      try {
        const updated = (await updateLeadStage(selectedLeadId, { assignment_locked: locked })) as Lead
        applyLeadPatchToList(updated)
        notify({
          title: t('app.leads.inbox.lock_saved'),
          variant: 'success',
        })
      } catch (err: unknown) {
        const info = getFriendlyErrorInfo(
          err,
          t('app.leads.detail.lock_update_failed'),
        )
        notify({ title: info.title, description: info.detail || info.hint, variant: 'error' })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [applyLeadPatchToList, notify, selectedLeadId, t],
  )
  const selectedIsMetaProblemLead = useMemo(
    () => (selectedLead ? isMetaProblemLead(selectedLead) : false),
    [selectedLead],
  )

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
        label: value ? t(`app.leads.stages.${value}`) : t('app.leads.filters.stage_all'),
      })),
    [t]
  )
  const nextActionOptions = useMemo<Array<{ value: '' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'; label: string }>>(
    () =>
      NEXT_ACTION_FILTERS.map((value) => ({
        value,
        label:
          value === ''
            ? t('common.filters.all')
            : value === 'no_next_action'
            ? t('app.leads.next_action.no_next_action')
            : value === 'overdue'
            ? t('app.leads.next_action.overdue')
            : value === 'stuck'
            ? t('app.leads.next_action.stuck')
            : t('app.leads.next_action.scheduled'),
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
            t('app.reminders.errors.load'),
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
      notify({ title: t('app.reminders.messages.created'), variant: 'success' })
      setPanelTab('focus')
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ??
        err?.message ??
        t('app.reminders.errors.create')
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
          t('app.reminders.errors.complete')
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

  const onMetaProblemPanelRefreshed = useCallback(async () => {
    await loadLeads(offset)
    refreshLeadInsights()
    if (panelTab === 'history' && selectedLeadId) {
      void loadLeadTimeline(selectedLeadId)
    }
  }, [loadLeadTimeline, loadLeads, offset, panelTab, refreshLeadInsights, selectedLeadId])

  const handleCreateServiceOrder = useCallback(
    async (leadId: string) => {
      setCreatingOrderLeadId(leadId)
      try {
        await createLeadServiceOrder(leadId)
        await loadLeads(offset)
        notify({
          title: t('app.leads.messages.service_order_created'),
          description: t('app.leads.messages.service_order_created_desc'),
          variant: 'success',
        })
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.service_order_create_failed')
        notify({
          title: t('app.leads.messages.service_order_create_failed'),
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
        if (panelTab === 'history' && selectedLeadId === leadId) {
          void loadLeadTimeline(leadId)
        }
        if (result?.status === 'needs_routing') {
          notify({
            title: t('app.leads.messages.needs_routing'),
            description:
              typeof result?.error === 'string' && result.error.trim()
                ? result.error
                : t('app.leads.messages.needs_routing_desc'),
            variant: 'success',
          })
        } else if (result?.status === 'processed' || result?.status === 'duplicated') {
          notify({
            title: t('app.leads.messages.processed'),
            description: t('app.leads.messages.processed_desc'),
            variant: 'success',
          })
        } else if (result?.status === 'failed') {
          notify({
            title: t('app.leads.messages.process_failed'),
            description:
              typeof result?.error === 'string' && result.error.trim()
                ? result.error
                : t('app.leads.messages.process_failed_retry_hint'),
            variant: 'error',
          })
        } else {
          notify({
            title: t('app.leads.messages.processed'),
            description: t('app.leads.messages.processed_desc_short'),
            variant: 'success',
          })
        }
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.process_failed')
        notify({
          title: t('app.leads.messages.process_failed'),
          description: typeof detail === 'string' ? detail : JSON.stringify(detail),
          variant: 'error',
        })
      } finally {
        setProcessingLeadId(null)
      }
    },
    [loadLeadTimeline, loadLeads, notify, offset, panelTab, selectedLeadId, t],
  )

  const handleRetryMetaLead = useCallback(
    async (leadId: string) => {
      setRetryingLeadId(leadId)
      try {
        const result = await retryLeads({ lead_ids: [String(leadId)], refresh_graph: true })
        const item = result.items?.[0]
        if (item?.processed) {
          notify({
            title: t('app.leads.messages.processed'),
            variant: 'success',
          })
        } else if (item?.message) {
          notify({
            title: t('app.leads.messages.process_failed'),
            description: item.message,
            variant: 'error',
          })
        } else {
          notify({
            title: t('app.leads.messages.process_failed'),
            variant: 'error',
          })
        }
        await loadLeads(offset)
        if (panelTab === 'history' && selectedLeadId === leadId) {
          void loadLeadTimeline(leadId)
        }
      } catch (err: any) {
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
        notify({
          title: t('app.admin.meta_leads.errors.retry'),
          description: String(detail),
          variant: 'error',
        })
      } finally {
        setRetryingLeadId(null)
      }
    },
    [loadLeadTimeline, loadLeads, notify, offset, panelTab, selectedLeadId, t],
  )

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
          title: t('app.leads.messages.invoice_created'),
          description: t('app.leads.messages.invoice_created_desc'),
          variant: 'success',
        })
        window.location.assign(CRM_APP_PATHS.invoices)
        return invoice
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ??
          err?.message ??
          t('app.leads.messages.invoice_create_failed')
        notify({
          title: t('app.leads.messages.invoice_create_failed'),
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
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold text-slate-900">{leadWorkspaceTitle}</h1>
              <ActiveOwnCompanyBadge />
              <Link
                to={CRM_APP_PATHS.leadsDistribution}
                className="ml-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-brand-700 hover:bg-slate-50"
              >
                {t('app.leads.workspace.distribution_cta')}
              </Link>
            </div>
            <p className="text-xs text-slate-500">{leadWorkspaceSubtitle}</p>
            {leadNba && leadNba.groups.some((g) => g.count > 0) ? (
              <NbaNextActionsChips
                groups={leadNba.groups}
                nbaQuickLoadingGroupId={nbaBulk.nbaQuickLoadingGroupId}
                onQuickFollowUp={nbaBulk.openNbaQuickFollowUp}
                teamTierFeatures={leadNba.nba_tier === 'team'}
                onQuickProcessNew={nbaBulk.openNbaQuickProcessNewLeads}
              />
            ) : null}
            {leadStageHealth && leadStageHealth.stages.length > 0 ? (
              <div className="mt-2">
                <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                  {t('app.leads.stage_health.title')}
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {leadStageHealth.stages.map((row) => (
                    <div
                      key={row.stage}
                      className="min-w-[148px] shrink-0 rounded-lg border border-slate-200 bg-slate-50/80 px-2 py-1.5 text-[11px] text-slate-700"
                    >
                      <div className="font-semibold text-slate-900">{stageLabels[row.stage] ?? row.stage}</div>
                      <div className="mt-1 space-y-0.5 tabular-nums">
                        <div>
                          <Link
                            to={leadsNextActionHref({ status: 'processed', stage: row.stage })}
                            className="text-brand-700 hover:underline"
                          >
                            {t('app.leads.stage_health.processed')}: {row.processed_total}
                          </Link>
                        </div>
                        {row.no_next_action > 0 ? (
                          <div>
                            <Link
                              to={leadsNextActionHref({
                                status: 'processed',
                                stage: row.stage,
                                next_action: 'no_next_action',
                              })}
                              className="text-amber-800 hover:underline"
                            >
                              {t('app.leads.next_action.no_next_action')}:{' '}
                              {row.no_next_action}
                            </Link>
                          </div>
                        ) : null}
                        {row.overdue > 0 ? (
                          <div>
                            <Link
                              to={leadsNextActionHref({
                                status: 'processed',
                                stage: row.stage,
                                next_action: 'overdue',
                              })}
                              className="text-rose-800 hover:underline"
                            >
                              {t('app.leads.next_action.overdue')}: {row.overdue}
                            </Link>
                          </div>
                        ) : null}
                        {row.stuck > 0 ? (
                          <div>
                            <Link
                              to={leadsNextActionHref({ stage: row.stage, next_action: 'stuck' })}
                              className="text-violet-900 hover:underline"
                            >
                              {t('app.leads.next_action.stuck')}: {row.stuck}
                            </Link>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {leadConversionFunnel && leadConversionFunnel.stages.length > 0 ? (
              <div className="mt-2">
                <div className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                  {t('app.leads.conversion_funnel.title')}
                </div>
                <p className="mb-1.5 max-w-3xl text-[10px] leading-snug text-slate-500">
                  {t('app.leads.conversion_funnel.hint')}
                </p>
                <div className="mb-2 max-w-3xl rounded-lg border border-dashed border-slate-200 bg-slate-50/80 px-2 py-1.5">
                  <div className="mb-1 text-[10px] font-medium text-slate-600">
                    {t('app.leads.conversion_funnel.slices_title')}
                  </div>
                  {leadNba?.nba_tier !== 'team' ? (
                    <p className="text-[10px] text-slate-500">{t('app.leads.conversion_funnel.slices_team_hint')}</p>
                  ) : (
                    <>
                      <div className="flex flex-wrap gap-2">
                        <label className="flex min-w-[100px] flex-1 flex-col text-[9px] font-medium text-slate-600">
                          {t('app.leads.conversion_funnel.slice_source')}
                          <input
                            className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 text-[10px]"
                            value={funnelSliceDraft.source}
                            onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, source: e.target.value }))}
                            placeholder="meta"
                            autoComplete="off"
                          />
                        </label>
                        <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
                          {t('app.leads.conversion_funnel.slice_vacancy_id')}
                          <input
                            className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                            value={funnelSliceDraft.vacancyId}
                            onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, vacancyId: e.target.value }))}
                            placeholder="UUID"
                            autoComplete="off"
                          />
                        </label>
                        <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
                          {t('app.leads.conversion_funnel.slice_funnel_id')}
                          <input
                            className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                            value={funnelSliceDraft.funnelId}
                            onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, funnelId: e.target.value }))}
                            placeholder="UUID"
                            autoComplete="off"
                          />
                        </label>
                        <label className="flex min-w-[120px] flex-1 flex-col text-[9px] font-medium text-slate-600">
                          {t('app.leads.conversion_funnel.slice_assignee')}
                          <input
                            className="input mt-0.5 h-7 rounded border-slate-300 px-1.5 font-mono text-[10px]"
                            value={funnelSliceDraft.assigneeUserId}
                            onChange={(e) => setFunnelSliceDraft((d) => ({ ...d, assigneeUserId: e.target.value }))}
                            placeholder="User UUID"
                            autoComplete="off"
                          />
                        </label>
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn-secondary h-7 rounded px-2 text-[10px]"
                          onClick={() => applyFunnelSlices()}
                        >
                          {t('app.leads.conversion_funnel.slices_apply')}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary h-7 rounded px-2 text-[10px]"
                          onClick={() => clearFunnelSlices()}
                        >
                          {t('app.leads.conversion_funnel.slices_clear')}
                        </button>
                      </div>
                    </>
                  )}
                  {leadConversionFunnel &&
                  (leadConversionFunnel.filter_source ||
                    leadConversionFunnel.filter_vacancy_id ||
                    leadConversionFunnel.filter_funnel_id ||
                    leadConversionFunnel.filter_assignee_user_id) ? (
                    <div className="mt-1.5 text-[9px] text-slate-600">
                      <span className="font-medium">{t('app.leads.conversion_funnel.slices_active')}:</span>{' '}
                      {[
                        leadConversionFunnel.filter_source
                          ? `${t('app.leads.conversion_funnel.slice_source')}=${leadConversionFunnel.filter_source}`
                          : null,
                        leadConversionFunnel.filter_vacancy_id
                          ? `${t('app.leads.conversion_funnel.slice_vacancy_id')}=${leadConversionFunnel.filter_vacancy_id}`
                          : null,
                        leadConversionFunnel.filter_funnel_id
                          ? `${t('app.leads.conversion_funnel.slice_funnel_id')}=${leadConversionFunnel.filter_funnel_id}`
                          : null,
                        leadConversionFunnel.filter_assignee_user_id
                          ? `${t('app.leads.conversion_funnel.slice_assignee')}=${leadConversionFunnel.filter_assignee_user_id}`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-end gap-1 text-[11px] text-slate-700">
                  {leadConversionFunnel.status_new_count > 0 ? (
                    <div className="mb-1 rounded-md border border-amber-200/80 bg-amber-50/90 px-2 py-1 tabular-nums">
                      <Link to={leadsNextActionHref({ status: 'new' })} className="font-medium text-amber-900 hover:underline">
                        {t('app.leads.conversion_funnel.new_status')}: {leadConversionFunnel.status_new_count}
                      </Link>
                    </div>
                  ) : null}
                  {leadConversionFunnel.lost_processed_count > 0 ? (
                    <div className="mb-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 tabular-nums">
                      <Link
                        to={leadsNextActionHref({ status: 'processed', stage: 'lost' })}
                        className="font-medium text-slate-800 hover:underline"
                      >
                        {t('app.leads.conversion_funnel.lost')}: {leadConversionFunnel.lost_processed_count}
                      </Link>
                      {(leadConversionFunnel.lost_dwell_sample_size ?? 0) > 0 &&
                      leadConversionFunnel.lost_dwell_avg_days != null ? (
                        <div className="mt-0.5 text-[9px] font-normal text-slate-500">
                          {t('app.leads.conversion_funnel.dwell_line', {
                            values: {
                              avg: leadConversionFunnel.lost_dwell_avg_days,
                              p50: leadConversionFunnel.lost_dwell_p50_days ?? '—',
                            },
                          })}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {leadConversionFunnel.lost_from_stage && leadConversionFunnel.lost_from_stage.length > 0 ? (
                    <div className="mb-1 mt-1 w-full max-w-xl rounded-md border border-slate-200 bg-white px-2 py-1.5">
                      <div className="text-[9px] font-medium uppercase tracking-wide text-slate-500">
                        {t('app.leads.conversion_funnel.lost_from_title')}
                      </div>
                      <p className="mb-1 text-[9px] text-slate-500">{t('app.leads.conversion_funnel.lost_from_hint')}</p>
                      <ul className="space-y-0.5 text-[10px] text-slate-700">
                        {leadConversionFunnel.lost_from_stage.map((row) => (
                          <li key={row.from_stage} className="flex justify-between gap-2 tabular-nums">
                            <span>
                              <span className="font-medium text-slate-800">
                                {stageLabels[row.from_stage as LeadStage] ?? row.from_stage}
                              </span>
                              <span className="text-slate-500"> → {t('app.leads.stages.lost')}</span>
                            </span>
                            <Link
                              to={leadsNextActionHref({ status: 'processed', stage: 'lost' })}
                              className="shrink-0 text-brand-700 hover:underline"
                            >
                              {row.lead_count}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {leadConversionFunnel.lost_reason_breakdown &&
                  leadConversionFunnel.lost_reason_breakdown.length > 0 ? (
                    <div className="mb-1 mt-1 w-full max-w-xl rounded-md border border-slate-200 bg-white px-2 py-1.5">
                      <div className="text-[9px] font-medium uppercase tracking-wide text-slate-500">
                        {t('app.leads.conversion_funnel.lost_reason_title')}
                      </div>
                      <p className="mb-1 text-[9px] text-slate-500">{t('app.leads.conversion_funnel.lost_reason_hint')}</p>
                      <ul className="space-y-0.5 text-[10px] text-slate-700">
                        {leadConversionFunnel.lost_reason_breakdown.map((row) => (
                          <li key={row.reason_code} className="flex justify-between gap-2 tabular-nums">
                            <span className="font-medium text-slate-800">
                              {t(`app.leads.lost_reason.codes.${row.reason_code}`)}
                            </span>
                            <Link
                              to={leadsNextActionHref({ status: 'processed', stage: 'lost' })}
                              className="shrink-0 text-brand-700 hover:underline"
                            >
                              {row.lead_count}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
                <div className="mt-1 flex flex-wrap items-end gap-x-1 gap-y-2">
                  {(() => {
                    const maxCount = Math.max(
                      1,
                      ...leadConversionFunnel.stages.map((s) => s.count),
                    )
                    return leadConversionFunnel.stages.map((s, idx) => {
                      const barW = Math.max(52, Math.round(52 + (s.count / maxCount) * 76))
                      const edge = leadConversionFunnel.edges[idx]
                      return (
                        <div key={s.stage} className="flex items-end gap-x-0.5">
                          <div className="flex flex-col items-center gap-0.5">
                            <div
                              className="flex min-h-[52px] items-end justify-center rounded-md border border-slate-200 bg-gradient-to-t from-brand-600/90 to-brand-500/80 px-1.5 pb-1 pt-2 shadow-sm"
                              style={{ width: barW }}
                            >
                              <Link
                                to={leadsNextActionHref({ status: 'processed', stage: s.stage })}
                                className="w-full text-center text-[10px] font-semibold leading-tight text-white hover:underline"
                              >
                                {s.count}
                              </Link>
                            </div>
                            <div className="max-w-[96px] text-center text-[10px] font-medium text-slate-700">
                              {stageLabels[s.stage as LeadStage] ?? s.stage}
                            </div>
                            {(s.dwell_sample_size ?? 0) > 0 && s.dwell_avg_days != null ? (
                              <div className="max-w-[104px] text-center text-[9px] leading-tight text-slate-500">
                                {t('app.leads.conversion_funnel.dwell_line', {
                                  values: { avg: s.dwell_avg_days, p50: s.dwell_p50_days ?? '—' },
                                })}
                              </div>
                            ) : null}
                          </div>
                          {edge ? (
                            <div className="mb-6 px-0.5 text-[9px] font-medium tabular-nums text-slate-500">
                              →{' '}
                              {edge.progressed_share != null
                                ? `${Math.round(edge.progressed_share * 100)}%`
                                : '—'}
                            </div>
                          ) : null}
                        </div>
                      )
                    })
                  })()}
                </div>
              </div>
            ) : null}
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
              {t('app.leads.filters.stage')}
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
              {t('app.leads.filters.next_action')}
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
          <label className="min-w-[200px] flex-1 text-xs font-medium text-slate-600">
            <span className="mb-1 inline-flex items-center gap-1">
              <IconSearch size={12} />
              {t('app.leads.filters.search')}
            </span>
            <input
              type="search"
              className="input h-9 w-full max-w-xs rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
              value={leadSearch}
              onChange={(e) => {
                setLeadSearch(e.target.value)
                setPage(1)
              }}
              placeholder={t('app.leads.filters.search_placeholder')}
              autoComplete="off"
            />
          </label>
          <button
            type="button"
            onClick={() => {
              setPage(1)
              void loadLeads(0)
              refreshLeadInsights()
            }}
            className="btn-secondary h-9 rounded-lg px-3 text-xs"
          >
            <IconRefresh size={14} />
            {t('app.candidates.actions.refresh')}
          </button>
        </div>
        {leadCustomFieldDefs.length > 0 ? (
          <div className="mt-2 flex flex-wrap items-end gap-2">
            <label className="min-w-[200px] text-xs font-medium text-slate-600">
              <span className="mb-1 inline-flex items-center gap-1">
                <IconFilter size={12} />
                {t('app.leads.filters.custom_field')}
              </span>
              <select
                className="input h-9 rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                value={customFieldKey}
                onChange={(e) => {
                  setCustomFieldKey(e.target.value)
                  setCustomFieldValue('')
                  setPage(1)
                }}
              >
                <option value="">{t('app.leads.filters.custom_field_none')}</option>
                {leadCustomFieldDefs.map((d) => (
                  <option key={d.id} value={d.key}>
                    {d.label || d.key}
                  </option>
                ))}
              </select>
            </label>
            <label className="min-w-[200px] flex-1 text-xs font-medium text-slate-600">
              <span className="mb-1 block">{t('app.leads.filters.custom_field_value')}</span>
              <input
                type="text"
                className="input h-9 w-full max-w-xs rounded-lg border-slate-300 bg-white px-2.5 py-1.5 text-sm"
                value={customFieldValue}
                onChange={(e) => {
                  setCustomFieldValue(e.target.value)
                  setPage(1)
                }}
                disabled={!customFieldKey.trim()}
                placeholder={t('app.leads.filters.custom_field_value_placeholder')}
              />
            </label>
            {customFieldKey.trim() ? (
              <button
                type="button"
                className="btn-secondary mb-0.5 h-9 rounded-lg px-2 text-xs"
                onClick={() => {
                  setCustomFieldKey('')
                  setCustomFieldValue('')
                  setPage(1)
                }}
              >
                {t('app.leads.filters.custom_field_clear')}
              </button>
            ) : null}
          </div>
        ) : null}
      </header>

      {filterBannerVisible && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-700">
              <span className="font-medium">{t('app.leads.inbox.banner.filtered')}</span>{' '}
              {[
                status ? statusLabels[status as LeadStatus] ?? status : null,
                stage ? stageLabels[stage as LeadStage] ?? stage : null,
                nextAction ? nextActionOptions.find((o) => o.value === nextAction)?.label ?? nextAction : null,
                customFieldKey.trim()
                  ? `${customFieldKey}=${customFieldValue}`
                  : null,
                leadSearch.trim().length >= 2
                  ? `${t('app.leads.filters.search')}: ${leadSearch.trim()}`
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
              {t('app.leads.inbox.banner.reset')}
            </button>
          </div>
        </div>
      )}

      <section className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {selectedCount > 0 && (
            <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700 flex flex-wrap items-center gap-2">
              <div className="font-medium">
                {t('app.leads.bulk.selected', { values: { count: selectedCount } })}
              </div>
              <select
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                value={bulkStage}
                onChange={(e) => setBulkStage(e.target.value as any)}
                disabled={bulkUpdating}
              >
                <option value="">{t('app.leads.bulk.stage')}</option>
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
                <option value="">{t('app.leads.bulk.status')}</option>
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
                {bulkUpdating ? t('common.loading') : t('app.leads.bulk.apply')}
              </button>
              {selectedMetaProblemLeadIds.length > 0 && (
                <button
                  type="button"
                  className="btn-secondary rounded-lg px-2.5 py-1 text-xs"
                  onClick={() => void doBulkRetryMetaLeads()}
                  disabled={bulkRetryingMetaLeads}
                >
                  {bulkRetryingMetaLeads
                    ? t('common.loading')
                    : t('app.leads.bulk.retry_meta', {
                        values: { count: selectedMetaProblemLeadIds.length },
                      })}
                </button>
              )}
              <button
                type="button"
                className="btn-secondary rounded-lg px-2.5 py-1 text-xs"
                onClick={() => nbaBulk.openSelectionBulkActivities()}
              >
                {t('app.leads.bulk.activities.action')}
              </button>
              <button type="button" className="btn-secondary rounded-lg px-2.5 py-1 text-xs" onClick={() => setChecked({})}>
                {t('app.leads.bulk.clear')}
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
                  <th className="w-[52px]" aria-label={t('app.leads.table.full_page')}>
                    <span className="sr-only">{t('app.leads.table.full_page')}</span>
                  </th>
                  <th>{t('app.leads.table.created')}</th>
                  <th>{t('app.leads.table.status')}</th>
                  <th>{t('app.leads.table.stage')}</th>
                  <th>{t('app.leads.table.next_action')}</th>
                  <th>{companyColumnLabel}</th>
                  <th>{vacancyColumnLabel}</th>
                  <th>{t('app.leads.table.contact')}</th>
                  <th>{t('app.leads.table.source')}</th>
                  <th>{t('app.leads.table.fit')}</th>
                  <th>{ownerColumnLabel}</th>
                  <th>{t('app.leads.table.error')}</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={13} className="px-3 py-5 text-center text-slate-500">
                      {t('common.loading')}
                    </td>
                  </tr>
                )}
                {error && !loading && (
                  <tr>
                    <td colSpan={13} className="px-3 py-4">
                      <ErrorRecoveryBanner
                        compact
                        info={error}
                        onRetry={() => void loadLeads(offset)}
                        retryLabel={t('common.retry')}
                        secondaryTo={CRM_APP_PATHS.settingsLeads}
                        secondaryLabel={t('app.leads.states.empty_cta_connect')}
                      />
                    </td>
                  </tr>
                )}
                {!loading && !error && items.length === 0 && (
                  <tr>
                    <td colSpan={13} className="px-3 py-6">
                      <EmptyStatePanel
                        compact
                        title={emptyTitle}
                        description={emptyDescription}
                        primaryAction={{
                          label: t('app.leads.states.empty_cta_connect'),
                          to: CRM_APP_PATHS.settingsLeads,
                        }}
                        secondaryAction={{
                          label: secondaryEmptyLabel,
                          to: CRM_APP_PATHS.clientsDirectory,
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
                    const rowMetaProblem = isMetaProblemLead(lead)
                    const metaErrorCode = (lead.error ?? '').trim()
                    const leadSuggestion = rowMetaProblem ? getLeadErrorSuggestion(lead.error, t) : null
                    const openCredentialsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=credentials`
                    const openMappingHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=mapping`
                    const openSettingsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=settings`
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
                          setPanelTab(rowMetaProblem ? 'fix' : 'composer')
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedLeadId(lead.id)
                            setPanelTab(rowMetaProblem ? 'fix' : 'composer')
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
                        <td className="w-[52px]" onClick={(e) => e.stopPropagation()}>
                          <Link
                            to={`${CRM_APP_PATHS.leads}/${lead.id}`}
                            className="inline-flex rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-brand-700"
                            title={t('app.leads.table.full_page')}
                            aria-label={t('app.leads.table.full_page')}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <IconExternalLink size={18} stroke={1.75} />
                          </Link>
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
                                {t('app.leads.next_action.overdue')}
                              </span>
                              {lead.next_action_due_at ? (
                                <span className="text-[11px] text-rose-700">{formatDateValue(lead.next_action_due_at)}</span>
                              ) : null}
                            </div>
                          ) : lead.next_action_status === 'scheduled' ? (
                            <div className="flex flex-col items-start gap-0.5">
                              <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                                {t('app.leads.next_action.scheduled')}
                              </span>
                              {lead.next_action_due_at ? (
                                <span className="text-[11px] text-slate-600">{formatDateValue(lead.next_action_due_at)}</span>
                              ) : null}
                            </div>
                          ) : (
                            <span className="inline-flex items-center rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                              {t('app.leads.next_action.no_next_action')}
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
                          {rowMetaProblem ? (
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
                                    ? t('common.loading')
                                    : t('app.admin.meta_leads.logs.actions.retry')}
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
                                      {t('app.admin.meta_leads.logs.actions.reroute')}
                                    </button>
                                    <Link
                                      to={openMappingHref}
                                      className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {t('app.admin.meta_leads.tabs.mapping')}
                                    </Link>
                                  </>
                                ) : null}

                                {leadSuggestion?.tab === 'credentials' ? (
                                  <Link
                                    to={openCredentialsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('app.admin.meta_leads.tabs.credentials')}
                                  </Link>
                                ) : null}

                                {leadSuggestion?.tab === 'settings' ? (
                                  <Link
                                    to={openSettingsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('app.admin.meta_leads.tabs.settings')}
                                  </Link>
                                ) : null}
                              </div>
                            </div>
                          ) : isServicesTenant ? (
                            <div className="flex flex-col items-start gap-1">
                              {lead.outcome_entity_id ? (
                                <Link
                                  to={`${CRM_APP_PATHS.agencyClients}/${lead.outcome_entity_id}`}
                                  onClick={(e) => e.stopPropagation()}
                                >
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
                                    {t('app.leads.actions.open_service_order')}
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
                                      ? t('common.loading')
                                      : t('app.leads.actions.create_invoice')}
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
                                    ? t('common.loading')
                                    : t('app.leads.actions.create_service_order')}
                                </button>
                              )}
                            </div>
                          ) : lead.candidate_id ? (
                            <Link
                              to={`${CRM_APP_PATHS.candidates}/${lead.candidate_id}`}
                              onClick={(e) => e.stopPropagation()}
                            >
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
                                    ? t('common.loading')
                                    : t('app.leads.actions.process')}
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
          open={nbaBulk.bulkActivitiesOpen}
          onClose={() => !nbaBulk.bulkActivitiesLoading && nbaBulk.closeBulkActivitiesModal()}
          hint={nbaBulk.bulkActivitiesHint}
          title={nbaBulk.bulkActivityTitle}
          dueAt={nbaBulk.bulkActivityDueAt}
          offsetMinutes={nbaBulk.bulkActivityOffsetMinutes}
          onTitleChange={nbaBulk.setBulkActivityTitle}
          onDueAtChange={nbaBulk.setBulkActivityDueAt}
          onOffsetMinutesChange={nbaBulk.setBulkActivityOffsetMinutes}
          onApply={() => void nbaBulk.applyBulkActivities(allSelectedLeadIds)}
          loading={nbaBulk.bulkActivitiesLoading}
          activityType={nbaBulk.bulkActivityType}
          onActivityTypeChange={nbaBulk.setBulkActivityType}
        />

        <LostReasonForLostStageModal
          open={Boolean(lostStagePrompt)}
          loading={Boolean(lostStagePrompt && patchingLeadId === lostStagePrompt.leadId)}
          onCancel={cancelLostStagePrompt}
          onConfirm={(p) => void confirmLostStageFromModal(p)}
        />

        <LostReasonForLostStageModal
          open={bulkLostModalOpen}
          loading={bulkUpdating}
          hintKey="app.leads.lost_reason.bulk_modal_hint"
          onCancel={() => setBulkLostModalOpen(false)}
          onConfirm={(p) => confirmBulkLostReason(p)}
        />

        <aside className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          {!selectedLead ? (
            <div className="p-4 text-sm text-slate-500">
              {t('app.leads.inbox.select_hint')}
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
                        t('app.leads.inbox.lead')}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-600">
                      <span className="font-medium">{t('app.leads.table.status')}:</span>{' '}
                      {statusLabels[selectedLead.status] ?? selectedLead.status}
                    </div>
                    <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                      <label className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        <span className="font-medium shrink-0">
                          {t('app.leads.table.stage')}
                        </span>
                        <select
                          className="input h-8 min-w-[10rem] rounded-lg border-slate-300 bg-white px-2 text-xs"
                          value={
                            lostStagePrompt?.leadId === selectedLead.id
                              ? lostStagePrompt.previousStage ?? ''
                              : selectedLead.stage ?? ''
                          }
                          disabled={patchingLeadId === selectedLead.id}
                          onChange={(e) => void handleInboxStageSelect(e.target.value)}
                        >
                          <option value="">{t('app.leads.inbox.stage_unset')}</option>
                          {CRM_STAGE_VALUES.map((v) => (
                            <option key={v} value={v}>
                              {stageLabels[v] ?? v}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600">
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={leadAssignmentLocked(selectedLead)}
                          disabled={patchingLeadId === selectedLead.id}
                          onChange={(e) => void handleInboxAssignmentLockToggle(e.target.checked)}
                        />
                        <span>{t('app.leads.inbox.lock_assignment')}</span>
                      </label>
                    </div>
                    <LeadLostReasonReadonly
                      lead={selectedLead}
                      formatAt={formatDateValue}
                      className="mt-2 border-t border-slate-200 pt-2 text-xs text-slate-700"
                    />
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5 sm:flex-row sm:items-start">
                    <Link
                      to={`${CRM_APP_PATHS.leads}/${selectedLead.id}`}
                      className="btn-secondary inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs"
                      title={t('app.leads.table.full_page')}
                    >
                      <IconExternalLink size={14} stroke={1.75} aria-hidden />
                      <span className="hidden sm:inline">{t('app.leads.table.full_page')}</span>
                    </Link>
                    <button
                      type="button"
                      className="btn-secondary h-8 rounded-lg px-2 text-xs"
                      onClick={() => setSelectedLeadId(null)}
                    >
                      {t('common.actions.close')}
                    </button>
                  </div>
                </div>

                <div className="mt-2 flex gap-2">
                  {selectedIsMetaProblemLead && (
                    <button
                      type="button"
                      className={panelTab === 'fix' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                      onClick={() => setPanelTab('fix')}
                    >
                      {t('app.leads.inbox.tabs.fix')}
                    </button>
                  )}
                  <button
                    type="button"
                    className={panelTab === 'composer' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('composer')}
                  >
                    {t('app.leads.inbox.tabs.composer')}
                  </button>
                  <button
                    type="button"
                    className={panelTab === 'focus' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('focus')}
                  >
                    {t('app.leads.inbox.tabs.focus')}
                  </button>
                  <button
                    type="button"
                    className={panelTab === 'history' ? 'btn-primary h-8 rounded-lg px-2 text-xs' : 'btn-secondary h-8 rounded-lg px-2 text-xs'}
                    onClick={() => setPanelTab('history')}
                  >
                    {t('app.leads.inbox.tabs.history')}
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-auto p-3">
                {panelTab === 'fix' && selectedLead && selectedIsMetaProblemLead && (
                  <div className="space-y-3">
                    <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
                    <LeadMetaProblemPanel lead={selectedLead} onRefreshed={onMetaProblemPanelRefreshed} />
                  </div>
                )}
                {panelTab === 'composer' && (
                  <div className="space-y-3">
                    <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-semibold text-slate-700">
                        {t('app.leads.inbox.composer.followup')}
                      </div>
                      <div className="mt-2 space-y-2">
                        <input
                          className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                          value={reminderTitle}
                          onChange={(e) => setReminderTitle(e.target.value)}
                          placeholder={t('app.reminders.fields.title')}
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <label className="text-xs font-medium text-slate-600">
                            <div className="mb-1">{t('app.reminders.fields.due_at')}</div>
                            <input
                              type="datetime-local"
                              className="input h-9 w-full rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                              value={reminderDueAt}
                              onChange={(e) => setReminderDueAt(e.target.value)}
                            />
                          </label>
                          <label className="text-xs font-medium text-slate-600">
                            <div className="mb-1">{t('app.reminders.fields.remind_before')}</div>
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
                          {t('app.reminders.actions.create')}
                        </button>
                        {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
                      </div>
                    </div>
                    <div className="text-xs text-slate-500">
                      {t('app.leads.inbox.composer.hint')}
                    </div>
                  </div>
                )}

                {panelTab === 'focus' && (
                  <div className="space-y-3">
                    <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-semibold text-slate-700">
                        {t('app.reminders.title')}
                      </div>
                      <button
                        type="button"
                        className="btn-secondary h-8 rounded-lg px-2 text-xs"
                        onClick={() => selectedLeadId && void loadLeadReminders(selectedLeadId)}
                      >
                        {t('common.actions.refresh')}
                      </button>
                    </div>
                    {remindersLoading ? (
                      <div className="py-4 text-center text-xs text-slate-500">{t('common.loading')}</div>
                    ) : reminders.length === 0 ? (
                      <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-500">
                        {t('app.reminders.states.empty')}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {reminders.slice(0, 20).map((r) => (
                          <div key={r.id} className="rounded-lg border border-slate-200 bg-white p-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-medium text-slate-900">{r.title || t('app.reminders.item.untitled')}</div>
                                <div className="mt-0.5 text-xs text-slate-600">
                                  <span className="font-medium">{t('app.reminders.fields.due_at')}:</span> {formatDateValue(r.due_at)}
                                </div>
                              </div>
                              <button
                                type="button"
                                className="btn-secondary h-8 rounded-lg px-2 text-xs"
                                onClick={() => void handleCompleteReminder(r.id)}
                              >
                                {t('app.reminders.actions.complete')}
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
                  <div className="space-y-3 text-xs">
                    <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
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
                          <span className="text-slate-500">{t('app.leads.table.stage')}:</span>{' '}
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
                          {t('app.leads.inbox.history.timeline_title')}
                        </div>
                        <button
                          type="button"
                          className="btn-secondary h-7 rounded-lg px-2 text-[11px]"
                          onClick={() => selectedLeadId && void loadLeadTimeline(selectedLeadId)}
                        >
                          {t('common.actions.refresh')}
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
                          {t('app.leads.inbox.history.empty')}
                        </div>
                      ) : (
                        <ul className="mt-2 space-y-1.5">
                          {timelineItems.map((ev, idx) => (
                            <li key={`${ev.at}-${ev.kind}-${idx}`} className="flex items-start gap-2">
                              <div className="mt-[3px] h-1.5 w-1.5 rounded-full bg-slate-400" />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="truncate text-[11px] font-medium text-slate-800">
                                    {ev.title || ev.kind || t('app.leads.inbox.history.event')}
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
