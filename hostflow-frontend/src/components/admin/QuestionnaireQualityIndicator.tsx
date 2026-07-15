import { useI18n } from '../../i18n'
import { questionnaireQuality } from '../../utils/questionnaireQuality'

type Props = {
  questionCount: number
}

export function QuestionnaireQualityIndicator({ questionCount }: Props) {
  const { t } = useI18n()
  const quality = questionnaireQuality(questionCount)

  const tone =
    quality.band === 'optimal'
      ? 'border-emerald-200 bg-emerald-50/80 text-emerald-900'
      : quality.band === 'long'
        ? 'border-amber-200 bg-amber-50/80 text-amber-900'
        : 'border-rose-200 bg-rose-50/80 text-rose-900'

  const icon = quality.band === 'optimal' ? '🟢' : quality.band === 'long' ? '🟡' : '🔴'

  const message =
    quality.band === 'optimal'
      ? t('admin.questionnaire.quality.optimal', {
          defaultValue: '{{count}} вопросов — оптимально',
          values: { count: quality.count },
        })
      : quality.band === 'long'
        ? t('admin.questionnaire.quality.long', {
            defaultValue: '{{count}} вопросов — длинная анкета',
            values: { count: quality.count },
          })
        : t('admin.questionnaire.quality.risky', {
            defaultValue: '{{count}} вопросов — возможна низкая конверсия',
            values: { count: quality.count },
          })

  if (questionCount <= 0) return null

  return (
    <p
      className={`rounded-xl border px-3 py-2 text-sm font-medium ${tone}`}
      data-testid="questionnaire-quality-indicator"
    >
      <span aria-hidden="true">{icon} </span>
      {message}
    </p>
  )
}
