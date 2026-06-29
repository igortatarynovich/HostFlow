import clsx from 'clsx'
import { useI18n } from '../../i18n'

type Props = {
  verified?: number | null
  total?: number | null
  hrReviewStatus?: string | null
  className?: string
}

export function HrVerificationProgressBadge({ verified, total, hrReviewStatus, className }: Props) {
  const { t } = useI18n()
  const status = String(hrReviewStatus || '').toLowerCase()

  if (status === 'approved_for_employment') {
    return (
      <span className={clsx('inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800', className)}>
        {t('app.hr.verify_badge.approved', { defaultValue: 'Approved' })}
      </span>
    )
  }

  if (typeof total === 'number' && total > 0) {
    const v = typeof verified === 'number' ? verified : 0
    const done = v >= total
    return (
      <span
        className={clsx(
          'inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium tabular-nums',
          done ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-950',
          className,
        )}
      >
        {t('app.hr.verify_badge.docs', {
          defaultValue: 'Docs {verified}/{total}',
          values: { verified: v, total },
        })}
      </span>
    )
  }

  if (status && status !== 'approved_for_employment') {
    return (
      <span className={clsx('inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-900', className)}>
        {t('app.hr.verify_badge.review_pending', { defaultValue: 'Verification pending' })}
      </span>
    )
  }

  return null
}
