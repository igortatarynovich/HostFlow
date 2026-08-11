import type { ReminderRecord } from '../../api/types/notification'
import type { HandoffStatusResponse } from '../../api/handoffs'
import type { DetailRailContactAction, DetailRailModel } from '../../platform/detail-rail'
import { recruitmentSearchPath, CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { CandidateDocsRailSummarySnapshot } from '../../components/candidate/CandidateDocsRailPanel'
import type { WorkPanelRequirementsSummary } from '../../utils/workPanelRequirements'
import type { DocBlockersPayload } from '../../utils/candidateStageDocPolicy'
import type { CandidatePipelineOverride } from '../../api/candidatePipelineOverrides'
import { CANDIDATES_RESOURCE_ID } from './candidatesResourceSchema'
import { formatDateSafe } from './candidateUtils'
import type { CandidatesWorkPanelCommsLinks } from './hooks/useCandidatesWorkPanelPreview'
import {
  buildDecisionHistoryItems,
  buildDocumentRailItems,
  candidateRailHasRecruiterAction,
  filterRecruiterActionReminders,
  formatCandidateReasonText,
  pickNextReminder,
  resolveCandidateRequiredContext,
  resolveCandidatesObjectDecision,
  resolveCandidateRailMode,
  resolveCandidatesNextAction,
  resolveEffectiveBlockers,
  resolveHeaderProcessLabel,
  resolveRecruitmentProcessOutcome,
} from './candidatesDetailRailLogic'

export type BuildCandidatesDetailRailArgs = {
  t: (key: string, options?: any) => string
  locale: string
  candidate: Record<string, unknown>
  stageLabel: string
  rowStatusLabel?: string
  managerLabel?: string
  vacancyLabel?: string
  vacancyId?: string | null
  companyLabel?: string
  sourceLabel?: string
  reasonCodes?: string[]
  reasonFallbackLabels?: string[]
  reasonLabelMap?: Map<string, string>
  updatedAtLabel?: string | null
  commsLinks?: CandidatesWorkPanelCommsLinks | null
  phoneHref?: string | null
  timelineItems?: Array<{ at: string; title?: string | null; description?: string | null; kind?: string; source?: string }>
  previewReminders?: ReminderRecord[]
  docsBlockers: DocBlockersPayload
  docsBlockersLoading?: boolean
  usesRequirementBlockers?: boolean
  previewRequirementsSummary?: WorkPanelRequirementsSummary | null
  previewPipelineOverrides?: CandidatePipelineOverride[]
  documentsSnapshot?: CandidateDocsRailSummarySnapshot | null
  handoffStatus?: HandoffStatusResponse | null
  contactAttemptCount?: number
  firstContactAt?: string | null
  recruitmentSearchId?: string | null
  recruitmentSearchLabel?: string | null
  onOpenFullProfile: (candidateId: string) => void
  onOpenDocuments: (candidateId: string) => void
  onOpenDocType?: (candidateId: string, typeCode: string) => void
  onOpenInbox?: (candidateId: string) => void
  onOpenVacancy?: (vacancyId: string) => void
  onOpenRecruitmentSearch?: (searchId: string) => void
  onCreateTask?: () => void
  onDocsRequestCreate?: () => void
  onCompleteNextReminder?: (reminderId: string) => void
  onHandoffAction?: () => void
}

function displayName(candidate: Record<string, unknown>, t: BuildCandidatesDetailRailArgs['t']): string {
  if (candidate.masked === true) {
    const shortId = candidate.short_id
    if (shortId) {
      return t('app.candidates.table.masked_label_short_id', {
        defaultValue: 'Кандидат {short_id}',
        values: { short_id: String(shortId) },
      })
    }
    const id = String(candidate.id ?? '').slice(0, 8)
    return t('app.candidates.table.masked_label', {
      defaultValue: 'Кандидат #{id}',
      values: { id },
    })
  }
  const name = `${candidate.first_name ?? ''} ${candidate.last_name ?? ''}`.trim()
  return name || t('common.labels.not_available', { defaultValue: '—' })
}

/** Maps candidate row → contextual decision rail (process state, not data dump). */
export function buildCandidatesDetailRailModel({
  t,
  locale,
  candidate,
  stageLabel,
  rowStatusLabel,
  managerLabel,
  vacancyId,
  commsLinks,
  phoneHref,
  timelineItems = [],
  previewReminders = [],
  docsBlockers,
  docsBlockersLoading = false,
  usesRequirementBlockers = false,
  previewRequirementsSummary = null,
  previewPipelineOverrides = [],
  documentsSnapshot = null,
  handoffStatus = null,
  contactAttemptCount = 0,
  reasonCodes = [],
  reasonFallbackLabels = [],
  reasonLabelMap,
  updatedAtLabel,
  onOpenFullProfile,
  onOpenDocuments,
  onOpenDocType,
  onOpenInbox,
  onOpenRecruitmentSearch,
  onCreateTask,
  onDocsRequestCreate,
  onCompleteNextReminder,
  onHandoffAction,
  recruitmentSearchId,
  recruitmentSearchLabel,
}: BuildCandidatesDetailRailArgs): DetailRailModel {
  const id = String(candidate.id ?? '')
  const phone = candidate.phone ? String(candidate.phone) : undefined
  const email = candidate.email ? String(candidate.email) : undefined
  const messagesHref = commsLinks?.messagesRelativeUrl
  const emailHref = commsLinks?.emailRelativeUrl ?? (email ? `mailto:${email}` : undefined)
  const tel = phoneHref ?? (phone ? `tel:${phone.replace(/\s/g, '')}` : undefined)
  const stageCode = String(candidate.stage || '') || null
  const railMode = resolveCandidateRailMode(candidate, handoffStatus)
  const hasRecruiterAction = candidateRailHasRecruiterAction(railMode)
  const reasonText = formatCandidateReasonText({ t, reasonCodes, reasonFallbackLabels, reasonLabelMap })

  const effectiveBlockers = resolveEffectiveBlockers({
    docsBlockers,
    usesRequirementBlockers,
    previewRequirementsSummary,
    previewPipelineOverrides,
  })

  const processOutcome = resolveRecruitmentProcessOutcome({
    t,
    locale,
    railMode,
    handoffStatus,
    reasonText,
    managerLabel,
    updatedAtLabel,
  })

  const nextActionResolved = hasRecruiterAction
    ? resolveCandidatesNextAction({
        t,
        locale,
        candidate,
        reminders: previewReminders,
        blockers: effectiveBlockers,
        docsBlockersLoading,
        usesRequirementBlockers,
        stageCode,
        vacancyId,
        contactAttemptCount,
        railMode,
        reasonText,
      })
    : null

  const actionableReminders = filterRecruiterActionReminders(previewReminders, railMode)
  const nextReminder = hasRecruiterAction ? pickNextReminder(actionableReminders) : null

  const primaryOnClick = () => {
    if (!nextActionResolved?.primaryActionKind) return
    switch (nextActionResolved.primaryActionKind) {
      case 'request_documents':
        onDocsRequestCreate?.() ?? onOpenDocuments(id)
        return
      case 'documents':
        onOpenDocuments(id)
        return
      case 'handoff':
        onHandoffAction?.() ?? onOpenFullProfile(id)
        return
      case 'complete_reminder': {
        const reminder = pickNextReminder(actionableReminders)
        if (reminder && onCompleteNextReminder) {
          onCompleteNextReminder(String(reminder.id))
        }
        return
      }
      case 'call':
      default:
        if (tel) window.location.href = tel
    }
  }

  const contactActions =
    hasRecruiterAction && (railMode === 'contact' || railMode === 'qualify' || railMode === 'docs')
      ? [
          tel
            ? ({
                id: 'call',
                label: t('app.candidates.actions.call', { defaultValue: 'Позвонить' }),
                href: tel,
                variant: nextActionResolved?.primaryActionKind === 'call' ? 'primary' : 'secondary',
                icon: 'phone',
              } satisfies DetailRailContactAction)
            : null,
          messagesHref
            ? ({
                id: 'whatsapp',
                label: 'WhatsApp',
                href: messagesHref,
                variant: 'secondary',
                icon: 'whatsapp',
              } satisfies DetailRailContactAction)
            : null,
          emailHref
            ? ({
                id: 'email',
                label: 'Email',
                href: emailHref,
                variant: 'secondary',
                icon: 'email',
              } satisfies DetailRailContactAction)
            : null,
        ].filter((action): action is DetailRailContactAction => action != null)
      : []

  const secondaryActions = hasRecruiterAction
    ? ([
        railMode === 'contact' || railMode === 'qualify'
          ? onCreateTask
            ? {
                id: 'task',
                label: t('app.candidates.actions.create_task', { defaultValue: 'Создать задачу' }),
                onClick: onCreateTask,
              }
            : null
          : null,
        railMode === 'docs' && onDocsRequestCreate
          ? {
              id: 'request-docs',
              label: t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Запросить документы' }),
              onClick: onDocsRequestCreate,
            }
          : null,
        onOpenInbox && (railMode === 'contact' || railMode === 'qualify')
          ? {
              id: 'inbox',
              label: t('app.candidates.preview.open_unified_inbox', { defaultValue: 'Inbox' }),
              onClick: () => onOpenInbox(id),
            }
          : null,
      ].filter(Boolean) as NonNullable<DetailRailModel['actions']>['secondary'])
    : []

  const summaryFields =
    railMode === 'rejected' || railMode === 'declined'
      ? undefined
      : railMode === 'recruitment_complete' && processOutcome?.ownerLabel
        ? ([
            {
              id: 'owner',
              label: t('app.candidates.detail.rail_process_owner', { defaultValue: 'Сейчас ведёт' }),
              value: processOutcome.ownerLabel,
            },
          ] as NonNullable<DetailRailModel['summaryFields']>)
        : undefined

  const relations: NonNullable<DetailRailModel['relations']> = []
  if (railMode === 'qualify' && recruitmentSearchId && recruitmentSearchLabel) {
    relations.push({
      id: 'search',
      label: recruitmentSearchLabel,
      onClick: onOpenRecruitmentSearch
        ? () => onOpenRecruitmentSearch(recruitmentSearchId)
        : () => {
            window.location.href = recruitmentSearchPath(recruitmentSearchId)
          },
    })
  }

  const documents =
    railMode === 'docs' || railMode === 'handoff_prep'
      ? buildDocumentRailItems({
          candidateId: id,
          snapshot: documentsSnapshot,
          blockers: effectiveBlockers,
          locale,
          t,
          onOpenDocuments,
          onOpenDocType,
        })
      : undefined

  const historyItems = buildDecisionHistoryItems({
    t,
    locale,
    timelineItems,
    contactAttemptCount,
    nextReminder,
    includeNextReminder: hasRecruiterAction,
  })

  const footerActions =
    railMode === 'rejected' || railMode === 'declined' || railMode === 'archived' || railMode === 'recruitment_complete'
      ? [
          {
            id: 'restore',
            label: t('app.candidates.detail.rail_restore', { defaultValue: 'Вернуть в работу' }),
            onClick: () => onOpenFullProfile(id),
          },
          {
            id: 'open-card',
            label: t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' }),
            onClick: () => onOpenFullProfile(id),
          },
        ]
      : [
          {
            id: 'open-card',
            label: t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' }),
            onClick: () => onOpenFullProfile(id),
          },
        ]

  const headerStatus = resolveHeaderProcessLabel({
    t,
    railMode,
    stageLabel,
    rowStatusLabel,
    handoffStatus,
  })

  const decision = resolveCandidatesObjectDecision({
    t,
    railMode,
    processOutcome,
    nextAction: nextActionResolved,
    hasRecruiterAction,
    contactActions,
    secondaryActions,
    primaryOnClick,
  })

  const scrollBlockOrder: DetailRailModel['blockOrder'] = ['header']
  for (const ctxId of decision.requiredContext) {
    if (ctxId === 'documents' && documents?.length) scrollBlockOrder.push('documents')
    if (ctxId === 'history' && historyItems.length) scrollBlockOrder.push('history')
    if ((ctxId === 'summary' || ctxId === 'handoff') && summaryFields?.length) {
      if (!scrollBlockOrder.includes('summary')) scrollBlockOrder.push('summary')
    }
  }
  if (relations.length) scrollBlockOrder.push('relations')
  if (footerActions.length) scrollBlockOrder.push('footer_actions')

  return {
    resourceId: CANDIDATES_RESOURCE_ID,
    decision,
    blockOrder: scrollBlockOrder,
    header: {
      title: displayName(candidate, t),
      titleHref: id ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(id)}` : undefined,
      statusLabel: headerStatus,
      statusSemantic:
        railMode === 'recruitment_complete' || railMode === 'completed'
          ? 'status'
          : railMode === 'rejected' || railMode === 'declined'
            ? 'status'
            : 'process_stage',
      entityId: id ? `#${String(candidate.short_id || id.slice(0, 8))}` : undefined,
      entityWorkspaceHref: id ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(id)}` : undefined,
      entityWorkspaceLabel: t('app.candidates.detail.open_full_profile', { defaultValue: 'Открыть полную карточку' }),
    },
    processOutcome: processOutcome ?? undefined,
    contacts:
      contactActions.length > 0
        ? {
            compact: true,
            actions: contactActions,
          }
        : undefined,
    nextAction: nextActionResolved
      ? {
          title: nextActionResolved.title,
          body: nextActionResolved.body,
          whyTitle: nextActionResolved.whyTitle,
          whyBody: nextActionResolved.whyBody,
          outcomeTitle: nextActionResolved.outcomeTitle,
          outcomeBody: nextActionResolved.outcomeBody,
          stepLabels: nextActionResolved.hideStepper ? undefined : [...nextActionResolved.stepLabels],
          activeStepIndex: nextActionResolved.hideStepper ? undefined : nextActionResolved.activeStepIndex,
          variant: nextActionResolved.variant,
          hideStepper: nextActionResolved.hideStepper,
          primaryAction: nextActionResolved.primaryActionLabel
            ? {
                id: 'next-primary',
                label: nextActionResolved.primaryActionLabel,
                onClick: primaryOnClick,
              }
            : null,
        }
      : undefined,
    actions: secondaryActions.length ? { secondary: secondaryActions } : undefined,
    summaryFields,
    timeline: historyItems.length
      ? historyItems.map((item, index) => ({
          id: `${id}-hist-${index}`,
          ...item,
        }))
      : undefined,
    documents,
    relations: relations.length ? relations : undefined,
    footerActions,
  }
}
