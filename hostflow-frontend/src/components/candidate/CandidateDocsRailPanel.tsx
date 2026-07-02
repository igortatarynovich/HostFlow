import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { getSummary } from '../../api/documents'
import type { CandidatePipelineOverride } from '../../api/candidatePipelineOverrides'
import {
  effectiveNonOverridableDocTypesSet,
  isNonOverridableDocTypeCode,
  isNonOverridableRequirementCode,
} from '../../constants/pipelineOverridePolicy'
import type { DocBlockersPayload } from '../../utils/candidateStageDocPolicy'
import { useHiringPipelineGates } from '../../contexts/HiringPipelineGatesContext'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'
import {
  extractRuntimeItemsFromSummary,
  runtimeBadgeFromRuntime,
  type RuntimeBadgeKind,
  type RuntimeBadgePresentation,
  type DocumentRuntimeV1,
} from '../../utils/runtimeBadgePresentation'
import {
  buildRuntimeWorkspaceFromSummary,
} from '../../utils/runtimeWorkspacePresentation'
import {
  RUNTIME_DOCUMENT_FILTERS,
  RUNTIME_FILTER_LABEL_KEYS,
  runtimeMatchesFilter,
  type RuntimeDocumentFilterSelection,
} from '../../utils/runtimeDocumentFilters'

type RequiredState = {
  missing: string[]
  problematic: string[]
  ready_types?: string[]
  in_progress_types?: string[]
}

type SummaryResponse = {
  percent_ready: number
  required?: RequiredState
  expiring_soon?: Array<{ type: string; expires_at: string }>
}

/** Serializable checklist snapshot (matches work-panel `documents_summary` + getSummary shape). */
export type CandidateDocsRailSummarySnapshot = SummaryResponse

/** When set, rail can skip duplicate `getSummary` while the parent work-panel bundle is loading or seeded. */
export type CandidateDocsRailEmbeddedDocumentsSummary = {
  ready: boolean
  summary: CandidateDocsRailSummarySnapshot | null
}

type Props = {
  candidateId: string
  ownerContext?: Record<string, any> | null
  uploadBusy?: boolean
  onUpload?: () => void
  refreshTrigger?: number
  // For pipeline gating + next action overriding
  onLoadedBlockers?: (blockers: { missing: string[]; problematic: string[]; inProgress: string[] }) => void
  onLoadingChange?: (loading: boolean) => void
  onSummaryLoaded?: (summary: SummaryResponse | null) => void
  onOpenDocs?: () => void
  onSelectType?: (typeCode: string) => void
  pollingEnabled?: boolean
  pollingIntervalMs?: number
  /** Current candidate stage label (for “relevant blockers” copy). */
  stageSummaryLabel?: string | null
  /**
   * When false, missing docs are shown as informational for this stage (not “blocking”).
   * When omitted, falls back to legacy behavior (any missing/problematic looks blocking).
   */
  docsPipelineBlocking?: boolean
  /** Document pipeline waivers (missing / review) — recruiter request → manager approve. */
  pipelineOverrides?: CandidatePipelineOverride[]
  pipelineOverrideBusy?: boolean
  canRequestPipelineOverride?: boolean
  canApprovePipelineOverride?: boolean
  onCreatePipelineOverride?: (input: {
    doc_type_code?: string
    requirement_code?: string
    reason: string
    requested_scope: 'pipeline' | 'both'
  }) => Promise<void>
  onApprovePipelineOverride?: (overrideId: string, granted: 'pipeline' | 'both') => Promise<void>
  onRejectPipelineOverride?: (overrideId: string) => Promise<void>
  /** When set (e.g. from CandidateCard), controls visibility — includes managers on read-only cards. */
  showPipelineWaiverSection?: boolean
  /** Card is read-only: explain why “Request waiver” form is hidden. */
  pipelineWaiverReadOnlyCard?: boolean
  /** Single priority step in the work rail (document gate). */
  primaryStepHighlight?: boolean
  /**
   * List work-panel: hydrate from `GET .../work-panel` `documents_summary` and avoid a redundant
   * `getSummary` when `ready` + non-null `summary`. Omit on candidate card (always fetch).
   */
  embeddedDocumentsSummary?: CandidateDocsRailEmbeddedDocumentsSummary
  /**
   * When ``historical``, missing/problematic docs use informational framing (closed candidate).
   * Does not hide the checklist (unlike ``docsPipelineBlocking === false`` for early funnel).
   */
  /**
   * When true, hides document-type checklist rows and blocker panels.
   * Requirements checklist (Candidate Evidence) is the primary confirmation UI.
   */
  hideDocumentTypeChecklist?: boolean
  /** When true, do not push document-summary blockers to parent (requirements path owns blockers). */
  suppressBlockerCallbacks?: boolean
  /** Requirement-centric waivers use requirement_code instead of doc_type_code. */
  waiverMode?: 'document' | 'requirement'
  /** Blocker lists for waiver eligibility when checklist is hidden (requirements path). */
  externalBlockers?: DocBlockersPayload
  /** When set with hidden checklist, primary CTA opens requirements workspace. */
  requirementsWorkspaceHref?: string | null
}

type RowStatus = 'missing' | 'expiring' | 'valid' | 'in_progress'

