import { useCallback, useEffect, useState } from 'react'
import type { HrReviewPanel } from '../../api/workforce'
import HrSequentialDocumentVerification from './HrSequentialDocumentVerification'
import HrVerificationReadyScreen from './HrVerificationReadyScreen'
import { isVerificationPlanReady } from './hrVerificationReadySummary'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  candidateId?: string | null
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
  verificationFocus?: { documentKey?: string | null; packCode?: string | null } | null
}

/** Document-centric sequential verification with PR14 ready screen when plan allows approve. */
export default function HrDataVerificationWorkspace(props: Props) {
  const planDocs = props.panel.verification_plan?.documents ?? []
  const legacyDocs = props.panel.documents_for_approval ?? []
  const hasDocs = planDocs.length > 0 || legacyDocs.length > 0
  const planReady = isVerificationPlanReady(props.panel)
  const [reviewAgain, setReviewAgain] = useState(false)

  useEffect(() => {
    if (!planReady) setReviewAgain(false)
  }, [planReady])

  const handlePanelUpdated = useCallback(
    (next: HrReviewPanel) => {
      props.onPanelUpdated?.(next)
      if (isVerificationPlanReady(next)) setReviewAgain(false)
    },
    [props],
  )

  if (!hasDocs && !planReady && (props.panel.data_verification_items?.length ?? 0) === 0) {
    return null
  }

  if (planReady && !reviewAgain) {
    return (
      <HrVerificationReadyScreen
        panel={props.panel}
        employeeId={props.employeeId}
        handoffId={props.handoffId}
        manage={props.manage ?? false}
        onPanelUpdated={handlePanelUpdated}
        onReviewDocuments={() => setReviewAgain(true)}
      />
    )
  }

  return (
    <HrSequentialDocumentVerification
      {...props}
      onPanelUpdated={handlePanelUpdated}
    />
  )
}
