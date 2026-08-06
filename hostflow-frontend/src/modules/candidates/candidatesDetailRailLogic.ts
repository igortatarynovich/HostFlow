import type { ReminderRecord } from '../../api/types/notification'
import type { HandoffStatusResponse } from '../../api/handoffs'
import type { CandidateDocsRailSummarySnapshot } from '../../components/candidate/CandidateDocsRailPanel'
import type { WorkPanelRequirementsSummary } from '../../utils/workPanelRequirements'
import type { DocBlockersPayload, HiringPipelineGatesRuntime } from '../../utils/candidateStageDocPolicy'
import {
  docsIssuesPresent,
  docsPipelineBlocksForward,
  pipelineRelaxedRequirementsFromOverrides,
  relaxRequirementBlockers,
} from '../../utils/candidateStageDocPolicy'
import type { CandidatePipelineOverride } from '../../api/candidatePipelineOverrides'
import { isPipelineCompletedCanonicalStage } from '../../utils/candidatePipelineCompleted'
import { canonicalStageKey } from '../../utils/stageLabels'
import {
  operationalHintForStageResolved,
  type StageOperationalHintKind,
} from '../../utils/stageOperationalHints'
import { formatDateSafe } from './candidateUtils'
import type { DetailRailBlockId } from '../../platform/detail-rail/detailRailTypes'

function normalizeLifecycleCode(value?: string | null): string {
  return String(value ?? '').trim().toLowerCase()
}

function parseTs(value?: string | null): number {
  if (!value) return 0
  const ts = Date.parse(String(value))
  return Number.isNaN(ts) ? 0 : ts
}

/** Same priority as CandidateNextActionPanel.pickNextAction */
export function pickNextReminder(reminders: ReminderRecord[], nowTs = Date.now()): ReminderRecord | null {
  const active = reminders.filter((r) => r && r.status !== 'done' && r.status !== 'cancelled')
  if (!active.length) return null
  active.sort((a, b) => {
    const aDue = parseTs(a.due_at)
    const bDue = parseTs(b.due_at)
    const aOver = a.status === 'overdue' || (aDue > 0 && aDue < nowTs)
    const bOver = b.status === 'overdue' || (bDue > 0 && bDue < nowTs)
    if (aOver !== bOver) return aOver ? -1 : 1
    if (aDue !== bDue) return (aDue || Number.MAX_SAFE_INTEGER) - (bDue || Number.MAX_SAFE_INTEGER)
    return String(a.id).localeCompare(String(b.id))
  })
  return active[0] ?? null
}

export function isReminderOverdue(reminder: ReminderRecord, nowTs = Date.now()): boolean {
  if (reminder.status === 'overdue') return true
  const ts = parseTs(reminder.due_at)
  return ts > 0 && ts < nowTs
}

export function stageHintTitle(t: (key: string, options?: any) => string, kind: StageOperationalHintKind): string {
  switch (kind) {
    case 'call_candidate':
      return t('app.candidate_card.next_action.stage_hint.call', { defaultValue: 'Связаться с кандидатом' })
    case 'assign_vacancy':
      return t('app.candidate_card.next_action.stage_hint.assign', { defaultValue: 'Квалификация и вакансия' })
    case 'request_documents':
      return t('app.candidate_card.next_action.stage_hint.request_docs', { defaultValue: 'Собрать документы' })
    case 'verify_documents':
      return t('app.candidate_card.next_action.stage_hint.verify_docs', { defaultValue: 'Проверить документы' })
    case 'handoff_prep':
      return t('app.candidate_card.next_action.stage_hint.handoff', { defaultValue: 'Подготовка к передаче' })
    case 'advance_pipeline':
      return t('app.candidate_card.next_action.stage_hint.advance', { defaultValue: 'Двинуть кейс дальше' })
    default:
      return ''
  }
}

export const CANDIDATES_PIPELINE_STEP_LABELS = [
  'Связаться',
  'Квалификация',
  'Документы',
  'Handoff',
  'Готово',
] as const

export function pipelineStepIndex(stageCode: string | null | undefined): number {
  const c = canonicalStageKey(String(stageCode || ''), null) || String(stageCode || '').toLowerCase()
  if (['new', 'no_answer'].includes(c)) return 0
  if (['contacted', 'questionnaire_submitted'].includes(c)) return 1
  if (['docs_wait', 'docs_got'].includes(c)) return 2
  if (
    ['ready_for_handoff', 'permit_ordered', 'processing_by_client', 'docs_submitted_permit', 'handoff_returned'].includes(
      c,
    )
  )
    return 3
  if (isPipelineCompletedCanonicalStage(c)) return 4
  return 1
}