type DocRow = {
  type: string
  status: RowStatus
  meta?: string
  badgePresentation?: RuntimeBadgePresentation
  runtime?: DocumentRuntimeV1 | null
}

function runtimeBadgeToRowStatus(badge: RuntimeBadgeKind): RowStatus {
  switch (badge) {
    case 'approved':
      return 'valid'
    case 'expiring_soon':
      return 'expiring'
    case 'pending':
      return 'in_progress'
    default:
      return 'missing'
  }
}

export default function CandidateDocsRailPanel({
  candidateId,
  ownerContext,
  uploadBusy,
  onUpload,
  refreshTrigger = 0,
  onLoadedBlockers,
  onLoadingChange,
  onSummaryLoaded,
  onOpenDocs,
  onSelectType,
  pollingEnabled = false,
  pollingIntervalMs = 30_000,
  stageSummaryLabel,
  docsPipelineBlocking,
  pipelineOverrides = [],
  pipelineOverrideBusy = false,
  canRequestPipelineOverride = false,
  canApprovePipelineOverride = false,
  onCreatePipelineOverride,
  onApprovePipelineOverride,
  onRejectPipelineOverride,
  showPipelineWaiverSection: showPipelineWaiverSectionProp,
  pipelineWaiverReadOnlyCard = false,
  embeddedDocumentsSummary,
  primaryStepHighlight = false,
  blockersPresentation = 'operational',
  hideDocumentTypeChecklist = false,
  suppressBlockerCallbacks = false,
  waiverMode: waiverModeProp,
  externalBlockers,
  requirementsWorkspaceHref,
}: Props) {
  const waiverMode = waiverModeProp ?? (hideDocumentTypeChecklist ? 'requirement' : 'document')
  const { t, locale } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { gates } = useHiringPipelineGates()
  const nonOverridableEffective = useMemo(
    () => effectiveNonOverridableDocTypesSet(gates?.effective_non_overridable_doc_types),
    [gates?.effective_non_overridable_doc_types],
  )
  const [loading, setLoading] = useState(false)
  const [documentsError, setDocumentsError] = useState<FriendlyErrorInfo | null>(null)
  const [summary, setSummary] = useState<SummaryResponse | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [runtimeTypeFilter, setRuntimeTypeFilter] = useState<RuntimeDocumentFilterSelection>('all')

  const load = useCallback(async () => {
    if (!candidateId) return
    setLoading(true)
    setDocumentsError(null)
    try {
      const res = await getSummary(candidateId, { context: ownerContext || null, fillMissing: true })
      const s = (res as any)?.summary as SummaryResponse | undefined
      setSummary(s ?? null)
    } catch (err: any) {
      const fb = t('common.errors.request_failed', { defaultValue: 'Request failed' })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setDocumentsError(getFriendlyErrorInfo(err, fb, t))
      }
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }, [candidateId, ownerContext, planLimitModal, t])

  useEffect(() => {
    if (embeddedDocumentsSummary !== undefined) return
    void load()
  }, [embeddedDocumentsSummary, load, refreshTrigger])

  useEffect(() => {
    if (embeddedDocumentsSummary === undefined) return
    if (refreshTrigger > 0) {
      void load()
      return
    }
    if (!embeddedDocumentsSummary.ready) {
      setLoading(true)
      return
    }
    if (embeddedDocumentsSummary.summary) {
      setSummary(embeddedDocumentsSummary.summary)
      setDocumentsError(null)
      setLoading(false)
      return
    }
    void load()
  }, [embeddedDocumentsSummary, load, refreshTrigger])

  useEffect(() => {
    onLoadingChange?.(loading)
  }, [loading, onLoadingChange])

  const expiringSoon = useMemo(() => summary?.expiring_soon ?? [], [summary])

  const workspace = useMemo(
    () => buildRuntimeWorkspaceFromSummary(summary as Record<string, unknown> | null),
    [summary],
  )

  const missing = useMemo(
    () => workspace?.pipelineBlockers.missing ?? summary?.required?.missing ?? [],
    [workspace, summary],
  )
  const problematic = useMemo(
    () => workspace?.pipelineBlockers.problematic ?? summary?.required?.problematic ?? [],
    [workspace, summary],
  )
  const inProgressTypes = useMemo(
    () => workspace?.pipelineBlockers.inProgress ?? summary?.required?.in_progress_types ?? [],
    [workspace, summary],
  )
  const readyTypes = useMemo(() => {
    if (workspace) {
      return workspace.items
        .filter((item) => item.runtime.satisfies_requirement === true)
        .map((item) => item.documentTypeCode)
    }
    return summary?.required?.ready_types ?? []
  }, [workspace, summary])

  const percentReady = workspace?.percentReady ?? summary?.percent_ready ?? 0

  const showMissingList = missing.length > 0 || problematic.length > 0
  const showInProgressOnly = !showMissingList && inProgressTypes.length > 0
  const pipelineBlockingEffective =
    blockersPresentation === 'historical'
      ? false
      : docsPipelineBlocking !== undefined
        ? docsPipelineBlocking
        : showMissingList || showInProgressOnly

  /** Hide checklist / blockers / request waiver noise when parent says docs do not block (e.g. New). */
  const hideEarlyStageDocDetails = docsPipelineBlocking === false && blockersPresentation !== 'historical'

  const waiverSectionVisible = useMemo(() => {
    if (docsPipelineBlocking === false && pipelineOverrides.length === 0) {
      return false
    }
    if (showPipelineWaiverSectionProp !== undefined) {
      return Boolean(showPipelineWaiverSectionProp)
    }
    return (
      pipelineOverrides.length > 0 ||
      canRequestPipelineOverride ||
      canApprovePipelineOverride
    )
  }, [
    docsPipelineBlocking,
    pipelineOverrides.length,
    showPipelineWaiverSectionProp,
    canRequestPipelineOverride,
    canApprovePipelineOverride,
  ])

  useEffect(() => {
    if (suppressBlockerCallbacks) return
    onLoadedBlockers?.({ missing, problematic, inProgress: inProgressTypes })
  }, [missing, problematic, inProgressTypes, onLoadedBlockers, suppressBlockerCallbacks])

  useEffect(() => {
    onSummaryLoaded?.(summary)
  }, [summary, onSummaryLoaded])

  useEffect(() => {
    if (!pollingEnabled || !candidateId) return
    const intervalMs = Math.max(pollingIntervalMs, 5_000)
    const timer = window.setInterval(() => {
      void load()
    }, intervalMs)
    return () => window.clearInterval(timer)
  }, [candidateId, load, pollingEnabled, pollingIntervalMs])

  // NOTE: polling is opt-in via `pollingEnabled` (e.g. while the documents drawer is open).

  const labelForType = useCallback(
    (code: string) => {
      const fromTypeCodes = t(`admin.documents.type_codes.${code}`, { defaultValue: '' }).trim()
      if (fromTypeCodes) return fromTypeCodes
      const fromProcessTypes = t(`admin.documents.process_types.${code}`, { defaultValue: '' }).trim()
      if (fromProcessTypes) return fromProcessTypes
      const normalized = String(code || '').replace(/[_-]+/g, ' ').trim()
      return normalized || code
    },
    [t],
  )

  const labelForRequirement = useCallback(
    (code: string) => {
      const fromKey = t(`app.candidate_card.requirements_checklist.requirements.${code}`, { defaultValue: '' }).trim()
      if (fromKey) return fromKey
      return String(code || '').replace(/_/g, ' ')
    },
    [t],
  )

  const labelForOverrideTarget = useCallback(
    (o: CandidatePipelineOverride) => {
      if (o.requirement_code) return labelForRequirement(o.requirement_code)
      return labelForType(String(o.doc_type_code || ''))
    },
    [labelForRequirement, labelForType],
  )

  const rows = useMemo(() => {
    const runtimeItems = extractRuntimeItemsFromSummary(summary as Record<string, unknown> | null)
    if (runtimeItems.length > 0) {
      const seen = new Set<string>()
      const out: DocRow[] = []
      for (const item of runtimeItems) {
        const type = String(item.document_type_code || '').trim()
        if (!type) continue
        const badgePresentation = runtimeBadgeFromRuntime(item.document_runtime)
        const status = runtimeBadgeToRowStatus(badgePresentation.badge)
        const key = `${type}::${status}`
        if (seen.has(key)) continue
        seen.add(key)
        out.push({ type, status, badgePresentation, runtime: item.document_runtime ?? null })
      }
      return out
    }

    const expMap = new Map<string, string>()
    for (const x of expiringSoon) {
      if (!x?.type) continue
      if (!expMap.has(String(x.type))) expMap.set(String(x.type), String(x.expires_at || ''))
    }

    const out: DocRow[] = []

    // Blockers first
    for (const code of missing) out.push({ type: code, status: 'missing' })
    for (const code of problematic) out.push({ type: code, status: 'missing', meta: 'needs_attention' })

    for (const code of readyTypes) out.push({ type: code, status: 'valid' })
    for (const code of inProgressTypes) out.push({ type: code, status: 'in_progress' })

    for (const code of expiringSoon.map((x) => String(x.type || '')).filter(Boolean)) {
      const expiresAt = expMap.get(code) || ''
      out.push({
        type: code,
        status: 'expiring',
        meta: expiresAt,
      })
    }

    // Deduplicate by type+status
    const seen = new Set<string>()
    return out.filter((r) => {
      const k = `${r.type}::${r.status}`
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
  }, [summary, expiringSoon, inProgressTypes, missing, problematic, readyTypes])

  const visibleRows = useMemo(() => {
    if (runtimeTypeFilter === 'all') return rows
    return rows.filter((row) => {
      if (row.runtime) {
        return runtimeMatchesFilter(row.runtime, runtimeTypeFilter)
      }
      return false
    })
  }, [rows, runtimeTypeFilter])

  const statusPill = useCallback(
    (s: RowStatus, opts?: { softChecklist?: boolean }) => {
      const soft = Boolean(opts?.softChecklist)
      switch (s) {
        case 'missing':
          return soft
            ? 'bg-slate-50 text-slate-700 border-slate-200'
            : 'bg-rose-50 text-rose-800 border-rose-200'
        case 'expiring':
          return 'bg-amber-50 text-amber-800 border-amber-200'
        case 'valid':
          return 'bg-emerald-50 text-emerald-800 border-emerald-200'
        case 'in_progress':
          return soft
            ? 'bg-slate-50 text-slate-600 border-slate-200'
            : 'bg-slate-50 text-slate-700 border-slate-200'
      }
    },
    [],
  )

  const normType = useCallback((c: string) => String(c || '').trim().toLowerCase(), [])

  const pendingByCode = useMemo(() => {
    const m = new Map<string, CandidatePipelineOverride>()
    for (const o of pipelineOverrides) {
      if (String(o.status).toLowerCase() !== 'pending') continue
      const k =
        waiverMode === 'requirement'
          ? normType(String(o.requirement_code || ''))
          : normType(String(o.doc_type_code || ''))
      if (!k) continue
      if (!m.has(k)) m.set(k, o)
    }
    return m
  }, [pipelineOverrides, normType, waiverMode])

  const blockerSource = externalBlockers ?? {
    missing,
    problematic,
    inProgress: inProgressTypes,
  }

  const blockerCodesForRequest = useMemo(() => {
    const codes = [
      ...blockerSource.missing,
      ...blockerSource.problematic,
      ...blockerSource.inProgress,
    ].filter(Boolean)
    const uniq: string[] = []
    const seen = new Set<string>()
    for (const c of codes) {
      const k = normType(c)
      if (!k || seen.has(k)) continue
      seen.add(k)
      uniq.push(c)
    }
    return uniq
  }, [blockerSource, normType])

  /** Codes that may appear in a waiver request (fail-safe targets excluded). */
  const waiverEligibleCodes = useMemo(() => {
    if (waiverMode === 'requirement') {
      return blockerCodesForRequest.filter((c) => !isNonOverridableRequirementCode(c))
    }
    return blockerCodesForRequest.filter((c) => !isNonOverridableDocTypeCode(c, nonOverridableEffective))
  }, [blockerCodesForRequest, nonOverridableEffective, waiverMode])

  const labelForWaiverCode = useCallback(
    (code: string) => (waiverMode === 'requirement' ? labelForRequirement(code) : labelForType(code)),
    [labelForRequirement, labelForType, waiverMode],
  )

  const allPipelineBlockersAreNonOverridable = useMemo(
    () =>
      docsPipelineBlocking === true &&
      blockerCodesForRequest.length > 0 &&
      waiverEligibleCodes.length === 0,
    [blockerCodesForRequest, waiverEligibleCodes, docsPipelineBlocking],
  )

  const [waiverTargetCode, setWaiverTargetCode] = useState<string>('')
  const [waiverReason, setWaiverReason] = useState('')
  const [waiverIncludeHandoff, setWaiverIncludeHandoff] = useState(false)

  useEffect(() => {
    if (!waiverTargetCode && waiverEligibleCodes.length) {
      setWaiverTargetCode(waiverEligibleCodes[0])
    }
  }, [waiverEligibleCodes, waiverTargetCode])

  const canOpenWaiverRequestModal = Boolean(
    docsPipelineBlocking === true &&
      canRequestPipelineOverride &&
      onCreatePipelineOverride &&
      waiverEligibleCodes.length &&
      !pipelineWaiverReadOnlyCard,
  )

  const [waiverModalOpen, setWaiverModalOpen] = useState(false)

  useEffect(() => {
    if (!waiverModalOpen || !waiverEligibleCodes.length) return
    if (!waiverEligibleCodes.includes(waiverTargetCode)) {
      setWaiverTargetCode(waiverEligibleCodes[0])
    }
  }, [waiverModalOpen, waiverEligibleCodes, waiverTargetCode])

  const formatExpDate = useCallback(
    (iso: string) => {
      if (!iso) return null
      try {
        return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : undefined, {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
        }).format(new Date(iso))
      } catch {
        return iso
      }
    },
    [locale],
  )

  const primary = Boolean(primaryStepHighlight)
  const shouldAutoOpenDetails = primary || showMissingList || showInProgressOnly || Boolean(documentsError)
  const canToggleDetails = !hideEarlyStageDocDetails

  useEffect(() => {
    if (!canToggleDetails) {
      setDetailsOpen(false)
      return
    }
    if (shouldAutoOpenDetails) {
      setDetailsOpen(true)
    }
  }, [canToggleDetails, shouldAutoOpenDetails])

  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white p-3 transition-shadow duration-200',
        primary && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
      )}
      data-rail-primary-step={primary ? 'true' : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold text-slate-800">
              {t('app.candidate_card.documents.title', { defaultValue: 'Documents' })}
            </div>
            {primary ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
                {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
              </span>
            ) : null}
          </div>

          <div className="mt-1 text-[11px] text-slate-600">
            {hideDocumentTypeChecklist && requirementsWorkspaceHref
              ? t('app.candidate_requirements.workspace.docs_rail_hint', {
                  defaultValue: 'Upload files here — confirm evidence in the requirements workspace.',
                })
              : hideDocumentTypeChecklist
              ? t('app.candidate_card.documents.operational_hub_hint', {
                  defaultValue: 'Upload and manage files — confirm requirements in the checklist above.',
                })
              : hideEarlyStageDocDetails
              ? t('app.candidate_card.documents.early_stage_hint', {
                  defaultValue: 'Documents are not required at this stage (e.g. New). Upload / Open full — optional.',
                })
              : showMissingList || showInProgressOnly
                ? pipelineBlockingEffective
                  ? t('app.candidate_card.documents.blockers_subtitle', { defaultValue: 'Blockers stop the pipeline' })
                  : blockersPresentation === 'historical'
                    ? t('app.candidate_card.documents.blockers_subtitle_historical', {
                        defaultValue: 'Checklist snapshot — informational for a closed candidate (not blocking).',
                      })
                    : t('app.candidate_card.documents.blockers_subtitle_soft', {
                        defaultValue: 'Checklist visible — not blocking this stage',
                      })
                : t('app.candidate_card.documents.ok_subtitle', {
                    defaultValue: 'Ready to move forward',
                    values: { percent: percentReady },
                  })}
          </div>
          {workspace && (!hideDocumentTypeChecklist || requirementsWorkspaceHref) ? (
            <div className="mt-1 text-[11px] font-medium text-slate-700">
              {t('app.candidate_card.documents.runtime_kpi', {
                defaultValue: '{ready}/{total} satisfied · {percent}%',
                values: {
                  ready: workspace.satisfiedCount,
                  total: workspace.totalRequired,
                  percent: workspace.percentReady,
                },
              })}
            </div>
          ) : null}
        </div>

        {onUpload ? (
          <button type="button" className="btn-primary btn-sm" onClick={onUpload} disabled={uploadBusy}>
            {uploadBusy ? t('common.saving', { defaultValue: 'Working...' }) : t('app.candidate_card.documents.upload_btn', { defaultValue: 'Upload' })}
          </button>
        ) : null}
      </div>

      {waiverSectionVisible ? (
        <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-indigo-900">
            {t('app.candidate_card.pipeline_override.section_title', {
              defaultValue:
                waiverMode === 'requirement' ? 'Requirement waivers' : 'Document waivers',
            })}
          </div>
          <div className="mt-1 text-[11px] text-indigo-800/90">
            {t('app.candidate_card.pipeline_override.section_hint', {
              defaultValue: 'Recruiter requests → manager approves. Pipeline-only or including handoff gate.',
            })}
          </div>

          {pipelineWaiverReadOnlyCard ? (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/80 px-2 py-1.5 text-[11px] text-amber-950">
              {t('app.candidate_card.pipeline_override.read_only_card', {
                defaultValue:
                  'This candidate card is read-only (e.g. declined). New waiver requests are disabled; pending items can still be approved by a manager.',
              })}
            </div>
          ) : null}

          {pipelineOverrides.filter((o) => String(o.status).toLowerCase() === 'pending').length ? (
            <div className="mt-2 space-y-2">
              {pipelineOverrides
                .filter((o) => String(o.status).toLowerCase() === 'pending')
                .map((o) => (
                  <div key={o.id} className="rounded-lg border border-indigo-200 bg-white p-2 text-xs">
                    <div className="font-semibold text-slate-900">{labelForOverrideTarget(o)}</div>
                    <div className="mt-0.5 text-[11px] text-slate-600">
                      {t('app.candidate_card.pipeline_override.requested_scope', {
                        defaultValue: 'Requested',
                      })}
                      :{' '}
                      {o.requested_scope === 'both'
                        ? t('app.candidate_card.pipeline_override.scope_both', { defaultValue: 'pipeline + handoff' })
                        : t('app.candidate_card.pipeline_override.scope_pipeline', { defaultValue: 'pipeline only' })}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-700 line-clamp-3">{o.reason}</div>
                    {canApprovePipelineOverride && onApprovePipelineOverride && onRejectPipelineOverride ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          disabled={pipelineOverrideBusy}
                          onClick={() => void onApprovePipelineOverride(o.id, 'pipeline')}
                        >
                          {t('app.candidate_card.pipeline_override.approve_pipeline', { defaultValue: 'Approve (pipeline)' })}
                        </button>
                        <button
                          type="button"
                          className="btn-primary btn-xs"
                          disabled={pipelineOverrideBusy}
                          onClick={() => void onApprovePipelineOverride(o.id, 'both')}
                        >
                          {t('app.candidate_card.pipeline_override.approve_both', { defaultValue: 'Approve + handoff' })}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary btn-xs text-rose-800"
                          disabled={pipelineOverrideBusy}
                          onClick={() => void onRejectPipelineOverride(o.id)}
                        >
                          {t('app.candidate_card.pipeline_override.reject', { defaultValue: 'Reject' })}
                        </button>
                      </div>
                    ) : (
                      <div className="mt-2 text-[11px] font-medium text-amber-800">
                        {t('app.candidate_card.pipeline_override.awaiting_manager', {
                          defaultValue: 'Awaiting manager approval',
                        })}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          ) : null}

          {pipelineOverrides.some((o) => String(o.status).toLowerCase() === 'approved') ? (
            <div className="mt-2 space-y-1">
              <div className="text-[11px] font-semibold text-emerald-900">
                {t('app.candidate_card.pipeline_override.active_title', { defaultValue: 'Active waivers' })}
              </div>
              <ul className="space-y-1">
                {pipelineOverrides
                  .filter((o) => String(o.status).toLowerCase() === 'approved')
                  .map((o) => (
                    <li key={o.id} className="text-[11px] text-emerald-900">
                      {labelForOverrideTarget(o)} —{' '}
                      {o.granted_scope === 'both'
                        ? t('app.candidate_card.pipeline_override.granted_both', { defaultValue: 'pipeline + handoff' })
                        : t('app.candidate_card.pipeline_override.granted_pipeline', { defaultValue: 'pipeline' })}
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}

          {canOpenWaiverRequestModal ? (
            <button
              type="button"
              className="btn-secondary btn-sm mt-3 w-full"
              onClick={() => setWaiverModalOpen(true)}
            >
              {t('app.candidate_card.pipeline_override.open_request_modal', {
                defaultValue: 'Request document waiver…',
              })}
            </button>
          ) : loading && docsPipelineBlocking === true && canRequestPipelineOverride && onCreatePipelineOverride ? (
            <div className="mt-2 text-[11px] text-indigo-800">
              {t('app.candidate_card.pipeline_override.loading_blockers', {
                defaultValue: 'Loading document list for waiver…',
              })}
            </div>
          ) : docsPipelineBlocking === true &&
            allPipelineBlockersAreNonOverridable &&
            !pipelineOverrides.some((o) => String(o.status).toLowerCase() === 'pending') &&
            !pipelineOverrides.some((o) => String(o.status).toLowerCase() === 'approved') ? (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/80 px-2 py-2 text-[11px] font-medium text-amber-950">
              {t('app.candidate_card.pipeline_override.non_overridable_blockers', {
                defaultValue:
                  'These missing documents (identity / work authorization) cannot be waived. Upload valid files or adjust the case with your compliance process.',
              })}
            </div>
          ) : docsPipelineBlocking === true &&
            !pipelineOverrides.some((o) => String(o.status).toLowerCase() === 'pending') &&
            !pipelineOverrides.some((o) => String(o.status).toLowerCase() === 'approved') &&
            !canOpenWaiverRequestModal &&
            !(loading && canRequestPipelineOverride && onCreatePipelineOverride) ? (
            <div className="mt-2 text-[11px] text-indigo-900/85">
              {t('app.candidate_card.pipeline_override.empty_state_blocking', {
                defaultValue:
                  'When documents block the pipeline, you can request a waiver here (opens a form). Supervisors approve pending items below.',
              })}
            </div>
          ) : null}
        </div>
      ) : null}

      {!hideEarlyStageDocDetails && !hideDocumentTypeChecklist ? (
        <div className="mt-3">
          {canToggleDetails ? (
            <button
              type="button"
              className="mb-2 text-[11px] text-slate-500 hover:text-slate-700"
              onClick={() => setDetailsOpen((v) => !v)}
            >
              {detailsOpen
                ? t('common.actions.collapse', { defaultValue: 'Collapse' })
                : t('common.actions.expand', { defaultValue: 'Expand' })}
            </button>
          ) : null}
          {detailsOpen ? (
            loading ? (
              <div className="text-xs text-slate-500">{t('common.loading')}</div>
            ) : documentsError ? (
              <div className="text-xs text-rose-600">
                <div>{documentsError.title}</div>
                {documentsError.detail ? (
                  <div className="mt-0.5 text-[11px] text-rose-700/90">{documentsError.detail}</div>
                ) : null}
              </div>
            ) : (
              <div className="space-y-1">
                <select
                  className="input mb-2 w-full text-xs"
                  aria-label={t('admin.documents.filters.runtime_status', { defaultValue: 'Runtime status' })}
                  value={runtimeTypeFilter}
                  onChange={(e) =>
                    setRuntimeTypeFilter(
                      e.target.value === 'all' ? 'all' : (e.target.value as RuntimeDocumentFilterSelection),
                    )
                  }
                >
                  <option value="all">{t('admin.documents.filters.all_statuses')}</option>
                  {RUNTIME_DOCUMENT_FILTERS.map((value) => (
                    <option key={value} value={value}>
                      {t(RUNTIME_FILTER_LABEL_KEYS[value], { defaultValue: value })}
                    </option>
                  ))}
                </select>
                {visibleRows.length ? (
                  visibleRows.map((r, idx) => (
                    <button
                      key={`${r.type}-${r.status}-${idx}`}
                      type="button"
                      className={clsx(
                        'w-full rounded-xl border px-2 py-1.5 text-left transition hover:shadow-sm',
                        statusPill(r.status, { softChecklist: !pipelineBlockingEffective }),
                      )}
                      onClick={() => {
                        if (r.type) onSelectType?.(r.type)
                        onOpenDocs?.()
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0 text-xs font-semibold text-slate-900 truncate">
                          {labelForType(r.type)}
                        </div>
                        <div className="shrink-0 text-[11px] font-semibold">
                          {r.badgePresentation ? (
                            <>
                              → {t(r.badgePresentation.labelKey, { defaultValue: r.badgePresentation.badge })}
                            </>
                          ) : r.status === 'missing'
                            ? pipelineBlockingEffective
                              ? `→ ${t('app.candidate_card.documents.status.missing', { defaultValue: 'missing' })}`
                              : `→ ${t('app.candidate_card.documents.status.checklist_not_uploaded', { defaultValue: 'not uploaded yet' })}`
                            : r.status === 'valid'
                              ? `→ ${t('app.candidate_card.documents.status.valid', { defaultValue: 'valid' })}`
                              : r.status === 'expiring'
                                ? `→ ${t('app.candidate_card.documents.status.expiring', { defaultValue: 'expiring' })}${r.meta ? ` · ${formatExpDate(r.meta)}` : ''}`
                                : pipelineBlockingEffective
                                  ? `→ ${t('app.candidate_card.documents.status.in_progress', { defaultValue: 'in progress' })}`
                                  : `→ ${t('app.candidate_card.documents.status.checklist_in_review', { defaultValue: 'uploaded — review later' })}`}
                        </div>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="text-xs text-slate-500">{t('admin.documents.filters.no_results', { defaultValue: 'No results.' })}</div>
                )}
              </div>
            )
          ) : (
            <div className="text-xs text-slate-500">
              {t('app.candidate_card.documents.compact_hint', {
                defaultValue: 'Document details are collapsed to reduce noise.',
              })}
            </div>
          )}
        </div>
      ) : null}

      {onOpenDocs || requirementsWorkspaceHref ? (
        <div className="mt-2 flex flex-col gap-2">
          {requirementsWorkspaceHref ? (
            <Link to={requirementsWorkspaceHref} className="btn-primary btn-sm w-full text-center">
              {t('app.candidate_requirements.workspace.open_workspace', { defaultValue: 'Open workspace' })}
            </Link>
          ) : null}
          {onOpenDocs ? (
            <button type="button" className="btn-secondary btn-sm w-full" onClick={onOpenDocs}>
              {t('app.candidate_card.docs_panel.open_full', { defaultValue: 'Open full' })}
            </button>
          ) : null}
        </div>
      ) : null}

      {!hideEarlyStageDocDetails && !hideDocumentTypeChecklist && detailsOpen ? (
        <div
          className={clsx(
            'mt-3 rounded-xl border p-3',
            showMissingList || (showInProgressOnly && pipelineBlockingEffective)
              ? pipelineBlockingEffective
                ? 'border-rose-200 bg-rose-50'
                : 'border-slate-200 bg-slate-50'
              : 'border-slate-200 bg-slate-50',
          )}
        >
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-700">
            {pipelineBlockingEffective
              ? t('app.candidate_card.documents.what_blocks_title', { defaultValue: 'What blocks this candidate' })
              : t('app.candidate_card.documents.checklist_panel_title', { defaultValue: 'Document checklist' })}
          </div>

          {stageSummaryLabel ? (
            <div className="mt-1 text-xs font-medium text-slate-600">
              {t('app.candidate_card.documents.stage_context', { defaultValue: 'Stage' })}: {stageSummaryLabel}
            </div>
          ) : null}

          {showMissingList ? (
            <div className="mt-2 space-y-2">
              <div>
                <div
                  className={clsx(
                    'text-xs font-semibold',
                    pipelineBlockingEffective ? 'text-rose-800' : 'text-slate-800',
                  )}
                >
                  {pipelineBlockingEffective
                    ? t('app.candidate_card.documents.missing_label', { defaultValue: 'Missing' })
                    : t('app.candidate_card.documents.checklist_not_yet_required', {
                        defaultValue: 'Not uploaded yet (not required at this stage)',
                      })}
                </div>
                <ul className="mt-1 space-y-1">
                  {(workspace?.blockingItems.length
                    ? workspace.blockingItems.map((item) => item.documentTypeCode)
                    : [...missing, ...problematic]
                  )
                    .slice(0, 8)
                    .map((code) => (
                    <li
                      key={code}
                      className={clsx('text-xs', pipelineBlockingEffective ? 'text-rose-800' : 'text-slate-800')}
                    >
                      {labelForType(code)}
                    </li>
                  ))}
                </ul>
              </div>

              {workspace?.warningOnlyItems.length ? (
                <div>
                  <div className="text-xs font-semibold text-amber-800">
                    {t('app.candidate_card.docs_checklist.expiring', { defaultValue: 'Expiring soon' })}
                  </div>
                  <ul className="mt-1 space-y-1">
                    {workspace.warningOnlyItems.slice(0, 6).map((item) => (
                      <li key={item.documentTypeCode} className="text-xs text-amber-900">
                        {labelForType(item.documentTypeCode)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div
                className={clsx(
                  'text-xs font-medium',
                  pipelineBlockingEffective ? 'text-rose-900' : 'text-slate-700',
                )}
              >
                {pipelineBlockingEffective
                  ? t('app.candidate_card.documents.next_step', { defaultValue: 'Next step: → Request documents' })
                  : t('app.candidate_card.documents.next_step_not_blocking', {
                      defaultValue: 'Not blocking pipeline at this stage — contact & qualify first.',
                    })}
              </div>
            </div>
          ) : showInProgressOnly ? (
            <div className="mt-2 space-y-2">
              <div className="text-xs font-semibold text-slate-800">
                {t('app.candidate_card.documents.in_progress_label', { defaultValue: 'In progress / review' })}
              </div>
              <ul className="mt-1 space-y-1">
                {inProgressTypes.slice(0, 8).map((code) => (
                  <li key={code} className="text-xs text-slate-800">
                    {labelForType(code)}
                  </li>
                ))}
              </ul>
              <div
                className={clsx(
                  'text-xs font-medium',
                  pipelineBlockingEffective ? 'text-amber-900' : 'text-slate-700',
                )}
              >
                {pipelineBlockingEffective
                  ? t('app.candidate_card.documents.next_step_verify', {
                      defaultValue: 'Next step: → Verify documents before moving forward',
                    })
                  : t('app.candidate_card.documents.in_progress_not_blocking', {
                      defaultValue: 'Uploads in progress — not blocking this stage.',
                    })}
              </div>
            </div>
          ) : (
            <div className="mt-2 text-xs text-slate-700">
              {t('app.candidate_card.documents.no_blocks', { defaultValue: 'No blockers for this stage.' })}
            </div>
          )}
        </div>
      ) : null}

      {waiverModalOpen && canOpenWaiverRequestModal && onCreatePipelineOverride && typeof document !== 'undefined'
        ? createPortal(
            <div
              className="fixed inset-0 z-[10060] flex items-center justify-center bg-black/40 p-4"
              role="presentation"
              onClick={() => !pipelineOverrideBusy && setWaiverModalOpen(false)}
              onKeyDown={(e) => {
                if (e.key === 'Escape' && !pipelineOverrideBusy) setWaiverModalOpen(false)
              }}
            >
              <div
                role="dialog"
                aria-modal="true"
                className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-xl"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="text-sm font-semibold text-slate-900">
                  {t('app.candidate_card.pipeline_override.request_title', { defaultValue: 'Request waiver' })}
                </div>
                <p className="mt-1 text-xs text-slate-600">
                  {t('app.candidate_card.pipeline_override.modal_hint', {
                    defaultValue: 'Ask a supervisor to waive a document requirement for pipeline or handoff.',
                  })}
                </p>
                <div className="mt-4 space-y-3">
                  <label className="block text-xs text-slate-600">
                    {t(
                      waiverMode === 'requirement'
                        ? 'app.candidate_card.pipeline_override.requirement_code'
                        : 'app.candidate_card.pipeline_override.doc_type',
                      {
                        defaultValue:
                          waiverMode === 'requirement' ? 'Requirement' : 'Document type',
                      },
                    )}
                    <select
                      className="mt-1 w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={waiverTargetCode}
                      onChange={(e) => setWaiverTargetCode(e.target.value)}
                    >
                      {waiverEligibleCodes.map((c) => (
                        <option key={c} value={c} disabled={pendingByCode.has(normType(c))}>
                          {labelForWaiverCode(c)}
                          {pendingByCode.has(normType(c))
                            ? ` (${t('app.candidate_card.pipeline_override.pending_suffix', { defaultValue: 'pending' })})`
                            : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-xs text-slate-600">
                    {t('app.candidate_card.pipeline_override.reason', { defaultValue: 'Reason (min. 8 characters)' })}
                    <textarea
                      className={clsx(
                        'mt-1 w-full rounded-md border px-2 py-1.5 text-sm',
                        waiverReason.trim().length > 0 && waiverReason.trim().length < 8
                          ? 'border-amber-300 bg-amber-50/50'
                          : 'border-slate-200',
                      )}
                      rows={4}
                      value={waiverReason}
                      onChange={(e) => setWaiverReason(e.target.value)}
                    />
                    <div className="mt-1 flex justify-between text-[10px] text-slate-500">
                      <span>{waiverReason.trim().length}/8</span>
                      {waiverReason.trim().length > 0 && waiverReason.trim().length < 8 ? (
                        <span className="font-medium text-amber-800">
                          {t('app.candidate_card.pipeline_override.reason_too_short', {
                            defaultValue: 'Enter at least 8 characters to submit.',
                          })}
                        </span>
                      ) : null}
                    </div>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-700">
                    <input
                      type="checkbox"
                      checked={waiverIncludeHandoff}
                      onChange={(e) => setWaiverIncludeHandoff(e.target.checked)}
                    />
                    {t('app.candidate_card.pipeline_override.ask_handoff', {
                      defaultValue: 'Also request handoff gate (ready_for_handoff)',
                    })}
                  </label>
                </div>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={pipelineOverrideBusy}
                    onClick={() => setWaiverModalOpen(false)}
                  >
                    {t('common.cancel', { defaultValue: 'Cancel' })}
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={
                      pipelineOverrideBusy ||
                      !waiverTargetCode ||
                      waiverReason.trim().length < 8 ||
                      pendingByCode.has(normType(waiverTargetCode))
                    }
                    onClick={() =>
                      void onCreatePipelineOverride({
                        ...(waiverMode === 'requirement'
                          ? { requirement_code: waiverTargetCode }
                          : { doc_type_code: waiverTargetCode }),
                        reason: waiverReason.trim(),
                        requested_scope: waiverIncludeHandoff ? 'both' : 'pipeline',
                      }).then(() => {
                        setWaiverReason('')
                        setWaiverIncludeHandoff(false)
                        setWaiverModalOpen(false)
                      })
                    }
                  >
                    {pipelineOverrideBusy
                      ? t('common.saving', { defaultValue: 'Working...' })
                      : t('app.candidate_card.pipeline_override.submit', { defaultValue: 'Submit request' })}
                  </button>
                </div>
              </div>
            </div>,
            document.body,
          )
        : null}
    </section>
  )
}
