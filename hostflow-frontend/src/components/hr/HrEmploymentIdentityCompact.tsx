import type { HrReviewPanel } from '../../api/workforce'

type Props = {
  panel: HrReviewPanel
}

const STATUS_CLASS: Record<string, string> = {
  complete: 'text-emerald-800 bg-emerald-50 ring-emerald-200',
  incomplete: 'text-slate-700 bg-slate-50 ring-slate-200',
  conflicted: 'text-amber-900 bg-amber-50 ring-amber-200',
  stale: 'text-orange-900 bg-orange-50 ring-orange-200',
}

export default function HrEmploymentIdentityCompact({ panel }: Props) {
  const identity = panel.employment_identity
  const dv = panel.data_verification_summary
  if (!identity && !dv) return null

  const status = identity?.status ?? dv?.identity_status ?? 'incomplete'
  const badgeClass = STATUS_CLASS[status] ?? STATUS_CLASS.incomplete

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs">
      <span className="font-medium text-slate-600">Employment identity</span>
      <span className={`inline-flex rounded-full px-2 py-0.5 font-semibold ring-1 ring-inset ${badgeClass}`}>
        {status}
        {identity?.filled_count != null && identity?.total_count != null
          ? ` · ${identity.filled_count}/${identity.total_count}`
          : null}
      </span>
      {identity?.missing_required?.length ? (
        <span className="text-amber-800">Missing: {identity.missing_required.length}</span>
      ) : null}
      {identity?.conflicts?.length ? (
        <span className="text-amber-800">Conflicts: {identity.conflicts.length}</span>
      ) : null}
      {identity?.ready_for_downstream ? (
        <span className="text-emerald-700">Ready for contracts / ZUS</span>
      ) : null}
    </div>
  )
}
