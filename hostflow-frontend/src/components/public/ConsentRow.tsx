import { forwardRef, type ReactNode } from 'react'

export type ConsentRowProps = {
  id: string
  checked: boolean
  onChange: (checked: boolean) => void
  showError?: boolean
  errorMessage?: string
  disabled?: boolean
  children: ReactNode
}

export const ConsentRow = forwardRef<HTMLInputElement, ConsentRowProps>(function ConsentRow(
  { id, checked, onChange, showError = false, errorMessage, disabled = false, children },
  ref,
) {
  const invalid = showError && !checked
  return (
    <div className="space-y-1" data-testid={`consent-row-${id}`}>
      <label
        htmlFor={id}
        className={`flex items-start gap-2.5 rounded-lg border px-2 py-2 text-sm transition ${
          invalid ? 'border-rose-400 bg-rose-50 text-rose-900' : 'border-transparent text-slate-700'
        }`}
      >
        <input
          ref={ref}
          id={id}
          type="checkbox"
          className={`mt-0.5 h-4 w-4 shrink-0 accent-brand-600 ${
            invalid ? 'outline outline-2 outline-rose-500 outline-offset-1' : ''
          }`}
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span className="leading-snug">{children}</span>
      </label>
      {invalid && errorMessage ? (
        <p className="pl-7 text-xs text-rose-700" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  )
})
