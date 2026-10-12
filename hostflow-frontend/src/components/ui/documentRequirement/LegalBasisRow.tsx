import type { ReactNode } from 'react'

/** A stay or work basis that is a legal regime, not a Hub document. */
export function LegalBasisRow({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mt-3 border-t border-slate-100 pt-3" data-testid="legal-basis-row">
      <div className="text-sm font-medium text-slate-800">{title}</div>
      {children ? <div className="mt-2 space-y-2">{children}</div> : null}
    </div>
  )
}
