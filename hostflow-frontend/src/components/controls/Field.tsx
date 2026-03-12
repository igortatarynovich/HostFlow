import type { PropsWithChildren } from 'react'
import clsx from 'clsx'

export default function Field({
  label, required, error, children, hint, className
}: PropsWithChildren<{label?: string; required?: boolean; error?: string; hint?: string; className?: string}>){
  return (
    <div className={clsx("space-y-1", className)}>
      {label && <div className="label">{label} {required && <span className="text-red-600">*</span>}</div>}
      {children}
      {(error || hint) && (
        <div className={clsx("text-xs", error ? "text-red-600" : "text-slate-500")}>
          {error || hint}
        </div>
      )}
    </div>
  )
}