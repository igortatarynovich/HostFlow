import { useI18n } from '../../../../i18n'
import type { PipelineMetrics } from '../pipelineMetrics'

type Props = {
  metrics: PipelineMetrics
}

function DonutChart({ value, size = 64 }: { value: number; size?: number }) {
  const strokeWidth = 6
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#e2e8f0"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="transition-all duration-500"
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        className="fill-slate-700 text-xs font-semibold"
      >
        {value}%
      </text>
    </svg>
  )
}

function KpiCard({
  label,
  value,
  subtext,
}: {
  label: string
  value: string | number
  subtext?: string
}) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-lg font-semibold text-slate-900">{value}</span>
      {subtext && <span className="text-xs text-slate-400">{subtext}</span>}
    </div>
  )
}

export function VacancyProgress({ metrics }: Props) {
  const { t } = useI18n()

  const { plan, hired, remaining, completionPct, hireRatePct, total } = metrics

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-4 text-sm font-medium text-slate-700">
        {t('app.vacancies.workspace.vacancy_progress.title', { defaultValue: 'Прогресс вакансии' })}
      </h3>

      <div className="flex items-center gap-6">
        {completionPct != null && <DonutChart value={completionPct} />}

        <div className="grid flex-1 grid-cols-2 gap-4 sm:grid-cols-4">
          <KpiCard
            label={t('app.vacancies.workspace.vacancy_progress.headcount', { defaultValue: 'План' })}
            value={plan ?? '—'}
          />
          <KpiCard
            label={t('app.vacancies.workspace.vacancy_progress.hired', { defaultValue: 'Нанято' })}
            value={hired}
          />
          <KpiCard
            label={t('app.vacancies.workspace.vacancy_progress.remaining', { defaultValue: 'Осталось' })}
            value={remaining ?? '—'}
          />
          <KpiCard
            label={t('app.vacancies.workspace.vacancy_progress.completion', { defaultValue: 'Выполнение' })}
            value={completionPct != null ? `${completionPct}%` : '—'}
          />
        </div>
      </div>

      {hireRatePct != null && (
        <p className="mt-3 text-xs text-slate-500">
          {t('app.vacancies.workspace.vacancy_progress.hire_rate', {
            defaultValue: 'Конверсия: {rate}% ({hired} из {total} кандидатов)',
            values: { rate: hireRatePct, hired, total },
          })}
        </p>
      )}
    </div>
  )
}
