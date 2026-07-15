import { readSalesQuestionnaireSummary, salesQuestionnaireStatusLabel } from '../../utils/salesQuestionnaire'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'

function row(label: string, value: unknown) {
  const text = Array.isArray(value) ? value.filter(Boolean).join(', ') : String(value ?? '').trim()
  if (!text) return null
  return (
    <li key={label} className="flex justify-between gap-3 border-b border-slate-100 pb-2 last:border-0 last:pb-0">
      <span className="text-slate-500">{label}</span>
      <span className="min-w-0 text-right font-medium text-slate-900">{text}</span>
    </li>
  )
}

export default function SalesQuestionnaireSummaryRail({ lead }: { lead: Lead }) {
  const { locale, t } = useI18n()
  const summary = readSalesQuestionnaireSummary(lead)
  const status = salesQuestionnaireStatusLabel(lead, { locale })

  return (
    <section className="space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.sales_questionnaire.title', { defaultValue: 'B2B questionnaire' })}
        </p>
        <p className="mt-1 text-sm font-medium text-slate-900">{status}</p>
      </div>
      <ul className="space-y-2 text-sm text-slate-800">
        {row('Potrzeba', summary.need_type_label || summary.need_type)}
        {row('Cel', summary.primary_outcome_label || summary.goal_label)}
        {row('Budżet', summary.monthly_ad_budget_label || summary.monthly_ad_budget)}
        {row('Start', summary.start_timeline_label || summary.start_timeline)}
        {row('Doświadczenie', summary.prior_ads_experience_label || summary.prior_ads_experience)}
        {row('Materiały', summary.materials_label || summary.materials)}
        {row('Decyzja', summary.decision_maker_label || summary.decision_maker)}
      </ul>
    </section>
  )
}