export type EffectiveBlockers = DocBlockersPayload

export function resolveEffectiveBlockers(args: {
  docsBlockers: DocBlockersPayload
  usesRequirementBlockers: boolean
  previewRequirementsSummary: WorkPanelRequirementsSummary | null
  previewPipelineOverrides: CandidatePipelineOverride[]
}): EffectiveBlockers {
  const relaxed = pipelineRelaxedRequirementsFromOverrides(args.previewPipelineOverrides)
  if (args.usesRequirementBlockers) {
    return relaxRequirementBlockers(args.docsBlockers, relaxed)
  }
  return args.docsBlockers
}

export function buildBlockerSummary(
  blockers: EffectiveBlockers,
  t: (key: string, options?: any) => string,
  maxItems = 4,
): string | null {
  const parts: string[] = []
  for (const code of blockers.missing.slice(0, maxItems)) {
    parts.push(t('app.candidates.detail.blocker_missing', { defaultValue: 'Нет: {code}', values: { code } }))
  }
  for (const code of blockers.problematic.slice(0, Math.max(0, maxItems - parts.length))) {
    parts.push(t('app.candidates.detail.blocker_problem', { defaultValue: 'Проблема: {code}', values: { code } }))
  }
  for (const code of blockers.inProgress.slice(0, Math.max(0, maxItems - parts.length))) {
    parts.push(t('app.candidates.detail.blocker_progress', { defaultValue: 'В работе: {code}', values: { code } }))
  }
  if (!parts.length) return null
  const extra =
    blockers.missing.length + blockers.problematic.length + blockers.inProgress.length > parts.length
      ? t('app.candidates.detail.blocker_more', { defaultValue: '…и ещё' })
      : null
  return extra ? `${parts.join(' · ')} ${extra}` : parts.join(' · ')
}

export function buildHandoffReadinessLabel(
  status: HandoffStatusResponse | null | undefined,
  t: (key: string, options?: any) => string,
): string | null {
  if (!status) return null
  if (status.client_owns) {
    return t('app.candidates.detail.handoff_client_owns', { defaultValue: 'Кандидат у клиента' })
  }
  if (status.pending) {
    return t('app.candidates.detail.handoff_pending', { defaultValue: 'Handoff ожидает решения клиента' })
  }
  if (status.accepted) {
    return t('app.candidates.detail.handoff_accepted', { defaultValue: 'Handoff принят клиентом' })
  }
  return t('app.candidates.detail.handoff_not_started', { defaultValue: 'Handoff не создан' })
}

export function buildDocumentRailItems(args: {
  candidateId: string
  snapshot: CandidateDocsRailSummarySnapshot | null
  blockers: EffectiveBlockers
  locale: string
  t: (key: string, options?: any) => string
  onOpenDocuments: (id: string) => void
  onOpenDocType?: (id: string, typeCode: string) => void
}) {
  const { snapshot, blockers, locale, t, candidateId, onOpenDocuments, onOpenDocType } = args
  const items: Array<{ id: string; name: string; meta?: string; onOpen?: () => void }> = []

  if (snapshot) {
    const pct = Math.round(snapshot.percent_ready ?? 0)
    items.push({
      id: 'docs-summary',
      name: t('app.candidates.detail.docs_readiness', {
        defaultValue: 'Готовность документов: {pct}%',
        values: { pct },
      }),
      meta:
        blockers.missing.length || blockers.problematic.length
          ? t('app.candidates.detail.docs_gaps', {
              defaultValue: 'Не хватает: {count}',
              values: { count: blockers.missing.length + blockers.problematic.length },
            })
          : undefined,
      onOpen: () => onOpenDocuments(candidateId),
    })

    for (const type of blockers.missing.slice(0, 3)) {
      items.push({
        id: `missing-${type}`,
        name: type,
        meta: t('app.candidates.detail.doc_missing', { defaultValue: 'Отсутствует' }),
        onOpen: onOpenDocType ? () => onOpenDocType(candidateId, type) : () => onOpenDocuments(candidateId),
      })
    }
    for (const type of blockers.problematic.slice(0, 2)) {
      items.push({
        id: `problem-${type}`,
        name: type,
        meta: t('app.candidates.detail.doc_problem', { defaultValue: 'Требует проверки' }),
        onOpen: onOpenDocType ? () => onOpenDocType(candidateId, type) : () => onOpenDocuments(candidateId),
      })
    }

    for (const exp of (snapshot.expiring_soon ?? []).slice(0, 2)) {
      items.push({
        id: `exp-${exp.type}`,
        name: exp.type,
        meta: t('app.candidates.detail.doc_expiring', {
          defaultValue: 'Истекает {date}',
          values: { date: formatDateSafe(exp.expires_at, locale) || exp.expires_at },
        }),
        onOpen: onOpenDocType ? () => onOpenDocType(candidateId, exp.type) : () => onOpenDocuments(candidateId),
      })
    }
  } else if (blockers.missing.length || blockers.problematic.length) {
    for (const type of [...blockers.missing, ...blockers.problematic].slice(0, 4)) {
      items.push({
        id: `blocker-${type}`,
        name: type,
        onOpen: () => onOpenDocuments(candidateId),
      })
    }
  }

  if (!items.length) {
    items.push({
      id: 'docs-open',
      name: t('app.candidates.actions.documents', { defaultValue: 'Документы' }),
      onOpen: () => onOpenDocuments(candidateId),
    })
  }

  return items
}

