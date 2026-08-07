import { useI18n } from '../../../i18n'
import StageTag from '../../StageTag'
import type { StageMetric } from './pipelineMetrics'

type Props = {
  stages: StageMetric[]
  onStageClick: (stageCode: string) => void
  loading?: boolean
}

export function StageMetricCards({ stages, onStageClick, loading }: Props) {
  const { t } = useI18n()

  if (loading) {
    return (
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 w-28 animate-pulse rounded-lg border border-slate-200 bg-slate-50"
          />
        ))}
      </div>
    )
  }

  if (stages.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        {t('app.vacancies.workspace.no_pipeline_data', { defaultValue: 'Нет данных по воронке' })}
      </p>
    )
  }

  const sortedStages = [...stages].sort((a, b) => b.count - a.count)

  return (
    <div className="flex flex-wrap gap-2">
      {sortedStages.map((stage) => (
        <button
          key={stage.code}
          type="button"
          onClick={() => onStageClick(stage.code)}
          className="flex flex-col items-start gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left transition-colors hover:border-slate-300 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
        >
          <span className="text-xl font-semibold text-slate-900">{stage.count}</span>
          <StageTag code={stage.code} size="sm" />
          <span className="text-xs text-slate-500">
            {t('app.vacancies.workspace.view_list', { defaultValue: 'Посмотреть' })}
          </span>
        </button>
      ))}
    </div>
  )
}

export function CompactStageStrip({
  stages,
  onStageClick,
}: {
  stages: StageMetric[]
  onStageClick: (stageCode: string) => void
}) {
  const { t } = useI18n()
  const sortedStages = [...stages]
    .filter((s) => s.count > 0)
    .sort((a, b) => b.count - a.count)

  if (sortedStages.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2">
      {sortedStages.map((stage) => (
        <button
          key={stage.code}
          type="button"
          onClick={() => onStageClick(stage.code)}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2 py-1 text-sm transition-colors hover:bg-slate-50"
          title={t('app.vacancies.workspace.click_to_filter', {
            defaultValue: 'Нажмите для фильтрации по этапу',
          })}
        >
          <StageTag code={stage.code} size="sm" />
          <span className="min-w-[1.25rem] rounded bg-slate-100 px-1.5 py-0.5 text-center text-xs font-semibold text-slate-700">
            {stage.count}
          </span>
        </button>
      ))}
    </div>
  )
}
