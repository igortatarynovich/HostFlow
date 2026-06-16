import type { HrReviewPanel } from '../../api/workforce'
import HrSequentialDocumentVerification from './HrSequentialDocumentVerification'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

/** Document-centric sequential verification (replaces field-by-field table). */
export default function HrDataVerificationWorkspace(props: Props) {
  const planDocs = props.panel.verification_plan?.documents ?? []
  const legacyDocs = props.panel.documents_for_approval ?? []
  const hasDocs = planDocs.length > 0 || legacyDocs.length > 0
  const planReady = props.panel.verification_plan?.can_approve === true
  if (!hasDocs && !planReady && (props.panel.data_verification_items?.length ?? 0) === 0) {
    return null
  }
  return <HrSequentialDocumentVerification {...props} />
}