export type ResolvedNextAction = {
  title: string
  body?: string
  whyTitle?: string
  whyBody?: string
  outcomeTitle?: string
  outcomeBody?: string
  stepLabels: readonly string[]
  activeStepIndex: number
  primaryActionLabel?: string
  primaryActionKind?: 'call' | 'documents' | 'handoff' | 'complete_reminder' | 'request_documents'
  isBlocker: boolean
  variant?: 'default' | 'blocker' | 'terminal' | 'success'
  hideStepper?: boolean
}

export type CandidateRailMode =
  | 'rejected'
  | 'declined'
  | 'archived'
  | 'recruitment_complete'
  | 'handoff_prep'
  | 'docs'
  | 'contact'
  | 'qualify'
  | 'completed'

export type ResolvedProcessOutcome = {
  title: string
  body?: string
  ownerLabel?: string
  whenLabel?: string
  whyLabel?: string
  variant?: 'default' | 'terminal' | 'success'
}

export function isRecruitmentCompleteForRecruiter(args: {
  candidate: Record<string, unknown>
  handoffStatus?: HandoffStatusResponse | null
}): boolean {
  const { candidate, handoffStatus } = args
  if (handoffStatus?.client_owns) return true
  if (handoffStatus?.accepted) return true
  const rowStatus = normalizeLifecycleCode(candidate.row_status as string)
  if (['handed_off', 'ready_for_hr', 'processing_by_hr', 'hired'].includes(rowStatus)) return true
  return false
}

export function resolveCandidateRailMode(
  candidate: Record<string, unknown>,
  handoffStatus?: HandoffStatusResponse | null,
): CandidateRailMode {
  const stage = normalizeLifecycleCode(candidate.stage as string)
  const rowStatus = normalizeLifecycleCode(candidate.row_status as string)
  const status = normalizeLifecycleCode(candidate.status as string)
  const canonical = canonicalStageKey(String(candidate.stage || ''), null) || stage

  if (['rejected'].includes(rowStatus) || ['rejected'].includes(stage) || ['rejected'].includes(status)) {
    return 'rejected'
  }
  if (['declined'].includes(rowStatus) || ['declined'].includes(stage)) {
    return 'declined'
  }
  if (rowStatus === 'archived') return 'archived'

  if (isRecruitmentCompleteForRecruiter({ candidate, handoffStatus })) {
    return 'recruitment_complete'
  }

  if (
    ['ready_for_handoff', 'handoff_returned', 'ready_for_hr', 'permit_ordered', 'processing_by_client', 'docs_submitted_permit'].includes(
      canonical,
    )
  ) {
    return 'handoff_prep'
  }
  if (['docs_wait', 'docs_got'].includes(canonical)) return 'docs'
  if (['new', 'no_answer'].includes(canonical)) return 'contact'
  if (['contacted', 'questionnaire_submitted'].includes(canonical)) return 'qualify'
  if (isPipelineCompletedCanonicalStage(canonical)) return 'completed'
  return 'qualify'
}

export function candidateRailHasRecruiterAction(mode: CandidateRailMode): boolean {
  return mode === 'contact' || mode === 'qualify' || mode === 'docs' || mode === 'handoff_prep'
}

export function isRecruitmentPipelineSystemReminder(reminder: ReminderRecord): boolean {
  const title = String(reminder.title || '').trim().toLowerCase()
  if (!title) return false
  if (title.includes('candidate pipeline:')) return true
  if (/ready_for_handoff|handoff_returned|docs_wait|docs_got|ready_for_hr/.test(title)) return true
  return false
}

