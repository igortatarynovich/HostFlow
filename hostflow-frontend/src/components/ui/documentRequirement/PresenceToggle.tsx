import clsx from 'clsx'

type Props = {
  value: boolean | null
  yesLabel: string
  noLabel: string
  disabled?: boolean
  onChange: (next: boolean) => void
}

/** Compact Нет | Есть control. Unknown stays unset; explicit Нет is neutral; Есть uses the brand accent. */
export function PresenceToggle({ value, yesLabel, noLabel, disabled, onChange }: Props) {
  const segment = (selected: boolean, tone: 'neutral' | 'brand') =>
    clsx(
      'h-8 min-w-[3.25rem] px-2.5 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200',
      disabled ? 'cursor-default' : 'cursor-pointer',
      selected
        ? tone === 'brand'
          ? 'bg-brand-600 text-white'
          : 'bg-slate-100 text-slate-800'
        : 'bg-transparent text-slate-500',
    )
  return (
    <div
      className={clsx(
        'inline-flex overflow-hidden rounded-lg border bg-white',
        value === null ? 'border-dashed border-slate-300' : 'border-slate-200',
      )}
      role="group"
      data-presence={value === null ? 'unknown' : value ? 'yes' : 'no'}
    >
      <button
        type="button"
        className={segment(value === false, 'neutral')}
        aria-pressed={value === false}
        disabled={disabled}
        onClick={() => onChange(false)}
      >
        {noLabel}
      </button>
      <button
        type="button"
        className={clsx(
          segment(value === true, 'brand'),
          value === null ? 'border-l border-dashed border-slate-300' : 'border-l border-slate-200',
        )}
        aria-pressed={value === true}
        disabled={disabled}
        onClick={() => onChange(true)}
      >
        {yesLabel}
      </button>
    </div>
  )
}
