import type { ReactNode } from 'react'

export function MarketingOptionCard({
  selected,
  onClick,
  children,
  disabled,
  testId,
}: {
  selected: boolean
  onClick: () => void
  children: ReactNode
  disabled?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      data-testid={testId}
      onClick={onClick}
      className={`w-full rounded-xl border-2 p-4 text-left text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
        selected
          ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {children}
    </button>
  )
}
