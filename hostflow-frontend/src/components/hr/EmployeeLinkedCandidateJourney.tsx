import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, listReminders } from '../../api/client'
import { getFunnel } from '../../api/funnels'
import {
  getCandidateProfile,
  listCandidateProfiles,
  type CandidateProfile,
} from '../../api/candidate_profiles'
import { getVacancy } from '../../api/vacancies'
import {
  listCandidatePipelineOverrides,
  type CandidatePipelineOverride,
} from '../../api/candidatePipelineOverrides'
import type { Candidate, CandidateExtra, ReminderRecord } from '../../api/types'
import type { CandidateNote, StageHistoryEntry } from '../../modules/candidate-card/types'
import { useI18n } from '../../i18n'
import { useMetaStages } from '../../store/useMeta'
import { useHiringPipelineGates } from '../../contexts/HiringPipelineGatesContext'
import { usePermissions } from '../../hooks/usePermissions'
import { useCandidateDocBlockers } from '../../hooks/useCandidateDocBlockers'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { useToast } from '../Toast'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import CandidateStageDecisionPanel from '../candidate/CandidateStageDecisionPanel'
import CandidateTimelinePanel from '../candidate/CandidateTimelinePanel'
import { canonicalStageKey, translateStageLabel } from '../../utils/stageLabels'
import { isPipelineCompletedCanonicalStage } from '../../utils/candidatePipelineCompleted'
import {
  docsPipelineBlocksForwardResolved,
  hiringPipelineGatesFromApi,
  pipelineRelaxedTypesFromOverrides,
  relaxDocBlockers,
  vacancyPipelineBlocksForward,
} from '../../utils/candidateStageDocPolicy'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { isUuidLike } from '../../modules/candidate-card/utils'

const DEFAULT_PROFILE_CODE = 'driver_ce_default'

function sanitizeExtraLoose(raw: unknown): CandidateExtra {
  if (!raw || typeof raw !== 'object') return {} as CandidateExtra
  return raw as CandidateExtra
}

function handoffThresholdMs(handoffAt: string | null | undefined): number | null {
  if (!handoffAt || !String(handoffAt).trim()) return null
  const ts = Date.parse(String(handoffAt))
  return Number.isNaN(ts) ? null : ts
}

type Props = {
  locale: string
  candidateId: string
  /** Bump when parent reloads employee / bundle */
  refreshSignal: number
  /** For workforce “trip” milestone — avoids a second candidate fetch in the parent. */
  onCandidateStageChange?: (stage: string | null) => void
  /**
   * HR workspace: show only post-handoff / client-facing deployment strip (no recruiter funnel).
   */
  hrPostHandoffOnly?: boolean
  /**
   * When set (e.g. `employee.handoff_at`), timeline payloads are limited to events at/after this time.
   */
  activitySinceHandoffAt?: string | null
  /** When false, inline timeline is omitted (open via activity modal from parent). */
  inlineActivityTimeline?: boolean
}