export function filterRecruiterActionReminders(
  reminders: ReminderRecord[],
  railMode: CandidateRailMode,
): ReminderRecord[] {
  if (!candidateRailHasRecruiterAction(railMode)) return []
  return reminders.filter((r) => r && r.status !== 'done' && r.status !== 'cancelled' && !isRecruitmentPipelineSystemReminder(r))
}

export function isPipelineSystemTimelineItem(item: {
  title?: string | null
  kind?: string
  source?: string
}): boolean {
  const title = String(item.title || '').trim().toLowerCase()
  const kind = String(item.kind || '').trim().toLowerCase()
  const source = String(item.source || '').trim().toLowerCase()
  if (title.includes('candidate pipeline:')) return true
  if (/ready_for_handoff|handoff_returned|ready_for_hr/.test(title)) return true
  if (kind === 'pipeline' || kind === 'stage' || kind === 'system') return true
  if (source.includes('pipeline') || source.includes('stage_automation')) return true
  return false
}

export function resolveCandidateRequiredContext(mode: CandidateRailMode): import('../../platform/decision-model/types').DecisionContextBlockId[] {
  switch (mode) {
    case 'contact':
    case 'qualify':
      return ['history']
    case 'docs':
      return ['documents', 'history']
    case 'handoff_prep':
      return ['handoff', 'documents', 'history']
    case 'recruitment_complete':
    case 'completed':
      return ['summary', 'history']
    case 'rejected':
    case 'declined':
    case 'archived':
      return ['summary', 'history']
    default:
      return ['history']
  }
}

export function resolveCandidatesObjectDecision(args: {
  railMode: CandidateRailMode
  processOutcome: ResolvedProcessOutcome | null
  nextAction: ResolvedNextAction | null
  hasRecruiterAction: boolean
  contactActions: import('../../platform/detail-rail/detailRailTypes').DetailRailContactAction[]
  secondaryActions: Array<{ id: string; label: string; onClick?: () => void }>
  primaryOnClick: () => void
}): import('../../platform/decision-model/types').ObjectDecision {
  const { railMode, processOutcome, nextAction, hasRecruiterAction, contactActions, secondaryActions, primaryOnClick } =
    args
  const requiredContext = resolveCandidateRequiredContext(railMode)

  if (processOutcome) {
    return {
      stateId: `candidate.${railMode}`,
      currentState: processOutcome.title,
      why: processOutcome.whyLabel ?? processOutcome.body,
      primaryAction: null,
      requiredContext,
      terminal: true,
      outcome: {
        title: processOutcome.title,
        body: processOutcome.body,
        why: processOutcome.whyLabel,
        variant: processOutcome.variant,
      },
    }
  }

  if (!hasRecruiterAction || !nextAction) {
    return {
      stateId: `candidate.${railMode}.idle`,
      currentState: nextAction?.title ?? 'Нет действий',
      why: nextAction?.whyBody,
      primaryAction: null,
      contactActions: contactActions.length ? contactActions : undefined,
      requiredContext,
      terminal: !hasRecruiterAction,
      variant: nextAction?.variant,
    }
  }

  return {
    stateId: `candidate.${railMode}`,
    currentState: nextAction.title,
    why: nextAction.whyBody ?? nextAction.body,
    primaryAction: nextAction.primaryActionLabel
      ? {
          id: 'primary',
          label: nextAction.primaryActionLabel,
          onClick: primaryOnClick,
        }
      : null,
    secondaryActions: secondaryActions.map((a) => ({
      id: a.id,
      label: a.label,
      onClick: a.onClick,
      variant: 'secondary' as const,
    })),
    contactActions: contactActions.length ? contactActions : undefined,
    requiredContext,
    afterActionHint: nextAction.outcomeBody,
    variant: nextAction.variant ?? (nextAction.isBlocker ? 'blocker' : 'default'),
  }
}

export function resolveCandidateRailBlockOrder(mode: CandidateRailMode): DetailRailBlockId[] {
  switch (mode) {
    case 'rejected':
    case 'declined':
      return ['header', 'outcome', 'summary', 'history', 'footer_actions']
    case 'archived':
      return ['header', 'outcome', 'footer_actions']
    case 'recruitment_complete':
    case 'completed':
      return ['header', 'outcome', 'summary', 'history', 'footer_actions']
    case 'docs':
      return ['header', 'next_action', 'documents', 'contacts', 'history', 'footer_actions']
    case 'handoff_prep':
      return ['header', 'next_action', 'documents', 'history', 'footer_actions']
    case 'contact':
      return ['header', 'next_action', 'contacts', 'history', 'footer_actions']
    case 'qualify':
      return ['header', 'next_action', 'contacts', 'history', 'footer_actions']
    default:
      return ['header', 'next_action', 'contacts', 'history', 'footer_actions']
  }
}

