import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { leadIntakeFormAnswerRows } from '../../utils/leadIntakeFormAnswers'

type Props = {
  lead: Lead
  className?: string
}

/** Primary intake Q&A — answers the recruiter must see before deciding. */
export default function LeadIntakeFormAnswers({ lead, className = '' }: Props) {
  const { t } = useI18n()
  const rows = leadIntakeFormAnswerRows(lead)

  if (rows.length === 0) {
    return (
      <section className={className} aria-labelledby="intake-form-answers-heading">
        <h2 id="intake-form-answers-heading" className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
          {t('app.leads.intake_workspace.form_answers.title')}
        </h2>
        <p className="mt-2 text-sm text-slate-500">{t('app.leads.intake_workspace.form_answers.empty')}</p>
      </section>
    )
  }

  return (
    <section className={className} aria-labelledby="intake-form-answers-heading">
      <h2 id="intake-form-answers-heading" className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
        {t('app.leads.intake_workspace.form_answers.title')}
      </h2>
      <p className="mt-1 text-[11px] leading-snug text-slate-500">
        {t('app.leads.intake_workspace.form_answers.subtitle')}
      </p>
      <div className="mt-3 overflow-hidden rounded-xl ring-1 ring-slate-900/[0.06]">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2">{t('app.leads.intake_workspace.form_answers.question', { defaultValue: 'Question' })}</th>
              <th className="px-3 py-2">{t('app.leads.intake_workspace.form_answers.answer', { defaultValue: 'Answer' })}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row) => (
              <tr key={row.name}>
                <td className="px-3 py-2.5 align-top text-xs font-medium text-slate-500">{row.label}</td>
                <td className="px-3 py-2.5 align-top font-medium text-slate-900">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