export default function EmployeeLinkedCandidateJourney({
  locale,
  candidateId,
  refreshSignal,
  onCandidateStageChange,
  hrPostHandoffOnly = false,
  activitySinceHandoffAt = null,
  inlineActivityTimeline = true,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const meta = useMetaStages()
  const { can } = usePermissions()
  const { gates: hiringGatesApi } = useHiringPipelineGates()
  const hiringGatesRuntime = useMemo(() => hiringPipelineGatesFromApi(hiringGatesApi), [hiringGatesApi])
  /** Same as CandidateCard: align GET/PATCH with list when X-Tenant-Id ≠ workspace tenant. */
  const scopeWorkspaceId = useCurrentTenantId()
  const apiScopeConfig = useMemo(() => {
    const tid = scopeWorkspaceId && isUuidLike(scopeWorkspaceId) ? String(scopeWorkspaceId).trim() : ''
    return tid ? { params: { scope_tenant_id: tid } } : {}
  }, [scopeWorkspaceId])

  const [model, setModel] = useState<Candidate | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null)
  const [profileFunnelStages, setProfileFunnelStages] = useState<Array<{ code: string; label: string }>>([])
  const [stageHistory, setStageHistory] = useState<StageHistoryEntry[]>([])
  const [stageSinceAt, setStageSinceAt] = useState<string | null>(null)
  const [notes, setNotes] = useState<CandidateNote[]>([])
  const [reminders, setReminders] = useState<ReminderRecord[]>([])
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [timelineError, setTimelineError] = useState<FriendlyErrorInfo | null>(null)
  const [pipelineOverrides, setPipelineOverrides] = useState<CandidatePipelineOverride[]>([])
  const [stageBump, setStageBump] = useState(0)

  const extra = useMemo(() => sanitizeExtraLoose(model?.extra), [model?.extra])
  const citizenship = String(extra?.citizenship || '')
  const { blockers: rawDocBlockers, loading: docsBlockersLoading, refresh: refreshDocBlockers } =
    useCandidateDocBlockers(candidateId, citizenship, refreshSignal + stageBump)

  const pipelineRelaxedTypes = useMemo(
    () => pipelineRelaxedTypesFromOverrides(pipelineOverrides),
    [pipelineOverrides],
  )
  const docsBlockers = useMemo(
    () => relaxDocBlockers(rawDocBlockers, pipelineRelaxedTypes),
    [rawDocBlockers, pipelineRelaxedTypes],
  )

  const loadProfileFromVacancy = useCallback(
    async (vacancyId: string | null | undefined) => {
      if (!vacancyId) {
        setCandidateProfile(null)
        setProfileFunnelStages([])
        return
      }
      try {
        let vacancy: { candidate_profile_id?: string | null } | null = null
        try {
          vacancy = await getVacancy(vacancyId)
        } catch (vacErr: unknown) {
          const st = Number((vacErr as { response?: { status?: number } })?.response?.status || 0)
          if (st === 404 || st === 403) {
            const profiles = await listCandidateProfiles()
            const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
            setCandidateProfile(defaultProfile ?? null)
            setProfileFunnelStages([])
            return
          }
          throw vacErr
        }
        if (!vacancy?.candidate_profile_id) {
          const profiles = await listCandidateProfiles()
          const defaultProfile = profiles.find((p) => p.code === DEFAULT_PROFILE_CODE)
          setCandidateProfile(defaultProfile ?? null)
          setProfileFunnelStages([])
          return
        }
        const profile = await getCandidateProfile(String(vacancy.candidate_profile_id))
        setCandidateProfile(profile)
      } catch {
        setCandidateProfile(null)
        setProfileFunnelStages([])
      }
    },
    [],
  )

  useEffect(() => {
    if (!candidateProfile?.funnel_id) {
      setProfileFunnelStages([])
      return
    }
    getFunnel(candidateProfile.funnel_id)
      .then((f) => setProfileFunnelStages((f.stages || []).map((s) => ({ code: s.code, label: s.label }))))
      .catch(() => setProfileFunnelStages([]))
  }, [candidateProfile?.funnel_id])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      setLoadError(null)
      try {
        const { data } = await api.get<Candidate>(
          `/candidates/${encodeURIComponent(candidateId)}`,
          apiScopeConfig,
        )
        if (cancelled) return
        setModel(data)
        await loadProfileFromVacancy(data.vacancy_id as string | null | undefined)
      } catch {
        if (!cancelled) {
          setModel(null)
          setLoadError(t('app.hr.employee_detail.linked_journey.load_error', { defaultValue: 'Could not load candidate' }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [candidateId, refreshSignal, loadProfileFromVacancy, t, apiScopeConfig])

  useEffect(() => {
    onCandidateStageChange?.(model?.stage ? String(model.stage) : null)
  }, [model?.stage, onCandidateStageChange])

  useEffect(() => {
    if (!candidateId) return
    let cancelled = false
    void (async () => {
      try {
        const items = await listCandidatePipelineOverrides(candidateId)
        if (!cancelled) setPipelineOverrides(items)
      } catch {
        if (!cancelled) setPipelineOverrides([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [candidateId, refreshSignal, stageBump])

  const loadTimeline = useCallback(async () => {
    if (!candidateId) return
    setTimelineLoading(true)
    setTimelineError(null)
    const fb = t('common.errors.request_failed', { defaultValue: 'Request failed' })
    try {
      const [{ data: hist }, { data: notesData }, res] = await Promise.all([
        api.get(`/candidates/${encodeURIComponent(candidateId)}/stage-history`, apiScopeConfig),
        api.get(`/candidates/${encodeURIComponent(candidateId)}/notes`, apiScopeConfig),
        listReminders({
          entityType: 'candidate',
          entityId: candidateId,
          status: ['pending', 'new', 'overdue', 'done', 'cancelled'],
        }),
      ])
      const entries = Array.isArray(hist) ? hist : []
      let normalized: StageHistoryEntry[] = entries.map((item: Record<string, unknown>, idx: number) => ({
        id: String(item?.id ?? `${item?.to_code ?? 'stage'}-${item?.at ?? idx}`),
        from_code: (item?.from_code as string | null) ?? null,
        to_code: (item?.to_code as string | null) ?? null,
        at: (item?.at as string | null) ?? null,
        actor: (item?.actor as string | null) ?? (item?.actor_name as string | null) ?? null,
        reason: (item?.reason as string | null) ?? null,
      }))
      let notesArr = Array.isArray(notesData) ? (notesData as CandidateNote[]) : []
      let items = Array.isArray(res?.items) ? res.items : []

      const sinceMs = handoffThresholdMs(activitySinceHandoffAt)
      if (sinceMs != null) {
        normalized = normalized.filter((h) => {
          if (!h.at) return false
          const ts = Date.parse(String(h.at))
          return !Number.isNaN(ts) && ts >= sinceMs
        })
        notesArr = notesArr.filter((n) => {
          const ts = Date.parse(String(n.created_at || ''))
          return !Number.isNaN(ts) && ts >= sinceMs
        })
        items = items.filter((r: ReminderRecord) => {
          const raw = r.created_at || r.due_at || r.remind_at
          const ts = raw ? Date.parse(String(raw)) : 0
          return ts >= sinceMs
        })
      }

      setStageHistory(normalized)
      const last = normalized.length ? normalized[normalized.length - 1] : null
      setStageSinceAt(last?.at ? String(last.at) : null)
      setNotes(notesArr)
      setReminders(items)
    } catch (err: unknown) {
      setTimelineError(getFriendlyErrorInfo(err, fb, t))
    } finally {
      setTimelineLoading(false)
    }
  }, [candidateId, t, apiScopeConfig, activitySinceHandoffAt])

  useEffect(() => {
    void loadTimeline()
  }, [loadTimeline, refreshSignal, stageBump])

  const profileStageCodes = useMemo(() => {
    let codes: string[] = []
    if (profileFunnelStages.length > 0) {
      codes = profileFunnelStages.map((s) => s.code)
    } else if (candidateProfile?.config?.stage_configs && Array.isArray(candidateProfile.config.stage_configs)) {
      const profileStages = candidateProfile.config.stage_configs
        .filter((stage: { active?: boolean }) => stage.active !== false)
        .map((stage: { stage_code?: string }) => stage.stage_code)
        .filter(Boolean) as string[]
      if (profileStages.length > 0) codes = profileStages
    }
    if (!codes.length) {
      codes = meta?.order || meta?.codes || []
    }
    return codes
  }, [candidateProfile, meta, profileFunnelStages])

  const stageOptions = useMemo(() => {
    let codes = profileStageCodes
    const metaOrder = meta?.order?.length ? meta.order : null
    const visibilityNarrowed = Boolean(meta?.stage_visibility_mode || meta?.recruiter_handoff_stage_filter)
    if (metaOrder && visibilityNarrowed) {
      const allow = new Set(metaOrder.map((c) => String(c).trim()).filter(Boolean))
      codes = profileStageCodes.filter((c) => allow.has(String(c).trim()))
    }
    if (!meta?.meta) return codes
    return codes
  }, [profileStageCodes, meta])

  const existingStageCodesSet = useMemo(
    () => new Set((profileStageCodes || []).map((code) => String(code).trim()).filter(Boolean)),
    [profileStageCodes],
  )

  const timelineStageCodesSet = useMemo(() => {
    const narrowed =
      meta?.stage_visibility_mode || meta?.recruiter_handoff_stage_filter
        ? (meta?.order || []).map((c) => String(c).trim()).filter(Boolean)
        : (profileStageCodes || []).map((c) => String(c).trim()).filter(Boolean)
    return new Set(narrowed.length ? narrowed : [])
  }, [meta, profileStageCodes])

  const timelineStageHistory = useMemo(
    () =>
      stageHistory.filter((entry) => {
        const fromCode = String(entry?.from_code || '').trim()
        const toCode = String(entry?.to_code || '').trim()
        const allow = timelineStageCodesSet
        if (allow.size === 0) {
          if (toCode && existingStageCodesSet.has(toCode)) return true
          if (fromCode && existingStageCodesSet.has(fromCode)) return true
          return false
        }
        if (toCode && allow.has(toCode)) return true
        if (fromCode && allow.has(fromCode)) return true
        return false
      }),
    [stageHistory, timelineStageCodesSet, existingStageCodesSet],
  )

  const stageLabelIntl = useCallback(
    (code: string) => {
      const funnelStage = profileFunnelStages.find((s) => s.code === code)
      let profileLabel: string | null = null
      if (candidateProfile?.config?.stage_configs) {
        const profileStage = candidateProfile.config.stage_configs.find(
          (s: { stage_code?: string }) => s.stage_code === code,
        ) as { stage_label?: string } | undefined
        if (profileStage?.stage_label) profileLabel = String(profileStage.stage_label)
      }
      const fallback = profileLabel || funnelStage?.label || meta?.labels?.[code] || code
      return translateStageLabel(t, code, fallback)
    },
    [candidateProfile, meta?.labels, profileFunnelStages, t],
  )

  const postHandoffStripOnly = hrPostHandoffOnly

  const {
    stageJourneyStagesPipeline,
    stageJourneyStagesDisplay,
    stageOutcomeStages,
    stageJourneyDisplayStage,
    stageJourneyOutcomeStage,
    stageJourneySignals,
  } = useMemo(() => {
    const visibilityNarrowed = Boolean(meta?.stage_visibility_mode || meta?.recruiter_handoff_stage_filter)
    const codesForDisplay = stageOptions
    const codesForPipeline = visibilityNarrowed
      ? stageOptions
      : profileFunnelStages.length > 0
        ? profileFunnelStages.map((s) => s.code)
        : profileStageCodes

    const uniqDisplay = Array.from(new Set((codesForDisplay || []).filter(Boolean)))
    const journeyOrder = [
      'processing_by_client',
      'docs_submitted_permit',
      'permit_received',
      'employment_pending',
      'employed',
      'on_trip',
    ]
    const allowedJourneyStages = new Set(journeyOrder)
    const journeyOrderRank = new Map(journeyOrder.map((code, idx) => [code, idx] as const))

    function buildOrderedStages(codesInput: string[], applyPostHandoffOnly: boolean) {
      const uniq = Array.from(new Set((codesInput || []).filter(Boolean)))
      const main: Array<{ code: string; label: string }> = []
      uniq.forEach((raw) => {
        const code = String(raw)
        const label = stageLabelIntl(code)
        const canonical = canonicalStageKey(code, label) || ''

        if (canonical === 'no_answer') return
        if (canonical === 'questionnaire_submitted') return
        if (canonical === 'handoff_returned' || canonical === 'rejected' || canonical === 'declined') {
          return
        }
        if (applyPostHandoffOnly && !allowedJourneyStages.has(canonical)) return
        main.push({ code, label })
      })
      if (applyPostHandoffOnly) {
        return [...main].sort((a, b) => {
          const aCanonical = canonicalStageKey(a.code, a.label) || ''
          const bCanonical = canonicalStageKey(b.code, b.label) || ''
          const aRank = journeyOrderRank.get(aCanonical)
          const bRank = journeyOrderRank.get(bCanonical)
          if (aRank === undefined && bRank === undefined) return 0
          if (aRank === undefined) return 1
          if (bRank === undefined) return -1
          return aRank - bRank
        })
      }
      return main
    }

    const orderedPipeline = buildOrderedStages(codesForPipeline, postHandoffStripOnly)
    const orderedDisplay = buildOrderedStages(codesForDisplay, postHandoffStripOnly)

    const currentCode = String(model?.stage || '')
    const currentCanonical = canonicalStageKey(currentCode, null) || ''
    const journeySignals: Array<{ key: string; label: string }> = []

    if (!postHandoffStripOnly && currentCanonical === 'no_answer') {
      journeySignals.push({ key: 'no_answer', label: translateStageLabel(t, 'no_answer', 'no_answer') })
    }
    const intakeSubmitted = Boolean(
      (model as { intake_submitted_at?: string })?.intake_submitted_at ||
        (model as { intake_status?: string })?.intake_status === 'submitted',
    )
    if (
      !postHandoffStripOnly &&
      (currentCanonical === 'questionnaire_submitted' || intakeSubmitted)
    ) {
      journeySignals.push({
        key: 'questionnaire_submitted',
        label: translateStageLabel(t, 'questionnaire_submitted', 'questionnaire_submitted'),
      })
    }

    let displayStage = currentCode || null
    if (postHandoffStripOnly && orderedPipeline.length) {
      const stripCodes = new Set(orderedPipeline.map((s) => s.code))
      if (!stripCodes.has(currentCode)) {
        displayStage = orderedPipeline[0]?.code ?? displayStage
      }
    } else if (currentCanonical === 'no_answer' || currentCanonical === 'questionnaire_submitted') {
      const contacted =
        uniqDisplay.find((c) => (canonicalStageKey(String(c), null) || '') === 'contacted') || 'contacted'
      displayStage = String(contacted)
    }

    return {
      stageJourneyStagesPipeline: orderedPipeline,
      stageJourneyStagesDisplay: orderedDisplay,
      stageOutcomeStages: [] as Array<{ code: string; label: string }>,
      stageJourneyDisplayStage: displayStage,
      stageJourneyOutcomeStage: null as string | null,
      stageJourneySignals: journeySignals,
    }
  }, [
    profileFunnelStages,
    profileStageCodes,
    stageLabelIntl,
    stageOptions,
    model?.stage,
    (model as { intake_status?: string })?.intake_status,
    (model as { intake_submitted_at?: string })?.intake_submitted_at,
    t,
    postHandoffStripOnly,
    meta,
  ])

  const effectiveStageForDocPolicy = useMemo(() => {
    const stored =
      canonicalStageKey(model?.stage ?? null, null) || String(model?.stage || '').trim().toLowerCase() || null
    if (stored && isPipelineCompletedCanonicalStage(stored)) return stored
    return String(stageJourneyDisplayStage || model?.stage || '').trim() || null
  }, [stageJourneyDisplayStage, model?.stage])

  const docResolved = useMemo(
    () =>
      docsPipelineBlocksForwardResolved(
        effectiveStageForDocPolicy,
        docsBlockers,
        docsBlockersLoading,
        hiringGatesRuntime,
      ),
    [effectiveStageForDocPolicy, docsBlockers, docsBlockersLoading, hiringGatesRuntime],
  )
  const docsPipelineBlockingValue = docResolved.hard
  const docsPipelineSoftWarnValue = docResolved.softWarnOnly
  const vacancyPipelineBlockingValue = vacancyPipelineBlocksForward(
    effectiveStageForDocPolicy,
    model?.vacancy_id as string | null | undefined,
    hiringGatesRuntime,
  )
  const contactAttemptPipelineBlockingValue = false

  const completedStageCodes = useMemo(() => {
    const set = new Set<string>()
    stageHistory.forEach((h) => {
      if (h.from_code) set.add(String(h.from_code))
      if (h.to_code) set.add(String(h.to_code))
    })
    return set
  }, [stageHistory])

  const canMutateStages = Boolean(model?.can_edit !== false && can('candidates.pipeline'))

  const handleMoveStage = useCallback(
    async (nextStage: string) => {
      if (!model?.id) return
      const steps = [...(stageJourneyStagesPipeline || []), ...(stageOutcomeStages || [])]
      const curCode = stageJourneyDisplayStage || model?.stage
      const curIdx = steps.findIndex((s) => s.code === curCode)
      const nextIdx = steps.findIndex((s) => s.code === nextStage)
      const isForward = curIdx >= 0 && nextIdx > curIdx
      if (isForward) {
        if (docsPipelineBlockingValue) return
        if (vacancyPipelineBlockingValue) return
      }
      try {
        await api.patch(
          `/candidates/${encodeURIComponent(model.id)}`,
          {
            stage: nextStage,
            status_reason: model.status_reason || [],
          },
          apiScopeConfig,
        )
        const { data } = await api.get<Candidate>(
          `/candidates/${encodeURIComponent(candidateId)}`,
          apiScopeConfig,
        )
        setModel(data)
        setStageBump((x) => x + 1)
        await refreshDocBlockers()
        await loadTimeline()
      } catch {
        notify({
          variant: 'error',
          title: t('app.hr.employee_detail.linked_journey.stage_save_error', {
            defaultValue: 'Could not update candidate stage',
          }),
        })
      }
    },
    [
      model,
      candidateId,
      stageJourneyStagesPipeline,
      stageOutcomeStages,
      stageJourneyDisplayStage,
      docsPipelineBlockingValue,
      vacancyPipelineBlockingValue,
      refreshDocBlockers,
      loadTimeline,
      notify,
      t,
      apiScopeConfig,
    ],
  )

  if (loadError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-3 text-sm text-rose-900">{loadError}</div>
    )
  }

  if (!model) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3 text-sm text-slate-600">
        {t('common.loading', { defaultValue: 'Loading…' })}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {model.permissions?.operational_owner === 'hr' ? (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-950">
          <div className="font-semibold">
            {t('app.hr.ownership.operational_owner', { defaultValue: 'Operational owner: HR' })}
          </div>
          <div className="mt-0.5 text-sky-900/90">
            {t('app.hr.ownership.recruitment_readonly', { defaultValue: 'Recruitment access: read-only' })}
          </div>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-slate-700">
          {hrPostHandoffOnly
            ? t('app.hr.employee_detail.linked_journey.title_hr_strip', {
                defaultValue: 'Deployment pipeline (after recruitment handoff)',
              })
            : t('app.hr.employee_detail.linked_journey.title', { defaultValue: 'Recruitment pipeline (linked candidate)' })}
        </div>
        <Link
          className="text-xs font-medium text-brand-700 underline decoration-brand-500/40 hover:decoration-brand-700"
          to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`}
        >
          {t('app.hr.employee_detail.linked_journey.open_full', { defaultValue: 'Open candidate card' })}
        </Link>
      </div>
      <CandidateStageDecisionPanel
        locale={locale}
        stageSinceAt={stageSinceAt}
        stageJourneyStages={stageJourneyStagesPipeline}
        journeyPanelStages={stageJourneyStagesDisplay}
        stageOutcomeStages={stageOutcomeStages}
        stageJourneyDisplayStage={stageJourneyDisplayStage}
        stageJourneyOutcomeStage={stageJourneyOutcomeStage}
        stageJourneySignals={stageJourneySignals}
        completedStageCodes={completedStageCodes}
        currentStageCode={model.stage}
        stageLabelIntl={stageLabelIntl}
        docsBlockers={docsBlockers}
        docsPipelineBlocking={docsPipelineBlockingValue}
        docsPipelineSoftWarn={docsPipelineSoftWarnValue}
        vacancyPipelineBlocking={vacancyPipelineBlockingValue}
        contactAttemptPipelineBlocking={contactAttemptPipelineBlockingValue}
        canEdit={canMutateStages}
        onMoveStage={handleMoveStage}
      />
      {inlineActivityTimeline ? (
        <CandidateTimelinePanel
          locale={locale}
          stageHistory={timelineStageHistory}
          notes={notes}
          reminders={reminders}
          loading={timelineLoading}
          timelineError={timelineError}
          resolveStageLabel={stageLabelIntl}
          onRequestLoad={loadTimeline}
          defaultOpen
          hideToggle
          variant="full"
          stageHistoryShortcut
        />
      ) : null}
    </div>
  )
}
