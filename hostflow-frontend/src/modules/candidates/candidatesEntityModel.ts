/**
 * Candidate Entity Model — reference implementation (Phase 2.1).
 *
 * Source of truth for: Entity Workspace, Detail Rail, Data Table projections.
 * Not UI. Not adapters.
 *
 * Spec: docs/specs/architecture/hostflow-entity-model-v1.md
 */

import type { HandoffStatusResponse } from '../../api/handoffs'
import type { ReminderRecord } from '../../api/types/notification'
import type { CandidateDocsRailSummarySnapshot } from '../../components/candidate/CandidateDocsRailPanel'
import {
  entityField,
  toResourceSchemaFromEntityModel,
  type EntityFieldDescriptor,
  type EntityModel,
  type EntityPassport,
} from '../../platform/entity-model'
import type { ResourceSchema } from '../../platform/data-table'
import type { WorkPanelRequirementsSummary } from '../../utils/workPanelRequirements'
import type { DocBlockersPayload } from '../../utils/candidateStageDocPolicy'
import type { CandidatePipelineOverride } from '../../api/candidatePipelineOverrides'
import { recruitmentSearchPath, CRM_APP_PATHS } from '../../app/crmAppPaths'
import { DEFAULT_COLUMN_ORDER, DEFAULT_VISIBLE_COLS } from './constants'
import { CANDIDATES_RESOURCE_ID } from './candidatesResourceSchema'
import type { AugmentedCandidate } from './types'
import { formatDateSafe } from './candidateUtils'
import {
  buildBlockerSummary,
  candidateRailHasRecruiterAction,
  CANDIDATES_PIPELINE_STEP_LABELS,
  filterRecruiterActionReminders,
  formatCandidateReasonText,
  isPipelineSystemTimelineItem,
  isReminderOverdue,
  pickNextReminder,
  pipelineStepIndex,
  resolveCandidateRailMode,
  resolveCandidatesNextAction,
  resolveEffectiveBlockers,
  resolveRecruitmentProcessOutcome,
  type CandidateRailMode,
  type ResolvedNextAction,
} from './candidatesDetailRailLogic'

export { CANDIDATES_RESOURCE_ID }

type TFn = (key: string, options?: Record<string, unknown>) => string

function candidatePhaseId(mode: CandidateRailMode): string {
  return `candidate.${mode}`
}

