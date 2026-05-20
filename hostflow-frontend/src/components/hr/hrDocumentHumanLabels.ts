import type { HrReviewDocumentRow } from '../../api/workforce'
import { isDocumentVerified } from './hrDocumentVerificationFields'

type TranslateFn = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

/** HR-facing document status — no raw engine enums in the main UI. */
export function humanDocumentStatusLabel(
  doc: HrReviewDocumentRow,
  t: TranslateFn,
): string {
  if (isDocumentVerified(doc)) {
    return t('app.hr.verify_shell.status.confirmed', { defaultValue: 'Confirmed' })
  }
  const raw = String(doc.verification_status || doc.status || 'pending').toLowerCase()
  if (raw === 'needs_correction') {
    return t('app.hr.verify_shell.status.needs_correction', { defaultValue: 'Correction requested' })
  }
  if (raw === 'rejected') {
    return t('app.hr.verify_shell.status.rejected', { defaultValue: 'Rejected' })
  }
  if (raw === 'opened') {
    return t('app.hr.verify_shell.status.in_review', { defaultValue: 'In review' })
  }
  if (!doc.document_id) {
    return t('app.hr.verify_shell.status.missing_file', { defaultValue: 'File missing' })
  }
  return t('app.hr.verify_shell.status.awaiting', { defaultValue: 'Awaiting confirmation' })
}

export function humanDocumentStatusTone(
  doc: HrReviewDocumentRow,
): 'success' | 'warning' | 'danger' | 'info' | 'neutral' {
  if (isDocumentVerified(doc)) return 'success'
  const raw = String(doc.verification_status || doc.status || '').toLowerCase()
  if (raw === 'rejected') return 'danger'
  if (raw === 'needs_correction') return 'warning'
  if (!doc.document_id) return 'warning'
  if (raw === 'opened') return 'info'
  return 'neutral'
}

export function statusToneClasses(tone: ReturnType<typeof humanDocumentStatusTone>): string {
  switch (tone) {
    case 'success':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'danger':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'warning':
      return 'border-amber-200 bg-amber-50 text-amber-900'
    case 'info':
      return 'border-sky-200 bg-sky-50 text-sky-900'
    default:
      return 'border-slate-200 bg-slate-50 text-slate-700'
  }
}
