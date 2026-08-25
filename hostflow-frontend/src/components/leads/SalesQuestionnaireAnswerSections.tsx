import type { ReactNode } from 'react'
import type { SubmissionAnswerRow, SubmissionAnswerSection } from '../../utils/salesQuestionnaireSubmissionDisplay'

function AnswerValue({ row }: { row: SubmissionAnswerRow }) {
  if (row.kind === 'chips' && row.chips && row.chips.length > 0) {
    return (
      <div className="flex flex-wrap justify-end gap-1.5">
        {row.chips.map((chip) => (
          <span
            key={`${row.qualifiedCode}-${chip}`}
            className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-800"
          >
            {chip}
          </span>
        ))}
      </div>
    )
  }

  if (row.kind === 'phone' && row.href) {
    return (
      <a href={row.href} className="font-medium text-brand-700 hover:underline">
        {row.value}
      </a>
    )
  }

  if (row.kind === 'email' && row.href) {
    return (
      <a href={row.href} className="break-all font-medium text-brand-700 hover:underline">
        {row.value}
      </a>
    )
  }

  if (row.kind === 'long_text') {
    return <p className="whitespace-pre-wrap text-left text-sm font-medium leading-relaxed text-slate-900">{row.value}</p>
  }

  return <span className="font-medium text-slate-900">{row.value}</span>
}

export function SalesQuestionnaireAnswerRowView({ row }: { row: SubmissionAnswerRow }) {
  return (
    <li
      className={`grid gap-1 border-b border-slate-100 py-2.5 last:border-0 last:pb-0 sm:grid-cols-[minmax(0,42%)_1fr] sm:gap-3 ${
        row.changed ? 'rounded-md bg-amber-50/70 px-2 -mx-2' : ''
      }`}
      data-testid={`sales-questionnaire-answer-${row.qualifiedCode}`}
    >
      <div className="flex items-start gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{row.label}</span>
        {row.changed ? (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
            ✦
          </span>
        ) : null}
      </div>
      <div className={row.kind === 'long_text' ? 'sm:text-left' : 'sm:text-right'}>
        <AnswerValue row={row} />
      </div>
    </li>
  )
}

export function SalesQuestionnaireAnswerSections({
  sections,
  empty,
}: {
  sections: SubmissionAnswerSection[]
  empty?: ReactNode
}) {
  if (sections.length === 0) return <>{empty}</>

  return (
    <div className="space-y-5" data-testid="sales-questionnaire-answer-sections">
      {sections.map((section) => (
        <section key={section.key} data-testid={`sales-questionnaire-section-${section.key}`}>
          <h3 className="mb-1 text-sm font-semibold text-slate-900">{section.title}</h3>
          <ul className="text-sm text-slate-800">
            {section.rows.map((row) => (
              <SalesQuestionnaireAnswerRowView key={row.qualifiedCode} row={row} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
