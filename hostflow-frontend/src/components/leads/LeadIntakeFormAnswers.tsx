import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import { leadIntakeFormAnswerRows } from '../../utils/leadIntakeFormAnswers'
import { FieldGrid } from '../ui/FieldGrid'

type Props = {
  lead: Lead
  className?: string
}

/** Primary intake Q&A — answers the recruiter must see before deciding. */
export default function LeadIntakeFormAnswers({ lead, className = '' }: Props) {
  const { t } = useI18n()
  const rows = leadIntakeFormAnswerRows(lead)

  return (
    <section className={className} aria-labelledby="intake-form-answers-heading">
      <h2 id="intake-form-answers-heading" className="text-base font-semibold tracking-tight text-slate-900">
        {t('app.leads.intake_workspace.form_answers.title')}
      </h2>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{t('app.leads.intake_workspace.form_answers.empty')}</p>
      ) : (
        <div className="mt-3 rounded-xl bg-white px-4 py-3 ring-1 ring-slate-900/[0.06]">
          <FieldGrid cols={1}>
            {rows.map((row) => (
              <div key={row.name}>
                <div className="text-sm text-slate-500">{row.label}</div>
                <div className="mt-0.5 text-base font-medium text-slate-900">{row.value}</div>
              </div>
            ))}
          </FieldGrid>
        </div>
      )}
    </section>
  )
}
