import clsx from 'clsx'
import { useI18n } from '../../../i18n'
import type { WorkspaceSummary, WorkspaceTransferReadiness } from '../../../api/candidateRequirements'

type Props = {
  summary: WorkspaceSummary
  transferReadiness: WorkspaceTransferReadiness
  canEdit?: boolean
  className?: string
}

export default function RequirementsWorkspaceSummaryBar({
  summary,
  transferReadiness,
  canEdit = true,
  className,
}: Props) {
  const { t } = useI18n()

  const requirementGate = transferReadiness.requirement_gate
  const requirementsClosed =
    requirementGate?.satisfied === true || (summary.all_fulfilled && !summary.blocking_open_count)
  const handoffReady = summary.handoff_ready === true

  const handoffLabel = handoffReady
    ? t('app.candidate_requirements.workspace.handoff_ready', { defaultValue: 'Ready for handoff' })
    : requirementsClosed
      ? t('app.candidate_requirements.workspace.requirements_closed', {
          defaultValue: 'Requirements closed — handoff may need extra confirmations',
        })
      : t('app.candidate_requirements.workspace.handoff_blocked', { defaultValue: 'Handoff blocked' })

  const handoffClass = handoffReady
    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
    : requirementsClosed
      ? 'border-sky-200 bg-sky-50 text-sky-900'
      : 'border-amber-200 bg-amber-50 text-amber-950'

  return (
    <div
      className={clsx(
        'flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="min-w-0 space-y-1">
        <div className="text-sm font-semibold text-slate-900">
          {t('app.candidate_requirements.workspace.summary_progress', {
            defaultValue: '{fulfilled} of {total} closed',
            fulfilled: summary.fulfilled_count,
            total: summary.total_requirements,
          })}
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] text-slate-600">
          {summary.pending_review_count > 0 ? (
            <span>
              {t('app.candidate_requirements.workspace.pending_review', {
                defaultValue: '{count} pending review',
                count: summary.pending_review_count,
              })}
            </span>
          ) : null}
          {summary.blocking_open_count > 0 ? (
            <span>
              {t('app.candidate_requirements.workspace.open_blockers', {
                defaultValue: '{count} open',
                count: summary.blocking_open_count,
              })}
            </span>
          ) : null}
          {!canEdit ? (
            <span className="text-amber-800">
              {t('app.candidate_requirements.workspace.read_only', {
                defaultValue: 'Recruitment locked — view only',
              })}
            </span>
          ) : null}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {summary.all_fulfilled ? (
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-900">
            {t('app.candidate_requirements.workspace.all_fulfilled', { defaultValue: 'All requirements closed' })}
          </span>
        ) : null}
        <span className={clsx('rounded-full border px-3 py-1 text-xs font-medium', handoffClass)}>{handoffLabel}</span>
      </div>
    </div>
  )
}
