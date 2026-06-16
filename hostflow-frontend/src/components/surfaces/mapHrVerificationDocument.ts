import type { HrReviewDocumentRow } from '../../api/workforce'

type Tone = 'ok' | 'warn' | 'bad' | 'info'

export function mapHrVerificationDocumentRow(
  doc: HrReviewDocumentRow,
  t: (key: string, opts?: any) => string,
): {
  row: {
    label: string
    subtitle?: string
    statusLabel: string
    displayStatus: string
    severity: Tone
  }
  statusLabel: string
  displayStatus: string
  severity: Tone
} {
  const raw = String(doc.verification_status || doc.status || '').toLowerCase()
  const verified = Boolean(doc.verified) || raw === 'verified'
  const needsCorrection = raw === 'needs_correction' || raw === 'rejected'
  const missing = raw === 'missing'

  const severity: Tone = verified ? 'ok' : needsCorrection || missing ? 'bad' : raw.includes('pending') ? 'warn' : 'info'
  const statusLabel = verified
    ? t('app.hr.verify_shell.status.verified', { defaultValue: 'Verified' })
    : needsCorrection
      ? t('app.hr.verify_shell.status.needs_correction', { defaultValue: 'Needs correction' })
      : missing
        ? t('app.hr.verify_shell.status.missing', { defaultValue: 'Missing' })
        : t('app.hr.verify_shell.status.pending', { defaultValue: 'Pending' })

  const displayStatus = raw || (verified ? 'verified' : 'pending')
  return {
    row: {
      label: doc.label,
      subtitle: doc.document_key,
      statusLabel,
      displayStatus,
      severity,
    },
    statusLabel,
    displayStatus,
    severity,
  }
}

