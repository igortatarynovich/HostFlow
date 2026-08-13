import { Checkbox } from '../ui/Checkbox'

export type EntityListSelectionCheckboxProps = {
  checked: boolean
  indeterminate?: boolean
  onChange: (checked: boolean) => void
  ariaLabel: string
  className?: string
}

/** Header or row checkbox with controlled selection (checkbox ≠ row navigation). */
export default function EntityListSelectionCheckbox({
  checked,
  indeterminate = false,
  onChange,
  ariaLabel,
  className,
}: EntityListSelectionCheckboxProps) {
  return (
    <Checkbox
      checked={checked}
      indeterminate={indeterminate}
      className={className ?? 'h-4 w-4 border-slate-300'}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.checked)}
      onClick={(e) => e.stopPropagation()}
    />
  )
}
