import { useI18n } from '../../i18n'
import { formAnswerRowsFromSources } from '../../utils/formAnswerRows'

export type MetaFormAnswersSectionProps = {
  answers?: unknown
  additionalAnswers?: unknown
  labels?: unknown
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function canonicalName(name: string): string {
  return name.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

/** Candidate/client answers from Meta. Ads attribution (campaign, adset, platform) is not shown. */
export function MetaFormAnswersSection({ answers, additionalAnswers, labels }: MetaFormAnswersSectionProps) {
  const { t } = useI18n()
  const rows = formAnswerRowsFromSources({
    fieldAnswers: answers,
    additionalAnswers,
    labels,
  })
  const additionalNames = new Set(
    (Array.isArray(additionalAnswers) ? additionalAnswers : [])
      .map((row) => canonicalName(text((row as { name?: unknown }).name)))
      .filter(Boolean),
  )

  if (rows.length === 0) return null

  return (
    <section className="space-y-2" data-testid="sales-meta-form-answers">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.sales_inquiry.meta_form_answers', { defaultValue: 'Ответы из формы Meta' })}
      </h3>
      <dl className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3">
        {rows.map((row) => {
          const isAdditional = additionalNames.has(canonicalName(row.name))
          return (
            <div key={row.name} className="min-w-0">
              <dt className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-slate-500">
                <span>{row.label}</span>
                {isAdditional ? (
                  <span className="rounded bg-amber-100 px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                    {t('app.sales_inquiry.additional_answer', { defaultValue: 'доп.' })}
                  </span>
                ) : null}
              </dt>
              <dd className="mt-0.5 break-words text-sm text-slate-900">{row.value || '—'}</dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
