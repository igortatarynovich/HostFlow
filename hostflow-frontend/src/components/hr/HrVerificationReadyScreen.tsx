import type { HrReviewPanel } from '../../api/workforce'
import { useI18n } from '../../i18n'
import HrReviewPanelCard from './HrReviewPanel'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
  onReviewDocuments?: () => void
}

export default function HrVerificationReadyScreen({
  panel,
  employeeId,
  handoffId,
  manage,
  onPanelUpdated,
  onReviewDocuments,
}: Props) {
  const { t } = useI18n()
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
        {t('app.hr.ready.all_done_hint', {
          defaultValue: 'All required documents are confirmed. You can approve employment.',
        })}
        {manage && onReviewDocuments ? (
          <div className="mt-2">
            <button type="button" className="btn-secondary btn-xs" onClick={onReviewDocuments}>
              {t('app.hr.ready.review_docs_again', { defaultValue: 'Review documents again' })}
            </button>
          </div>
        ) : null}
      </div>
      <HrReviewPanelCard
        panel={panel}
        manage={manage}
        onUpdated={onPanelUpdated || (() => {})}
        employeeId={employeeId}
        handoffId={handoffId}
        hideDocuments={false}
        caseDecisionMode
      />
    </div>
  )
}

