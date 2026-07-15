import { useEffect, useMemo, useState } from 'react'
import { getEntityProfileFields } from '../../api/intakeForms'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import type { FieldOption } from '../../utils/serviceSalesFieldOptions'
import {
  buildAnswerRowsFromLead,
  latestSubmission,
  listSubmissions,
  submissionSourceLabel,
} from '../../utils/salesQuestionnaireSubmissions'
import { salesQuestionnaireStatusLabel } from '../../utils/salesQuestionnaire'

const TARGETED_ADVERTISING_PROFILE = 'service_sales.targeted_advertising'

type Props = {
  lead: Lead
}

function formatWhen(iso: string | undefined, locale: string): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(locale === 'pl' ? 'pl-PL' : locale === 'en' ? 'en-US' : 'ru-RU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function SalesQuestionnaireAnswersPanel({ lead }: Props) {
  const { locale, t } = useI18n()
  const [optionsByCode, setOptionsByCode] = useState<Record<string, FieldOption[]>>({})

  useEffect(() => {
    let cancelled = false
    void getEntityProfileFields(TARGETED_ADVERTISING_PROFILE)
      .then((profile) => {
        if (cancelled) return
        const map: Record<string, FieldOption[]> = {}
        for (const field of profile.fields) {
          if (field.options?.length) map[field.qualified_code] = field.options
        }
        setOptionsByCode(map)
      })
      .catch(() => {
        if (!cancelled) setOptionsByCode({})
      })
    return () => {
      cancelled = true
    }
  }, [])

  const rows = useMemo(() => buildAnswerRowsFromLead(lead, optionsByCode), [lead, optionsByCode])
  const submissions = useMemo(() => listSubmissions(lead), [lead])
  const latest = useMemo(() => latestSubmission(lead), [lead])
  const status = salesQuestionnaireStatusLabel(lead, { locale })

  if (rows.length === 0 && submissions.length === 0) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-questionnaire-answers-empty">
        {t('app.sales_questionnaire.answers_empty', { defaultValue: 'Клиент ещё не ответил на вопросы.' })}
      </p>
    )
  }

  return (
    <div className="space-y-4" data-testid="sales-questionnaire-answers-panel">
      <div>
        <p className="text-sm font-medium text-slate-900">{status}</p>
        {latest ? (
          <p className="mt-1 text-xs text-slate-500">
            {submissionSourceLabel(latest)} · {formatWhen(latest.submitted_at, locale)}
          </p>
        ) : null}
      </div>

      {rows.length > 0 ? (
        <ul className="space-y-2 text-sm text-slate-800">
          {rows.map((row) => (
            <li
              key={row.qualifiedCode}
              className="flex justify-between gap-3 border-b border-slate-100 pb-2 last:border-0 last:pb-0"
              data-testid={`sales-questionnaire-answer-${row.qualifiedCode}`}
            >
              <span className="text-slate-500">{row.label}</span>
              <span className="min-w-0 text-right font-medium text-slate-900">{row.value}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {submissions.length > 1 ? (
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.sales_questionnaire.history_title', { defaultValue: 'История заполнений' })}
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-600">
            {submissions.map((submission, index) => (
              <li key={submission.submission_id || index}>
                #{index + 1} · {submissionSourceLabel(submission)} · {formatWhen(submission.submitted_at, locale)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
