import { useI18n } from '../../../i18n'

const STATUS_COPY: Record<string, { key: string; fallback: string }> = {
  confirmed: { key: 'app.candidate_card.ia.legalization_status_confirmed', fallback: 'Confirmed' },
  needs_verification: { key: 'app.candidate_card.ia.legalization_status_needs_verification', fallback: 'Needs verification' },
  needs_review: { key: 'app.candidate_card.ia.legalization_status_needs_review', fallback: 'Needs review' },
  needs_permit: { key: 'app.candidate_card.ia.legalization_status_needs_verification', fallback: 'Needs verification' },
  permit_ordered: { key: 'app.candidate_card.ia.legalization_status_ordered', fallback: 'Permit ordered' },
}

/** Resolved legalization result. It is not the operator's yes/no and not the file status. */
export function LegalizationStatus({
  status,
  missing,
  detail,
  hideGap = false,
}: {
  status?: string | null
  missing?: string[] | null
  detail?: string | null
  /** The document rows already show a missing file. Do not repeat it as a resolver code. */
  hideGap?: boolean
}) {
  const { t } = useI18n()
  if (!status) return null
  if (hideGap && (status === 'needs_document' || status === 'needs_permit' || status === 'permit_ordered')) return null
  const humanName = (code: string) => {
    const typed = t(`admin.documents.type_codes.${code}`, { defaultValue: '' }).trim()
    if (typed && typed !== code) return typed
    const basis = t(`app.candidate_card.ia.legalization.basis.${code}`, { defaultValue: '' }).trim()
    if (basis && basis !== code) return basis
    return ''
  }
  const names = (missing || []).map(humanName).filter(Boolean)
  let label = STATUS_COPY[status]
    ? t(STATUS_COPY[status].key, { defaultValue: STATUS_COPY[status].fallback })
    : ''
  if (detail === 'employment_mismatch') {
    label = t('app.candidate_card.ia.legalization_employment_mismatch', {
      defaultValue: 'Does not match the current employment',
    })
  } else if (!hideGap && names.length && (status === 'needs_document' || status === 'needs_permit')) {
    label = t('app.candidate_card.ia.legalization_missing', {
      defaultValue: 'Still needed: {items}',
      values: { items: names.join(', ') },
    })
  }
  if (!label || label === status) return null
  return (
    <p className="text-sm text-slate-600" data-testid="legalization-status">
      {label}
    </p>
  )
}
