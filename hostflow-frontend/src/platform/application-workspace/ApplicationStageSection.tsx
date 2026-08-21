import type { ApplicationStage } from '../../api/applications'
import type { Application } from '../../api/types/application'
import { useI18n } from '../../i18n'
import { APPLICATION_STAGE_ACTIONS, applicationRodoState, applicationStageCode } from './applicationRail'

type Props = {
  application: Application
  disabled?: boolean
  onStage: (stage: ApplicationStage) => void
  onReject: () => void
}

export function ApplicationStageSection({ application, disabled, onStage, onReject }: Props) {
  const { t } = useI18n()
  const current = applicationStageCode(application)
  const terminal = application.status === 'completed' || application.status === 'rejected'
  const rodoOk = applicationRodoState(application).satisfied

  return (
    <div className="flex flex-wrap gap-2" data-testid="recruitment-stage-picker">
      {APPLICATION_STAGE_ACTIONS.map((stage) => {
        const active = current === stage
        const rodoBlocks = stage === 'contacted' && !rodoOk
        const label = t(`app.recruitment_inquiry.stages.${stage}`, {
          defaultValue: stage === 'contacted' ? 'Contacted' : stage === 'qualified' ? 'Qualified' : 'Lost',
        })
        return (
          <button
            key={stage}
            type="button"
            disabled={disabled || terminal || active || rodoBlocks}
            title={
              rodoBlocks
                ? t('app.recruitment_inquiry.errors.LEAD_RODO_REQUIRED', {
                    defaultValue: 'Confirm RODO before this action.',
                  })
                : undefined
            }
            data-testid={`recruitment-stage-${stage}`}
            onClick={() => {
              if (stage === 'lost') onReject()
              else onStage(stage)
            }}
            className={`rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 ${
              active
                ? 'bg-brand-700 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
