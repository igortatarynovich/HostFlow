import clsx from 'clsx'

export type PresenceState = boolean | 'ordered' | null

type Props = {
  value: PresenceState
  yesLabel: string
  noLabel: string
  /** When set, the row can be Нет | Заказано | Есть. Ordered is a procedure state, not a file. */
  orderedLabel?: string
  disabled?: boolean
  onChange: (next: boolean) => void
  onOrdered?: () => void
}

/** Compact Нет | Есть control. Unknown stays unset; explicit Нет is neutral; Есть uses the brand accent. */
export function PresenceToggle({ value, yesLabel, noLabel, orderedLabel, disabled, onChange, onOrdered }: Props) {
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
  const divider = value === null ? 'border-l border-dashed border-slate-300' : 'border-l border-slate-200'
  const presence = value === null ? 'unknown' : value === 'ordered' ? 'ordered' : value ? 'yes' : 'no'
  return (
    <div
      className={clsx(
        'inline-flex overflow-hidden rounded-lg border bg-white',
        value === null ? 'border-dashed border-slate-300' : 'border-slate-200',
      )}
      role="group"
      data-presence={presence}
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
      {orderedLabel ? (
        <button
          type="button"
          className={clsx(segment(value === 'ordered', 'neutral'), divider)}
          aria-pressed={value === 'ordered'}
          disabled={disabled}
          onClick={() => onOrdered?.()}
        >
          {orderedLabel}
        </button>
      ) : null}
      <button
        type="button"
        className={clsx(segment(value === true, 'brand'), divider)}
        aria-pressed={value === true}
        disabled={disabled}
        onClick={() => onChange(true)}
      >
        {yesLabel}
      </button>
    </div>
  )
}
