import clsx from 'clsx'
import type { EntityListTableFrameProps } from './entityListTypes'

const DEFAULT_LOADING = (
  <p className="px-4 py-8 text-center text-sm text-slate-500" role="status">
    Loading…
  </p>
)

const DEFAULT_EMPTY = (
  <p className="px-4 py-8 text-center text-sm text-slate-500">No rows match the current filters.</p>
)

const DEFAULT_ERROR = (
  <p className="px-4 py-8 text-center text-sm text-rose-700" role="alert">
    Could not load this list. Try again.
  </p>
)

/**
 * Switches table body by explicit status — no boolean props on EntityListShell.
 */
export default function EntityListTableFrame({
  status,
  table,
  loading = DEFAULT_LOADING,
  empty = DEFAULT_EMPTY,
  error = DEFAULT_ERROR,
  className,
}: EntityListTableFrameProps) {
  let body = table
  if (status === 'loading') body = loading
  else if (status === 'empty') body = empty
  else if (status === 'error') body = error

  return (
    <div
      className={clsx(
        'entity-list-table-frame overflow-auto border border-slate-200 bg-white shadow-sm',
        className,
      )}
      data-entity-list-table-status={status}
    >
      {body}
    </div>
  )
}
