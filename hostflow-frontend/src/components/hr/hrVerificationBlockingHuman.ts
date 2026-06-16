import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'

export function humanVerificationBlockingMessages(
  panel: HrReviewPanel,
  docs: HrReviewDocumentRow[],
  t: (key: string, opts?: any) => string,
): string[] {
  const messages: string[] = []
  const blockers = Array.isArray(panel.blockers) ? panel.blockers : []
  for (const b of blockers) {
    const text = String(b || '').trim()
    if (text) messages.push(text.replace(/_/g, ' '))
  }
  const unverifiedRequired = docs.filter((d) => {
    const raw = String(d.verification_status || d.status || '').toLowerCase()
    const required = d.required !== false
    const verified = Boolean(d.verified) || raw === 'verified'
    return required && !verified
  })
  if (unverifiedRequired.length > 0) {
    messages.push(
      t('app.hr.ready.docs_pending', {
        defaultValue: '{count} required document(s) are still not verified.',
        values: { count: unverifiedRequired.length },
      }),
    )
  }
  return Array.from(new Set(messages))
}

