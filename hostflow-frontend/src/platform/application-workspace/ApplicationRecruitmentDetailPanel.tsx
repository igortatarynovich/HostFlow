import { ApplicationWorkspaceCapabilityHost } from '../workspace-capability/ApplicationWorkspaceCapabilityHost'
import { RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS } from '../workspace-capability/proof'
import type { Application } from '../../api/types/application'

export type ApplicationRecruitmentDetailPanelProps = {
  application: Application
  patching: boolean
  onClose: () => void
  onRefresh: () => void
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
}

/**
 * Recruitment Application proof bind. Host places kit contributions.
 * This file must not compose vacancy/assignee/notes/consent locally.
 */
export function ApplicationRecruitmentDetailPanel({
  application,
  patching,
  onClose,
  onRefresh,
  onStage,
}: ApplicationRecruitmentDetailPanelProps) {
  return (
    <ApplicationWorkspaceCapabilityHost
      application={application}
      patching={patching}
      onClose={onClose}
      onRefresh={onRefresh}
      onStage={onStage}
      contributions={RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS}
    />
  )
}
