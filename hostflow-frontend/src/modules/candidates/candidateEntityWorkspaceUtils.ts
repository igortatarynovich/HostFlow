import type { Candidate } from '../../api/types'
import type { EntityPassport } from '../../platform/entity-model'
import type { EntityWorkspaceActionConfig } from '../../platform/entity-workspace'
import type { DetailRailAction } from '../../platform/detail-rail/detailRailTypes'
import { extractExtraObject } from './candidateUtils'
import type { AugmentedCandidate, UICandidate } from './types'
import { deriveDocsMeta, normalizeCandidateExtra } from './utils'

function normalizeReasonList(value: unknown): string[] {
  if (value == null) return []
  if (Array.isArray(value)) {
    return value.flatMap((item) => normalizeReasonList(item))
  }
  if (typeof value === 'string') {
    return value
      .split(/[,;|]/)
      .map((part) => part.trim())
      .filter(Boolean)
  }
  return []
}

export function deriveCandidateReasonData(
  candidate: Record<string, unknown>,
  extraSource: Record<string, unknown>,
): { codes: string[]; fallbackLabels: string[] } {
  const codes = new Set(
    normalizeReasonList(
      candidate.statusReason ??
        candidate.status_reason ??
        candidate.reason ??
        candidate.status_reason_details ??
        candidate.status_reason_codes ??
        '',
    ),
  )
  const fallback: string[] = []
  const labelSources = [
    candidate.status_reason_labels,
    candidate.reason_labels,
    extraSource.status_reason_labels,
    extraSource.reason_labels,
    extraSource.status_reason_details,
  ]
  normalizeReasonList(labelSources).forEach((label) => {
    const normalized = label.trim().toLowerCase()
    if (!normalized) return
    if (!fallback.some((existing) => existing.trim().toLowerCase() === normalized)) {
      fallback.push(label)
    }
  })
  return {
    codes: Array.from(codes),
    fallbackLabels: fallback,
  }
}

/** List/card enrichment — required for resolveCandidateEntityPassport. */
export function augmentCandidateForEntityPassport(candidate: UICandidate | Candidate): AugmentedCandidate {
  const rawExtra = extractExtraObject(
    (candidate as Record<string, unknown>).extra_summary ??
      (candidate as Record<string, unknown>).extra ??
      candidate.extra ??
      null,
  )
  const extra = normalizeCandidateExtra(rawExtra)
  const reasonData = deriveCandidateReasonData(candidate as Record<string, unknown>, rawExtra)
  return {
    ...candidate,
    __docsMeta: deriveDocsMeta(candidate as UICandidate),
    __extra: extra,
    __reasonCodes: reasonData.codes,
    __reasonFallbackLabels: reasonData.fallbackLabels,
  }
}

export function candidateTelHref(display: string | null | undefined): string | undefined {
  if (!display) return undefined
  const digits = display.replace(/[\s()-]/g, '')
  return digits ? `tel:${digits}` : undefined
}

type BuildCandidateActionConfigArgs = {
  passport: EntityPassport
  phoneHref?: string
  emailHref?: string
  messagesHref?: string
  onOpenDocuments?: () => void
  onCompleteNextReminder?: (reminderId: string) => void
  nextReminderId?: string | null
}

function capabilityAction(
  capabilityId: string | null | undefined,
  args: BuildCandidateActionConfigArgs,
): DetailRailAction | null {
  const { passport, phoneHref, emailHref, messagesHref, onOpenDocuments, onCompleteNextReminder, nextReminderId } = args
  const actions = passport.sections.actions
  if (!actions.workAllowed || !capabilityId) return null

  const label = actions.decisionTitle || capabilityId
  switch (capabilityId) {
    case 'call':
      return phoneHref ? { id: 'call', label, href: phoneHref } : null
    case 'message_whatsapp':
      return messagesHref ? { id: 'message_whatsapp', label: 'WhatsApp', href: messagesHref } : null
    case 'message_email':
      return emailHref ? { id: 'message_email', label: 'Email', href: emailHref } : null
    case 'request_documents':
      return onOpenDocuments ? { id: 'request_documents', label, onClick: onOpenDocuments } : null
    case 'open_documents':
      return onOpenDocuments ? { id: 'open_documents', label, onClick: onOpenDocuments } : null
    case 'complete_task':
      return nextReminderId && onCompleteNextReminder
        ? { id: 'complete_task', label, onClick: () => onCompleteNextReminder(nextReminderId) }
        : null
    default:
      return { id: capabilityId, label }
  }
}

/** Module-owned actions — Shell geometry stays generic. */
export function buildCandidateEntityWorkspaceActionConfig(args: BuildCandidateActionConfigArgs): EntityWorkspaceActionConfig {
  const { passport } = args
  const actions = passport.sections.actions
  if (!actions.workAllowed) {
    return {}
  }

  const primary = capabilityAction(actions.primaryCapabilityId, args)
  const secondary = actions.capabilities
    .filter((cap) => cap.allowed && cap.id !== actions.primaryCapabilityId)
    .map((cap) => capabilityAction(cap.id, args))
    .filter((action): action is DetailRailAction => action != null)

  return {
    contextActions: {
      primary,
      secondary,
    },
    headerActions: [primary, ...secondary].filter((action): action is DetailRailAction => action != null),
  }
}
