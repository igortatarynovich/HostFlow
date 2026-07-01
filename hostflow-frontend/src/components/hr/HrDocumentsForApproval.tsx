import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import HrDocumentVerificationCard from './HrDocumentVerificationCard'
import { useI18n } from '../../i18n'

type Props = {
  documents: HrReviewDocumentRow[]
  employeeId?: string
  handoffId?: string
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

export default function HrDocumentsForApproval({
  documents,
  employeeId,
  handoffId,
  manage = false,
  onPanelUpdated,
}: Props) {
  const { t } = useI18n()
  if (documents.length === 0) return null

  return (
    <section id="hr-review-documents" className="scroll-mt-24 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.hr.review_case.docs_required', { defaultValue: 'Documents required for approval' })}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {t('app.hr.doc_verify.section_hint', {
            defaultValue:
              'Verify each document against profile data. Checklist items update when all required cards are verified.',
          })}
        </p>
      </div>
      {documents.map((d) => (
        <HrDocumentVerificationCard
          key={d.document_key}
          doc={d}
          employeeId={employeeId}
          handoffId={handoffId}
          manage={manage}
          onPanelUpdated={onPanelUpdated}
        />
      ))}
    </section>
  )
}
