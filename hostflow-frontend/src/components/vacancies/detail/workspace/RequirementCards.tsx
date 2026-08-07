import { useI18n } from '../../../../i18n'
import type { CriteriaSummary } from '../criteriaForm'

type Props = {
  summary: CriteriaSummary
}

function RequirementCard({
  title,
  items,
  emptyText,
}: {
  title: string
  items: { label: string; value: string | number }[]
  emptyText: string
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <h4 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">{title}</h4>
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">{emptyText}</p>
      ) : (
        <ul className="space-y-1">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-center justify-between text-sm">
              <span className="text-slate-600">{item.label}</span>
              <span className="font-medium text-slate-800">{item.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function RequirementCards({ summary }: Props) {
  const { t } = useI18n()

  const mandatoryItems: { label: string; value: string | number }[] = []
  const preferredItems: { label: string; value: string | number }[] = []

  if (summary.mandatoryDocsCount > 0) {
    mandatoryItems.push({
      label: t('app.vacancies.workspace.requirements.docs', { defaultValue: 'Документы' }),
      value: summary.mandatoryDocsCount,
    })
  }
  if (summary.mandatoryGeoCount > 0) {
    mandatoryItems.push({
      label: t('app.vacancies.workspace.requirements.geo', { defaultValue: 'Страны' }),
      value: summary.mandatoryGeoCount,
    })
  }
  if (summary.minExperience != null) {
    mandatoryItems.push({
      label: t('app.vacancies.workspace.requirements.experience', { defaultValue: 'Мин. опыт (лет)' }),
      value: summary.minExperience,
    })
  }

  if (summary.preferredDocsCount > 0) {
    preferredItems.push({
      label: t('app.vacancies.workspace.requirements.docs', { defaultValue: 'Документы' }),
      value: summary.preferredDocsCount,
    })
  }
  if (summary.preferredGeoCount > 0) {
    preferredItems.push({
      label: t('app.vacancies.workspace.requirements.geo', { defaultValue: 'Страны' }),
      value: summary.preferredGeoCount,
    })
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <RequirementCard
        title={t('app.vacancies.workspace.requirements.mandatory', { defaultValue: 'Обязательно' })}
        items={mandatoryItems}
        emptyText={t('app.vacancies.workspace.requirements.none', { defaultValue: 'Не указано' })}
      />
      <RequirementCard
        title={t('app.vacancies.workspace.requirements.preferred', { defaultValue: 'Предпочтительно' })}
        items={preferredItems}
        emptyText={t('app.vacancies.workspace.requirements.none', { defaultValue: 'Не указано' })}
      />
    </div>
  )
}
