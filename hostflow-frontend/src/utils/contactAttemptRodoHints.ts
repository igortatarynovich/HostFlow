import type { RodoStatusOut } from '../api/legalDocuments'

type TFn = (key: string, opts?: { defaultValue?: string }) => string

/** Whether candidate likely has email (supports API before candidate_has_email existed). */
export function rodoStatusHasRecipientEmail(status: RodoStatusOut): boolean {
  if (status.candidate_has_email === true) return true
  if (status.candidate_has_email === false) return false
  return Boolean((status.recipient || '').trim())
}

/** Human-readable lines: why RODO was not sent yet / cannot be sent. */
export function explainWhyRodoNotSentYet(status: RodoStatusOut, t: TFn): string[] {
  if (status.sent) return []
  const lines: string[] = []
  if (!rodoStatusHasRecipientEmail(status)) {
    lines.push(
      t('app.candidate_card.rodo.reason_no_email_detail', {
        defaultValue:
          'The candidate has no email on file. Add an email in the profile, then send RODO from the block above.',
      }),
    )
  }
  if (status.active_rodo_template === false) {
    lines.push(
      t('app.candidate_card.rodo.reason_no_template_detail', {
        defaultValue:
          'There is no active RODO clause document for your organization. An administrator must publish a RODO text in Legal documents.',
      }),
    )
  }
  if (lines.length === 0 && !status.can_send) {
    lines.push(
      t('app.candidate_card.rodo.reason_send_unavailable_detail', {
        defaultValue:
          'RODO cannot be sent automatically yet — check the candidate email and that an active RODO clause exists for your tenant.',
      }),
    )
  }
  if (lines.length === 0) {
    lines.push(
      t('app.candidate_card.rodo.reason_ready_to_send_detail', {
        defaultValue: 'RODO has not been sent yet. Use “Send RODO” in the block above.',
      }),
    )
  }
  return lines
}

export function explainContactTrackingDisabled(reason: string | null | undefined, t: TFn): string {
  switch (reason) {
    case 'no_company':
      return t('app.candidate_card.contact_attempts.tracking_disabled_no_company', {
        defaultValue:
          'Link this candidate to a company or vacancy so contact-attempt settings from the client agreement can apply.',
      })
    case 'no_tenant_link':
      return t('app.candidate_card.contact_attempts.tracking_disabled_no_link', {
        defaultValue:
          'No active agency–client link was found for this company. Contact attempts stay off until handoff / tenant link and policy are configured.',
      })
    case 'disabled_in_link':
      return t('app.candidate_card.contact_attempts.tracking_disabled_in_link', {
        defaultValue: 'Contact attempt tracking is turned off in the client link settings (Handoff & contact attempts).',
      })
    default:
      return t('app.candidate_card.contact_attempts.tracking_disabled_generic', {
        defaultValue: 'Contact attempt tracking is not available for this candidate.',
      })
  }
}
