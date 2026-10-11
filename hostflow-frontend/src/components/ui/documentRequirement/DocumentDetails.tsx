import type { ReactNode } from 'react'

export function DocumentDetails({ file, metadata }: { file: ReactNode; metadata: ReactNode }) {
  return (
    <div className="mt-2 space-y-3 border-t border-slate-100 pt-2">
      <div className="flex min-w-0 flex-wrap items-center gap-2">{file}</div>
      <div className="min-w-0">{metadata}</div>
    </div>
  )
}
