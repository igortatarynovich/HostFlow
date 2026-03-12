import { useState } from 'react'
import { useI18n } from '../../i18n'

type Props = {
  title: string
  description?: string
  children: React.ReactNode
  collapsible?: boolean
  defaultOpen?: boolean
}

export function SectionCard({ title, description, children, collapsible = false, defaultOpen = true }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const { t } = useI18n()
  const toggle = () => {
    if (!collapsible) return
    setOpen((prev) => !prev)
  }
  return (
    <section className="card p-4">
      <header className="flex flex-col gap-1 pb-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
          {description && <p className="text-sm text-slate-500">{description}</p>}
        </div>
        {collapsible && (
          <button
            type="button"
            onClick={toggle}
            className="text-sm font-medium text-brand-600 hover:text-brand-500"
            aria-expanded={open}
          >
            {open ? '−' : '+'} {open ? t('common.actions.collapse') : t('common.actions.expand')}
          </button>
        )}
      </header>
      {(!collapsible || open) && <div className="space-y-4">{children}</div>}
    </section>
  )
}
