import clsx from 'clsx'
import { forwardRef, useEffect, useRef, type InputHTMLAttributes, type Ref } from 'react'

export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label?: string
  indeterminate?: boolean
}

function mergeRefs<T>(...refs: Array<Ref<T> | undefined>) {
  return (node: T | null) => {
    for (const ref of refs) {
      if (!ref) continue
      if (typeof ref === 'function') ref(node)
      else ref.current = node
    }
  }
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className, label, id, indeterminate = false, ...rest },
  ref,
) {
  const localRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (localRef.current) localRef.current.indeterminate = Boolean(indeterminate)
  }, [indeterminate])

  const input = (
    <input
      id={id}
      ref={mergeRefs(localRef, ref)}
      type="checkbox"
      className={clsx('h-4 w-4 border-slate-300', className)}
      {...rest}
    />
  )
  if (!label) return input
  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm text-slate-700">
      {input}
      <span>{label}</span>
    </label>
  )
})
