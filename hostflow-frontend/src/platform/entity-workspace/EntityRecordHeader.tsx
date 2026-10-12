import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { EntitySummaryHeader } from '../../components/ui/EntitySummaryHeader'

function initialsFromTitle(title: string): string {
  const letters = title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
  return letters || '•'
}

/**
 * Entity record header. Callers supply identity, context and actions.
 * The header does not own candidate or HR actions.
 */
export function EntityRecordHeader({
  title,
  code,
  initials,
  onCopyCode,
  copyLabel,
  back,
  actions,
  meta,
  context,
  pipeline,
  extra,
}: {
  title: string
  code?: string | null
  initials?: string | null
  onCopyCode?: () => void
  copyLabel?: string
  back?: { to: string; label: string } | null
  actions?: ReactNode
  /** Chips under the name. Not the context row. */
  meta?: ReactNode
  /** Separate row under the identity block: vacancy, employer, process facts. */
  context?: ReactNode
  pipeline?: ReactNode
  extra?: ReactNode
}) {
  return (
    <>
      {back ? (
        <div className="mb-1 text-[11px] text-slate-500">
          <Link className="hover:underline" to={back.to}>
            {back.label}
          </Link>
        </div>
      ) : null}
      <EntitySummaryHeader
        initials={initials || initialsFromTitle(title || '')}
        title={title || '—'}
        code={code}
        onCopyCode={onCopyCode}
        copyLabel={copyLabel}
        actions={actions}
        meta={meta}
        context={context}
        pipeline={pipeline}
      />
      {extra ? <div className="mt-2 rounded-xl border border-slate-200 bg-white px-3 py-2">{extra}</div> : null}
    </>
  )
}
