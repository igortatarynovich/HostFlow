import { StatusBadge } from '../../../components/ui/StatusBadge'
import type { StatusBadgeSemantic } from '../../../components/ui/statusBadgeSemantics'
import { applicationStatusLabel } from '../../application-workspace/applicationDisplay'
import { useI18n } from '../../../i18n'
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
  const { t } = useI18n()
  if (!application) return null
  const statusKey = application.status
  return (
    <div data-capability-id="status">
      <StatusBadge
        label={applicationStatusLabel(statusKey, t)}
        semantic={STATUS_SEMANTIC[statusKey] ?? 'neutral'}
        shape="pill"
        size="sm"
      />
    </div>
  )
}
