/**
 * Communication model (internal).
 *
 * Lead → Workflow → Available actions → Communication → Message → Attachments[]
 *
 * UI shows operator-facing *actions*; attachments are the transport layer only.
 */

/** Internal attachment kinds — not shown in operator UI. */
export type CommunicationAttachmentKind =
  | 'intake_form'
  | 'documents'
  | 'photos_videos'
  | 'commercial_proposal'
  | 'contract'
  | 'invoice'
  | 'calendar_invite'
  | 'brief'

export type CommunicationAttachment = {
  kind: CommunicationAttachmentKind
  actionId: string
  label: string
  formId?: string
  url?: string
}

export type CommunicationPurpose =
  | 'write_message'
  | 'obtain_information'
  | 'send_outbound'
  | 'schedule_meeting'
  | 'other'

export type CommunicationPurposeOption = {
  id: CommunicationPurpose
  label: string
  enabled: boolean
}

/** Operator-facing action published by workflow (not capability). */
export type CommunicationAction = {
  id: string
  label: string
  enabled: boolean
  attachmentKind: CommunicationAttachmentKind
  /** When action has selectable variants (e.g. questionnaire forms). */
  variantPickerLabel?: string
  variants?: Array<{ id: string; label: string }>
  /** Auto-selected when only one variant applies — not shown as a picker. */
  resolvedVariant?: { id: string; label: string }
}

/** Ready menu for composer — resolved from lead context before render. */
export type LeadCommunicationMenu = {
  purposes: CommunicationPurposeOption[]
  obtainInformation: CommunicationAction[]
  sendOutbound: CommunicationAction[]
}

export type OutboundCommunicationDraft = {
  purpose: CommunicationPurpose
  channel: 'email' | 'whatsapp' | 'link'
  text: string
  emailSubject?: string
  selectedActionIds: string[]
  attachments: CommunicationAttachment[]
  formVariantId?: string
  formLocale?: 'ru' | 'pl' | 'en'
}

export function buildAttachmentsFromSelectedActions(args: {
  menu: LeadCommunicationMenu
  purpose: CommunicationPurpose
  selectedActionIds: string[]
  formVariantId: string | null
  applyUrl: string | null
}): CommunicationAttachment[] {
  const pool =
    args.purpose === 'obtain_information'
      ? args.menu.obtainInformation
      : args.purpose === 'send_outbound'
        ? args.menu.sendOutbound
        : []

  const attachments: CommunicationAttachment[] = []
  for (const actionId of args.selectedActionIds) {
    const action = pool.find((row) => row.id === actionId)
    if (!action || !action.enabled) continue

    if (action.attachmentKind === 'intake_form') {
      const variant =
        action.variants?.find((row) => row.id === args.formVariantId) ||
        action.variants?.[0] ||
        null
      if (!variant) continue
      attachments.push({
        kind: action.attachmentKind,
        actionId: action.id,
        label: variant.label,
        formId: variant.id,
        url: args.applyUrl || undefined,
      })
      continue
    }

    attachments.push({
      kind: action.attachmentKind,
      actionId: action.id,
      label: action.label,
    })
  }
  return attachments
}

export function draftHasIntakeForm(draft: OutboundCommunicationDraft): boolean {
  return draft.attachments.some((attachment) => attachment.kind === 'intake_form')
}