function displayName(candidate: Record<string, unknown>, t: TFn): string {
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

function resolveProcessLabel(args: {
  t: TFn
  railMode: CandidateRailMode
  stageLabel: string
  rowStatusLabel?: string
  handoffStatus?: HandoffStatusResponse | null
}): string {
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

function mapPrimaryCapability(kind?: ResolvedNextAction['primaryActionKind']): EntityActionCapabilityId | null {
  switch (kind) {
    case 'call':
      return 'call'
    case 'request_documents':
      return 'request_documents'
    case 'documents':
      return 'open_documents'
    case 'handoff':
      return 'handoff'
    case 'complete_reminder':
      return 'complete_task'
    default:
      return null
  }
}

import type { EntityActionCapability, EntityActionCapabilityId } from '../../platform/entity-model'

function buildActionCapabilities(args: {
  railMode: CandidateRailMode
  workAllowed: boolean
  phoneHref?: string
  emailHref?: string
  whatsappHref?: string
  primaryKind?: ResolvedNextAction['primaryActionKind']
  t: TFn
}): EntityActionCapability[] {
  const { railMode, workAllowed, phoneHref, emailHref, whatsappHref, primaryKind, t } = args
  if (!workAllowed) return []

  const primaryCap = mapPrimaryCapability(primaryKind)
  const caps: EntityActionCapability[] = []

  const allowContact = railMode === 'contact' || railMode === 'qualify' || railMode === 'docs' || railMode === 'handoff_prep'

  if (phoneHref && allowContact) {
    caps.push({
      id: 'call',
      allowed: true,
      primary: primaryCap === 'call',
    })
  }
  if (whatsappHref && allowContact) {
    caps.push({
      id: 'message_whatsapp',
      allowed: true,
      primary: false,
    })
  }
  if (emailHref && allowContact) {
    caps.push({
      id: 'message_email',
      allowed: true,
      primary: false,
    })
  }
  if (railMode === 'docs' || railMode === 'handoff_prep') {
    caps.push({
      id: 'request_documents',
      allowed: railMode === 'docs',
      primary: primaryCap === 'request_documents',
    })
    caps.push({
      id: 'open_documents',
      allowed: true,
      primary: primaryCap === 'open_documents' || primaryKind === 'documents',
    })
  }
  if (railMode === 'qualify') {
    caps.push({
      id: 'assign_vacancy',
      allowed: true,
      primary: false,
    })
  }
  if (railMode === 'handoff_prep') {
    caps.push({
      id: 'handoff',
      allowed: true,
      primary: primaryCap === 'handoff',
    })
  }
  if (primaryKind === 'complete_reminder') {
    caps.push({
      id: 'complete_task',
      allowed: true,
      primary: true,
    })
  }
  if (railMode === 'contact' || railMode === 'qualify') {
    caps.push({
      id: 'create_task',
      allowed: true,
      primary: false,
    })
  }

  return caps
}

/** Static field registry + projection flags — design once, project everywhere. */
export function buildCandidatesEntityModelSchema(t: TFn): EntityModel {
  const fields: EntityFieldDescriptor[] = [
    entityField({
      id: 'name',
      label: t('app.candidates.table.name', { defaultValue: 'Name' }),
      kind: 'text',
      section: 'identity',
      sortable: true,
      projection: { showInTable: true, showInSearch: true, showInEntitySummary: true, searchable: true },
    }),
    entityField({
      id: 'short',
      label: t('app.candidates.table.short_id', { defaultValue: 'ID' }),
      kind: 'text',
      section: 'identity',
      sortable: true,
      projection: { showInTable: true, showInSearch: true, searchable: true },
    }),
    entityField({
      id: 'stage',
      label: t('app.candidates.table.stage', { defaultValue: 'Stage' }),
      kind: 'enum',
      section: 'state',
      sortable: true,
      semanticRole: 'process_stage',
      projection: { showInTable: true, showInRail: true, showInEntitySummary: true, filterable: true },
    }),
    entityField({
      id: 'row_status',
      label: t('app.candidates.table.status', { defaultValue: 'Status' }),
      kind: 'enum',
      section: 'state',
      projection: { showInEntitySummary: true, filterable: true },
    }),
    entityField({
      id: 'reasons',
      label: t('app.candidates.table.reasons', { defaultValue: 'Reasons' }),
      kind: 'tags',
      section: 'outcome',
      sortable: true,
      projection: { showInTable: true, showInRail: true, filterable: true },
    }),
    entityField({
      id: 'manager',
      label: t('app.candidates.table.manager', { defaultValue: 'Manager' }),
      kind: 'user',
      section: 'ownership',
      sortable: true,
      projection: { showInTable: true, showInEntitySummary: true, filterable: true },
    }),
    entityField({
      id: 'email',
      label: t('app.candidates.table.email', { defaultValue: 'Email' }),
      kind: 'text',
      section: 'contacts',
      sortable: true,
      projection: { showInTable: true, showInSearch: true, searchable: true },
    }),
    entityField({
      id: 'phone',
      label: t('app.candidates.table.phone', { defaultValue: 'Phone' }),
      kind: 'text',
      section: 'contacts',
      sortable: true,
      projection: { showInTable: true, showInRail: true, showInSearch: true, searchable: true },
    }),
    entityField({
      id: 'preferredChannel',
      label: t('app.candidates.table.preferred_channel', { defaultValue: 'Channel' }),
      kind: 'enum',
      section: 'contacts',
      projection: { showInTable: true, filterable: true },
    }),
    entityField({
      id: 'citizenship',
      label: t('app.candidates.table.citizenship', { defaultValue: 'Citizenship' }),
      kind: 'text',
      section: 'contacts',
      sortable: true,
      projection: { showInTable: true, filterable: true, editable: true },
    }),
    entityField({
      id: 'docsStatus',
      label: t('app.candidates.table.docs_status', { defaultValue: 'Documents' }),
      kind: 'enum',
      section: 'documents',
      sortable: true,
      semanticRole: 'status',
      projection: { showInTable: true, showInRail: true, showInEntitySummary: true, filterable: true },
    }),
    entityField({
      id: 'docsOrdered',
      label: t('app.candidates.table.docs_ordered', { defaultValue: 'Docs ordered' }),
      kind: 'date',
      section: 'documents',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'docsValid',
      label: t('app.candidates.table.docs_valid', { defaultValue: 'Docs valid from' }),
      kind: 'date',
      section: 'documents',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'docsFiles',
      label: t('app.candidates.table.docs_files', { defaultValue: 'Docs files' }),
      kind: 'boolean',
      section: 'documents',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'vacancy',
      label: t('app.candidates.table.vacancy', { defaultValue: 'Vacancy' }),
      kind: 'ref',
      section: 'relations',
      sortable: true,
      projection: { showInTable: true, showInRail: true, filterable: true },
    }),
    entityField({
      id: 'created',
      label: t('app.candidates.table.created', { defaultValue: 'Created' }),
      kind: 'datetime',
      section: 'timeline',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'firstContact',
      label: t('app.candidates.table.first_contact', { defaultValue: 'First contact' }),
      kind: 'datetime',
      section: 'timeline',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'risk',
      label: t('app.candidates.table.risk', { defaultValue: 'Risk' }),
      kind: 'number',
      section: 'state',
      sortable: true,
      projection: { showInTable: true },
    }),
    entityField({
      id: 'is_favorite',
      label: t('app.candidates.table.favorite', { defaultValue: 'Favorite' }),
      kind: 'boolean',
      section: 'identity',
      sortable: true,
      projection: { showInTable: true, filterable: true },
    }),
    entityField({
      id: 'inPoland',
      label: t('app.candidates.table.in_poland', { defaultValue: 'In Poland' }),
      kind: 'enum',
      section: 'identity',
      projection: { filterable: true, editable: true },
    }),
    entityField({
      id: 'polandBasis',
      label: t('app.candidates.table.poland_basis', { defaultValue: 'Poland basis' }),
      kind: 'enum',
      section: 'identity',
      projection: { filterable: true, editable: true },
    }),
    entityField({
      id: 'trailerTypes',
      label: t('app.candidates.table.trailer_types', { defaultValue: 'Trailer types' }),
      kind: 'tags',
      section: 'identity',
      projection: { filterable: true, editable: true },
    }),
    entityField({
      id: 'intakeKind',
      label: t('app.candidates.table.intake_kind', { defaultValue: 'Intake' }),
      kind: 'enum',
      section: 'identity',
      projection: { showInTable: true, filterable: true },
    }),
  ]

  return {
    resourceId: CANDIDATES_RESOURCE_ID,
    sections: [
      'identity',
      'state',
      'outcome',
      'ownership',
      'contacts',
      'tasks',
      'documents',
      'timeline',
      'relations',
      'actions',
    ],
    fields,
  }
}

/** Table projection — use when migrating Collection (Phase 2.3). */
export function buildCandidatesResourceSchemaFromEntityModel(t: TFn): ResourceSchema {
  const base = toResourceSchemaFromEntityModel(buildCandidatesEntityModelSchema(t))
  const defaultVisibleFieldIds = Object.entries(DEFAULT_VISIBLE_COLS)
    .filter(([, visible]) => visible)
    .map(([id]) => id)

  return {
    ...base,
    entityLinks: [
      {
        id: 'candidate-card',
        role: 'primary',
        fieldId: 'name',
        label: t('app.candidates.table.name', { defaultValue: 'Name' }),
      },
      {
        id: 'vacancy-link',
        role: 'secondary',
        fieldId: 'vacancy',
        label: t('app.candidates.table.vacancy', { defaultValue: 'Vacancy' }),
      },
    ],
    defaultVisibleFieldIds,
    defaultFieldOrder: DEFAULT_COLUMN_ORDER,
  }
}

export type ResolveCandidateEntityPassportArgs = {
  t: TFn
  locale: string
  candidate: AugmentedCandidate | Record<string, unknown>
  stageLabel: string
  rowStatusLabel?: string
  managerLabel?: string
  vacancyId?: string | null
  vacancyLabel?: string
  phoneHref?: string
  emailHref?: string
  messagesHref?: string
  handoffStatus?: HandoffStatusResponse | null
  previewReminders?: ReminderRecord[]
  docsBlockers: DocBlockersPayload
  docsBlockersLoading?: boolean
  usesRequirementBlockers?: boolean
  previewRequirementsSummary?: WorkPanelRequirementsSummary | null
  previewPipelineOverrides?: CandidatePipelineOverride[]
  documentsSnapshot?: CandidateDocsRailSummarySnapshot | null
  timelineItems?: Array<{ at?: string; title?: string; description?: string; kind?: string; source?: string }>
  reasonCodes?: string[]
  reasonFallbackLabels?: string[]
  reasonLabelMap?: Map<string, string>
  contactAttemptCount?: number
  recruitmentSearchId?: string | null
  recruitmentSearchLabel?: string
}

/**
 * Resolve runtime Candidate Entity Passport from list/card API payload + enrichments.
 * All lifecycle rules (rejected, HR handoff, active recruitment) live here.
 */
export function resolveCandidateEntityPassport(args: ResolveCandidateEntityPassportArgs): EntityPassport {
  const {
    t,
    locale,
    candidate,
    stageLabel,
    rowStatusLabel,
    managerLabel,
    vacancyId,
    vacancyLabel,
    phoneHref,
    emailHref,
    messagesHref,
    handoffStatus,
    previewReminders = [],
    docsBlockers,
    docsBlockersLoading = false,
    usesRequirementBlockers = false,
    previewRequirementsSummary = null,
    previewPipelineOverrides = [],
    timelineItems = [],
    reasonCodes = [],
    reasonFallbackLabels = [],
    reasonLabelMap,
    contactAttemptCount,
    recruitmentSearchId,
    recruitmentSearchLabel,
  } = args

  const c = candidate as Record<string, unknown>
  const id = String(c.id || '')
  const stageCode = String(c.stage || '') || null
  const railMode = resolveCandidateRailMode(c, handoffStatus)
  const workAllowed = candidateRailHasRecruiterAction(railMode)

  const reasonText = formatCandidateReasonText({ t, reasonCodes, reasonFallbackLabels, reasonLabelMap })
  const updatedAtLabel = c.updated_at ? formatDateSafe(String(c.updated_at), locale) : undefined

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

  const nextAction = workAllowed
    ? resolveCandidatesNextAction({
        t,
        locale,
        candidate: c,
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
  const nextReminder = workAllowed ? pickNextReminder(actionableReminders) : null

  const capabilities = buildActionCapabilities({
    railMode,
    workAllowed,
    phoneHref,
    emailHref: emailHref,
    whatsappHref: messagesHref,
    primaryKind: nextAction?.primaryActionKind,
    t,
  })

  const primaryCapabilityId = capabilities.find((cap) => cap.primary)?.id ?? mapPrimaryCapability(nextAction?.primaryActionKind)

  const augmented = candidate as AugmentedCandidate
  const docsMeta = augmented.__docsMeta
  const extra = augmented.__extra

  const channels: EntityPassport['sections']['contacts']['channels'] = []
  if (phoneHref && c.phone && !c.masked) {
    channels.push({ kind: 'phone', value: String(c.phone), href: phoneHref, primary: true })
  }
  if (emailHref && c.email && !c.masked) {
    channels.push({ kind: 'email', value: String(c.email), href: emailHref })
  }
  if (messagesHref && !c.masked) {
    channels.push({ kind: 'whatsapp', value: 'WhatsApp', href: messagesHref })
  }

  const relations: EntityPassport['sections']['relations']['items'] = []
  if (vacancyId && vacancyLabel) {
    relations.push({
      id: 'vacancy',
      kind: 'vacancy',
      label: vacancyLabel,
      entityId: String(vacancyId),
      href: `${CRM_APP_PATHS.vacancies}/${encodeURIComponent(String(vacancyId))}`,
    })
  }
  if (recruitmentSearchId && recruitmentSearchLabel) {
    relations.push({
      id: 'search',
      kind: 'recruitment_search',
      label: recruitmentSearchLabel,
      entityId: recruitmentSearchId,
      href: recruitmentSearchPath(recruitmentSearchId),
    })
  }
  if (handoffStatus?.pending?.destination || handoffStatus?.accepted?.destination) {
    relations.push({
      id: 'hr',
      kind: 'hr',
      label: handoffStatus.accepted?.destination || handoffStatus.pending?.destination || 'HR',
    })
  }

  const timelineFiltered = timelineItems
    .filter((item) => !isPipelineSystemTimelineItem(item))
    .slice(0, 50)
    .map((item, index) => ({
      id: `${id}-tl-${index}`,
      at: String(item.at || ''),
      title: String(item.title || ''),
      description: item.description ? String(item.description) : undefined,
      kind: item.kind ? String(item.kind) : undefined,
    }))

  const taskItems: EntityPassport['sections']['tasks']['items'] = actionableReminders.map((r) => ({
    id: String(r.id),
    title: String(r.title || ''),
    dueAt: r.due_at ? String(r.due_at) : undefined,
    status: r.status ? String(r.status) : undefined,
    overdue: isReminderOverdue(r),
  }))

  const processLabel = resolveProcessLabel({ t, railMode, stageLabel, rowStatusLabel, handoffStatus })

  return {
    resourceId: CANDIDATES_RESOURCE_ID,
    entityId: id,
    sections: {
      identity: {
        title: displayName(c, t),
        shortId: c.short_id ? String(c.short_id) : undefined,
        masked: c.masked === true,
      },
      state: {
        phaseId: candidatePhaseId(railMode),
        processPhase: workAllowed ? 'active' : 'terminal',
        processLabel,
        stageCode: stageCode || undefined,
        stageLabel,
        rowStatusCode: c.row_status ? String(c.row_status) : undefined,
        rowStatusLabel,
        pipelineStepIndex: pipelineStepIndex(stageCode),
        pipelineStepLabels: CANDIDATES_PIPELINE_STEP_LABELS,
        why: nextAction?.whyBody ?? processOutcome?.whyLabel,
        recruiterWorkActive: workAllowed,
      },
      outcome: processOutcome
        ? {
            title: processOutcome.title,
            body: processOutcome.body,
            why: processOutcome.whyLabel,
            ownerLabel: processOutcome.ownerLabel,
            whenLabel: processOutcome.whenLabel,
            variant: processOutcome.variant ?? 'default',
          }
        : null,
      ownership: {
        managerId: (c.manager_id ?? c.assignee_id ?? c.manager) ? String(c.manager_id ?? c.assignee_id ?? c.manager) : undefined,
        managerLabel,
      },
      contacts: {
        displayName: displayName(c, t),
        channels,
        preferredChannel: extra?.preferredContact ?? undefined,
        citizenship: extra?.citizenship ?? (c.citizenship ? String(c.citizenship) : undefined),
      },
      tasks: {
        items: taskItems,
        nextTaskId: nextReminder ? String(nextReminder.id) : undefined,
      },
      documents: {
        readinessState: docsMeta?.readinessState,
        readinessLabel: docsMeta?.readinessKey,
        blockersSummary: buildBlockerSummary(effectiveBlockers, t),
        missing: [...effectiveBlockers.missing],
        problematic: [...effectiveBlockers.problematic],
        inProgress: [...effectiveBlockers.inProgress],
        orderedAt: docsMeta?.orderDate ?? null,
        validFrom: docsMeta?.validFrom ?? null,
        hasFiles: docsMeta?.hasFiles,
      },
      timeline: {
        items: timelineFiltered,
      },
      relations: {
        items: relations,
      },
      actions: {
        workAllowed,
        capabilities,
        primaryCapabilityId: workAllowed ? primaryCapabilityId : null,
        decisionTitle: nextAction?.title ?? processOutcome?.title,
        decisionWhy: nextAction?.whyBody ?? nextAction?.body ?? processOutcome?.whyLabel,
        afterActionHint: nextAction?.outcomeBody,
      },
    },
  }
}