export function resolveRecruitmentProcessOutcome(args: {
  t: (key: string, options?: any) => string
  locale: string
  railMode: CandidateRailMode
  handoffStatus?: HandoffStatusResponse | null
  reasonText?: string | null
  managerLabel?: string | null
  updatedAtLabel?: string | null
}): ResolvedProcessOutcome | null {
  const { t, locale, railMode, handoffStatus, reasonText, managerLabel, updatedAtLabel } = args

  if (railMode === 'recruitment_complete') {
    const accepted = handoffStatus?.accepted
    const pending = handoffStatus?.pending
    const ownerName =
      accepted?.destination ||
      pending?.destination ||
      accepted?.assigned_to_user_name ||
      t('app.candidates.detail.rail_owner_hr', { defaultValue: 'HR' })
    const whenRaw = accepted?.reviewed_at || accepted?.requested_at || pending?.requested_at || updatedAtLabel
    const whenLabel = whenRaw ? formatDateSafe(String(whenRaw), locale) || String(whenRaw) : undefined

    let title = t('app.candidates.detail.rail_recruitment_complete_title', { defaultValue: 'Рекрутинг завершён' })
    let body = t('app.candidates.detail.rail_recruitment_complete_body', {
      defaultValue: 'Кандидат передан в HR. Дальнейшая обработка — в модуле HR.',
    })
    if (handoffStatus?.client_owns) {
      title = t('app.candidates.detail.rail_transferred_hr_title', { defaultValue: 'Передан в HR' })
    } else if (accepted) {
      title = t('app.candidates.detail.rail_accepted_hr_title', { defaultValue: 'Принят HR' })
      body = t('app.candidates.detail.rail_accepted_hr_body', {
        defaultValue: 'Рекрутер завершил работу. Кандидат на стороне HR.',
      })
    } else if (pending) {
      title = t('app.candidates.detail.rail_pending_hr_title', { defaultValue: 'Ожидает проверки HR' })
      body = t('app.candidates.detail.rail_pending_hr_body', {
        defaultValue: 'Передача создана. HR обрабатывает кандидата.',
      })
    }

    return {
      title,
      body,
      ownerLabel: ownerName,
      whenLabel,
      variant: 'success',
    }
  }

  if (railMode === 'rejected') {
    return {
      title: t('app.candidates.detail.rail_rejected_title', { defaultValue: 'Кандидат отклонён' }),
      body: t('app.candidates.detail.rail_rejected_body', {
        defaultValue: 'Рекрутинг завершён без продолжения.',
      }),
      whyLabel: reasonText ?? t('app.candidates.detail.rail_rejected_no_reason', { defaultValue: 'Причина не указана' }),
      ownerLabel: managerLabel ?? undefined,
      whenLabel: updatedAtLabel ?? undefined,
      variant: 'terminal',
    }
  }

  if (railMode === 'declined') {
    return {
      title: t('app.candidates.detail.rail_declined_title', { defaultValue: 'Кандидат отказался' }),
      body: t('app.candidates.detail.rail_declined_body', {
        defaultValue: 'Рекрутинг остановлен по инициативе кандидата.',
      }),
      whyLabel: reasonText ?? undefined,
      ownerLabel: managerLabel ?? undefined,
      whenLabel: updatedAtLabel ?? undefined,
      variant: 'terminal',
    }
  }

  if (railMode === 'archived') {
    return {
      title: t('app.candidates.detail.rail_archived_title', { defaultValue: 'Кандидат в архиве' }),
      body: t('app.candidates.detail.rail_archived_body', {
        defaultValue: 'Восстановите из карточки, если нужно вернуть в работу.',
      }),
      variant: 'terminal',
    }
  }

  if (railMode === 'completed') {
    return {
      title: t('app.candidate_card.next_action.pipeline_completed_title', { defaultValue: 'Процесс завершён' }),
      body: t('app.candidate_card.next_action.pipeline_completed_body', {
        defaultValue: 'Дальнейшие шаги воронки не требуются.',
      }),
      variant: 'success',
    }
  }

  return null
}

