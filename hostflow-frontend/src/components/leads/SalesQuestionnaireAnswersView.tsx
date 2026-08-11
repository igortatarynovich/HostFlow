import { useEffect, useState } from 'react'

import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import {
  formLocaleLabel,
  formatSubmittedAt,
  loadGroupedSubmissionAnswersForLead,
  type GroupedSubmissionAnswers,
} from '../../utils/salesQuestionnaireSubmissionDisplay'
import { SalesQuestionnaireAnswerSections } from './SalesQuestionnaireAnswerSections'

type Props = {
  lead: Lead
}

export default function SalesQuestionnaireAnswersView({ lead }: Props) {
  const { t, locale } = useI18n()
  const [grouped, setGrouped] = useState<GroupedSubmissionAnswers | null>(null)
  const [historyIndex, setHistoryIndex] = useState(0)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void loadGroupedSubmissionAnswersForLead(lead, { t, locale, historyIndex })
      .then((next) => {
        if (!cancelled) setGrouped(next)
      })
      .catch(() => {
        if (!cancelled) setGrouped(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lead, locale, t, historyIndex])

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }

  if (!grouped || grouped.sections.length === 0) return null

  const submittedLabel = formatSubmittedAt(grouped.submittedAt, locale)
  const localeLabel = formLocaleLabel(grouped.formLocale, t)
  const metaParts = [
    submittedLabel
      ? t('app.sales_questionnaire.received_at', { defaultValue: 'Received {datetime}',
          values: { datetime: submittedLabel },
        })
      : null,
    localeLabel || null,
  ].filter(Boolean)

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="sales-questionnaire-answers">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.sales_questionnaire.client_info_title', { defaultValue: 'Information from the client' })}
        </h3>
        {metaParts.length > 0 ? <p className="mt-1 text-sm text-slate-600">{metaParts.join(' · ')}</p> : null}
        {grouped.isResubmission && historyIndex === 0 ? (
          <p className="mt-2 inline-flex rounded-md bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-800">
            {t('app.sales_questionnaire.resubmission_badge', { defaultValue: 'Resubmission' })}
          </p>
        ) : null}
      </div>

      <SalesQuestionnaireAnswerSections sections={grouped.sections} />

      {grouped.history.length > 1 ? (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <button
            type="button"
            className="text-sm font-semibold text-brand-700 hover:underline"
            onClick={() => setHistoryOpen((open) => !open)}
          >
            {historyOpen
              ? t('app.sales_questionnaire.history_hide', { defaultValue: 'Hide answer history' })
              : t('app.sales_questionnaire.history_show', { defaultValue: 'Answer history' })}
          </button>
          {historyOpen ? (
            <ul className="mt-2 space-y-1.5">
              {grouped.history.map((item, index) => {
                const label = formatSubmittedAt(item.submitted_at, locale) || `#${grouped.history.length - index}`
                return (
                  <li key={item.submission_id || `${item.submitted_at}-${index}`}>
                    <button
                      type="button"
                      className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${
                        index === historyIndex
                          ? 'bg-brand-50 font-semibold text-brand-800'
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                      onClick={() => setHistoryIndex(index)}
                    >
                      {index === 0
                        ? t('app.sales_questionnaire.history_latest', { defaultValue: 'Latest answer · {datetime}',
                            values: { datetime: label },
                          })
                        : label}
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
