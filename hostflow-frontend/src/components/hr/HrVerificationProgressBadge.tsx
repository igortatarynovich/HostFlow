import { useI18n } from '../../i18n'
import { StatusBadge } from '../ui/StatusBadge'
import type { StatusBadgeSemantic } from '../ui/statusBadgeSemantics'

type Props = {
  verified?: number | null
  total?: number | null
  hrReviewStatus?: string | null
  className?: string
}

/** Thin HR adapter over system StatusBadge — no local pill CSS. */
export function HrVerificationProgressBadge({ verified, total, hrReviewStatus, className }: Props) {
  const { t } = useI18n()
  const status = String(hrReviewStatus || '').toLowerCase()

  if (status === 'approved_for_employment') {
    return (
      <StatusBadge
        className={className}
        size="sm"
        shape="pill"
        semantic="success"
        label={t('app.hr.verify_badge.approved', { defaultValue: 'Approved' })}
      />
    )
  }

  if (typeof total === 'number' && total > 0) {
    const v = typeof verified === 'number' ? verified : 0
    const done = v >= total
    const semantic: StatusBadgeSemantic = done ? 'success' : 'warning'
    return (
      <StatusBadge
        className={className}
        size="sm"
        shape="pill"
        semantic={semantic}
        label={t('app.hr.verify_badge.docs', {
          defaultValue: 'Docs {verified}/{total}',
          values: { verified: v, total },
        })}
      />
    )
  }

  if (status && status !== 'approved_for_employment') {
    return (
      <StatusBadge
        className={className}
        size="sm"
        shape="pill"
        semantic="info"
        label={t('app.hr.verify_badge.review_pending', { defaultValue: 'Verification pending' })}
      />
    )
  }

  return null
}
