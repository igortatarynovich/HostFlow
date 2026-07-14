import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  completeActivity,
  confirmLeadVacancy,
  convertClientLeadToClient,
  createActivity,
  deleteLead,
  getLead,
  getLeadTimeline,
  getOnboardingStatus,
  listReminders,
  processLead,
  submitLeadIntakeDecision,
  updateLeadStage,
} from '../api/client'
import type { Lead, LeadStage, LeadStatus } from '../api/types'
import type { ReminderRecord } from '../api/types/notification'
import LeadMetaProblemPanel from '../components/leads/LeadMetaProblemPanel'
import LeadQualificationSuggestionPanel from '../components/leads/LeadQualificationSuggestionPanel'
import LeadQualificationSummaryCard from '../components/leads/LeadQualificationSummaryCard'
import LeadNextActionPlaybook from '../components/leads/LeadNextActionPlaybook'
import { NextActionBadge } from '../components/candidate/NextActionBadge'
import { useLeadNextAction } from '../components/lead/useLeadNextAction'
import ClientLeadDetailView from '../components/leads/ClientLeadDetailView'
import {
  RecruitmentAgencyAuditDetailView,
  RecruitmentAgencyIntakeDetailView,
} from './LeadDetailRecruitmentAgencyViews'
import LeadLostReasonReadonly from '../components/leads/LeadLostReasonReadonly'
import LostReasonForLostStageModal from '../components/leads/LostReasonForLostStageModal'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useToast } from '../components/Toast'
import { useI18n } from '../i18n'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import LeadIntakeResolutionPanel from '../components/leads/LeadIntakeResolutionPanel'
import SalesQuestionnairePanel from '../components/leads/SalesQuestionnairePanel'
import SalesQuestionnaireSummaryRail from '../components/leads/SalesQuestionnaireSummaryRail'
import {
  leadIntakeWorkspaceBlocking,
  manualProcessBlockHint,
  manualProcessBlockedUserMessage,
  parseProcessBlockedCodeFromAxios,
} from '../utils/intakeResolution'
import { CRM_STAGE_VALUES, leadAssignmentLocked, leadSupportsManualProcess } from '../utils/leadCrm'
import { leadIntakeColumnStatusKey } from '../utils/leadIntakeWorkspace'
import { leadIntakeResolutionRejected } from '../utils/intakeResolution'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { useAuth } from '../store/auth'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { serviceOrderWorkspacePath } from '../modules/services/utils'
import { formatLeadPipelineError } from '../utils/leadPipelineErrors'
import { readSalesQuestionnaireSummary } from '../utils/salesQuestionnaire'

const LOCALE_TO_DATE = {
  en: 'en-US',
  ru: 'ru-RU',
  pl: 'pl-PL',
} as const

const DATE_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
}

type TimelineItem = {
  at: string
  kind: string
  source: string
  title?: string | null
  description?: string | null
}

function formatDateValue(iso: string | null | undefined, locale: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const loc = LOCALE_TO_DATE[locale as keyof typeof LOCALE_TO_DATE] ?? 'en-US'
  return d.toLocaleString(loc, DATE_FORMAT_OPTIONS)
}

function jsonPreview(value: unknown): string {
  try {
    return JSON.stringify(value ?? null, null, 2)
  } catch {
    return String(value)
  }
}

function formatCustomFieldCell(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return jsonPreview(v)
  return String(v)
}

function leadProcessingModeLabel(t: (key: string) => string, modeKey: string): string {
  const k = `app.leads.detail.ingest_processing.mode_labels.${modeKey}`
  const tr = t(k)
  return tr === k ? modeKey : tr
}

/**
 * §2.10 / §2.11: tie Source & ingest to Assisted / Automatic semantics using stamps on normalized.
 */
function LeadIngestProcessingCallout({ normalized }: { normalized: Record<string, unknown> }) {
  const { t } = useI18n()
  const rawMode = normalized.leads_processing_mode_v1
  const mode = typeof rawMode === 'string' ? rawMode.trim().toLowerCase() : ''
  if (mode !== 'manual' && mode !== 'assisted' && mode !== 'automatic') return null

  const rawConfigured = normalized.leads_processing_mode_configured_v1
  const configured =
    typeof rawConfigured === 'string' ? rawConfigured.trim().toLowerCase() : ''
  const modeMismatch =
    Boolean(configured) &&
    (configured === 'manual' || configured === 'assisted' || configured === 'automatic') &&
    configured !== mode

  const downgrade =
    typeof normalized.leads_processing_mode_downgrade_v1 === 'string'
      ? normalized.leads_processing_mode_downgrade_v1
      : null

  const ac = normalized.leads_auto_convert_on_fit_effective_v1
  const autoconvKnown = ac === true || ac === false
  const autoconv = ac === true

  const modeLineKey = `app.leads.detail.ingest_processing.modes.${mode}`
  const modeSentence = t(modeLineKey)
  const modeBody = modeSentence === modeLineKey ? mode : modeSentence

  return (
    <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
      <p>
        <span className="font-semibold text-slate-800">{t('app.leads.detail.ingest_processing.title')}</span>{' '}
        {modeBody}
      </p>
      {modeMismatch ? (
        <p className="mt-1 text-slate-600">
          {t('app.leads.detail.ingest_processing.configured_effective_mismatch', {
            values: {
              configured: leadProcessingModeLabel(t, configured),
              effective: leadProcessingModeLabel(t, mode),
            },
          })}
        </p>
      ) : null}
      {mode === 'assisted' ? (
        <p className="mt-1 text-slate-600">{t('app.leads.detail.ingest_processing.assisted_link')}</p>
      ) : null}
      {mode === 'automatic' && autoconvKnown && !autoconv ? (
        <p className="mt-1 text-amber-900/90">{t('app.leads.detail.ingest_processing.auto_convert_off')}</p>
      ) : null}
      {downgrade === 'team_plan_required' ? (
        <p className="mt-1 text-amber-900/90">{t('app.leads.detail.ingest_processing.downgrade_team')}</p>
      ) : null}
    </div>
  )
}

