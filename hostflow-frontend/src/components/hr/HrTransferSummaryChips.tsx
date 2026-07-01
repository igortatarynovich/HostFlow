import { useI18n } from '../../i18n'
import { humanizeToken } from './hrEmployeeUiFormat'

export type HrTransferSummary = {
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  phone?: string | null
  citizenship?: string | null
  work_country?: string | null
  position_category?: string | null
  vacancy_title?: string | null
  documents_count?: number | null
}

type Props = {
  summary?: HrTransferSummary | null
  className?: string
}

export function HrTransferSummaryChips({ summary, className }: Props) {
  const { t } = useI18n()
  if (!summary) return null

  const chips: string[] = []
  const name = [summary.first_name, summary.last_name].filter(Boolean).join(' ').trim()
  if (name) chips.push(name)
  if (summary.position_category) chips.push(humanizeToken(String(summary.position_category)))
  if (summary.vacancy_title) chips.push(String(summary.vacancy_title))
  if (summary.citizenship) {
    chips.push(
      t('app.hr.transfer.citizenship', {
        defaultValue: 'Citizenship: {value}',
        values: { value: String(summary.citizenship) },
      }),
    )
  }
  if (summary.work_country) {
    chips.push(
      t('app.hr.transfer.work_country', {
        defaultValue: 'Work country: {value}',
        values: { value: String(summary.work_country) },
      }),
    )
  }
  if (typeof summary.documents_count === 'number' && summary.documents_count > 0) {
    chips.push(
      t('app.hr.transfer.docs_count', {
        defaultValue: '{n} docs from recruitment',
        values: { n: summary.documents_count },
      }),
    )
  }

  if (!chips.length) return null

  return (
    <div className={className}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {t('app.hr.transfer.from_recruitment', { defaultValue: 'From recruitment' })}
      </p>
      <div className="mt-1 flex flex-wrap gap-1">
        {chips.map((chip) => (
          <span key={chip} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-700">
            {chip}
          </span>
        ))}
      </div>
    </div>
  )
}
