// src/components/controls/Select.tsx
import { useEffect, useMemo, useRef, useState } from 'react'

export type Option = { value: string; label: string }

type Props = {
  options: Option[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export default function Select({
  options,
  value,
  onChange,
  placeholder = 'Выберите…',
  disabled,
  className = '',
}: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef<HTMLDivElement | null>(null)

  const selected = useMemo(
    () => options.find(o => o.value === value) || null,
    [options, value]
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter(o => o.label.toLowerCase().includes(q))
  }, [options, query])

  // Закрытие по клику вне
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current) return
      if (!rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  function choose(v: string) {
    onChange(v)
    setOpen(false)
    setQuery('')
  }

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled}
        className="w-full text-left input"
        onClick={() => setOpen(o => !o)}
      >
        {selected ? selected.label : <span className="text-gray-400">{placeholder}</span>}
      </button>

      {open && (
        <div className="absolute z-50 mt-2 w-full rounded-2xl border bg-white shadow-xl">
          <div className="p-2">
            <input
              autoFocus
              placeholder="Поиск..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              className="input w-full"
            />
          </div>

          <div className="max-h-72 overflow-auto py-1">
            {filtered.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-500">нет совпадений</div>
            )}
            {filtered.map(opt => (
              <button
                key={opt.value}
                type="button"
                className={`block w-full px-4 py-2 text-left hover:bg-gray-50 ${
                  opt.value === value ? 'bg-gray-50' : ''
                }`}
                onClick={() => choose(opt.value)}
              >
                {opt.label /* ВАЖНО: label — обычная строка, никакой конкатенации с объектами */}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}