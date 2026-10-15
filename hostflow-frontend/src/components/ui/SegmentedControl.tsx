import clsx from 'clsx'

export type SegmentedTone = 'neutral' | 'brand'

export type SegmentedOption = {
  value: string
  label: string
  tone?: SegmentedTone
}

type Props = {
  value: string | null
  options: SegmentedOption[]
  onChange: (value: string) => void
  disabled?: boolean
  /** Operational presence marker. Unknown stays visually distinct from an explicit choice. */
  presence?: string
}

/** One compact choice control. Unknown is unselected; an explicit choice fills its segment. */
export function SegmentedControl({ value, options, onChange, disabled, presence }: Props) {
  const unknown = value == null || value === ''
  const segment = (selected: boolean, tone: SegmentedTone) =>
    clsx(
      'h-8 min-w-[3.25rem] px-2.5 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-200',
      disabled ? 'cursor-default' : 'cursor-pointer',
      selected
        ? tone === 'brand'
          ? 'bg-brand-600 text-white'
          : 'bg-slate-100 text-slate-800'
        : 'bg-transparent text-slate-500',
    )
  const divider = unknown ? 'border-l border-dashed border-slate-300' : 'border-l border-slate-200'
  return (
    <div
      className={clsx(
        'inline-flex overflow-hidden rounded-lg border bg-white',
        unknown ? 'border-dashed border-slate-300' : 'border-slate-200',
      )}
      role="group"
      data-presence={presence ?? (unknown ? 'unknown' : value)}
    >
      {options.map((option, index) => (
        <button
          key={option.value}
          type="button"
          className={clsx(segment(value === option.value, option.tone ?? 'neutral'), index > 0 && divider)}
          aria-pressed={value === option.value}
          disabled={disabled}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
