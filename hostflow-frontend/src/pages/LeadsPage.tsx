import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  IconArrowRight,
  IconExternalLink,
  IconFilter,
  IconFlame,
  IconLayoutKanban,
  IconMail,
  IconPhone,
  IconRefresh,
  IconSearch,
  IconTable,
} from '@tabler/icons-react'

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
import { getOpsCounters, recordPerfMeasurement, type OpsCounters } from '../api/analytics'
import { useI18n } from '../i18n'
import EmptyStatePanel from '../components/EmptyStatePanel'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useNbaQuickBulkFlow } from '../components/nba/useNbaQuickBulkFlow'
import { BulkActivitiesModal } from '../modules/candidates/components'
import { useToast } from '../components/Toast'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { getLeadErrorSuggestion } from '../utils/leadErrorSuggestion'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { serviceOrderWorkspacePath } from '../modules/services/utils'
import { listCustomFieldDefinitions, type CustomFieldDefinition } from '../api/custom_fields'
import LeadsKanbanBoard from '../components/leads/LeadsKanbanBoard'
import LeadMetaProblemPanel from '../components/leads/LeadMetaProblemPanel'
import LeadNextActionPlaybook from '../components/leads/LeadNextActionPlaybook'
import LeadQualificationSuggestionPanel from '../components/leads/LeadQualificationSuggestionPanel'
import LeadLostReasonReadonly from '../components/leads/LeadLostReasonReadonly'
import LostReasonForLostStageModal from '../components/leads/LostReasonForLostStageModal'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import {
  CRM_STAGE_VALUES,
  isMetaProblemLead,
  leadAssignmentLocked,
  leadSupportsManualProcess,
} from '../utils/leadCrm'
import { formatLeadPipelineError } from '../utils/leadPipelineErrors'

const STATUS_FILTERS: Array<'' | LeadStatus> = ['', 'new', 'processed', 'duplicated', 'needs_routing', 'failed']
const STAGE_FILTERS: Array<'' | LeadStage> = ['', 'new', 'contacted', 'qualified', 'converted', 'lost']
const NEXT_ACTION_FILTERS: Array<'' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'> = [
  '',
  'no_next_action',
  'overdue',
  'scheduled',
  'stuck',
]

const PIPELINE_ERROR_QUERY_VALUES = ['LEAD_FIT_NO_MATCH', 'LEAD_FIT_NEEDS_INFO'] as const
type PipelineErrorFilter = '' | (typeof PIPELINE_ERROR_QUERY_VALUES)[number]

const LEADS_HREF_QUEUE_NEW = `${CRM_APP_PATHS.leads}?status=new`
const LEADS_HREF_QUEUE_IN_PROGRESS = `${CRM_APP_PATHS.leads}?status=processed&stage=contacted`
const LEADS_HREF_QUEUE_WAITING = `${CRM_APP_PATHS.leads}?status=processed&next_action=scheduled`
const LEADS_HREF_QUEUE_OVERDUE = `${CRM_APP_PATHS.leads}?status=processed&next_action=overdue`

function leadOpsNum(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return String(Math.max(0, Math.floor(Number(n))))
}

function parsePipelineErrorParam(raw: string | null | undefined): PipelineErrorFilter {
  const v = (raw || '').trim()
  return (PIPELINE_ERROR_QUERY_VALUES as readonly string[]).includes(v) ? (v as PipelineErrorFilter) : ''
}
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

type LeadConversionRootFilter = '' | 'lead' | 'qualified' | 'active' | 'final'

function initialConversionRootFromLocation(): LeadConversionRootFilter {
  if (typeof window === 'undefined') return ''
  try {
    const sp = new URLSearchParams(window.location.search)
    const v = (sp.get('conversion_root') || '').trim().toLowerCase()
    if (v === 'lead' || v === 'qualified' || v === 'active' || v === 'final') return v
  } catch {
    /* noop */
  }
  return ''
}

function initialLostReasonCodeFromLocation(): string {
  if (typeof window === 'undefined') return ''
  try {
    const v = (new URLSearchParams(window.location.search).get('lost_reason_code') || '').trim()
    if (/^[A-Za-z0-9_-]{1,64}$/.test(v)) return v
  } catch {
    /* noop */
  }
  return ''
}

/** Mirrors GET /leads validation for `lost_from_crm_stage`. */
function parseLostFromCrmStageParam(raw: string | null | undefined): string {
  const v = (raw || '').trim().toLowerCase()
  if (!v) return ''
  if (v === 'unknown') return 'unknown'
  if (/^[a-z0-9_-]{1,32}$/.test(v)) return v
  return ''
}

