import { useEffect, useState } from 'react'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import {
  formLocaleLabel,
  formatSubmittedAt,
  loadGroupedSubmissionAnswersForLead,
  type GroupedSubmissionAnswers,
} from '../../utils/salesQuestionnaireSubmissionDisplay'
import { salesQuestionnaireStatusLabel } from '../../utils/salesQuestionnaire'
import { SalesQuestionnaireAnswerSections } from './SalesQuestionnaireAnswerSections'

export default function SalesQuestionnaireSummaryRail({ lead }: { lead: Lead }) {
  const { locale, t } = useI18n()
  const status = salesQuestionnaireStatusLabel(lead, { t, locale })
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

  const submittedLabel = formatSubmittedAt(grouped?.submittedAt, locale)
  const localeLabel = formLocaleLabel(grouped?.formLocale || null, t)
  const metaParts = [
    submittedLabel
      ? t('app.sales_questionnaire.received_at', { defaultValue: 'Received {datetime}',
          values: { datetime: submittedLabel },
        })
      : null,
    localeLabel || null,
  ].filter(Boolean)

  return (
    <section className="space-y-4" data-testid="sales-questionnaire-summary-rail">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_questionnaire.client_info_title', { defaultValue: 'Information from the client' })}
        </p>
        {metaParts.length > 0 ? (
          <p className="mt-1 text-sm text-slate-600">{metaParts.join(' · ')}</p>
        ) : (
          <p className="mt-1 text-sm font-medium text-slate-900">{status}</p>
        )}
        {grouped?.isResubmission && historyIndex === 0 ? (
          <p className="mt-2 inline-flex rounded-md bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-800">
            {t('app.sales_questionnaire.resubmission_badge', { defaultValue: 'Resubmission' })}
          </p>
        ) : null}
        {historyIndex > 0 ? (
          <p className="mt-2 text-xs font-medium text-amber-800">
            {t('app.sales_questionnaire.history_viewing', { defaultValue: 'Viewing a previous submission',
            })}
          </p>
        ) : null}
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      ) : (
        <SalesQuestionnaireAnswerSections
          sections={grouped?.sections || []}
          empty={
            <p className="text-sm text-slate-500">
              {t('app.sales_questionnaire.answers_empty', { defaultValue: 'No questionnaire answers yet.' })}
            </p>
          }
        />
      )}

      {(grouped?.history.length || 0) > 1 ? (
        <div className="border-t border-slate-100 pt-3">
          <button
            type="button"
            className="text-sm font-semibold text-brand-700 hover:underline"
            onClick={() => setHistoryOpen((open) => !open)}
            data-testid="sales-questionnaire-history-toggle"
          >
            {historyOpen
              ? t('app.sales_questionnaire.history_hide', { defaultValue: 'Hide answer history' })
              : t('app.sales_questionnaire.history_show', { defaultValue: 'Answer history' })}
          </button>
          {historyOpen ? (
            <ul className="mt-2 space-y-1.5" data-testid="sales-questionnaire-history-list">
              {grouped!.history.map((item, index) => {
                const label = formatSubmittedAt(item.submitted_at, locale) || `#${grouped!.history.length - index}`
                const active = index === historyIndex
                return (
                  <li key={item.submission_id || `${item.submitted_at}-${index}`}>
                    <button
                      type="button"
                      className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${
                        active ? 'bg-brand-50 font-semibold text-brand-800' : 'text-slate-700 hover:bg-slate-50'
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
