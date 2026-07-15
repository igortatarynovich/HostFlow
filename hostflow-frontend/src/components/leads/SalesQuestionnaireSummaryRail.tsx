import { useEffect, useState } from 'react'
import { salesQuestionnaireStatusLabel } from '../../utils/salesQuestionnaire'
import { loadSubmissionAnswerRowsForLead, type SubmissionAnswerRow } from '../../utils/salesQuestionnaireSubmissionDisplay'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'

function AnswerRow({ row }: { row: SubmissionAnswerRow }) {
  return (
    <li
      className="flex justify-between gap-3 border-b border-slate-100 pb-2 last:border-0 last:pb-0"
      data-testid={`sales-questionnaire-answer-${row.qualifiedCode}`}
    >
      <span className="text-slate-500">{row.label}</span>
      <span className="min-w-0 text-right font-medium text-slate-900">{row.value}</span>
    </li>
  )
}

export default function SalesQuestionnaireSummaryRail({ lead }: { lead: Lead }) {
  const { locale, t } = useI18n()
  const status = salesQuestionnaireStatusLabel(lead, { locale })
  const [rows, setRows] = useState<SubmissionAnswerRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void loadSubmissionAnswerRowsForLead(lead, { t, locale })
      .then((nextRows) => {
        if (!cancelled) setRows(nextRows)
      })
      .catch(() => {
        if (!cancelled) setRows([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lead, locale, t])

  return (
    <section className="space-y-3" data-testid="sales-questionnaire-summary-rail">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_questionnaire.answers_title', { defaultValue: 'Questionnaire answers' })}
        </p>
        <p className="mt-1 text-sm font-medium text-slate-900">{status}</p>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-slate-500">
          {t('app.sales_questionnaire.answers_empty', { defaultValue: 'No questionnaire answers yet.' })}
        </p>
      ) : (
        <ul className="space-y-2 text-sm text-slate-800">
          {rows.map((row) => (
            <AnswerRow key={row.qualifiedCode} row={row} />
          ))}
        </ul>
      )}
    </section>
  )
}