function initialLostFromCrmStageFromLocation(): string {
  if (typeof window === 'undefined') return ''
  try {
    return parseLostFromCrmStageParam(new URLSearchParams(window.location.search).get('lost_from_crm_stage'))
  } catch {
    /* noop */
  }
  return ''
}

function initialPipelineErrorFromLocation(): PipelineErrorFilter {
  if (typeof window === 'undefined') return ''
  try {
    return parsePipelineErrorParam(new URLSearchParams(window.location.search).get('pipeline_error'))
  } catch {
    /* noop */
  }
  return ''
}

export default function LeadsPage() {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const { entitySingular, openEntityLabel } = useBusinessTerminology()
  const location = useLocation()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'' | LeadStatus>('')
  const [stage, setStage] = useState<'' | LeadStage>('')
  /** GET /leads created_before_hours — stale new leads (Work hub deep link). */
  const [createdBeforeHoursFilter, setCreatedBeforeHoursFilter] = useState<number | null>(() => {
    if (typeof window === 'undefined') return null
    try {
      const sp = new URLSearchParams(window.location.search)
      const n = parseInt(sp.get('created_before_hours') || '', 10)
      if (Number.isFinite(n) && n > 0) return n
      if ((sp.get('filter') || '').trim().toLowerCase() === 'no_first_contact_24h') return 24
    } catch {
      /* noop */
    }
    return null
  })
  const [nextAction, setNextAction] = useState<'' | 'no_next_action' | 'overdue' | 'scheduled' | 'stuck'>('')
  const [conversionRoot, setConversionRoot] = useState<LeadConversionRootFilter>(initialConversionRootFromLocation)
  const [lostReasonCode, setLostReasonCode] = useState(initialLostReasonCodeFromLocation)
  const [lostFromCrmStage, setLostFromCrmStage] = useState(initialLostFromCrmStageFromLocation)
  const [pipelineError, setPipelineError] = useState<PipelineErrorFilter>(initialPipelineErrorFromLocation)
  const [workspaceView, setWorkspaceView] = useState<'table' | 'kanban'>('table')
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

  const selectFirstAfterTriageRef = useRef(false)
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
  const [leadOps, setLeadOps] = useState<OpsCounters | null>(null)
  const [leadOpsLoading, setLeadOpsLoading] = useState(true)
  const [lostStagePrompt, setLostStagePrompt] = useState<{ leadId: string; previousStage: string | null } | null>(
    null,
  )
  const [bulkLostModalOpen, setBulkLostModalOpen] = useState(false)

  useEffect(() => {
    if (lostStagePrompt && selectedLeadId && lostStagePrompt.leadId !== selectedLeadId) {
      setLostStagePrompt(null)
    }
  }, [lostStagePrompt, selectedLeadId])

  const refreshLeadInsights = useCallback(() => {
    void getOpsCounters()
      .then((d) => setLeadOps(d))
      .catch(() => {})
  }, [])

  useEffect(() => {
    refreshLeadInsights()
  }, [refreshLeadInsights])

  useEffect(() => {
    let cancelled = false
    setLeadOpsLoading(true)
    void getOpsCounters()
      .then((d) => {
        if (!cancelled) setLeadOps(d)
      })
      .catch(() => {
        if (!cancelled) setLeadOps(null)
      })
      .finally(() => {
        if (!cancelled) setLeadOpsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

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
    const filterRaw = (sp.get('filter') || '').trim().toLowerCase()
    const cbhRaw = sp.get('created_before_hours')
    const parsedCbh = cbhRaw != null ? parseInt(String(cbhRaw), 10) : NaN
    const nextCbh =
      Number.isFinite(parsedCbh) && parsedCbh > 0 ? parsedCbh : filterRaw === 'no_first_contact_24h' ? 24 : null
    if (nextCbh !== createdBeforeHoursFilter) {
      setCreatedBeforeHoursFilter(nextCbh)
      setPage(1)
    }
    if (filterRaw === 'no_first_contact_24h' && !nextStatus) {
      setStatus('new')
      setPage(1)
    } else if (nextCbh != null && nextCbh > 0 && !nextStatus) {
      setStatus('new')
      setPage(1)
    }
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
    const nextConvRoot = (sp.get('conversion_root') || '').trim().toLowerCase() as LeadConversionRootFilter
    const convOk =
      nextConvRoot === 'lead' ||
      nextConvRoot === 'qualified' ||
      nextConvRoot === 'active' ||
      nextConvRoot === 'final'
    if (convOk && nextConvRoot !== conversionRoot) {
      setConversionRoot(nextConvRoot)
      setPage(1)
    }
    const nextLrc = (sp.get('lost_reason_code') || '').trim()
    const lrcOk = /^[A-Za-z0-9_-]{1,64}$/.test(nextLrc)
    if (lrcOk && nextLrc !== lostReasonCode) {
      setLostReasonCode(nextLrc)
      setPage(1)
    } else if (!sp.has('lost_reason_code') && lostReasonCode) {
      setLostReasonCode('')
      setPage(1)
    }
    const nextLfCrm = parseLostFromCrmStageParam(sp.get('lost_from_crm_stage'))
    if (nextLfCrm && nextLfCrm !== lostFromCrmStage) {
      setLostFromCrmStage(nextLfCrm)
      setPage(1)
    } else if (!sp.has('lost_from_crm_stage') && lostFromCrmStage) {
      setLostFromCrmStage('')
      setPage(1)
    }
    if (nextCfKey && hasCfValParam && nextCfVal !== null) {
      if (nextCfKey !== customFieldKey) setCustomFieldKey(nextCfKey)
      if (nextCfVal !== customFieldValue) setCustomFieldValue(nextCfVal)
      setPage(1)
    }
    const nextPipelineError = parsePipelineErrorParam(sp.get('pipeline_error'))
    if (nextPipelineError && nextPipelineError !== pipelineError) {
      setPipelineError(nextPipelineError)
      setPage(1)
    } else if (!sp.has('pipeline_error') && pipelineError) {
      setPipelineError('')
      setPage(1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, conversionRoot, lostReasonCode, lostFromCrmStage, pipelineError, createdBeforeHoursFilter])

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
    status ||
      stage ||
      nextAction ||
      conversionRoot ||
      lostReasonCode ||
      lostFromCrmStage ||
      pipelineError ||
      customFieldKey.trim() ||
      leadSearch.trim().length >= 2 ||
      createdBeforeHoursFilter != null,
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
          createdBeforeHours: createdBeforeHoursFilter ?? undefined,
          nextAction: nextAction || undefined,
          conversionRoot: conversionRoot || undefined,
          lostReasonCode: lostReasonCode || undefined,
          lostFromCrmStage: lostFromCrmStage || undefined,
          pipelineError: pipelineError || undefined,
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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.messages.load_failed'))) {
          setError(null)
        } else {
          setError(getFriendlyErrorInfo(err, t('app.leads.messages.load_failed'), t))
        }
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
            conversion_root: conversionRoot || null,
            lost_reason_code: lostReasonCode || null,
            lost_from_crm_stage: lostFromCrmStage || null,
            pipeline_error: pipelineError || null,
            limit,
            offset: nextOffset,
          },
        }).catch(() => {})
        setLoading(false)
      }
    },
    [
      conversionRoot,
      lostReasonCode,
      lostFromCrmStage,
      pipelineError,
      customFieldKey,
      customFieldValue,
      leadSearch,
      limit,
      nextAction,
      offset,
      stage,
      status,
      createdBeforeHoursFilter,
      planLimitModal,
      t,
    ],
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
    setConversionRoot('')
    setLostReasonCode('')
    setLostFromCrmStage('')
    setPipelineError('')
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

  const startLeadTriage = useCallback(() => {
    selectFirstAfterTriageRef.current = true
    navigate(CRM_APP_DRILLDOWN_HREFS.leadsNeedsRouting)
  }, [navigate])

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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.bulk.update_failed'))) {
          return
        }
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
    [allSelectedLeadIds, bulkStage, bulkStatus, loadLeads, notify, offset, planLimitModal, refreshLeadInsights, t],
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
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.retry'))) {
        return
      }
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
      notify({
        title: t('admin.meta_leads.errors.retry'),
        description: String(detail),
        variant: 'error',
      })
    } finally {
      setBulkRetryingMetaLeads(false)
    }
  }, [loadLeads, notify, offset, planLimitModal, retryLeads, selectedMetaProblemLeadIds, t])

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
    if (!selectFirstAfterTriageRef.current || loading) return
    if (items.length === 0) {
      selectFirstAfterTriageRef.current = false
      return
    }
    selectFirstAfterTriageRef.current = false
    setSelectedLeadId(items[0].id)
  }, [loading, items])

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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.stage_update_failed'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [
      applyLeadPatchToList,
      loadLeads,
      notify,
      offset,
      planLimitModal,
      refreshLeadInsights,
      selectedLead,
      selectedLeadId,
      t,
    ],
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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.stage_update_failed'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.stage_update_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [applyLeadPatchToList, loadLeads, lostStagePrompt, notify, offset, planLimitModal, refreshLeadInsights, t],
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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.lock_update_failed'))) {
          return
        }
        const info = getFriendlyErrorInfo(err, t('app.leads.detail.lock_update_failed'), t)
        notify({
          title: info.title,
          description: [info.detail, info.hint].filter(Boolean).join(' '),
          variant: 'error',
        })
      } finally {
        setPatchingLeadId(null)
      }
    },
    [applyLeadPatchToList, notify, planLimitModal, selectedLeadId, t],
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
    ;(['lead', 'qualified', 'active', 'final'] as const).forEach((value) => {
      map[value] = t(`app.leads.conversion_funnel.roots.${value}`)
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

  const formatDateValue = (value?: string | null) => {
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
    } catch (err: any) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) {
        return
      }
      const detail =
        err?.response?.data?.detail ??
        err?.message ??
        t('app.reminders.errors.create')
      setRemindersError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      notify({ title: typeof detail === 'string' ? detail : t('app.reminders.errors.create'), variant: 'error' })
    }
  }, [loadLeadReminders, notify, planLimitModal, reminderDueAt, reminderOffset, reminderTitle, selectedLeadId, t])

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

  useEffect(() => {
    if (!selectedLeadId) {
      setTimelineItems([])
      setTimelineError(null)
      return
    }
    void loadLeadTimeline(selectedLeadId)
  }, [selectedLeadId, loadLeadTimeline])

  const onMetaProblemPanelRefreshed = useCallback(async () => {
    await loadLeads(offset)
    refreshLeadInsights()
    if (selectedLeadId) void loadLeadTimeline(selectedLeadId)
  }, [loadLeadTimeline, loadLeads, offset, refreshLeadInsights, selectedLeadId])

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
        if (
          planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.messages.service_order_create_failed'))
        ) {
          return
        }
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
    [loadLeads, notify, offset, planLimitModal, t],
  )

  const handleProcessLead = useCallback(
    async (leadId: string) => {
      setProcessingLeadId(leadId)
      try {
        const result = await processLead(leadId)
        await loadLeads(offset)
        if (selectedLeadId === leadId) void loadLeadTimeline(leadId)
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
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.messages.process_failed'))) {
          return
        }
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
    [loadLeadTimeline, loadLeads, notify, offset, planLimitModal, selectedLeadId, t],
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
        if (selectedLeadId === leadId) void loadLeadTimeline(leadId)
      } catch (err: any) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('admin.meta_leads.errors.retry'))) {
          return
        }
        const detail = err?.response?.data?.detail ?? err?.message ?? 'Retry failed'
        notify({
          title: t('admin.meta_leads.errors.retry'),
          description: String(detail),
          variant: 'error',
        })
      } finally {
        setRetryingLeadId(null)
      }
    },
    [loadLeadTimeline, loadLeads, notify, offset, planLimitModal, selectedLeadId, t],
  )

  const handleRerouteMetaLeadFromError = useCallback((leadId: string, _leadCompanyId?: string | null) => {
    setSelectedLeadId(leadId)
  }, [])

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
        if (
          planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.messages.invoice_create_failed'))
        ) {
          return
        }
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
    [notify, planLimitModal, t],
  )

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-[1600px] flex-1 flex-col gap-5">
      <header className="space-y-4 rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white py-4 shadow-none">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold text-slate-900">{leadWorkspaceTitle}</h1>
            <Link
              to={CRM_APP_PATHS.leadsDistribution}
              className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-brand-700 hover:bg-slate-50"
            >
              {t('app.leads.workspace.distribution_cta')}
            </Link>
            <Link
              to={`${CRM_APP_PATHS.overview}#lead-conversion`}
              className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
            >
              {t('app.leads.workspace.funnel_analytics_link', { defaultValue: 'Conversion funnel (analytics)' })}
            </Link>
          </div>
          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600">
            <IconTable size={14} />
            <span>{t('app.leads.pagination.shown', { values: { count: items.length, total: data.total } })}</span>
          </div>
        </div>

        <section className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <IconFlame size={16} className="text-rose-500" aria-hidden />
            {t('app.leads.workspace.block_attention', { defaultValue: 'Needs processing' })}
          </div>
          {leadOpsLoading ? (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="flex items-center justify-between gap-3 rounded-2xl border-2 border-rose-200 bg-white px-4 py-3 shadow-sm">
                <div className="min-w-0">
                  <p className="text-2xl font-bold tabular-nums text-slate-900">
                    {leadOpsNum(leadOps?.leads_needs_routing)}
                  </p>
                  <p className="text-sm font-medium text-slate-700">
                    {t('app.leads.workspace.attention_needs_routing', { defaultValue: 'Leads to triage' })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={startLeadTriage}
                  className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                >
                  {t('app.leads.workspace.start_processing', { defaultValue: 'Start processing' })}
                  <IconArrowRight size={18} stroke={2} aria-hidden />
                </button>
              </div>
              <Link
                to={LEADS_HREF_QUEUE_OVERDUE}
                className="flex items-center justify-between gap-3 rounded-2xl border-2 border-amber-200 bg-white px-4 py-3 shadow-sm transition hover:border-amber-300"
              >
                <div className="min-w-0">
                  <p className="text-2xl font-bold tabular-nums text-slate-900">{leadOpsNum(leadOps?.leads_overdue)}</p>
                  <p className="text-sm font-medium text-slate-700">
                    {t('app.leads.workspace.attention_overdue', { defaultValue: 'Overdue follow-ups' })}
                  </p>
                </div>
                <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
                  {t('app.leads.workspace.fix_overdue', { defaultValue: 'Fix now' })}
                  <IconArrowRight size={18} stroke={2} aria-hidden />
                </span>
              </Link>
            </div>
          )}
        </section>

        <section className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.leads.workspace.block_queue', { defaultValue: 'Lead queue' })}
          </div>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-4">
            <Link
              to={LEADS_HREF_QUEUE_NEW}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
            >
              {t('app.leads.workspace.queue_new', { defaultValue: 'New' })}
              <IconArrowRight size={16} className="text-slate-400" aria-hidden />
            </Link>
            <Link
              to={LEADS_HREF_QUEUE_IN_PROGRESS}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
            >
              {t('app.leads.workspace.queue_in_progress', { defaultValue: 'In progress' })}
              <IconArrowRight size={16} className="text-slate-400" aria-hidden />
            </Link>
            <Link
              to={LEADS_HREF_QUEUE_WAITING}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
            >
              {t('app.leads.workspace.queue_waiting', { defaultValue: 'Waiting for reply' })}
              <IconArrowRight size={16} className="text-slate-400" aria-hidden />
            </Link>
            <Link
              to={LEADS_HREF_QUEUE_OVERDUE}
              className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
            >
              {t('app.leads.workspace.queue_overdue', { defaultValue: 'Overdue' })}
              <IconArrowRight size={16} className="text-slate-400" aria-hidden />
            </Link>
          </div>
        </section>

        <details className="rounded-xl border border-slate-200 bg-slate-50/90 px-3 py-2">
          <summary className="cursor-pointer select-none text-xs font-semibold text-slate-700">
            {t('app.leads.workspace.advanced_filters', { defaultValue: 'Advanced filters & view' })}
          </summary>
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
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
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
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
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
            <div
              className="inline-flex h-9 overflow-hidden rounded-lg border border-slate-300 bg-slate-100 p-0.5"
              role="group"
              aria-label={t('app.leads.workspace.view_switch')}
            >
              <button
                type="button"
                onClick={() => setWorkspaceView('table')}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                  workspaceView === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <IconTable size={14} />
                {t('app.leads.workspace.view_table')}
              </button>
              <button
                type="button"
                onClick={() => setWorkspaceView('kanban')}
                className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                  workspaceView === 'kanban' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <IconLayoutKanban size={14} />
                {t('app.leads.workspace.view_kanban')}
              </button>
            </div>
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
        </details>
      </header>

      <PageBreadcrumb className="max-w-5xl" />

      {filterBannerVisible && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-700">
              <span className="font-medium">{t('app.leads.inbox.banner.filtered')}</span>{' '}
              {[
                status ? statusLabels[status as LeadStatus] ?? status : null,
                stage ? stageLabels[stage as LeadStage] ?? stage : null,
                conversionRoot ? stageLabels[conversionRoot] ?? conversionRoot : null,
                lostReasonCode
                  ? `${t('app.leads.conversion_funnel.lost_reason_title')}: ${t(`app.leads.lost_reason.codes.${lostReasonCode}`)}`
                  : null,
                lostFromCrmStage
                  ? t('app.leads.conversion_funnel.lost_from_filter_banner', {
                      values: {
                        stage:
                          lostFromCrmStage === 'unknown'
                            ? t('app.leads.conversion_funnel.lost_from_stage_unknown')
                            : stageLabels[lostFromCrmStage as LeadStage] ?? lostFromCrmStage,
                      },
                    })
                  : null,
                nextAction ? nextActionOptions.find((o) => o.value === nextAction)?.label ?? nextAction : null,
                pipelineError ? formatLeadPipelineError(pipelineError, t) : null,
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
          {workspaceView === 'table' && selectedCount > 0 && (
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
          {workspaceView === 'table' ? (
            <>
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
                  <th>{t('app.leads.workspace.col_name', { defaultValue: 'Name' })}</th>
                  <th>{t('app.leads.table.contact')}</th>
                  <th>{t('app.leads.table.source')}</th>
                  <th>{vacancyColumnLabel}</th>
                  <th>{t('app.leads.table.status')}</th>
                  <th>{t('app.leads.table.next_action')}</th>
                  <th>{t('app.leads.workspace.col_actions', { defaultValue: 'Actions' })}</th>
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
                        retryLabel={t('common.retry')}
                        {...friendlyErrorBannerSecondary(
                          error,
                          CRM_APP_PATHS.settingsIntegrationsMeta,
                          t('app.leads.states.empty_cta_connect'),
                        )}
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
                          label: t('app.leads.states.empty_cta_connect'),
                          to: CRM_APP_PATHS.settingsIntegrationsMeta,
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
                    const isSelected = selectedLeadId === lead.id
                    const rowMetaProblem = isMetaProblemLead(lead)
                    const metaErrorCode = (lead.error ?? '').trim()
                    const leadSuggestion = rowMetaProblem ? getLeadErrorSuggestion(lead.error, t) : null
                    const openCredentialsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=credentials`
                    const openMappingHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=mapping`
                    const openSettingsHref = `${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=settings`

                    return (
                      <tr
                        key={lead.id}
                        className={isSelected ? 'bg-brand-50 hover:bg-brand-50' : 'hover:bg-slate-50'}
                        role="button"
                        tabIndex={0}
                        onClick={() => setSelectedLeadId(lead.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedLeadId(lead.id)
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
                        <td className="max-w-[200px] font-medium text-slate-900">
                          <div className="truncate">{contactName || lead.company_name || '—'}</div>
                          {lead.stage ? (
                            <div className="truncate text-[11px] font-normal text-slate-500">
                              {stageLabels[lead.stage] ?? lead.stage}
                            </div>
                          ) : null}
                        </td>
                        <td className="max-w-[180px] text-slate-700">
                          {contactPhone ? <div className="truncate text-sm">{contactPhone}</div> : null}
                          {contactEmail ? <div className="truncate text-xs text-slate-500">{contactEmail}</div> : null}
                          {!contactPhone && !contactEmail ? '—' : null}
                        </td>
                        <td className="text-slate-700">{lead.source || '—'}</td>
                        <td className="max-w-[160px] truncate text-slate-800">{lead.vacancy_title || lead.vacancy_id || '—'}</td>
                        <td>
                          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                            {statusLabels[lead.status] ?? lead.status}
                          </span>
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
                        <td className="max-w-[220px]">
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
                                    : t('admin.meta_leads.logs.actions.retry')}
                                </button>

                                {leadSuggestion?.tab === 'field_mapping' ? (
                                  <>
                                    <button
                                      type="button"
                                      className="btn-secondary rounded-lg px-2 py-1 text-[11px]"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        void handleRerouteMetaLeadFromError(lead.id, lead.company_id)
                                      }}
                                    >
                                      {t('admin.meta_leads.logs.actions.reroute')}
                                    </button>
                                    <Link
                                      to={openMappingHref}
                                      className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      {t('admin.meta_leads.tabs.mapping')}
                                    </Link>
                                  </>
                                ) : null}

                                {leadSuggestion?.tab === 'advanced' ? (
                                  <Link
                                    to={openCredentialsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('admin.meta_leads.tabs.credentials')}
                                  </Link>
                                ) : null}

                                {leadSuggestion?.tab === 'processing' ? (
                                  <Link
                                    to={openSettingsHref}
                                    className="text-xs text-slate-500 hover:text-brand-700 hover:underline"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('admin.meta_leads.tabs.settings')}
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
                              {leadSupportsManualProcess(lead) ? (
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
                          {lead.error ? (
                            <div className="mt-1 text-[11px] text-red-600">{formatLeadPipelineError(lead.error, t)}</div>
                          ) : null}
                        </td>
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
            </>
          ) : (
            <LeadsKanbanBoard
              base={{
                conversionRoot: conversionRoot || undefined,
                lostReasonCode: lostReasonCode || undefined,
                lostFromCrmStage: lostFromCrmStage || undefined,
                pipelineError: pipelineError || undefined,
                customFieldKey: customFieldKey.trim() || undefined,
                customFieldValue,
                q: leadSearch,
              }}
              stageLabels={stageLabels}
              onOpenLead={(id) => setSelectedLeadId(id)}
            />
          )}
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
                    <div className="truncate text-base font-semibold text-slate-900">
                      {selectedLead.normalized?.full_name ||
                        `${selectedLead.normalized?.first_name || ''} ${selectedLead.normalized?.last_name || ''}`.trim() ||
                        selectedLead.company_name ||
                        t('app.leads.inbox.lead')}
                    </div>
                    {selectedLead.normalized?.phone ? (
                      <div className="mt-1 text-sm text-slate-700">{selectedLead.normalized.phone}</div>
                    ) : null}
                    {selectedLead.normalized?.email ? (
                      <div className="mt-0.5 truncate text-xs text-slate-600">{selectedLead.normalized.email}</div>
                    ) : null}
                    <div className="mt-2 text-xs text-slate-600">
                      <span className="font-medium">{t('app.leads.table.source')}:</span> {selectedLead.source || '—'}
                    </div>
                    <div className="mt-1 text-xs text-slate-600">
                      <span className="font-medium">{t('app.leads.table.status')}:</span>{' '}
                      {statusLabels[selectedLead.status] ?? selectedLead.status}
                      {selectedLead.stage ? (
                        <>
                          {' · '}
                          <span className="font-medium">{t('app.leads.table.stage')}:</span>{' '}
                          {stageLabels[selectedLead.stage] ?? selectedLead.stage}
                        </>
                      ) : null}
                    </div>
                    <div className="mt-1 text-xs text-slate-600">
                      <span className="font-medium">{t('app.leads.table.next_action')}:</span>{' '}
                      {selectedLead.next_action_status === 'overdue'
                        ? t('app.leads.next_action.overdue')
                        : selectedLead.next_action_status === 'scheduled'
                          ? t('app.leads.next_action.scheduled')
                          : t('app.leads.next_action.no_next_action')}
                    </div>
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

                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedLead.normalized?.phone &&
                  String(selectedLead.normalized.phone).replace(/\D/g, '').length > 0 ? (
                    <a
                      href={`tel:${String(selectedLead.normalized.phone).replace(/\s/g, '')}`}
                      className="btn-primary inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold sm:flex-none"
                    >
                      <IconPhone size={18} stroke={1.75} aria-hidden />
                      {t('app.leads.inbox.action_call', { defaultValue: 'Call' })}
                    </a>
                  ) : null}
                  {selectedLead.normalized?.email && String(selectedLead.normalized.email).includes('@') ? (
                    <a
                      href={`mailto:${encodeURIComponent(selectedLead.normalized.email)}`}
                      className="btn-secondary inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold sm:flex-none"
                    >
                      <IconMail size={18} stroke={1.75} aria-hidden />
                      {t('app.leads.inbox.action_write', { defaultValue: 'Write' })}
                    </a>
                  ) : null}
                  {leadSupportsManualProcess(selectedLead) && !selectedLead.candidate_id ? (
                    <button
                      type="button"
                      className="btn-primary inline-flex min-w-[10rem] flex-1 items-center justify-center gap-1 rounded-lg px-3 py-2 text-sm font-semibold sm:flex-none"
                      disabled={processingLeadId === selectedLead.id}
                      onClick={() => void handleProcessLead(selectedLead.id)}
                    >
                      {processingLeadId === selectedLead.id
                        ? t('common.loading')
                        : t('app.leads.actions.convert_to_candidate', { defaultValue: 'Convert to candidate' })}
                    </button>
                  ) : null}
                  {selectedLead.candidate_id ? (
                    <Link
                      to={`${CRM_APP_PATHS.candidates}/${selectedLead.candidate_id}`}
                      className="btn-secondary inline-flex flex-1 items-center justify-center rounded-lg px-3 py-2 text-sm font-semibold sm:flex-none"
                    >
                      {t('app.leads.inbox.open_candidate', { defaultValue: 'Open candidate' })}
                    </Link>
                  ) : null}
                </div>
              </div>

              <div className="flex-1 overflow-auto p-3">
                <div className="space-y-3">
                  {selectedIsMetaProblemLead ? (
                    <div className="space-y-2">
                      <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
                      <LeadMetaProblemPanel lead={selectedLead} onRefreshed={onMetaProblemPanelRefreshed} />
                    </div>
                  ) : (
                    <LeadNextActionPlaybook lead={selectedLead} formatDueAt={formatDateValue} />
                  )}

                  <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-2">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                      {t('app.leads.inbox.details.qualification', { defaultValue: 'Fit & suggestions' })}
                    </summary>
                    <div className="mt-2">
                      <LeadQualificationSuggestionPanel
                        lead={selectedLead}
                        isServicesTenant={isServicesTenant}
                        onProcess={() => void handleProcessLead(selectedLead.id)}
                        processing={processingLeadId === selectedLead.id}
                      />
                    </div>
                  </details>

                  <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-2">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                      {t('app.leads.inbox.details.crm_fields', { defaultValue: 'Stage & assignment' })}
                    </summary>
                    <div className="mt-2 space-y-2">
                      <label className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        <span className="font-medium shrink-0">{t('app.leads.table.stage')}</span>
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
                      <LeadLostReasonReadonly
                        lead={selectedLead}
                        formatAt={formatDateValue}
                        className="border-t border-slate-200 pt-2 text-xs text-slate-700"
                      />
                    </div>
                  </details>

                  <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-2" open>
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                      {t('app.leads.inbox.composer.followup')}
                    </summary>
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
                  </details>

                  <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-2">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                      {t('app.reminders.title')}
                    </summary>
                    <div className="mt-2 space-y-2">
                      <button
                        type="button"
                        className="btn-secondary h-8 rounded-lg px-2 text-xs"
                        onClick={() => selectedLeadId && void loadLeadReminders(selectedLeadId)}
                      >
                        {t('common.actions.refresh')}
                      </button>
                      {remindersLoading ? (
                        <div className="py-3 text-center text-xs text-slate-500">{t('common.loading')}</div>
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
                                  <div className="truncate text-sm font-medium text-slate-900">
                                    {r.title || t('app.reminders.item.untitled')}
                                  </div>
                                  <div className="mt-0.5 text-xs text-slate-600">
                                    <span className="font-medium">{t('app.reminders.fields.due_at')}:</span>{' '}
                                    {formatDateValue(r.due_at)}
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
                  </details>

                  <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-2">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-700">
                      {t('app.leads.inbox.history.timeline_title')}
                    </summary>
                    <div className="mt-2 space-y-2 text-xs">
                      <div className="rounded-lg border border-slate-200 bg-white p-3 text-slate-600">
                        <div>
                          {companyColumnLabel}: {selectedLead.company_name || selectedLead.company_id || '—'}
                        </div>
                        <div>
                          {vacancyColumnLabel}: {selectedLead.vacancy_title || selectedLead.vacancy_id || '—'}
                        </div>
                        <div>
                          {t('app.leads.table.created')}: {formatDateValue(selectedLead.created_at)}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary h-7 rounded-lg px-2 text-[11px]"
                        onClick={() => selectedLeadId && void loadLeadTimeline(selectedLeadId)}
                      >
                        {t('common.actions.refresh')}
                      </button>
                      {timelineLoading ? (
                        <div className="py-3 text-center text-[11px] text-slate-500">{t('common.loading')}</div>
                      ) : timelineError ? (
                        <div className="rounded border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-700">
                          {timelineError}
                        </div>
                      ) : timelineItems.length === 0 ? (
                        <div className="rounded border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-500">
                          {t('app.leads.inbox.history.empty')}
                        </div>
                      ) : (
                        <ul className="space-y-1.5">
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
                                  <div className="mt-0.5 truncate text-[11px] text-slate-600">{ev.description}</div>
                                ) : null}
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </details>
                </div>
              </div>
            </div>
          )}
        </aside>
      </section>
    </div>
  )
}
