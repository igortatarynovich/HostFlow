import { StatusBadge } from '../../../components/ui/StatusBadge'
import type { StatusBadgeSemantic } from '../../../components/ui/statusBadgeSemantics'
import { APPLICATION_STATUS_TEXT } from '../../application-workspace/applicationDisplay'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

const STATUS_SEMANTIC: Record<string, StatusBadgeSemantic> = {
  new: 'success',
  in_progress: 'warning',
  waiting: 'info',
  questionnaire_submitted: 'brand',
  completed: 'neutral',
  rejected: 'danger',
}

export function StatusCapability({ application }: WorkspaceCapabilityRenderContext) {
  const statusKey = application.status
  return (
    <div data-capability-id="status">
      <StatusBadge
        label={APPLICATION_STATUS_TEXT[statusKey]}
        semantic={STATUS_SEMANTIC[statusKey] ?? 'neutral'}
        shape="pill"
        size="sm"
      />
    </div>
  )
}
