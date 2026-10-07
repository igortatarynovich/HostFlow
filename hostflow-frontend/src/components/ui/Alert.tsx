import clsx from 'clsx'
import { IconAlertTriangle, IconCircleCheck, IconInfoCircle } from '@tabler/icons-react'
import type { ReactNode } from 'react'

type AlertSemantic = 'success' | 'warning' | 'info' | 'danger'

const SURFACE: Record<AlertSemantic, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-950',
  warning: 'border-amber-200 bg-amber-50 text-amber-950',
  info: 'border-cyan-200 bg-cyan-50 text-cyan-950',
  danger: 'border-rose-200 bg-rose-50 text-rose-950',
}

const ICON: Record<AlertSemantic, typeof IconInfoCircle> = {
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  info: IconInfoCircle,
  danger: IconAlertTriangle,
}

export function Alert({
  semantic,
  title,
  children,
  action,
  className,
}: {
  semantic: AlertSemantic
  title: ReactNode
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  const Icon = ICON[semantic]
  return (
    <div className={clsx('flex flex-wrap items-start gap-3 rounded-lg border px-3 py-3', SURFACE[semantic], className)}>
      <Icon className="mt-0.5 shrink-0" size={18} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{title}</p>
        {children ? <div className="mt-0.5 text-sm opacity-80">{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
