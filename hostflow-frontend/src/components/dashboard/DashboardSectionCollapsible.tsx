import { useCallback, useEffect, useState } from 'react'
import { IconChevronDown } from '@tabler/icons-react'

type Props = {
  /** For deep links, e.g. #lead-conversion */
  id?: string
  storagePrefix: string
  sectionKey: string
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: React.ReactNode
}

function readOpen(prefix: string, key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(`${prefix}:sections`)
    if (!raw) return fallback
    const o = JSON.parse(raw) as Record<string, unknown>
    if (typeof o[key] === 'boolean') return o[key] as boolean
  } catch {
    /* ignore */
  }
  return fallback
}

export function DashboardSectionCollapsible({
  id,
  storagePrefix,
  sectionKey,
  title,
  subtitle,
  defaultOpen = true,
  children,
}: Props) {
  const [open, setOpen] = useState(() => readOpen(storagePrefix, sectionKey, defaultOpen))

  useEffect(() => {
    setOpen(readOpen(storagePrefix, sectionKey, defaultOpen))
  }, [storagePrefix, sectionKey, defaultOpen])

  const persist = useCallback(
    (next: boolean) => {
      setOpen(next)
      try {
        const fullKey = `${storagePrefix}:sections`
        const raw = localStorage.getItem(fullKey)
        const o = raw ? (JSON.parse(raw) as Record<string, boolean>) : {}
        o[sectionKey] = next
        localStorage.setItem(fullKey, JSON.stringify(o))
      } catch {
        /* ignore */
      }
    },
    [storagePrefix, sectionKey],
  )

  return (
    <div id={id} className="mb-4 scroll-mt-4 rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50/80"
        onClick={() => persist(!open)}
        aria-expanded={open}
      >
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-900">{title}</div>
          {subtitle ? <div className="mt-0.5 text-xs text-slate-500">{subtitle}</div> : null}
        </div>
        <IconChevronDown
          size={20}
          className={`shrink-0 text-slate-500 transition-transform ${open ? 'rotate-180' : ''}`}
          stroke={1.8}
        />
      </button>
      {open ? <div className="border-t border-slate-100">{children}</div> : null}
    </div>
  )
}
