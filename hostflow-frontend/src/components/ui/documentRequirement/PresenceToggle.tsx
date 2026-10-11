import clsx from 'clsx'

type Props = {
  value: boolean | null
  yesLabel: string
  noLabel: string
  disabled?: boolean
  onChange: (next: boolean) => void
}

export function PresenceToggle({ value, yesLabel, noLabel, disabled, onChange }: Props) {
  const segment = (selected: boolean) =>
    clsx(
      'px-3 py-1 text-xs font-medium',
      selected ? 'bg-slate-900 text-white' : 'bg-white text-slate-700',
      disabled ? 'cursor-default' : 'cursor-pointer',
    )
  return (
    <div className="inline-flex overflow-hidden rounded-lg border border-slate-200" role="group">
      <button
        type="button"
        className={segment(value === false)}
        aria-pressed={value === false}
        disabled={disabled}
        onClick={() => onChange(false)}
      >
        {noLabel}
      </button>
      <button
        type="button"
        className={clsx(segment(value === true), 'border-l border-slate-200')}
        aria-pressed={value === true}
        disabled={disabled}
        onClick={() => onChange(true)}
      >
        {yesLabel}
      </button>
    </div>
  )
}
