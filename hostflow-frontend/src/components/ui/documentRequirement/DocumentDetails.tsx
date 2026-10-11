import type { ReactNode } from 'react'

export function DocumentDetails({ file, metadata }: { file: ReactNode; metadata: ReactNode }) {
  return (
    <div className="mt-2 grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-2">
      <div className="min-w-0 space-y-2">{file}</div>
      <div className="min-w-0 space-y-2">{metadata}</div>
    </div>
  )
}
