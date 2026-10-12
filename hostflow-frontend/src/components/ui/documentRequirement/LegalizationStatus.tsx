import { useI18n } from '../../../i18n'

/** Resolved legalization result. It is not the operator's yes/no and not the file status. */
export function LegalizationStatus({
  status,
  missing,
  detail,
}: {
  status?: string | null
  missing?: string[] | null
  detail?: string | null
}) {
  const { t } = useI18n()
  if (!status) return null
  const names = (missing || [])
    .map((code) => t(`app.candidate_card.ia.legalization.evidence.${code}`, { defaultValue: code }))
    .filter(Boolean)
  let label = t(`app.candidate_card.ia.legalization.status.${status}`, { defaultValue: status })
  if (detail === 'employment_mismatch') {
    label = t('app.candidate_card.ia.legalization.employment_mismatch', {
      defaultValue: 'Does not match the current employment',
    })
  } else if (status === 'needs_document' && names.length) {
    label = t('app.candidate_card.ia.legalization.missing', {
      defaultValue: 'Missing: {{items}}',
      values: { items: names.join(', ') },
    })
  }
  return (
    <p className="text-sm text-slate-600" data-testid="legalization-status">
      {label}
    </p>
  )
}
