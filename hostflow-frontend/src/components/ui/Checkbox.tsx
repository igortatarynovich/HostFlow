import clsx from 'clsx'
import { useId, type ReactNode } from 'react'

export type CheckboxProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: ReactNode
  description?: ReactNode
  disabled?: boolean
  name?: string
  id?: string
  className?: string
}

export function Checkbox({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  name,
  id,
  className,
}: CheckboxProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId

  return (
    <label
      className={clsx('checkbox-field', disabled && 'checkbox-field-disabled', className)}
      htmlFor={inputId}
    >
      <input
        id={inputId}
        name={name}
        type="checkbox"
        className="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label || description ? (
        <span className="min-w-0">
          {label ? <span className="checkbox-label">{label}</span> : null}
          {description ? <span className="checkbox-description">{description}</span> : null}
        </span>
      ) : null}
    </label>
  )
}
