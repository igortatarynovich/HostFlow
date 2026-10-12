import type { ReactNode } from 'react'
import clsx from 'clsx'

/** Continuation of a document row: file cluster beside metadata, not a nested card. */
export function DocumentDetails({
  file,
  metadata,
}: {
  file?: ReactNode
  metadata?: ReactNode
}) {
  const both = Boolean(file) && Boolean(metadata)
  return (
    <div
      className={clsx(
        'mt-2 border-t border-slate-100 pt-3',
        both ? 'grid gap-4 md:grid-cols-[minmax(12rem,16rem)_minmax(0,1fr)]' : 'space-y-3',
      )}
    >
      {file ? <div className="min-w-0 space-y-2">{file}</div> : null}
      {metadata ? <div className="min-w-0 space-y-2">{metadata}</div> : null}
    </div>
  )
}
