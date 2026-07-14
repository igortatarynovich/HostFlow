import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../../api/client'
import { getCachedCandidate, setCachedCandidate } from '../../../api/candidateCache'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { useMetaStages } from '../../../store/useMeta'
import { useI18n } from '../../../i18n'
import { translateReasonLabel, translateStageLabel } from '../../../utils/stageLabels'
import type { AugmentedCandidate } from '../types'
import {
  augmentCandidateForEntityPassport,
  buildCandidateEntityWorkspaceActionConfig,
  candidateTelHref,
  deriveCandidateReasonData,
} from '../candidateEntityWorkspaceUtils'
import {
  buildCandidatesEntityModelSchema,
  resolveCandidateEntityPassport,
} from '../candidatesEntityModel'
import { useCandidatesWorkPanelPreview } from './useCandidatesWorkPanelPreview'
import { useCandidatesDetailRailHandoff } from './useCandidatesDetailRailHandoff'
import { extractExtraObject } from '../candidateUtils'
import { useCandidateEntityWorkspaceProfile } from './useCandidateEntityWorkspaceProfile'
import { useEffectiveCandidateLayout } from '../../../hooks/useEffectiveCandidateLayout'

export function useCandidateEntityWorkspace(candidateId: string | undefined) {
  const { t, locale } = useI18n()
  const navigate = useNavigate()
  const meta = useMetaStages()

  const [candidate, setCandidate] = useState<AugmentedCandidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const workPanel = useCandidatesWorkPanelPreview({
    t,
    selectedCandidateId: candidateId ?? null,
  })
  const { handoffStatus, handoffLoading } = useCandidatesDetailRailHandoff(candidateId ?? null)

  const { candidateProfile, profileLoading } = useCandidateEntityWorkspaceProfile(candidate?.vacancy_id ?? null)
  const { effectiveLayout, layoutLoading } = useEffectiveCandidateLayout({
    enabled: Boolean(candidateId),
    candidateId: candidateId ?? null,
    candidateProfileId: candidateProfile?.id ?? null,
  })

  const reloadCandidate = useCallback(async () => {
    if (!candidateId) return
    const { data } = await api.get(`/candidates/${candidateId}`)
    const augmented = augmentCandidateForEntityPassport(data)
    setCandidate(augmented)
    setCachedCandidate(candidateId, data)
  }, [candidateId])

  useEffect(() => {
    if (!candidateId) {
      setCandidate(null)
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    void (async () => {
      try {
        const cached = getCachedCandidate(candidateId)
        if (cached && !cancelled) {
          setCandidate(augmentCandidateForEntityPassport(cached))
        }
        const { data } = await api.get(`/candidates/${candidateId}`)
        if (cancelled) return
        const augmented = augmentCandidateForEntityPassport(data)
        setCandidate(augmented)
        setCachedCandidate(candidateId, data)
      } catch (err: unknown) {
        if (cancelled) return
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 404) {
          navigate(CRM_APP_PATHS.candidates)
          return
        }
        setError(t('common.errors.load_failed', { defaultValue: 'Не удалось загрузить кандидата' }))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [candidateId, navigate, t])

  const entityModel = useMemo(() => buildCandidatesEntityModelSchema(t), [t])

  const reasonLabelMap = useMemo(() => {
    const map = new Map<string, string>()
    candidate?.__reasonCodes?.forEach((code) => {
      map.set(code, translateReasonLabel(t, code, code))
    })
    return map
  }, [candidate?.__reasonCodes, t])

  const passport = useMemo(() => {
    if (!candidate) return null
    const c = candidate as Record<string, unknown>
    const stageCode = String(candidate.stage || '')
    const stageLabel = translateStageLabel(
      t,
      stageCode,
      String((candidate as { stage_label?: string }).stage_label || meta?.labels?.[stageCode] || stageCode),
    )
    const rowStatus = (candidate as { row_status?: string }).row_status
    const rowStatusLabel = rowStatus
      ? t(`app.candidates.row_status.${rowStatus}`, { defaultValue: String(rowStatus) })
      : undefined
    const managerId = (candidate as { manager_id?: string }).manager_id ?? candidate.manager
    const managerLabel =
      candidate.manager_name ??
      (managerId ? String(managerId) : undefined)
    const vacancyId = candidate.vacancy_id
    const vacancyLabel = candidate.vacancy_name ?? undefined
    const origin = (candidate as { origin?: Record<string, unknown> }).origin
    const recruitmentSearchId =
      typeof origin?.recruitment_search_id === 'string'
        ? origin.recruitment_search_id
        : typeof origin?.search_id === 'string'
          ? origin.search_id
          : null
    const recruitmentSearchLabel =
      typeof origin?.recruitment_search_title === 'string'
        ? origin.recruitment_search_title
        : typeof origin?.search_title === 'string'
          ? origin.search_title
          : vacancyLabel ?? null

    const phoneHref = candidateTelHref(String(candidate.phone || ''))
    const emailHref = workPanel.previewCommsLinks?.emailRelativeUrl ??
      (candidate.email ? `mailto:${candidate.email}` : undefined)
    const messagesHref = workPanel.previewCommsLinks?.messagesRelativeUrl

    return resolveCandidateEntityPassport({
      t,
      locale,
      candidate,
      stageLabel,
      rowStatusLabel,
      managerLabel: managerLabel ?? undefined,
      vacancyId,
      vacancyLabel,
      phoneHref,
      emailHref,
      messagesHref,
      handoffStatus,
      previewReminders: workPanel.previewReminders,
      docsBlockers: workPanel.docsBlockers,
      docsBlockersLoading: workPanel.docsBlockersLoading,
      usesRequirementBlockers: workPanel.usesRequirementBlockers,
      previewRequirementsSummary: workPanel.previewRequirementsSummary,
      previewPipelineOverrides: workPanel.previewPipelineOverrides,
      documentsSnapshot: workPanel.previewDocumentsSummarySnapshot,
      timelineItems: workPanel.previewTimelineItems,
      reasonCodes: candidate.__reasonCodes ?? [],
      reasonFallbackLabels: candidate.__reasonFallbackLabels ?? [],
      reasonLabelMap,
      contactAttemptCount: workPanel.previewCandidateExtra?.contact_attempt_count ?? 0,
      recruitmentSearchId,
      recruitmentSearchLabel,
    })
  }, [
    candidate,
    handoffStatus,
    locale,
    meta?.labels,
    reasonLabelMap,
    t,
    workPanel.docsBlockers,
    workPanel.docsBlockersLoading,
    workPanel.previewCandidateExtra?.contact_attempt_count,
    workPanel.previewCommsLinks?.emailRelativeUrl,
    workPanel.previewCommsLinks?.messagesRelativeUrl,
    workPanel.previewDocumentsSummarySnapshot,
    workPanel.previewPipelineOverrides,
    workPanel.previewReminders,
    workPanel.previewRequirementsSummary,
    workPanel.previewTimelineItems,
    workPanel.usesRequirementBlockers,
  ])

  const buildActionConfig = useCallback(
    (onOpenDocuments: () => void) => {
      if (!passport) return undefined
      return buildCandidateEntityWorkspaceActionConfig({
        passport,
        phoneHref: candidateTelHref(String(candidate?.phone || '')),
        emailHref:
          workPanel.previewCommsLinks?.emailRelativeUrl ??
          (candidate?.email ? `mailto:${candidate.email}` : undefined),
        messagesHref: workPanel.previewCommsLinks?.messagesRelativeUrl,
        onOpenDocuments,
        onCompleteNextReminder: workPanel.handleCompletePreviewReminder,
        nextReminderId: passport.sections.tasks.nextTaskId,
      })
    },
    [candidate?.email, candidate?.phone, passport, workPanel.handleCompletePreviewReminder, workPanel.previewCommsLinks],
  )

  const enrichLoading = loading || workPanel.previewRemindersLoading || handoffLoading || profileLoading || layoutLoading

  return {
    candidate,
    entityModel,
    passport,
    enrichLoading,
    error,
    workPanel,
    handoffStatus,
    reloadCandidate,
    buildActionConfig,
    candidateProfile,
    effectiveLayout,
    deriveReasonData: candidate
      ? deriveCandidateReasonData(
          candidate as Record<string, unknown>,
          extractExtraObject(
            (candidate as Record<string, unknown>).extra_summary ??
              (candidate as Record<string, unknown>).extra ??
              candidate.extra ??
              null,
          ),
        )
      : null,
  }
}
