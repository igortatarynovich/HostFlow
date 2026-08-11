import { useEffect, useMemo, useRef, useState } from 'react'
import clsx from 'clsx'
import type { Option } from './Select'
import { useI18n } from '../../i18n'

export default function MultiSelect({
  options,
  values,
  onChange,
  placeholder,
  className,
}:{
  options: Option[]
  values: string[]
  onChange: (vals: string[])=>void
  placeholder?: string
  className?: string
}){
  const { t } = useI18n()
  const resolvedPlaceholder =
    placeholder ?? t('app.controls.select_values', { defaultValue: 'Select values' })
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onDoc(e: MouseEvent){
      if (!rootRef.current) return
      if (!rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase()
    if (!qq) return options
    return options.filter(o => o.label.toLowerCase().includes(qq) || o.value.toLowerCase().includes(qq))
  }, [q, options])

  const chips = options.filter(o => values.includes(o.value))

  function toggle(v: string){
    if (values.includes(v)) onChange(values.filter(x => x !== v))
    else onChange([...values, v])
  }

  return (
    <div ref={rootRef} className={clsx('relative', className)}>
      <button type="button" className="input w-full text-left" onClick={()=>setOpen(o=>!o)}>
        {chips.length === 0 ? <span className="text-slate-500">{resolvedPlaceholder}</span> : (
          <div className="flex flex-wrap gap-1">
            {chips.map(c => (
              <span key={c.value} className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 text-xs">{c.label}</span>
            ))}
          </div>
        )}
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg overflow-hidden">
          <div className="p-2 border-b">
            <input
              autoFocus
              className="w-full px-3 py-2 rounded bg-slate-50 outline-none"
              placeholder={t('app.controls.search_placeholder', { defaultValue: 'Search…' })}
              value={q}
              onChange={e=>setQ(e.target.value)}
            />
          </div>
          <div className="max-h-64 overflow-auto">
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-sm text-slate-500">
                {t('app.controls.no_results', { defaultValue: 'No matches' })}
              </div>
            )}
            {filtered.map(o => {
              const active = values.includes(o.value)
              return (
                <label key={o.value} className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-slate-50">
                  <input type="checkbox" checked={active} onChange={()=>toggle(o.value)} />
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
