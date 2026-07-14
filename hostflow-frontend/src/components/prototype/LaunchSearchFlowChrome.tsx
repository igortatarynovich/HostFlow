import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowLeft, IconSearch } from '@tabler/icons-react'

type LaunchSearchFlowChromeProps = {
  step: number
  totalSteps: number
  title: string
  subtitle?: string
  backTo?: string
  backLabel?: string
  children: ReactNode
  testId?: string
}

export function LaunchSearchFlowChrome({
  step,
  totalSteps,
  title,
  subtitle,
  backTo = '/app/recruitment/searches',
  backLabel = 'К активным поискам',
  children,
  testId = 'launch-search-wizard',
}: LaunchSearchFlowChromeProps) {
  return (
    <div className="mx-auto max-w-2xl space-y-4" data-testid={testId}>
      <Link
        to={backTo}
        className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-brand-700"
      >
        <IconArrowLeft size={14} stroke={1.9} />
        {backLabel}
      </Link>

      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-1 rounded-lg bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
            <IconSearch size={14} stroke={1.9} />
            Запустить поиск
          </div>
          <span className="text-xs text-slate-500">
            Шаг {step} из {totalSteps}
          </span>
        </div>
        <div className="mt-4 flex gap-1">
          {Array.from({ length: totalSteps }, (_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full ${i < step ? 'bg-brand-500' : 'bg-slate-200'}`}
            />
          ))}
        </div>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900">{title}</h1>
        {subtitle ? <p className="mt-2 text-sm text-slate-600">{subtitle}</p> : null}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">{children}</section>

      <p className="text-center text-xs text-slate-400">Прототип · без подключения к серверу</p>
    </div>
  )
}
