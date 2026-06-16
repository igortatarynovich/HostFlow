import clsx from 'clsx'

type ReadinessItem = {
  id: string
  label: string
  ready: boolean
}

type Props = {
  title: string
  items: ReadinessItem[]
  className?: string
}

export default function ReadinessPanel({ title, items, className }: Props) {
  if (!items.length) return null
  return (
    <section className={clsx('rounded-lg border border-slate-200 bg-white p-3', className)}>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <ul className="mt-2 space-y-1.5 text-sm">
        {items.map((item) => (
          <li key={item.id} className={clsx('flex items-start gap-2', item.ready ? 'text-emerald-800' : 'text-slate-700')}>
            <span className="mt-0.5 text-xs leading-none">{item.ready ? '✓' : '○'}</span>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