export function resolveHeaderProcessLabel(args: {
  t: (key: string, options?: any) => string
  railMode: CandidateRailMode
  stageLabel: string
  rowStatusLabel?: string
  handoffStatus?: HandoffStatusResponse | null
}): string | undefined {
  const { t, railMode, stageLabel, rowStatusLabel, handoffStatus } = args
  if (railMode === 'recruitment_complete') {
    if (handoffStatus?.client_owns) {
      return t('app.candidates.detail.rail_transferred_hr_title', { defaultValue: 'Передан в HR' })
    }
    if (handoffStatus?.accepted) {
      return t('app.candidates.detail.rail_accepted_hr_title', { defaultValue: 'Принят HR' })
    }
    if (handoffStatus?.pending) {
      return t('app.candidates.detail.rail_pending_hr_title', { defaultValue: 'Ожидает проверки HR' })
    }
    return rowStatusLabel || t('app.candidates.detail.rail_recruitment_complete_title', { defaultValue: 'Рекрутинг завершён' })
  }
  if (railMode === 'rejected' || railMode === 'declined' || railMode === 'archived') {
    return rowStatusLabel || stageLabel
  }
  return stageLabel
}

export function formatCandidateReasonText(args: {
  t: (key: string, options?: any) => string
  reasonCodes: string[]
  reasonFallbackLabels: string[]
  reasonLabelMap?: Map<string, string>
}): string | null {
  const labels: string[] = []
  for (const code of args.reasonCodes) {
    const mapped = args.reasonLabelMap?.get(code) ?? args.reasonLabelMap?.get(code.toLowerCase())
    labels.push(mapped ?? code)
  }
  for (const label of args.reasonFallbackLabels) {
    if (!labels.includes(label)) labels.push(label)
  }
  if (!labels.length) return null
  return labels.join(' · ')
}

export function resolveOutcomeAfterAction(args: {
  t: (key: string, options?: any) => string
  railMode: CandidateRailMode
  primaryActionKind?: ResolvedNextAction['primaryActionKind']
  canonicalStage: string | null
}): { outcomeTitle?: string; outcomeBody?: string } | null {
  const { t, railMode, primaryActionKind, canonicalStage } = args
  if (railMode === 'rejected' || railMode === 'declined' || railMode === 'archived' || railMode === 'completed' || railMode === 'recruitment_complete') {
    return null
  }
  if (primaryActionKind === 'call') {
    return {
      outcomeBody: t('app.candidates.detail.rail_outcome_after_call', {
        defaultValue: 'После контакта кандидат перейдёт на этап «Связались».',
      }),
    }
  }
  if (primaryActionKind === 'request_documents' || primaryActionKind === 'documents') {
    return {
      outcomeBody: t('app.candidates.detail.rail_outcome_after_docs', {
        defaultValue: 'После запроса документов ожидайте загрузку и проверку.',
      }),
    }
  }
  if (primaryActionKind === 'handoff') {
    return {
      outcomeBody: t('app.candidates.detail.rail_outcome_after_handoff', {
        defaultValue: 'После передачи кейс уйдёт клиенту на решение.',
      }),
    }
  }
  if (primaryActionKind === 'complete_reminder') {
    return {
      outcomeBody: t('app.candidates.detail.rail_outcome_after_task', {
        defaultValue: 'После выполнения задачи откроется следующий шаг воронки.',
      }),
    }
  }
  if (canonicalStage === 'new') {
    return {
      outcomeBody: t('app.candidates.detail.rail_outcome_first_contact', {
        defaultValue: 'Первый контакт запускает квалификацию кандидата.',
      }),
    }
  }
  return null
}

export function buildDecisionHistoryItems(args: {
  t: (key: string, options?: any) => string
  locale: string
  timelineItems: Array<{ at: string; kind?: string; title?: string | null; description?: string | null; source?: string }>
  contactAttemptCount?: number
  nextReminder?: ReminderRecord | null
  includeNextReminder?: boolean
  maxItems?: number
}): Array<{ id: string; at: string; title: string; description?: string }> {
  const {
    t,
    locale,
    timelineItems,
    contactAttemptCount = 0,
    nextReminder,
    includeNextReminder = true,
    maxItems = 4,
  } = args
  const commsKinds = new Set(['call', 'message', 'email', 'sms', 'whatsapp', 'contact', 'comms', 'inbox'])
  const comms = timelineItems.filter((item) => {
    if (isPipelineSystemTimelineItem(item)) return false
    const kind = String(item.kind || '').toLowerCase()
    const source = String(item.source || '').toLowerCase()
    return commsKinds.has(kind) || source.includes('comms') || source.includes('inbox')
  })

  const items: Array<{ id: string; at: string; title: string; description?: string }> = []

  if (includeNextReminder && nextReminder?.due_at && !isRecruitmentPipelineSystemReminder(nextReminder)) {
    items.push({
      id: 'next-contact',
      at: formatDateSafe(String(nextReminder.due_at), locale) || String(nextReminder.due_at),
      title: t('app.candidates.detail.rail_next_contact', { defaultValue: 'Следующий контакт' }),
      description: nextReminder.title ?? undefined,
    })
  }

  for (const [index, item] of comms.slice(0, maxItems).entries()) {
    items.push({
      id: `comms-${index}`,
      at: formatDateSafe(item.at, locale) || item.at,
      title: item.title || t('app.candidates.detail.contact', { defaultValue: 'Контакт' }),
      description: item.description ?? undefined,
    })
  }

  if (!items.length) {
    if (contactAttemptCount > 0) {
      items.push({
        id: 'attempts',
        at: '—',
        title: t('app.candidates.detail.contact_attempts', {
          defaultValue: 'Попыток контакта: {count}',
          values: { count: contactAttemptCount },
        }),
      })
    } else {
      items.push({
        id: 'no-contact',
        at: '—',
        title: t('app.candidates.detail.rail_no_contact_yet', { defaultValue: 'Связи с кандидатом ещё не было' }),
      })
    }
  }

  return items.slice(0, maxItems)
}

