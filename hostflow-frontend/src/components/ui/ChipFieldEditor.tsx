import { Chip } from './Chip'

type Option = { value: string; label: string }

/** Selected values as chips, with one compact add control. The row chrome stays outside. */
export function ChipFieldEditor({
  options,
  values,
  onChange,
  disabled,
  addLabel,
  dismissLabel,
}: {
  options: Option[]
  values: string[]
  onChange: (next: string[]) => void
  disabled?: boolean
  addLabel: string
  dismissLabel?: string
}) {
  const selected = new Set(values)
  const chosen = options.filter((option) => selected.has(option.value))
  const rest = options.filter((option) => !selected.has(option.value))
  return (
    <div className="flex flex-wrap items-center gap-1">
      {chosen.map((option) => (
        <Chip
          key={option.value}
          behavior="dismissible"
          size="sm"
          label={option.label}
          disabled={disabled}
          dismissLabel={dismissLabel}
          onDismiss={disabled ? undefined : () => onChange(values.filter((value) => value !== option.value))}
        />
      ))}
      {rest.length ? (
        <select
          className="input w-auto max-w-full px-2"
          aria-label={addLabel}
          disabled={disabled}
          value=""
          onChange={(event) => {
            const next = event.target.value
            if (!next) return
            onChange([...values, next])
          }}
        >
          <option value="">{addLabel}</option>
          {rest.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      ) : null}
    </div>
  )
}
