import { SegmentedControl } from '../SegmentedControl'

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

/** Operational document presence. Same SegmentedControl as entity boolean fields. */
export function PresenceToggle({ value, yesLabel, noLabel, orderedLabel, disabled, onChange, onOrdered }: Props) {
  const current = value === true ? 'yes' : value === false ? 'no' : value === 'ordered' ? 'ordered' : null
  const presence = value === null ? 'unknown' : value === 'ordered' ? 'ordered' : value ? 'yes' : 'no'
  const options = [
    { value: 'no', label: noLabel },
    ...(orderedLabel ? [{ value: 'ordered', label: orderedLabel }] : []),
    { value: 'yes', label: yesLabel, tone: 'brand' as const },
  ]
  return (
    <SegmentedControl
      value={current}
      options={options}
      disabled={disabled}
      presence={presence}
      onChange={(next) => {
        if (next === 'ordered') onOrdered?.()
        else onChange(next === 'yes')
      }}
    />
  )
}
