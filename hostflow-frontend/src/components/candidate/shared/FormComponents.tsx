import { useState, useRef, useEffect, useMemo } from 'react'
import type { InputHTMLAttributes } from 'react'
import clsx from 'clsx'

type Option = { value: string; label: string; extra?: any }

function useClickOutside<T extends HTMLElement>(onOutside: () => void) {
  const ref = useRef<T | null>(null)
  useEffect(() => {
    function handler(e: MouseEvent) {
      const el = ref.current
      if (!el) return
      if (!el.contains(e.target as Node)) onOutside()
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') onOutside()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', onEsc)
    }
  }, [onOutside])
  return ref
}

export type InputProps = InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; containerClassName?: string }
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
          isReadOnly && 'bg-slate-100 text-slate-600 cursor-not-allowed',
          className,
        )}
      />
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </label>
  )
}

export const Checkbox = ({ label, checked, onChange }:{
  label: string; checked?: boolean; onChange?: (v:boolean)=>void
}) => (
  <label className="flex items-center gap-2">
    <input type="checkbox" checked={!!checked} onChange={e=>onChange?.(e.currentTarget.checked)} />
    <span>{label}</span>
  </label>
)

export function SearchableSelect({
  options,
  value,
  onChange,
  disabled,
  placeholder,
  className,
  searchPlaceholder,
  noResultsLabel,
}: {
  options: Option[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  searchPlaceholder?: string;
  noResultsLabel?: string;
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const current = useMemo(() => options.find(o => o.value === value)?.label || '', [options, value])
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return options
    return options.filter((option: Option) => option.label.toLowerCase().includes(s) || option.value.toLowerCase().includes(s))
  }, [q, options])
  const close = () => setOpen(false)
  const boxRef = useClickOutside<HTMLDivElement>(close)

  return (
    <div className={clsx('relative', className)} ref={boxRef}>
      <button
        type="button"
        className={clsx(
          'input w-full text-left',
          disabled && 'bg-slate-100 text-slate-600 cursor-not-allowed',
        )}
        disabled={disabled}
        onClick={() => {
          if (disabled) return
          setOpen(o => !o)
          setQ('')
        }}
      >
        {current || (placeholder || '— select —')}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-full rounded-xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              className="input"
              placeholder={searchPlaceholder || 'Search…'}
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="max-h-64 overflow-auto">
            {filtered.length === 0 && <div className="px-3 py-2 text-slate-500">{noResultsLabel || 'No matches'}</div>}
            {filtered.map((o: Option) => (
              <button
                key={o.value}
                type="button"
                className={clsx('w-full px-3 py-2 text-left hover:bg-slate-50', o.value === value && 'bg-slate-50')}
                onClick={() => { onChange(o.value); close() }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function CheckboxMultiSelect({
  options,
  values,
  onChange,
  disabled,
  placeholder,
  className,
  searchPlaceholder,
  noResultsLabel,
  multiSelectedLabel,
}: {
  options: Option[];
  values: string[];
  onChange: (vals: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  searchPlaceholder?: string;
  noResultsLabel?: string;
  multiSelectedLabel?: (count: number) => string;
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const boxRef = useClickOutside<HTMLDivElement>(() => setOpen(false))
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return options
    return options.filter((option: Option) => option.label.toLowerCase().includes(s) || option.value.toLowerCase().includes(s))
  }, [q, options])
  const toggle = (v: string) => {
    if (disabled) return
    const set = new Set(values)
    set.has(v) ? set.delete(v) : set.add(v)
    onChange(Array.from(set))
  }
  const caption = values.length === 0
    ? (placeholder || 'Not selected')
    : (values.length <= 3
        ? values
            .map((v) => {
              const found = options.find((option: Option) => option.value === v)
              return found?.label || v
            })
            .join(', ')
        : multiSelectedLabel
          ? multiSelectedLabel(values.length)
          : `${values.length} selected`)

  return (
    <div className={clsx('relative', className)} ref={boxRef}>
      <button
        type="button"
        className={clsx(
          'input w-full text-left',
          disabled && 'bg-slate-100 text-slate-600 cursor-not-allowed',
        )}
        disabled={disabled}
        onClick={() => {
          if (disabled) return
          setOpen(o => !o)
          setQ('')
        }}
      >
        {caption}
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-full rounded-xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              className="input"
              placeholder={searchPlaceholder || 'Search…'}
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <div className="max-h-72 overflow-auto">
            {filtered.length === 0 && <div className="px-3 py-2 text-slate-500">{noResultsLabel || 'No matches'}</div>}
            {filtered.map((o: Option) => {
              const checked = values.includes(o.value)
              return (
                <label
                  key={o.value}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2',
                    disabled ? 'cursor-not-allowed text-slate-500' : 'hover:bg-slate-50 cursor-pointer',
                  )}
                  onClick={() => {
                    if (disabled) return
                    toggle(o.value)
                  }}
                >
                  <input type="checkbox" readOnly checked={checked} />
                  <span>{o.label}</span>
                </label>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
