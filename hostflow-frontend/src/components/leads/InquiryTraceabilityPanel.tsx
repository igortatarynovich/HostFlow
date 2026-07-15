import { Link } from 'react-router-dom'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import {
  clientCompanyPath,
  inquiryQuestionnaireFormPath,
  inquiryRequiresReview,
  inquiryReviewMessage,
} from '../../utils/inquiryTraceability'

type Props = {
  lead: Lead
}

export function InquiryTraceabilityPanel({ lead }: Props) {
  const { t } = useI18n()
  const convertedId = String(lead.converted_client_id || '').trim()
  const formPath = inquiryQuestionnaireFormPath(lead)
  const needsReview = inquiryRequiresReview(lead)

  if (!convertedId && !formPath && !needsReview) return null

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-4"
      data-testid="inquiry-traceability-panel"
    >
      {needsReview ? (
        <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {inquiryReviewMessage(lead)}
        </p>
      ) : null}

      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.sales_inquiry.traceability_title', { defaultValue: 'Связанные записи' })}
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {convertedId ? (
          <Link to={clientCompanyPath(convertedId)} className="btn-secondary btn-sm">
            {t('app.sales_inquiry.open_client', { defaultValue: 'Открыть клиента' })}
          </Link>
        ) : null}
        {formPath ? (
          <Link to={formPath} className="btn-secondary btn-sm">
            {t('app.sales_inquiry.open_questionnaire', { defaultValue: 'Открыть анкету' })}
          </Link>
        ) : null}
      </div>
    </section>
  )
}
