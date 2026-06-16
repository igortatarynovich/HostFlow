import type { InputHTMLAttributes } from 'react'
import clsx from 'clsx'

import { Combobox, type ComboboxProps } from '../../ui/Combobox'
import { MultiCombobox, type MultiComboboxProps } from '../../ui/MultiCombobox'

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string
  hint?: string
  containerClassName?: string
}

export const Input = (props: InputProps) => {
  const { label, hint, className, containerClassName, ...rest } = props
  const isReadOnly = rest.readOnly || rest.disabled
  return (
    <label className={clsx('block', containerClassName)}>
      {label && <div className="label">{label}</div>}
      <input
        {...rest}
        className={clsx(
          'input',
          isReadOnly && 'cursor-not-allowed bg-slate-100 text-slate-600',
          className,
        )}
      />
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </label>
  )
}

export const Checkbox = ({
  label,
  checked,
  onChange,
}: {
  label: string
  checked?: boolean
  onChange?: (v: boolean) => void
}) => (
  <label className="flex items-center gap-2">
    <input type="checkbox" checked={!!checked} onChange={(e) => onChange?.(e.currentTarget.checked)} />
    <span>{label}</span>
  </label>
)

/** @deprecated use `Combobox` from `components/ui/Combobox` */
export function SearchableSelect(props: ComboboxProps) {
  return <Combobox {...props} />
}

/** @deprecated use `MultiCombobox` from `components/ui/MultiCombobox` */
export function CheckboxMultiSelect(props: MultiComboboxProps) {
  return <MultiCombobox {...props} />
}
