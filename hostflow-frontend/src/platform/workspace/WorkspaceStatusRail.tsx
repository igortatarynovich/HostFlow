import clsx from 'clsx'
import { Link } from 'react-router-dom'
import type { WorkspaceStatusSnapshot } from '@hostflow/workspace'
import { useI18n } from '../../i18n'

type Props = {
  snapshot: WorkspaceStatusSnapshot | null
  loading?: boolean
  className?: string
}

function resolveLabel(t: (key: string, opts?: { defaultValue?: string }) => string, key: string): string {
  if (key.startsWith('workspace.') || key.includes('.')) {
    return t(key, { defaultValue: key })
  }
  return key
}

export default function WorkspaceStatusRail({ snapshot, loading, className }: Props) {
  const { t } = useI18n()

  if (loading && !snapshot) {
    return (
      <div className={clsx('rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500', className)}>
        {t('workspace.status.loading', { defaultValue: 'Checking readiness…' })}
      </div>
    )
  }

  if (!snapshot) return null

  const { aggregated_severity, contributions, displayed_next_action } = snapshot
  const blockers = contributions.flatMap((c) => c.blockers ?? [])

  const severityClass =
    aggregated_severity === 'ready'
      ? 'border-emerald-200 bg-emerald-50'
      : aggregated_severity === 'blocked'
        ? 'border-amber-200 bg-amber-50'
        : aggregated_severity === 'warning'
          ? 'border-sky-200 bg-sky-50'
          : 'border-slate-200 bg-white'

  const nextActionLabel = displayed_next_action
    ? resolveLabel(t, displayed_next_action.label_key)
    : null

  const nextActionHref =
    displayed_next_action?.handler_kind === 'navigation' ? displayed_next_action.handler_ref : null

  return (
    <aside
      className={clsx('rounded-xl border p-4', severityClass, className)}
      aria-label={t('workspace.status.rail_label', { defaultValue: 'Workspace status' })}
      data-testid="workspace-status-rail"
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
        {t('workspace.status.title', { defaultValue: 'Workspace status' })}
      </div>

      {blockers.length > 0 ? (
        <ul className="mt-3 space-y-2" data-testid="workspace-status-blockers">
          {blockers.map((blocker) => (
            <li
              key={blocker.block_id}
              className={clsx(
                'text-sm',
                blocker.severity === 'blocked' ? 'text-amber-950' : 'text-slate-700',
              )}
            >
              {resolveLabel(t, blocker.label_key)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-emerald-900" data-testid="workspace-status-no-blockers">
          {t('workspace.status.no_blockers', { defaultValue: 'No blocking items' })}
        </p>
      )}

      {displayed_next_action ? (
        <div className="mt-4" data-testid="workspace-status-next-action">
          {nextActionHref ? (
            <Link
              to={nextActionHref}
              className="btn-primary btn-sm inline-flex"
            >
              {nextActionLabel}
            </Link>
          ) : (
            <span className="text-sm font-medium text-slate-900">{nextActionLabel}</span>
          )}
        </div>
      ) : null}
    </aside>
  )
}