export default function LeadDetailPage() {
  const { leadId } = useParams<{ leadId: string }>()
  const navigate = useNavigate()
  const { me } = useAuth()
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()

  const [onboardingBusinessType, setOnboardingBusinessType] = useState<string | null>(null)
  const [lead, setLead] = useState<Lead | null>(null)
  const [loadError, setLoadError] = useState<FriendlyErrorInfo | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [timelineItems, setTimelineItems] = useState<TimelineItem[]>([])
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [timelineError, setTimelineError] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [remindersLoading, setRemindersLoading] = useState(false)
  const [remindersError, setRemindersError] = useState<string | null>(null)
  const [reminderTitle, setReminderTitle] = useState('')
  const [reminderDueAt, setReminderDueAt] = useState(() => new Date(Date.now() + 60 * 60 * 1000).toISOString().slice(0, 16))
  const [reminderOffset, setReminderOffset] = useState(15)
  const [patching, setPatching] = useState(false)
  const [lostStagePrompt, setLostStagePrompt] = useState<{ previousStage: string | null } | null>(null)
  const [deletingLead, setDeletingLead] = useState(false)
  const [convertingClientLead, setConvertingClientLead] = useState(false)
  const [quickRemindBusy, setQuickRemindBusy] = useState(false)
  const [routingConfirming, setRoutingConfirming] = useState(false)
  const [poolBusyDetail, setPoolBusyDetail] = useState(false)

  // G-8 stage 2.0: refresh tick the page bumps after a stage / process /
  // assignment mutation so the per-lead next-action badge re-resolves
  // without holding a `refetch` reference. Keeps the hook surface read-only.
  const [nextActionTick, setNextActionTick] = useState(0)
  const bumpNextActionTick = useCallback(() => setNextActionTick((n) => n + 1), [])
  const isServicesTenant = onboardingBusinessType === 'services'

  const {
    data: leadNextAction,
    loading: leadNextActionLoading,
    error: leadNextActionError,
  } = useLeadNextAction(isServicesTenant ? (leadId ?? null) : null, nextActionTick)
  const canDeleteLead = Boolean(me?.role && me.role !== 'viewer')

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const st = await getOnboardingStatus()
        if (!cancelled) {
          setOnboardingBusinessType(st?.business_type ?? 'agency')
        }
      } catch {
        if (!cancelled) setOnboardingBusinessType('agency')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setLostStagePrompt(null)
  }, [leadId])

  const loadLead = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!leadId) return
      const silent = Boolean(opts?.silent)
      if (!silent) {
        setLoading(true)
        setLoadError(null)
        setNotFound(false)
      }
      try {
        const data = await getLead(leadId)
        setLead(data)
        if (silent) {
          setLoadError(null)
        }
      } catch (err: unknown) {
        if (silent) return
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 404) {
          setNotFound(true)
          setLead(null)
        } else if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.load_failed'))) {
          setLead(null)
          setLoadError(null)
        } else {
          setLead(null)
          setLoadError(getFriendlyErrorInfo(err, t('app.leads.detail.load_failed'), t))
        }
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [leadId, planLimitModal, t],
  )

  const loadTimeline = useCallback(async () => {
    if (!leadId) return
    setTimelineLoading(true)
    setTimelineError(null)
    try {
      const res = await getLeadTimeline(leadId)
      const items = Array.isArray(res?.items) ? res.items : []
      setTimelineItems(
        items.map((item: Record<string, unknown>) => ({
          at: String(item.at ?? ''),
          kind: String(item.kind || ''),
          source: String(item.source || ''),
          title: item.title != null ? String(item.title) : null,
          description: item.description != null ? String(item.description) : null,
        })),
      )
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.timeline_load_failed'))) {
        setTimelineError(null)
      } else {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.leads.detail.timeline_load_failed')
        setTimelineError(String(detail))
      }
    } finally {
      setTimelineLoading(false)
    }
  }, [leadId, planLimitModal, t])

  useEffect(() => {
    void loadLead()
  }, [loadLead])

  useEffect(() => {
    if (lead?.id) void loadTimeline()
  }, [lead?.id, loadTimeline])

  const refreshLeadAndTimeline = useCallback(async () => {
    await loadLead({ silent: true })
    void loadTimeline()
  }, [loadLead, loadTimeline])

  const loadLeadReminders = useCallback(async () => {
    if (!leadId) return
    setRemindersLoading(true)
    setRemindersError(null)
    try {
      const res = await listReminders({ entityType: 'lead', entityId: leadId, status: ['pending', 'new', 'overdue'] })
      const list = Array.isArray(res?.items) ? (res.items as ReminderRecord[]) : []
      setReminders(list)
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.load'))) {
        setRemindersError(null)
      } else {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.reminders.errors.load')
        setRemindersError(typeof detail === 'string' ? detail : String(detail))
      }
      setReminders([])
    } finally {
      setRemindersLoading(false)
    }
  }, [leadId, planLimitModal, t])

  useEffect(() => {
    if (lead?.id) void loadLeadReminders()
  }, [lead?.id, loadLeadReminders])

  const handleCreateLeadReminder = useCallback(async () => {
    if (!leadId || !reminderTitle.trim() || !reminderDueAt) return
    try {
      const due = new Date(reminderDueAt)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createActivity({
        title: reminderTitle.trim(),
        description: '',
        type: 'custom',
        entity_type: 'lead',
        entity_id: leadId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        source: 'manual',
      })
      setReminderTitle('')
      setReminderDueAt(new Date(due.getTime() + 60 * 60 * 1000).toISOString().slice(0, 16))
      await loadLeadReminders()
      notify({ title: t('app.reminders.messages.created'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.reminders.errors.create')
      notify({ title: typeof detail === 'string' ? detail : String(detail), variant: 'error' })
    }
  }, [leadId, loadLeadReminders, notify, planLimitModal, reminderDueAt, reminderOffset, reminderTitle, t])

  const handleQuickRemindClient = useCallback(async () => {
    if (!leadId) return
    setQuickRemindBusy(true)
    try {
      const due = new Date(Date.now() + 24 * 60 * 60 * 1000)
      const remindAt = new Date(due.getTime() - reminderOffset * 60 * 1000)
      await createActivity({
        title: t('app.leads.detail.remind_client.default_title'),
        description: '',
        type: 'custom',
        entity_type: 'lead',
        entity_id: leadId,
        due_at: due.toISOString(),
        remind_at: remindAt.toISOString(),
        priority: 'normal',
        source: 'manual',
      })
      await loadLeadReminders()
      notify({ title: t('app.reminders.messages.created'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.create'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.reminders.errors.create')
      notify({ title: typeof detail === 'string' ? detail : String(detail), variant: 'error' })
    } finally {
      setQuickRemindBusy(false)
    }
  }, [leadId, loadLeadReminders, notify, planLimitModal, reminderOffset, t])

  const handleCompleteReminder = useCallback(
    async (id: string) => {
      try {
        await completeActivity(id)
        await loadLeadReminders()
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.reminders.errors.complete'))) {
          return
        }
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.reminders.errors.complete')
        notify({ title: typeof detail === 'string' ? detail : String(detail), variant: 'error' })
      }
    },
    [loadLeadReminders, notify, planLimitModal, t],
  )

  const statusLabels = useMemo(
    () =>
      ({
        new: t('app.leads.statuses.new'),
        processed: t('app.leads.statuses.processed'),
        duplicated: t('app.leads.statuses.duplicated'),
        needs_routing: t('app.leads.statuses.needs_routing'),
        failed: t('app.leads.statuses.failed'),
        duplicate_review: t('app.leads.statuses.duplicate_review'),
        rejected: t('app.leads.statuses.rejected'),
      }) satisfies Record<LeadStatus, string>,
    [t],
  )

  const stageLabels = useMemo(
    () =>
      ({
        new: t('app.leads.stages.new'),
        contacted: t('app.leads.stages.contacted'),
        qualified: t('app.leads.stages.qualified'),
        converted: t('app.leads.stages.converted'),
        lost: t('app.leads.stages.lost'),
      }) satisfies Record<LeadStage, string>,
    [t],
  )

  const companyLabel = isServicesTenant ? t('app.leads.table.client') : t('app.leads.table.company')
  const vacancyLabel = isServicesTenant ? t('app.leads.table.service_order') : t('app.leads.table.vacancy')

  const normalized = lead?.normalized && typeof lead.normalized === 'object' && !Array.isArray(lead.normalized) ? lead.normalized : {}
  const isClientLead = Boolean(lead && lead.lead_type === 'client' && lead.lead_target_type === 'client_lead')
  const showSalesQuestionnaire = Boolean(isServicesTenant && lead && lead.lead_type === 'client')
  const salesQuestionnaireSummary = lead ? readSalesQuestionnaireSummary(lead) : {}
  const showSalesQuestionnaireSummary = showSalesQuestionnaire && Object.keys(salesQuestionnaireSummary).length > 0
  const leadRejected = Boolean(lead && leadIntakeResolutionRejected(lead))
  const crmStageValues = useMemo(
    () => (leadRejected ? CRM_STAGE_VALUES.filter((v) => v !== 'lost') : CRM_STAGE_VALUES),
    [leadRejected],
  )
  const contactName =
    (normalized as Record<string, unknown>).full_name ||
    `${(normalized as Record<string, unknown>).first_name || ''} ${(normalized as Record<string, unknown>).last_name || ''}`.trim()
  const contactEmail = (normalized as Record<string, unknown>).email
  const contactPhone = (normalized as Record<string, unknown>).phone
  const contactLine = [contactName, contactEmail, contactPhone].filter(Boolean).join(' · ') || '—'

  const leadDisplayName = useMemo(() => {
    if (lead?.lead_type === 'client' && lead.lead_target_type === 'client_lead') {
      const profile = (normalized as Record<string, unknown>).company_profile
      const companyProfile = profile && typeof profile === 'object' && !Array.isArray(profile) ? (profile as Record<string, unknown>) : {}
      const fromProfile = typeof companyProfile.name === 'string' ? companyProfile.name.trim() : ''
      if (fromProfile) return fromProfile
      const cnRaw = (normalized as Record<string, unknown>).company_name
      const cn = typeof cnRaw === 'string' ? cnRaw.trim() : ''
      if (cn) return cn
      if (lead.company_name) return lead.company_name
    }
    const fn = (normalized as Record<string, unknown>).full_name
    if (typeof fn === 'string' && fn.trim()) return fn.trim()
    const first = typeof (normalized as Record<string, unknown>).first_name === 'string' ? (normalized as Record<string, unknown>).first_name : ''
    const last = typeof (normalized as Record<string, unknown>).last_name === 'string' ? (normalized as Record<string, unknown>).last_name : ''
    const composed = `${first} ${last}`.trim()
    if (composed) return composed
    const emRaw = (normalized as Record<string, unknown>).email
    const em = typeof emRaw === 'string' ? emRaw.trim() : ''
    if (em) return em
    const phRaw = (normalized as Record<string, unknown>).phone
    const ph = typeof phRaw === 'string' ? phRaw.trim() : ''
    if (ph) return ph
    return t('app.leads.detail.title')
  }, [lead?.company_name, lead?.lead_target_type, lead?.lead_type, normalized, t])

  const canManualProcessLead = leadSupportsManualProcess(lead)
  const processBlockCode = lead ? manualProcessBlockHint(lead) : null
  const intakeWorkspaceBlocking = useMemo(
    () => Boolean(lead && leadIntakeWorkspaceBlocking(lead, isServicesTenant)),
    [isServicesTenant, lead],
  )

  const recruitmentLeadConverted = Boolean(lead && !isServicesTenant && lead.candidate_id)

  const intakeNote = useMemo(() => {
    if (!lead?.normalized || typeof lead.normalized !== 'object' || Array.isArray(lead.normalized)) return null
    const ir = (lead.normalized as Record<string, unknown>).intake_resolution_v1
    if (!ir || typeof ir !== 'object' || Array.isArray(ir)) return null
    const note = String((ir as { note?: unknown }).note ?? '').trim()
    return note || null
  }, [lead?.normalized])

  const intakeStatusLabel = useMemo(() => {
    if (!lead || isServicesTenant) return ''
    const k = leadIntakeColumnStatusKey(lead, false)
    const tr = t(k)
    return tr === k ? String(lead.status) : tr
  }, [isServicesTenant, lead, t])

  const customFieldsEntries = useMemo(() => {
    const raw = lead?.custom_fields
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return []
    return Object.entries(raw as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b))
  }, [lead?.custom_fields])

  const runProcessLead = useCallback(async (explicitId?: string) => {
    const id = explicitId ?? lead?.id
    if (!id) return
    setProcessing(true)
    try {
      const result = await processLead(id)
      await loadLead({ silent: true })
      void loadTimeline()
      bumpNextActionTick()
      if (result?.status === 'needs_routing') {
        notify({
          title: t('app.leads.messages.needs_routing'),
          description:
            typeof result?.error === 'string' && result.error.trim()
              ? formatLeadPipelineError(result.error, t)
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
              : t('app.leads.messages.process_failed'),
          variant: 'error',
        })
      }
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.messages.process_failed'))) {
        return
      }
      const blocked = parseProcessBlockedCodeFromAxios(err)
      if (blocked) {
        notify({
          title: manualProcessBlockedUserMessage(t, blocked),
          variant: 'warning',
        })
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.messages.process_failed')
      notify({ title: typeof detail === 'string' ? detail : String(detail), variant: 'error' })
    } finally {
      setProcessing(false)
    }
  }, [lead?.id, loadLead, loadTimeline, notify, planLimitModal, t, bumpNextActionTick])

  const handleProcess = useCallback(() => void runProcessLead(), [runProcessLead])

  const handleConfirmLeadRoutingDetail = useCallback(
    async (vacancyId: string, thenProcess: boolean) => {
      if (!lead?.id) return
      setRoutingConfirming(true)
      try {
        const updated = await confirmLeadVacancy(lead.id, { vacancy_id: vacancyId })
        setLead(updated)
        bumpNextActionTick()
        void loadTimeline()
        notify({ title: t('app.leads.detail.intake_resolution.confirm_success'), variant: 'success' })
        if (thenProcess) {
          await runProcessLead(updated.id)
        }
      } catch (err: unknown) {
        if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.confirm_failed'))) {
          return
        }
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.leads.detail.intake_resolution.confirm_failed')
        notify({
          title: typeof detail === 'string' ? detail : JSON.stringify(detail),
          variant: 'error',
        })
      } finally {
        setRoutingConfirming(false)
      }
    },
    [bumpNextActionTick, lead?.id, loadTimeline, notify, planLimitModal, runProcessLead, t],
  )

  const handlePoolDetail = useCallback(async () => {
    if (!lead?.id) return
    setPoolBusyDetail(true)
    try {
      const updated = await submitLeadIntakeDecision(lead.id, { decision: 'pool' })
      setLead(updated)
      bumpNextActionTick()
      void loadTimeline()
      notify({ title: t('app.leads.detail.intake_resolution.intake_actions.success'), variant: 'success' })
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.intake_resolution.intake_actions.failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.intake_resolution.intake_actions.failed')
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setPoolBusyDetail(false)
    }
  }, [bumpNextActionTick, lead?.id, loadTimeline, notify, planLimitModal, t])

  const handleDetailStageChange = useCallback(
    async (nextRaw: string) => {
      if (!lead?.id) return
      const next = (nextRaw || null) as LeadStage | null
      const cur = lead.stage ?? null
      if (String(cur || '') === String(next || '')) return
      setPatching(true)
      try {
        const updated = (await updateLeadStage(lead.id, { stage: next })) as Lead
        setLead(updated)
        bumpNextActionTick()
        notify({
          title: t('app.leads.inbox.stage_updated'),
          variant: 'success',
        })
        void loadTimeline()
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
        setPatching(false)
      }
    },
    [lead, loadTimeline, notify, planLimitModal, t, bumpNextActionTick],
  )

  const handleDetailStageSelect = useCallback(
    (nextRaw: string) => {
      if (!lead?.id) return
      const next = nextRaw || ''
      if (next === 'lost') {
        if (leadIntakeResolutionRejected(lead)) return
        setLostStagePrompt({ previousStage: lead.stage ?? null })
        return
      }
      setLostStagePrompt(null)
      void handleDetailStageChange(next)
    },
    [handleDetailStageChange, lead, lead?.id, lead?.stage],
  )

  const cancelLostStagePrompt = useCallback(() => setLostStagePrompt(null), [])

  const confirmLostStageFromModal = useCallback(
    async (p: { lost_reason_code: string; lost_reason_note: string }) => {
      if (!lead?.id) return
      setPatching(true)
      try {
        const updated = (await updateLeadStage(lead.id, {
          stage: 'lost',
          lost_reason_code: p.lost_reason_code,
          lost_reason_note: p.lost_reason_note || undefined,
        })) as Lead
        setLostStagePrompt(null)
        setLead(updated)
        bumpNextActionTick()
        notify({
          title: t('app.leads.inbox.stage_updated'),
          variant: 'success',
        })
        void loadTimeline()
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
        setPatching(false)
      }
    },
    [lead?.id, loadTimeline, notify, planLimitModal, t, bumpNextActionTick],
  )

  const handleConvertClientLead = useCallback(async () => {
    if (!lead?.id) return
    setConvertingClientLead(true)
    try {
      const updated = await convertClientLeadToClient(lead.id)
      setLead(updated)
      bumpNextActionTick()
      const clientId = String(updated.converted_client_id || '').trim()
      notify({ title: t('app.clients.created_from_lead', { defaultValue: 'Клиент создан из анкеты' }), variant: 'success' })
      void loadTimeline()
      if (clientId) {
        navigate(`${CRM_APP_PATHS.agencyClients}/${clientId}?ctab=overview`)
      }
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, 'Не удалось создать клиента')) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        'Не удалось создать клиента'
      notify({ title: typeof detail === 'string' ? detail : JSON.stringify(detail), variant: 'error' })
    } finally {
      setConvertingClientLead(false)
    }
  }, [bumpNextActionTick, lead?.id, loadTimeline, navigate, notify, planLimitModal, t])

  const handleDeleteLead = useCallback(async () => {
    if (!leadId) return
    if (!window.confirm(t('app.leads.detail.delete_confirm'))) return
    setDeletingLead(true)
    try {
      await deleteLead(leadId)
      notify({ title: t('app.leads.detail.delete_success'), variant: 'success' })
      navigate(CRM_APP_PATHS.leads)
    } catch (err: unknown) {
      if (planLimitModal?.showPlanLimitIfNeeded(err, t('app.leads.detail.delete_failed'))) {
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.leads.detail.delete_failed')
      notify({ title: typeof detail === 'string' ? detail : String(detail), variant: 'error' })
    } finally {
      setDeletingLead(false)
    }
  }, [leadId, navigate, notify, planLimitModal, t])

  const handleDetailAssignmentLockToggle = useCallback(
    async (locked: boolean) => {
      if (!lead?.id) return
      setPatching(true)
      try {
        const updated = (await updateLeadStage(lead.id, { assignment_locked: locked })) as Lead
        setLead(updated)
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
        setPatching(false)
      }
    },
    [lead?.id, notify, planLimitModal, t],
  )

  if (!leadId) {
    return (
      <PageShell>
        <PageShellHeader>
          <PageHeader breadcrumbCurrentLabel={t('app.leads.detail.missing_id')} kind="browse" />
        </PageShellHeader>
        <div className="mx-4 text-sm text-slate-600">
          <Link to={CRM_APP_PATHS.leads} className="text-brand-700 hover:underline">
            {t('app.leads.detail.back_to_list')}
          </Link>
        </div>
      </PageShell>
    )
  }

  const clientLeadConvertedId =
    lead?.converted_client_id != null ? String(lead.converted_client_id).trim() : ''

  const clientLeadSecondaryActions =
    lead && isClientLead && !loading && !notFound ? (
      <>
        {!leadRejected && !clientLeadConvertedId ? (
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={convertingClientLead || patching}
            onClick={() => void handleConvertClientLead()}
          >
            {convertingClientLead ? 'Создаём…' : 'Создать клиента'}
          </button>
        ) : null}
        {!leadRejected && !clientLeadConvertedId ? (
          <>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={patching || convertingClientLead}
              onClick={() => void handleDetailStageSelect('contacted')}
            >
              Позвонил
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={patching || convertingClientLead}
              onClick={() => void handleDetailStageSelect('qualified')}
            >
              Заинтересован
            </button>
            <button
              type="button"
              className="btn-danger btn-sm"
              disabled={patching || convertingClientLead}
              onClick={() => void handleDetailStageSelect('lost')}
            >
              Закрыть запрос
            </button>
          </>
        ) : null}
        {canDeleteLead ? (
          <button
            type="button"
            className="btn-danger btn-sm"
            disabled={deletingLead || patching || convertingClientLead}
            onClick={() => void handleDeleteLead()}
          >
            {deletingLead ? t('common.loading') : t('app.leads.detail.delete_lead')}
          </button>
        ) : null}
      </>
    ) : null

  const leadDetailSecondaryActions =
    lead && !loading && !notFound && !isClientLead ? (
      <>
        {canManualProcessLead && !isServicesTenant && !lead.candidate_id ? (
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={processing || Boolean(processBlockCode)}
            title={processBlockCode ? manualProcessBlockedUserMessage(t, processBlockCode) : undefined}
            onClick={() => void handleProcess()}
          >
            {processing ? t('common.loading') : t('app.leads.actions.process')}
          </button>
        ) : null}
        {!intakeWorkspaceBlocking && !recruitmentLeadConverted && !isClientLead ? (
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={quickRemindBusy || patching || processing || deletingLead}
            onClick={() => void handleQuickRemindClient()}
            title={t('app.leads.detail.remind_client.hint')}
          >
            {quickRemindBusy ? t('app.leads.detail.remind_client.busy') : t('app.leads.detail.remind_client.cta')}
          </button>
        ) : null}
        {!isServicesTenant && lead.candidate_id ? (
          <Link to={`${CRM_APP_PATHS.candidates}/${lead.candidate_id}`} className="btn-secondary btn-sm">
            {t('app.leads.table.candidate')}
          </Link>
        ) : null}
        {isServicesTenant && lead.outcome_entity_id ? (
          <Link to={`${CRM_APP_PATHS.agencyClients}/${lead.outcome_entity_id}`} className="btn-secondary btn-sm">
            {lead.outcome_entity_name || companyLabel}
          </Link>
        ) : null}
        {isServicesTenant && lead.service_order_id ? (
          <Link
            to={serviceOrderWorkspacePath(String(lead.service_order_id), lead.company_id)}
            className="btn-secondary btn-sm"
          >
            {t('app.leads.actions.open_service_order')}
          </Link>
        ) : null}
        {canDeleteLead ? (
          <button
            type="button"
            className="btn-danger btn-sm"
            disabled={deletingLead || patching || processing}
            onClick={() => void handleDeleteLead()}
          >
            {deletingLead ? t('common.loading') : t('app.leads.detail.delete_lead')}
          </button>
        ) : null}
      </>
    ) : null

  return (
    <PageShell>
      <PageShellHeader>
        {loading ? (
          <PageHeader breadcrumbCurrentLabel={t('common.loading')} kind="browse" />
        ) : lead ? (
          <PageHeader
            breadcrumbCurrentLabel={leadDisplayName}
            subtitle={
              <div className="flex flex-wrap items-center gap-2">
                {!isClientLead && contactLine !== '—' ? <span>{contactLine}</span> : null}
                {[lead.company_name, lead.vacancy_title].filter(Boolean).join(' · ') ? (
                  <span>{[lead.company_name, lead.vacancy_title].filter(Boolean).join(' · ')}</span>
                ) : null}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {statusLabels[lead.status] ?? lead.status}
                </span>
                {!recruitmentLeadConverted && !isClientLead ? (
                  <NextActionBadge
                    dto={leadNextAction}
                    loading={leadNextActionLoading}
                    error={leadNextActionError}
                  />
                ) : null}
                {intakeStatusLabel && !isServicesTenant && !isClientLead ? (
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {intakeStatusLabel}
                  </span>
                ) : null}
              </div>
            }
            secondaryActions={isClientLead ? clientLeadSecondaryActions : leadDetailSecondaryActions}
          />
        ) : notFound ? (
          <PageHeader breadcrumbCurrentLabel={t('app.leads.detail.not_found')} kind="browse" />
        ) : null}
        {!loading && loadError ? (
          <div className="mt-2">
            <ErrorRecoveryBanner
              info={loadError}
              onRetry={() => void loadLead()}
              retryLabel={t('common.retry')}
              {...friendlyErrorBannerSecondary(
                loadError,
                CRM_APP_PATHS.settingsIntegrationsMeta,
                t('app.leads.states.empty_cta_connect'),
              )}
            />
          </div>
        ) : null}
      </PageShellHeader>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 pb-4">
        {!loading && notFound ? (
          <div className="card p-6 shadow-md shadow-slate-900/[0.04]">
            <h1 className="text-lg font-semibold text-slate-900">{t('app.leads.detail.not_found')}</h1>
            <p className="mt-2 text-sm text-slate-600">{t('app.leads.detail.not_found_hint')}</p>
          </div>
        ) : null}

        {!loading && !notFound && lead ? (
        <>
          {isClientLead ? (
            <>
            {showSalesQuestionnaire ? (
              <SalesQuestionnairePanel
                lead={lead}
                onLeadUpdated={(updated) => {
                  setLead(updated)
                  bumpNextActionTick()
                }}
              />
            ) : null}
            {showSalesQuestionnaireSummary ? <SalesQuestionnaireSummaryRail lead={lead} /> : null}
            <ClientLeadDetailView
              embedded
              lead={lead}
              formatDate={(iso) => formatDateValue(iso, locale)}
              converting={convertingClientLead}
              patching={patching}
              onConvert={() => void handleConvertClientLead()}
              onStage={(stage) => void handleDetailStageSelect(stage)}
              moreSection={
                <div className="space-y-6">
                  <LeadMetaProblemPanel lead={lead} onRefreshed={refreshLeadAndTimeline} />
                  <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
                  <LeadNextActionPlaybook lead={lead} formatDueAt={(iso) => formatDateValue(iso, locale)} />
                  <section>
                    <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('app.leads.detail.followup_title')}</h2>
                    <div className="space-y-3 rounded-xl border border-slate-100 bg-slate-50/70 p-4">
                      <input
                        className="input h-9 w-full max-w-xl rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                        value={reminderTitle}
                        onChange={(e) => setReminderTitle(e.target.value)}
                        placeholder={t('app.reminders.fields.title')}
                      />
                      <div className="grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
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
                        className="btn-primary h-9 rounded-lg px-4 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={!reminderTitle.trim() || !reminderDueAt}
                        onClick={() => void handleCreateLeadReminder()}
                      >
                        {t('app.reminders.actions.create')}
                      </button>
                      {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
                    </div>
                  </section>
                  <section>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <h2 className="text-sm font-semibold text-slate-900">{t('app.reminders.title')}</h2>
                      <button type="button" className="btn-secondary h-8 rounded-lg px-2 text-xs" onClick={() => void loadLeadReminders()}>
                        {t('common.actions.refresh')}
                      </button>
                    </div>
                    {remindersLoading ? (
                      <p className="text-sm text-slate-500">{t('common.loading')}</p>
                    ) : reminders.length === 0 ? (
                      <p className="text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
                    ) : (
                      <ul className="space-y-2">
                        {reminders.slice(0, 30).map((r) => (
                          <li key={r.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3">
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-slate-900">{r.title || t('app.reminders.item.untitled')}</div>
                              <div className="mt-0.5 text-xs text-slate-600">
                                {t('app.reminders.fields.due_at')}: {formatDateValue(r.due_at, locale)}
                              </div>
                            </div>
                            <button type="button" className="btn-secondary h-8 shrink-0 rounded-lg px-2 text-xs" onClick={() => void handleCompleteReminder(r.id)}>
                              {t('app.reminders.actions.complete')}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                  <section>
                    <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('app.leads.detail.timeline')}</h2>
                    {timelineLoading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
                    {timelineError && <p className="text-sm text-red-600">{timelineError}</p>}
                    {!timelineLoading && !timelineError && timelineItems.length === 0 && (
                      <p className="text-sm text-slate-500">{t('app.leads.detail.timeline_empty')}</p>
                    )}
                    {!timelineLoading && timelineItems.length > 0 && (
                      <ul className="space-y-3 border-l-2 border-slate-200 pl-4">
                        {timelineItems.map((item, idx) => (
                          <li key={`${item.at}-${item.kind}-${idx}`} className="relative">
                            <span className="absolute -left-[calc(0.5rem+2px)] top-1.5 h-2 w-2 rounded-full bg-brand-500" aria-hidden />
                            <div className="text-xs text-slate-500">{formatDateValue(item.at, locale)}</div>
                            <div className="text-sm font-medium text-slate-900">{item.title || item.kind || '—'}</div>
                            {item.description ? <div className="text-sm text-slate-600">{item.description}</div> : null}
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                  <section>
                    <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('app.leads.detail.source_ingest_title')}</h2>
                    <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                      <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                        {t('app.leads.detail.normalized_json')}
                      </summary>
                      <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                        {jsonPreview(normalized)}
                      </pre>
                    </details>
                    <details className="group mt-2 rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                      <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                        {t('app.leads.detail.raw_payload')}
                      </summary>
                      <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                        {jsonPreview(lead.payload)}
                      </pre>
                    </details>
                  </section>
                </div>
              }
            />
            </>
          ) : isServicesTenant ? (
          <>
          {showSalesQuestionnaire ? (
            <SalesQuestionnairePanel
              lead={lead}
              onLeadUpdated={(updated) => {
                setLead(updated)
                bumpNextActionTick()
              }}
            />
          ) : null}
          {showSalesQuestionnaireSummary ? <SalesQuestionnaireSummaryRail lead={lead} /> : null}
          {recruitmentLeadConverted ? (
            <div className="card border border-emerald-200/80 bg-emerald-50/40 p-4 shadow-sm sm:p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                {t('app.leads.intake_workspace.audit.badge')}
              </p>
              <p className="mt-1 text-sm text-slate-700">{t('app.leads.intake_workspace.audit.subtitle')}</p>
              <Link
                to={`${CRM_APP_PATHS.candidates}/${lead.candidate_id}`}
                className="btn-primary mt-3 inline-flex rounded-xl px-4 py-2 text-sm font-semibold"
              >
                {t('app.leads.intake_workspace.audit.open_candidate')}
              </Link>
            </div>
          ) : null}

          {intakeWorkspaceBlocking ? (
            <>
              <LeadIntakeResolutionPanel
                lead={lead}
                isServicesTenant={isServicesTenant}
                onLeadUpdated={(l) => {
                  setLead(l)
                  bumpNextActionTick()
                  void loadTimeline()
                }}
                onRequestProcess={() => void handleProcess()}
              />
              <LeadQualificationSummaryCard
                lead={lead}
                isServicesTenant={isServicesTenant}
                formatAt={(iso) => formatDateValue(iso, locale)}
                className="!border-0 bg-slate-50/60 shadow-none ring-1 ring-slate-900/[0.05]"
              />
            </>
          ) : (
            <>
              <LeadQualificationSummaryCard
                lead={lead}
                isServicesTenant={isServicesTenant}
                formatAt={(iso) => formatDateValue(iso, locale)}
              />
              <LeadQualificationSuggestionPanel
                lead={lead}
                isServicesTenant={isServicesTenant}
                onProcess={() => void handleProcess()}
                processing={processing}
                hideProcessButton
              />
              <LeadIntakeResolutionPanel
                lead={lead}
                isServicesTenant={isServicesTenant}
                onLeadUpdated={(l) => {
                  setLead(l)
                  bumpNextActionTick()
                  void loadTimeline()
                }}
                onRequestProcess={() => void handleProcess()}
              />
            </>
          )}

          {!intakeWorkspaceBlocking && !recruitmentLeadConverted ? (
            <LeadNextActionPlaybook lead={lead} formatDueAt={(iso) => formatDateValue(iso, locale)} />
          ) : null}

          <LeadMetaProblemPanel lead={lead} onRefreshed={refreshLeadAndTimeline} />

          {recruitmentLeadConverted ? (
            <details className="card overflow-hidden p-0 shadow-md shadow-slate-900/[0.03]">
              <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 marker:content-none hover:bg-slate-50/80 hover:text-slate-700 [&::-webkit-details-marker]:hidden">
                {t('app.leads.intake_workspace.section.more')}
              </summary>
              <div className="border-t border-slate-100 bg-white/95 p-4 sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                  <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                    <span className="shrink-0 font-medium">{t('app.leads.table.stage')}</span>
                    <select
                      className="input h-9 min-w-[11rem] rounded-lg border-slate-300 bg-white px-2 text-sm"
                      value={lostStagePrompt ? lostStagePrompt.previousStage ?? '' : lead.stage ?? ''}
                      disabled={patching || leadRejected}
                      onChange={(e) => void handleDetailStageSelect(e.target.value)}
                    >
                      <option value="">{t('app.leads.inbox.stage_unset')}</option>
                      {crmStageValues.map((v) => (
                        <option key={v} value={v}>
                          {stageLabels[v] ?? v}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="rounded border-slate-300"
                      checked={leadAssignmentLocked(lead)}
                      disabled={patching || leadRejected}
                      onChange={(e) => void handleDetailAssignmentLockToggle(e.target.checked)}
                    />
                    <span>{t('app.leads.inbox.lock_assignment')}</span>
                  </label>
                </div>
                <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
              </div>
            </details>
          ) : intakeWorkspaceBlocking ? (
            <details className="card overflow-hidden p-0 shadow-md shadow-slate-900/[0.03]">
              <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 marker:content-none hover:bg-slate-50/80 hover:text-slate-700 [&::-webkit-details-marker]:hidden">
                {t('app.leads.routing.expand_crm_tools')}
              </summary>
              <div className="border-t border-slate-100 bg-white/95 p-4 sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                  <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                    <span className="shrink-0 font-medium">{t('app.leads.table.stage')}</span>
                    <select
                      className="input h-9 min-w-[11rem] rounded-lg border-slate-300 bg-white px-2 text-sm"
                      value={lostStagePrompt ? lostStagePrompt.previousStage ?? '' : lead.stage ?? ''}
                      disabled={patching || leadRejected}
                      onChange={(e) => void handleDetailStageSelect(e.target.value)}
                    >
                      <option value="">{t('app.leads.inbox.stage_unset')}</option>
                      {crmStageValues.map((v) => (
                        <option key={v} value={v}>
                          {stageLabels[v] ?? v}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="rounded border-slate-300"
                      checked={leadAssignmentLocked(lead)}
                      disabled={patching || leadRejected}
                      onChange={(e) => void handleDetailAssignmentLockToggle(e.target.checked)}
                    />
                    <span>{t('app.leads.inbox.lock_assignment')}</span>
                  </label>
                </div>
                <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
              </div>
            </details>
          ) : (
            <div className="card p-4 shadow-md shadow-slate-900/[0.03] sm:p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                  <span className="shrink-0 font-medium">{t('app.leads.table.stage')}</span>
                  <select
                    className="input h-9 min-w-[11rem] rounded-lg border-slate-300 bg-white px-2 text-sm"
                    value={lostStagePrompt ? lostStagePrompt.previousStage ?? '' : lead.stage ?? ''}
                    disabled={patching || leadRejected}
                    onChange={(e) => void handleDetailStageSelect(e.target.value)}
                  >
                    <option value="">{t('app.leads.inbox.stage_unset')}</option>
                    {crmStageValues.map((v) => (
                      <option key={v} value={v}>
                        {stageLabels[v] ?? v}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="rounded border-slate-300"
                    checked={leadAssignmentLocked(lead)}
                    disabled={patching || leadRejected}
                    onChange={(e) => void handleDetailAssignmentLockToggle(e.target.checked)}
                  />
                  <span>{t('app.leads.inbox.lock_assignment')}</span>
                </label>
              </div>
              <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
            </div>
          )}

          <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6" aria-labelledby="lead-detail-fields-heading">
            <h2 id="lead-detail-fields-heading" className="mb-4 text-sm font-semibold text-slate-900">
              {t('app.leads.detail.details_heading')}
            </h2>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.created')}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{formatDateValue(lead.created_at, locale)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.status')}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{statusLabels[lead.status] ?? lead.status}</dd>
            </div>
            {!intakeWorkspaceBlocking && !recruitmentLeadConverted ? (
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.stage')}</dt>
                <dd className="mt-0.5 text-sm text-slate-900">
                  {lead.stage ? (
                    <span className="inline-flex items-center rounded-md bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-800">
                      {stageLabels[lead.stage] ?? lead.stage}
                    </span>
                  ) : (
                    '—'
                  )}
                </dd>
              </div>
            ) : null}
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{companyLabel}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{lead.company_name || lead.company_id || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{vacancyLabel}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{lead.vacancy_title || lead.vacancy_id || '—'}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.contact')}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{contactLine}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.source')}</dt>
              <dd className="mt-0.5 text-sm text-slate-900">{lead.source}</dd>
              {String(lead.source || '').toLowerCase() === 'public-intake' &&
              String(lead.external_id || '').toLowerCase().startsWith('public-intake:') ? (
                <p className="mt-1 text-xs text-slate-600">{t('app.leads.detail.public_intake_hint')}</p>
              ) : null}
            </div>
            {lead.error ? (
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.error')}</dt>
                <dd className="mt-0.5 text-sm text-red-600">{formatLeadPipelineError(lead.error, t)}</dd>
              </div>
            ) : null}
          </dl>
          </section>

          <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6">
            {recruitmentLeadConverted ? (
              <details>
                <summary className="cursor-pointer text-sm font-semibold text-slate-900">
                  {t('app.leads.detail.source_ingest_title')}
                </summary>
                <div className="mt-4 space-y-4">
                  <LeadIngestProcessingCallout normalized={normalized as Record<string, unknown>} />
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.source')}</dt>
                      <dd className="mt-0.5 text-sm text-slate-900">{lead.source || '—'}</dd>
                    </div>
                    {lead.ad_id != null ? (
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.detail.ad_id')}</dt>
                        <dd className="mt-0.5 font-mono text-sm text-slate-900">{String(lead.ad_id)}</dd>
                      </div>
                    ) : null}
                  </dl>
                  <div>
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                      {t('app.leads.detail.mapped_custom_fields')}
                    </h3>
                    {customFieldsEntries.length === 0 ? (
                      <p className="text-sm text-slate-500">{t('app.leads.detail.mapped_custom_fields_empty')}</p>
                    ) : (
                      <div className="overflow-x-auto rounded-md border border-slate-200">
                        <table className="min-w-full text-left text-sm">
                          <thead className="bg-slate-50 text-xs font-medium uppercase text-slate-600">
                            <tr>
                              <th className="px-3 py-2">{t('app.leads.detail.field_key')}</th>
                              <th className="px-3 py-2">{t('app.leads.detail.field_value')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {customFieldsEntries.map(([k, v]) => (
                              <tr key={k} className="border-t border-slate-100">
                                <td className="px-3 py-2 font-mono text-xs text-slate-800">{k}</td>
                                <td className="max-w-md whitespace-pre-wrap break-words px-3 py-2 text-slate-700">{formatCustomFieldCell(v)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                  <div className="space-y-2">
                    <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                      <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                        {t('app.leads.detail.normalized_json')}
                      </summary>
                      <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                        {jsonPreview(normalized)}
                      </pre>
                    </details>
                    <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                      <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                        {t('app.leads.detail.raw_payload')}
                      </summary>
                      <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                        {jsonPreview(lead.payload)}
                      </pre>
                    </details>
                  </div>
                </div>
              </details>
            ) : (
              <>
                <h2 className="mb-4 text-sm font-semibold text-slate-900">{t('app.leads.detail.source_ingest_title')}</h2>
                <LeadIngestProcessingCallout normalized={normalized as Record<string, unknown>} />
                <dl className="mb-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.source')}</dt>
                    <dd className="mt-0.5 text-sm text-slate-900">{lead.source || '—'}</dd>
                  </div>
                  {lead.ad_id != null ? (
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.detail.ad_id')}</dt>
                      <dd className="mt-0.5 font-mono text-sm text-slate-900">{String(lead.ad_id)}</dd>
                    </div>
                  ) : null}
                </dl>
                <div className="mb-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                    {t('app.leads.detail.mapped_custom_fields')}
                  </h3>
                  {customFieldsEntries.length === 0 ? (
                    <p className="text-sm text-slate-500">{t('app.leads.detail.mapped_custom_fields_empty')}</p>
                  ) : (
                    <div className="overflow-x-auto rounded-md border border-slate-200">
                      <table className="min-w-full text-left text-sm">
                        <thead className="bg-slate-50 text-xs font-medium uppercase text-slate-600">
                          <tr>
                            <th className="px-3 py-2">{t('app.leads.detail.field_key')}</th>
                            <th className="px-3 py-2">{t('app.leads.detail.field_value')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {customFieldsEntries.map(([k, v]) => (
                            <tr key={k} className="border-t border-slate-100">
                              <td className="px-3 py-2 font-mono text-xs text-slate-800">{k}</td>
                              <td className="max-w-md whitespace-pre-wrap break-words px-3 py-2 text-slate-700">{formatCustomFieldCell(v)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                    <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                      {t('app.leads.detail.normalized_json')}
                    </summary>
                    <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                      {jsonPreview(normalized)}
                    </pre>
                  </details>
                  <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                    <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                      {t('app.leads.detail.raw_payload')}
                    </summary>
                    <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                      {jsonPreview(lead.payload)}
                    </pre>
                  </details>
                </div>
              </>
            )}
          </section>

          {!intakeWorkspaceBlocking && !recruitmentLeadConverted ? (
          <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-900">
              {t('app.leads.detail.followup_title')}
            </h2>
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="space-y-3">
                <input
                  className="input h-9 w-full max-w-xl rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                  value={reminderTitle}
                  onChange={(e) => setReminderTitle(e.target.value)}
                  placeholder={t('app.reminders.fields.title')}
                />
                <div className="grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
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
                  className="btn-primary h-9 rounded-lg px-4 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!reminderTitle.trim() || !reminderDueAt}
                  onClick={() => void handleCreateLeadReminder()}
                >
                  {t('app.reminders.actions.create')}
                </button>
                {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
              </div>
            </div>
            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="text-xs font-semibold text-slate-700">{t('app.reminders.title')}</h3>
                <button
                  type="button"
                  className="btn-secondary h-8 rounded-lg px-2 text-xs"
                  onClick={() => void loadLeadReminders()}
                >
                  {t('common.actions.refresh')}
                </button>
              </div>
              {remindersLoading ? (
                <p className="text-sm text-slate-500">{t('common.loading')}</p>
              ) : reminders.length === 0 ? (
                <p className="text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
              ) : (
                <ul className="space-y-2">
                  {reminders.slice(0, 30).map((r) => (
                    <li key={r.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-slate-900">{r.title || t('app.reminders.item.untitled')}</div>
                        <div className="mt-0.5 text-xs text-slate-600">
                          {t('app.reminders.fields.due_at')}: {formatDateValue(r.due_at, locale)}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary h-8 shrink-0 rounded-lg px-2 text-xs"
                        onClick={() => void handleCompleteReminder(r.id)}
                      >
                        {t('app.reminders.actions.complete')}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
          ) : null}

          {isServicesTenant && !intakeWorkspaceBlocking && !recruitmentLeadConverted ? (
          <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6">
            <h2 className="mb-4 text-sm font-semibold text-slate-900">{t('app.leads.detail.timeline')}</h2>
            {timelineLoading && <p className="text-sm text-slate-500">{t('common.loading')}</p>}
            {timelineError && <p className="text-sm text-red-600">{timelineError}</p>}
            {!timelineLoading && !timelineError && timelineItems.length === 0 && (
              <p className="text-sm text-slate-500">{t('app.leads.detail.timeline_empty')}</p>
            )}
            {!timelineLoading && timelineItems.length > 0 && (
              <ul className="space-y-3 border-l-2 border-slate-200 pl-4">
                {timelineItems.map((item, idx) => (
                  <li key={`${item.at}-${item.kind}-${idx}`} className="relative">
                    <span className="absolute -left-[calc(0.5rem+2px)] top-1.5 h-2 w-2 rounded-full bg-brand-500" aria-hidden />
                    <div className="text-xs text-slate-500">{formatDateValue(item.at, locale)}</div>
                    <div className="text-sm font-medium text-slate-900">{item.title || item.kind || '—'}</div>
                    {item.description ? <div className="text-sm text-slate-600">{item.description}</div> : null}
                    <div className="text-[11px] text-slate-400">
                      {item.kind}
                      {item.source ? ` · ${item.source}` : ''}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          ) : null}

          </>
          ) : recruitmentLeadConverted ? (
            <>
              <RecruitmentAgencyAuditDetailView
                lead={lead}
                leadDisplayName={leadDisplayName}
                normalized={normalized as Record<string, unknown>}
                companyLabel={companyLabel}
                vacancyLabel={vacancyLabel}
                formatDateValue={(iso) => formatDateValue(iso, locale)}
                locale={locale}
                t={t}
                timelineItems={timelineItems}
                timelineLoading={timelineLoading}
                timelineError={timelineError}
                auditDiagnostics={
                  <>
                    <LeadMetaProblemPanel lead={lead} onRefreshed={refreshLeadAndTimeline} />
                    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                      <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                        <span className="shrink-0 font-medium">{t('app.leads.table.stage')}</span>
                        <select
                          className="input h-9 min-w-[11rem] rounded-lg border-slate-300 bg-white px-2 text-sm"
                          value={lostStagePrompt ? lostStagePrompt.previousStage ?? '' : lead.stage ?? ''}
                          disabled={patching || leadRejected}
                          onChange={(e) => void handleDetailStageSelect(e.target.value)}
                        >
                          <option value="">{t('app.leads.inbox.stage_unset')}</option>
                          {crmStageValues.map((v) => (
                            <option key={v} value={v}>
                              {stageLabels[v] ?? v}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={leadAssignmentLocked(lead)}
                          disabled={patching || leadRejected}
                          onChange={(e) => void handleDetailAssignmentLockToggle(e.target.checked)}
                        />
                        <span>{t('app.leads.inbox.lock_assignment')}</span>
                      </label>
                    </div>
                    <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
                    <section aria-labelledby="lead-rec-audit-ingest">
                      <h2 id="lead-rec-audit-ingest" className="mb-3 text-sm font-semibold text-slate-900">
                        {t('app.leads.detail.source_ingest_title')}
                      </h2>
                      <LeadIngestProcessingCallout normalized={normalized as Record<string, unknown>} />
                      <dl className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.source')}</dt>
                          <dd className="mt-0.5 text-sm text-slate-900">{lead.source || '—'}</dd>
                        </div>
                        {lead.ad_id != null ? (
                          <div>
                            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.detail.ad_id')}</dt>
                            <dd className="mt-0.5 font-mono text-sm text-slate-900">{String(lead.ad_id)}</dd>
                          </div>
                        ) : null}
                      </dl>
                    </section>
                  </>
                }
              />
            </>
          ) : (
            <>
              <RecruitmentAgencyIntakeDetailView
                lead={lead}
                leadDisplayName={leadDisplayName}
                normalized={normalized as Record<string, unknown>}
                companyLabel={companyLabel}
                vacancyLabel={vacancyLabel}
                intakeNote={intakeNote}
                formatDateValue={(iso) => formatDateValue(iso, locale)}
                locale={locale}
                t={t}
                processing={processing}
                routingConfirming={routingConfirming}
                poolBusy={poolBusyDetail}
                onLeadUpdated={(l) => {
                  setLead(l)
                  bumpNextActionTick()
                  void loadTimeline()
                }}
                onRequestProcess={() => void handleProcess()}
                onConfirmRouting={(vacancyId, thenProcess) => void handleConfirmLeadRoutingDetail(vacancyId, thenProcess)}
                onPool={() => void handlePoolDetail()}
                timelineItems={timelineItems}
                timelineLoading={timelineLoading}
                timelineError={timelineError}
              />
              <details className="card mt-6 overflow-hidden p-0 shadow-md shadow-slate-900/[0.03]">
                <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 marker:content-none hover:bg-slate-50/80 hover:text-slate-700 [&::-webkit-details-marker]:hidden">
                  {t('app.leads.intake_workspace.section.more')}
                </summary>
                <div className="border-t border-slate-100 bg-white/95 p-4 sm:p-5 space-y-6">
                  <LeadMetaProblemPanel lead={lead} onRefreshed={refreshLeadAndTimeline} />
                  <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
                    <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">
                      <span className="shrink-0 font-medium">{t('app.leads.table.stage')}</span>
                      <select
                        className="input h-9 min-w-[11rem] rounded-lg border-slate-300 bg-white px-2 text-sm"
                        value={lostStagePrompt ? lostStagePrompt.previousStage ?? '' : lead.stage ?? ''}
                        disabled={patching || leadRejected}
                        onChange={(e) => void handleDetailStageSelect(e.target.value)}
                      >
                        <option value="">{t('app.leads.inbox.stage_unset')}</option>
                        {crmStageValues.map((v) => (
                          <option key={v} value={v}>
                            {stageLabels[v] ?? v}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        className="rounded border-slate-300"
                        checked={leadAssignmentLocked(lead)}
                        disabled={patching || leadRejected}
                        onChange={(e) => void handleDetailAssignmentLockToggle(e.target.checked)}
                      />
                      <span>{t('app.leads.inbox.lock_assignment')}</span>
                    </label>
                  </div>
                  <LeadLostReasonReadonly lead={lead} formatAt={(iso) => formatDateValue(iso, locale)} />
                  <LeadNextActionPlaybook lead={lead} formatDueAt={(iso) => formatDateValue(iso, locale)} />
                  <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6">
                    <h2 className="mb-4 text-sm font-semibold text-slate-900">{t('app.leads.detail.followup_title')}</h2>
                    <div className="rounded-xl border border-slate-100 bg-gradient-to-br from-brand-50/40 to-slate-50/80 p-4 ring-1 ring-slate-900/[0.04]">
                      <div className="space-y-3">
                        <input
                          className="input h-9 w-full max-w-xl rounded-lg border-slate-300 bg-white px-2.5 text-sm"
                          value={reminderTitle}
                          onChange={(e) => setReminderTitle(e.target.value)}
                          placeholder={t('app.reminders.fields.title')}
                        />
                        <div className="grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
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
                          className="btn-primary h-9 rounded-lg px-4 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={!reminderTitle.trim() || !reminderDueAt}
                          onClick={() => void handleCreateLeadReminder()}
                        >
                          {t('app.reminders.actions.create')}
                        </button>
                        {remindersError ? <div className="text-xs text-red-600">{remindersError}</div> : null}
                      </div>
                    </div>
                    <div className="mt-4">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold text-slate-700">{t('app.reminders.title')}</h3>
                        <button
                          type="button"
                          className="btn-secondary h-8 rounded-lg px-2 text-xs"
                          onClick={() => void loadLeadReminders()}
                        >
                          {t('common.actions.refresh')}
                        </button>
                      </div>
                      {remindersLoading ? (
                        <p className="text-sm text-slate-500">{t('common.loading')}</p>
                      ) : reminders.length === 0 ? (
                        <p className="text-sm text-slate-500">{t('app.reminders.states.empty')}</p>
                      ) : (
                        <ul className="space-y-2">
                          {reminders.slice(0, 30).map((r) => (
                            <li key={r.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3">
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-900">{r.title || t('app.reminders.item.untitled')}</div>
                                <div className="mt-0.5 text-xs text-slate-600">
                                  {t('app.reminders.fields.due_at')}: {formatDateValue(r.due_at, locale)}
                                </div>
                              </div>
                              <button
                                type="button"
                                className="btn-secondary h-8 shrink-0 rounded-lg px-2 text-xs"
                                onClick={() => void handleCompleteReminder(r.id)}
                              >
                                {t('app.reminders.actions.complete')}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </section>
                  <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6" aria-labelledby="lead-rec-intake-fields-heading">
                    <h2 id="lead-rec-intake-fields-heading" className="mb-4 text-sm font-semibold text-slate-900">
                      {t('app.leads.detail.details_heading')}
                    </h2>
                    <dl className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.created')}</dt>
                        <dd className="mt-0.5 text-sm text-slate-900">{formatDateValue(lead.created_at, locale)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.status')}</dt>
                        <dd className="mt-0.5 text-sm text-slate-900">{statusLabels[lead.status] ?? lead.status}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{companyLabel}</dt>
                        <dd className="mt-0.5 text-sm text-slate-900">{lead.company_name || lead.company_id || '—'}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{vacancyLabel}</dt>
                        <dd className="mt-0.5 text-sm text-slate-900">{lead.vacancy_title || lead.vacancy_id || '—'}</dd>
                      </div>
                    </dl>
                  </section>
                  <section className="card p-5 shadow-md shadow-slate-900/[0.03] sm:p-6">
                    <h2 className="mb-4 text-sm font-semibold text-slate-900">{t('app.leads.detail.source_ingest_title')}</h2>
                    <LeadIngestProcessingCallout normalized={normalized as Record<string, unknown>} />
                    <dl className="mb-4 grid gap-3 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.table.source')}</dt>
                        <dd className="mt-0.5 text-sm text-slate-900">{lead.source || '—'}</dd>
                      </div>
                      {lead.ad_id != null ? (
                        <div>
                          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('app.leads.detail.ad_id')}</dt>
                          <dd className="mt-0.5 font-mono text-sm text-slate-900">{String(lead.ad_id)}</dd>
                        </div>
                      ) : null}
                    </dl>
                    <div className="space-y-2">
                      <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                          {t('app.leads.detail.normalized_json')}
                        </summary>
                        <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                          {jsonPreview(normalized)}
                        </pre>
                      </details>
                      <details className="group rounded-md border border-slate-200 bg-slate-50 open:bg-white">
                        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800">
                          {t('app.leads.detail.raw_payload')}
                        </summary>
                        <pre className="max-h-72 overflow-auto border-t border-slate-200 bg-slate-900/95 p-3 text-xs text-slate-100">
                          {jsonPreview(lead.payload)}
                        </pre>
                      </details>
                    </div>
                  </section>
                </div>
              </details>
            </>
          )}

          <LostReasonForLostStageModal
            open={Boolean(lostStagePrompt)}
            loading={patching}
            onCancel={cancelLostStagePrompt}
            onConfirm={(p) => void confirmLostStageFromModal(p)}
          />
        </>
        ) : null}
      </div>
    </PageShell>
  )
}
