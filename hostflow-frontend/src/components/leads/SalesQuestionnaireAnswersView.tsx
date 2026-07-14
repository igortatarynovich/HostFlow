import { useMemo } from 'react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { buildSalesQuestionnaireAnswerRows } from '../../utils/salesQuestionnaireDisplay'

type Props = {
  lead: Lead
}

export default function SalesQuestionnaireAnswersView({ lead }: Props) {
  const { t, locale } = useI18n()
  const rows = useMemo(() => buildSalesQuestionnaireAnswerRows(lead, t, locale), [lead, locale, t])

  if (rows.length === 0) return null

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="sales-questionnaire-answers">
      <h3 className="text-sm font-semibold text-slate-900">
        {t('app.sales_inquiry.questionnaire_answers_title', { defaultValue: 'Odpowiedzi klienta' })}
      </h3>
      <dl className="mt-3 space-y-2">
        {rows.map((row) => (
          <div key={row.key} className="grid gap-1 border-b border-slate-100 pb-2 last:border-0 last:pb-0 sm:grid-cols-[minmax(0,40%)_1fr] sm:gap-3">
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{row.label}</dt>
            <dd className="text-sm font-medium text-slate-900">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
