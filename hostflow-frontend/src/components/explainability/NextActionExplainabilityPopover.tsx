import type { NextActionDTO } from '../../api/nextAction'
import { useI18n } from '../../i18n'
import { ExplainabilityPopover, ExplainabilityRow } from './ExplainabilityPopover'

/**
 * G-10 explainability popover for the per-entity primary CTA badge.
 *
 * Surfaces the machine-readable `reason_code` from
 * `backend/app/services/next_action.py` plus a short translated rationale so
 * the operator sees WHY the system suggested this action — not just WHAT.
 *
 * Translation strategy:
 * - i18n key per reason code: `app.explain.next_action.reason.<code>`. When
 *   missing we fall back to the English rationale baked into this file.
 * - A handful of `terminal_stage_*` / `terminal_status_*` codes share a
 *   single key with stage / status as a value to avoid an i18n key explosion.
 * - Some reason codes are reused across entities (`reminder_due`,
 *   `no_signal`, `invalid_input`); only the lookup-not-found copy needs to
 *   know about the entity.
 */

interface Props {
  dto: NextActionDTO
  /** Visual variant: `inverse` for the dark candidate header (lighter "?"
   *  trigger), `default` otherwise. */
  variant?: 'inverse' | 'default'
}

const REASON_FALLBACK: Record<string, string> = {
  reminder_overdue: 'Suggested because there is an active reminder past its due date.',
  reminder_due: 'Suggested because there is an active reminder coming up.',
  no_contact_attempt: 'Suggested because no contact attempt has been logged yet.',
  handoff_pending_client_decision: 'Waiting on the client to accept or reject the handoff.',
  terminal_deleted: 'Entity is deleted — no actions are recommended.',
  no_signal: 'No reminders, no pending handoff, no contact gap — nothing to do right now.',
  candidate_not_found: 'Candidate not found in this tenant — recommendation unavailable.',
  // G-8 stage 2.0: lead-specific codes.
  lead_not_found: 'Lead not found in this tenant — recommendation unavailable.',
  lead_needs_routing: 'The auto-pipeline is paused waiting for a routing decision on this lead.',
  lead_unqualified: 'This lead is fresh — confirm intent and contact info before routing.',
  // G-8 stage 2.1: vacancy-specific codes.
  vacancy_not_found: 'Vacancy not found in this tenant — recommendation unavailable.',
  // Shared by vacancy (stage 2.1) and thread (stage 2.3). Generic copy
  // reads correctly for both — entity-specific naming would force a
  // discriminator, which the popover does not have.
  terminal_archived: 'Archived — no further action.',
  vacancy_paused: 'You paused this vacancy — resume it when you are ready to continue sourcing.',
  vacancy_no_recruiter:
    'No active recruiters are assigned — lead distribution will skip this vacancy until you assign one.',
  // G-8 stage 2.2: document-specific codes.
  // Note: `terminal_deleted` reuses the candidate-side fallback above —
  // the entity is named generically there, which reads correctly for docs.
  document_not_found: 'Document not found in this tenant — recommendation unavailable.',
  document_overdue:
    'The SLA on this document has been breached. Open the candidate and resolve the document.',
  document_expired: 'The document is past its validity date and must be renewed.',
  document_expired_by_date:
    'Status still says "resolved" but the validity date has passed — the document needs to be renewed.',
  document_expiring_soon: 'The document expires within the next 30 days — start the renewal now.',
  document_missing: 'The document is required but has not been provided yet.',
  document_rejected: 'The document was rejected and must be re-submitted.',
  document_to_prepare: 'The document needs to be prepared before it can move forward.',
  document_to_register: 'The document needs to be registered before it can move forward.',
  document_needs_verification:
    'A file is uploaded — review and approve or reject it.',
  document_awaiting_party:
    'The document is in flight with an external party — there is nothing to do until they respond or a reminder fires.',
  // G-8 stage 2.3: thread-specific codes. `terminal_archived` is shared
  // with vacancy (defined above). `terminal_deleted` reuses the generic
  // fallback (it reads correctly for threads). `terminal_status_*` is
  // handled by `defaultExplanationFor` further down.
  thread_not_found: 'Thread not found in this tenant — recommendation unavailable.',
  thread_sla_overdue:
    'The reply SLA on this thread has been breached. Open the inbox and respond now.',
  thread_unread_inbound:
    'The candidate or client sent a new message that is still unread.',
  thread_awaiting_reply:
    'The last message was inbound — they are waiting for a reply from your team.',
  thread_sla_due_soon:
    'The reply SLA is approaching — answer now to avoid a breach.',
  thread_snoozed:
    'The thread is snoozed by the operator — no action is expected until it resumes.',
  thread_pending:
    'The thread is paused pending an external trigger — no operator action is expected right now.',
  invalid_input: 'Recommendation could not be computed from the inputs.',
}

function defaultExplanationFor(reasonCode: string): string {
  if (reasonCode.startsWith('terminal_stage_')) {
    const stage = reasonCode.slice('terminal_stage_'.length)
    return `Stage is "${stage}" — pipeline outcome is recorded, no further action.`
  }
  if (reasonCode.startsWith('terminal_status_')) {
    const status = reasonCode.slice('terminal_status_'.length)
    return `Status is "${status}" — lead is not active, no further action.`
  }
  return REASON_FALLBACK[reasonCode] || 'No further detail available for this recommendation.'
}

export function NextActionExplainabilityPopover({ dto }: Props) {
  const { t } = useI18n()

  const stageSpecific = dto.reason_code.startsWith('terminal_stage_')
  const statusSpecific = dto.reason_code.startsWith('terminal_status_')
  let explanationKey: string
  let explanationValues: Record<string, string> | undefined
  if (stageSpecific) {
    explanationKey = 'app.explain.next_action.reason.terminal_stage'
    explanationValues = { stage: dto.reason_code.slice('terminal_stage_'.length) }
  } else if (statusSpecific) {
    explanationKey = 'app.explain.next_action.reason.terminal_status'
    explanationValues = { status: dto.reason_code.slice('terminal_status_'.length) }
  } else {
    explanationKey = `app.explain.next_action.reason.${dto.reason_code}`
    explanationValues = undefined
  }
  const explanationText = t(explanationKey, {
    defaultValue: defaultExplanationFor(dto.reason_code),
    values: explanationValues,
  })

  return (
    <ExplainabilityPopover
      title={t('app.explain.next_action.title', { defaultValue: 'Why this recommendation?' })}
      align="right"
      triggerAriaLabel={t('app.explain.next_action.trigger_aria', {
        defaultValue: 'Show why this action is recommended',
      })}
    >
      <ExplainabilityRow
        label={t('app.explain.next_action.field.kind', { defaultValue: 'Kind' })}
        value={t(`app.next_action.kind.${dto.kind}`, { defaultValue: dto.kind })}
        mono
      />
      <ExplainabilityRow
        label={t('app.explain.next_action.field.priority', { defaultValue: 'Priority' })}
        value={t(`app.next_action.priority.${dto.priority}`, { defaultValue: dto.priority })}
        mono
      />
      <ExplainabilityRow
        label={t('app.explain.next_action.field.reason', { defaultValue: 'Reason code' })}
        value={dto.reason_code}
        mono
      />
      {dto.due_at && (
        <ExplainabilityRow
          label={t('app.explain.next_action.field.due_at', { defaultValue: 'Due' })}
          value={new Date(dto.due_at).toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        />
      )}
      <p className="pt-1 text-[10.5px] italic leading-snug text-slate-600">
        {explanationText}
      </p>
    </ExplainabilityPopover>
  )
}

export default NextActionExplainabilityPopover
