import { useI18n } from '../../../../i18n'
import type { Vacancy } from '../../../../api/vacancies'

type Props = {
  vacancy: Vacancy & {
    description?: string | null
    location?: string | null
    employment_type?: string | null
    salary_from?: number | string | null
    salary_to?: number | string | null
    currency?: string | null
  }
  companyName?: string | null
}

export function MainInfo({ vacancy, companyName }: Props) {
  const { t } = useI18n()

  const salaryDisplay = (() => {
    const from = vacancy.salary_from
    const to = vacancy.salary_to
    const cur = vacancy.currency || ''
    if (!from && !to) return null
    if (from && to) return `${from} – ${to} ${cur}`.trim()
    if (from) return `от ${from} ${cur}`.trim()
    return `до ${to} ${cur}`.trim()
  })()

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-700">
        {t('app.vacancies.workspace.main_info.title', { defaultValue: 'Информация о позиции' })}
      </h3>

      <div className="space-y-2 text-sm">
        <InfoRow
          label={t('app.vacancies.workspace.main_info.title_field', { defaultValue: 'Должность' })}
          value={vacancy.title}
        />
        {companyName && (
          <InfoRow
            label={t('app.vacancies.workspace.main_info.company', { defaultValue: 'Компания' })}
            value={companyName}
          />
        )}
        {vacancy.location && (
          <InfoRow
            label={t('app.vacancies.workspace.main_info.location', { defaultValue: 'Локация' })}
            value={vacancy.location}
          />
        )}
        {vacancy.employment_type && (
          <InfoRow
            label={t('app.vacancies.workspace.main_info.employment_type', { defaultValue: 'Тип занятости' })}
            value={vacancy.employment_type}
          />
        )}
        {salaryDisplay && (
          <InfoRow
            label={t('app.vacancies.workspace.main_info.salary', { defaultValue: 'Зарплата' })}
            value={salaryDisplay}
          />
        )}
        {vacancy.description && (
          <div className="pt-2">
            <span className="text-xs text-slate-500">
              {t('app.vacancies.workspace.main_info.description', { defaultValue: 'Описание' })}
            </span>
            <p className="mt-1 whitespace-pre-wrap text-slate-700">{vacancy.description}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  if (!value) return null
  return (
    <div className="flex items-baseline gap-2">
      <span className="shrink-0 text-xs text-slate-500">{label}:</span>
      <span className="text-slate-800">{value}</span>
    </div>
  )
}
