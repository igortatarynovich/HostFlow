import type { ReactNode } from 'react'

/** Compact field grid in the same control language as workspace editors. Short values stay short. */
export function MetadataGrid({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div>
      {title ? <div className="mb-2 text-xs font-medium text-slate-700">{title}</div> : null}
      <div className="workspace-editor grid grid-cols-[repeat(auto-fill,minmax(12rem,16rem))] gap-x-4 gap-y-3">
        {children}
      </div>
    </div>
  )
}
