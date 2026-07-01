import clsx from 'clsx'

type BlockerSeverity = 'blocker' | 'warning' | 'info'

type BlockerItem = {
  id: string
  label: string
  severity?: BlockerSeverity
}

type Props = {
  title: string
  items: BlockerItem[]
  className?: string
  severity?: BlockerSeverity
}

function toneClasses(severity: BlockerSeverity): string {
  if (severity === 'warning') return 'border-amber-200 bg-amber-50 text-amber-900'
  if (severity === 'info') return 'border-sky-200 bg-sky-50 text-sky-900'
  return 'border-rose-200 bg-rose-50 text-rose-900'
}

export default function BlockerPanel({ title, items, className, severity = 'blocker' }: Props) {
  if (!items.length) return null
  return (
    <section className={clsx('rounded-lg border p-3', toneClasses(severity), className)}>
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-2 space-y-1 text-sm">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-2">
            <span className="mt-0.5 text-xs leading-none">•</span>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

