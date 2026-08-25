import { useEffect, useRef } from 'react'

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
  const ref = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate
  }, [indeterminate])

  return (
    <input
      ref={ref}
      type="checkbox"
      className={className ?? 'h-4 w-4 rounded border-slate-300'}
      checked={checked}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.checked)}
      onClick={(e) => e.stopPropagation()}
    />
  )
}
