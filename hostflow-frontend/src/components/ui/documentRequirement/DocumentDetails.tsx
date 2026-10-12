import type { ReactNode } from 'react'

/**
 * Continuation of a document row.
 * The row owns file, status, and actions. This surface owns document data only.
 */
export function DocumentDetails({ children }: { children: ReactNode }) {
  return <div className="mt-2 border-t border-slate-100 pt-3">{children}</div>
}
