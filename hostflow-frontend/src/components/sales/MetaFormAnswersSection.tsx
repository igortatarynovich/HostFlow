import { useI18n } from '../../i18n'

export type MetaFormAnswerRow = {
  name?: unknown
  values?: unknown
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

function formatValues(values: unknown): string {
  if (Array.isArray(values)) {
    return values.map((v) => text(v)).filter(Boolean).join(', ')
  }
  return text(values)
}

export type MetaFormAnswersSectionProps = {
  answers?: unknown
  additionalAnswers?: unknown
}

/** Meta Lead Ads Q&A on the Sales inquiry card — never drop unmapped answers. */
export function MetaFormAnswersSection({ answers, additionalAnswers }: MetaFormAnswersSectionProps) {
  const { t } = useI18n()
  const rows = Array.isArray(answers) ? (answers as MetaFormAnswerRow[]) : []
  const additionalNames = new Set(
    (Array.isArray(additionalAnswers) ? (additionalAnswers as MetaFormAnswerRow[]) : [])
      .map((row) => text(row.name).toLowerCase())
      .filter(Boolean),
  )

  if (rows.length === 0) return null

  return (
    <section className="space-y-2" data-testid="sales-meta-form-answers">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.sales_inquiry.meta_form_answers', { defaultValue: 'Ответы из формы Meta' })}
      </h3>
      <dl className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3">
        {rows.map((row, idx) => {
          const name = text(row.name) || `Field ${idx + 1}`
          const isAdditional = additionalNames.has(name.toLowerCase())
          return (
            <div key={`${name}-${idx}`} className="min-w-0">
              <dt className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-slate-500">
                <span>{name}</span>
                {isAdditional ? (
                  <span className="rounded bg-amber-100 px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                    {t('app.sales_inquiry.additional_answer', { defaultValue: 'доп.' })}
                  </span>
                ) : null}
              </dt>
              <dd className="mt-0.5 break-words text-sm text-slate-900">{formatValues(row.values) || '—'}</dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
