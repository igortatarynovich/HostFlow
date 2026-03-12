import { useEffect, useMemo, useRef, useState } from 'react'
import clsx from 'clsx'

type Option = { value: string; label: string }

export default function SelectAsync({
  fetcher,                 // (q) => Promise<Option[]>
  value,
  onChange,
  placeholder = '— выбрать —',
  className,
  initialLabel = '',
}:{
  fetcher: (q: string)=>Promise<Option[]>
  value: string | null | undefined
  onChange: (v: string)=>void
  placeholder?: string
  className?: string
  initialLabel?: string
}){
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [opts, setOpts] = useState<Option[]>([])
  const [loading, setLoading] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  // клик вне
  useEffect(() => {
    function onDoc(e: MouseEvent){
      if (!rootRef.current) return
      if (!rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  // загрузка при открытии и поиске
  useEffect(() => {
    let cancelled = false
    async function run(){
      setLoading(true)
      try{
        const data = await fetcher(q)
        if (!cancelled) setOpts(data)
      } finally { if (!cancelled) setLoading(false) }
    }
    if (open) {
      const t = setTimeout(run, 200)
      return () => { cancelled = true; clearTimeout(t) }
    }
  }, [open, q, fetcher])

  const current = useMemo(() => {
    if (value && opts.every(o => o.value !== value) && initialLabel) {
      return { value, label: initialLabel }
    }
    return opts.find(o => o.value === value)
  }, [value, opts, initialLabel])

  return (
    <div ref={rootRef} className={clsx('relative', className)}>
      <button type="button" className="input w-full text-left" onClick={()=>setOpen(o=>!o)}>
        {current?.label || placeholder}
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg overflow-hidden">
          <div className="p-2 border-b">
            <input
              autoFocus
              className="w-full px-3 py-2 rounded bg-slate-50 outline-none"
              placeholder="Поиск…"
              value={q}
              onChange={e=>setQ(e.target.value)}
            />
          </div>
          <div className="max-h-64 overflow-auto">
            {loading && <div className="px-3 py-2 text-sm text-slate-500">Загрузка…</div>}
            {!loading && opts.length === 0 && <div className="px-3 py-2 text-sm text-slate-500">нет совпадений</div>}
            {opts.map(o => (
              <div
                key={o.value}
                className={clsx('px-3 py-2 cursor-pointer hover:bg-slate-50', o.value===value && 'bg-slate-100')}
                onClick={() => { onChange(o.value); setOpen(false); setQ('') }}
              >
                {o.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}