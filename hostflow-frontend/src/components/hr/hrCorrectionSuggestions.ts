/** Quick picks for HR document correction — human phrases only (no engine codes). */

export const CORRECTION_SUGGESTION_KEYS = [
  'missing_document',
  'unreadable_scan',
  'data_mismatch',
  'expired_document',
  'missing_field',
  'clearer_file',
] as const

export type CorrectionSuggestionKey = (typeof CORRECTION_SUGGESTION_KEYS)[number]

export function correctionSuggestionLabel(
  key: CorrectionSuggestionKey,
  t: (k: string, o?: { defaultValue?: string }) => string,
): string {
  const map: Record<CorrectionSuggestionKey, string> = {
    missing_document: t('app.hr.decisions.suggest.missing_document', { defaultValue: 'Missing document' }),
    unreadable_scan: t('app.hr.decisions.suggest.unreadable_scan', { defaultValue: 'Unreadable scan' }),
    data_mismatch: t('app.hr.decisions.suggest.data_mismatch', { defaultValue: 'Data mismatch' }),
    expired_document: t('app.hr.decisions.suggest.expired_document', { defaultValue: 'Expired document' }),
    missing_field: t('app.hr.decisions.suggest.missing_field', { defaultValue: 'Missing required field' }),
    clearer_file: t('app.hr.decisions.suggest.clearer_file', { defaultValue: 'Upload clearer file' }),
  }
  return map[key]
}
