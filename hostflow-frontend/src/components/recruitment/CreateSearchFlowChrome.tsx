import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowLeft } from '@tabler/icons-react'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type CreateSearchFlowChromeProps = {
  step: number
  totalSteps: number
  title: string
  subtitle?: string
  children: ReactNode
  testId?: string
}

export function CreateSearchFlowChrome({
  step,
  totalSteps,
  title,
  subtitle,
  children,
  testId = 'm1-create-search-wizard',
}: CreateSearchFlowChromeProps) {
  return (
    <div className="mx-auto max-w-2xl space-y-4" data-testid={testId}>
      <Link
        to={CRM_APP_PATHS.launchpad}
        className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-brand-700"
      >
        <IconArrowLeft size={14} stroke={1.9} />
        Launchpad
      </Link>

      <section className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-brand-700">Создать подбор</p>
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
    </div>
  )
}