export function resolveCandidatesNextAction(args: {
  t: (key: string, options?: any) => string
  locale: string
  candidate: Record<string, unknown>
  reminders: ReminderRecord[]
  blockers: EffectiveBlockers
  docsBlockersLoading: boolean
  usesRequirementBlockers: boolean
  stageCode: string | null
  vacancyId?: string | null
  contactAttemptCount?: number
  railMode: CandidateRailMode
  reasonText?: string | null
  hiringGates?: HiringPipelineGatesRuntime | null
}): ResolvedNextAction | null {
  const {
    t,
    locale,
    candidate,
    reminders,
    blockers,
    docsBlockersLoading,
    stageCode,
    vacancyId,
    contactAttemptCount,
    railMode,
    hiringGates,
  } = args

  if (!candidateRailHasRecruiterAction(railMode)) {
    return null
  }

  const stepLabels = CANDIDATES_PIPELINE_STEP_LABELS
  const activeStepIndex = pipelineStepIndex(stageCode)
  const canonical = stageCode ? canonicalStageKey(stageCode, null) || stageCode.toLowerCase() : null
  const actionableReminders = filterRecruiterActionReminders(reminders, railMode)

  const appendOutcome = (action: ResolvedNextAction): ResolvedNextAction => {
    const outcome = resolveOutcomeAfterAction({
      t,
      railMode,
      primaryActionKind: action.primaryActionKind,
      canonicalStage: canonical,
    })
    if (!outcome) return action
    return { ...action, outcomeTitle: outcome.outcomeTitle, outcomeBody: outcome.outcomeBody }
  }

  const docsIssues = docsIssuesPresent(blockers, docsBlockersLoading)
  const docsPipelineBlocking =
    canonical && docsPipelineBlocksForward(canonical, blockers, docsBlockersLoading, hiringGates)

  const nextReminder = pickNextReminder(actionableReminders)
  if (nextReminder?.title) {
    const dueLabel = nextReminder.due_at
      ? formatDateSafe(String(nextReminder.due_at), locale)
      : undefined
    const overdue = isReminderOverdue(nextReminder)
    return appendOutcome({
      title: nextReminder.title,
      body: dueLabel
        ? `${t('app.candidate_card.next_action.due', { defaultValue: 'Срок' })}: ${dueLabel}${overdue ? ` · ${t('app.candidate_card.next_action.overdue', { defaultValue: 'Просрочено' })}` : ''}`
        : undefined,
      whyBody: overdue
        ? t('app.candidates.detail.rail_overdue_task', { defaultValue: 'Задача просрочена — блокирует следующий шаг.' })
        : undefined,
      stepLabels,
      activeStepIndex,
      primaryActionLabel: t('app.candidates.actions.complete_task', { defaultValue: 'Выполнить' }),
      primaryActionKind: 'complete_reminder',
      isBlocker: overdue,
      variant: overdue ? 'blocker' : 'default',
      hideStepper: railMode === 'contact' || railMode === 'docs',
    })
  }

  const contactBlocking =
    canonical === 'new' && (contactAttemptCount ?? 0) < 1 ? true : canonical === 'new' ? false : undefined
  const vacancyBlocking =
    ['contacted', 'questionnaire_submitted'].includes(canonical || '') && !vacancyId
      ? true
      : ['contacted', 'questionnaire_submitted'].includes(canonical || '')
        ? false
        : undefined

  const stageHint = operationalHintForStageResolved(canonical, null, {
    contactAttemptPipelineBlocking: contactBlocking,
    vacancyPipelineBlocking: vacancyBlocking,
  })

  if (docsPipelineBlocking && docsIssues) {
    const blockerText = buildBlockerSummary(blockers, t)
    const requestDocs = railMode === 'docs'
    return appendOutcome({
      title:
        stageHint?.kind === 'verify_documents'
          ? stageHintTitle(t, 'verify_documents')
          : stageHintTitle(t, 'request_documents'),
      whyBody: blockerText ?? t('app.candidates.detail.rail_docs_blocker', { defaultValue: 'Без этих документов нельзя перейти дальше.' }),
      stepLabels,
      activeStepIndex,
      primaryActionLabel: requestDocs
        ? t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Запросить документы' })
        : t('app.candidates.actions.open_documents', { defaultValue: 'Открыть документы' }),
      primaryActionKind: requestDocs ? 'request_documents' : 'documents',
      isBlocker: true,
      variant: 'blocker',
      hideStepper: railMode === 'docs',
    })
  }

  if (stageHint) {
    const whyBody =
      stageHint.kind === 'call_candidate' && canonical === 'no_answer'
        ? t('app.candidates.detail.rail_no_answer', { defaultValue: 'Кандидат не отвечает — нужен повторный контакт.' })
        : stageHint.kind === 'assign_vacancy' && vacancyBlocking
          ? t('app.candidates.detail.rail_no_vacancy', { defaultValue: 'Без вакансии нельзя двигать кейс дальше.' })
          : undefined
    return appendOutcome({
      title: stageHintTitle(t, stageHint.kind),
      body:
        docsIssues && !docsPipelineBlocking
          ? t('app.candidate_card.next_action.docs_soft_nudge', {
              defaultValue: 'Есть пробелы в документах — проверьте чеклист.',
            })
          : undefined,
      whyBody,
      stepLabels,
      activeStepIndex,
      hideStepper: railMode === 'contact' || railMode === 'handoff_prep',
      primaryActionLabel:
        stageHint.kind === 'call_candidate'
          ? t('app.candidates.actions.call', { defaultValue: 'Позвонить' })
          : stageHint.kind === 'handoff_prep'
            ? t('app.candidates.detail.handoff_action', { defaultValue: 'Подготовить handoff' })
            : stageHint.kind === 'request_documents'
              ? t('app.candidate_card.next_action.docs_request_title', { defaultValue: 'Запросить документы' })
              : undefined,
      primaryActionKind:
        stageHint.kind === 'call_candidate'
          ? 'call'
          : stageHint.kind === 'handoff_prep'
            ? 'handoff'
            : stageHint.kind === 'request_documents'
              ? 'request_documents'
              : undefined,
      isBlocker: Boolean(vacancyBlocking || contactBlocking),
      variant: vacancyBlocking || contactBlocking ? 'blocker' : 'default',
    })
  }

  if (railMode === 'handoff_prep') {
    return appendOutcome({
      title: t('app.candidates.detail.handoff_action', { defaultValue: 'Подготовить handoff' }),
      body: t('app.candidates.detail.rail_handoff_body', {
        defaultValue: 'Передайте готового кандидата клиенту.',
      }),
      stepLabels,
      activeStepIndex,
      hideStepper: true,
      primaryActionLabel: t('app.candidates.detail.handoff_action', { defaultValue: 'Подготовить handoff' }),
      primaryActionKind: 'handoff',
      isBlocker: false,
    })
  }

  return appendOutcome({
    title: t('app.candidates.detail.contact_next', { defaultValue: 'Связаться с кандидатом' }),
    body: t('app.candidates.detail.contact_next_body', {
      defaultValue: 'Первый контакт или уточнение статуса.',
    }),
    whyBody:
      (contactAttemptCount ?? 0) < 1
        ? t('app.candidates.detail.rail_first_contact_needed', { defaultValue: 'Первый контакт ещё не зафиксирован.' })
        : undefined,
    stepLabels,
    activeStepIndex,
    hideStepper: railMode === 'contact',
    primaryActionLabel: t('app.candidates.actions.call', { defaultValue: 'Позвонить' }),
    primaryActionKind: 'call',
    isBlocker: false,
  })
}

export function findLastContactTimelineItem(
  items: Array<{ at: string; kind?: string; title?: string | null; description?: string | null; source?: string }>,
) {
  const commsKinds = new Set(['call', 'message', 'email', 'sms', 'whatsapp', 'contact', 'comms', 'inbox'])
  for (const item of items) {
    const kind = String(item.kind || '').toLowerCase()
    const source = String(item.source || '').toLowerCase()
    if (commsKinds.has(kind) || source.includes('comms') || source.includes('inbox')) {
      return item
    }
  }
  return items[0] ?? null
}
