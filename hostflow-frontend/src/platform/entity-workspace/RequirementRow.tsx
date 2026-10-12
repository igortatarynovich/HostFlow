import { useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import {
  evidenceStatusLabelKey,
  requirementStatusBadgeClass,
  type RequirementRowStatus,
} from './requirementRowStatus'

/**
 * Compact requirement row shared by the candidate checklist and the employee record.
 * Children are the expanded details. Recruitment actions stay with the caller that has them.
 */
export function RequirementRowFrame({
  label,
  status,
  children,
}: {
  label: string
  status: RequirementRowStatus
  children?: ReactNode
}) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState(false)
  const statusLabel = t(evidenceStatusLabelKey(status), {
    defaultValue:
      status === 'not_applicable'
        ? 'Not applicable'
        : status === 'pending_review'
          ? 'Pending review'
          : status === 'approved'
            ? 'Approved'
            : status === 'rejected'
              ? 'Rejected'
              : status === 'superseded'
                ? 'Superseded'
                : status === 'missing'
                  ? 'Missing'
                  : 'Selected',
  })
  return (
    <div className="border-b border-slate-100 py-1">
      <button
        type="button"
        className="flex w-full items-center gap-3 py-1 text-left"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">{label}</span>
        <span className={clsx('shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold', requirementStatusBadgeClass(status))}>
          {statusLabel}
        </span>
        <span className="shrink-0 text-xs font-medium text-brand-700">
          {expanded ? t('common.actions.collapse') : t('app.candidate_card.ia.open_row', { defaultValue: 'Open' })}
        </span>
      </button>
      {expanded ? children : null}
    </div>
  )
}

export { RequirementRowFrame as RequirementRow }
