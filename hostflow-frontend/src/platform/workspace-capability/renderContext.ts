import type { Application } from '../../api/types/application'
import type { WorkspaceCapabilityHostId } from './hosts'

export type RecruitmentApplicationStage = 'contacted' | 'qualified' | 'lost'

/** Converted object on Entity Workspace. Not an Application. */
export type WorkspaceEntityRef = {
  resourceType: string
  resourceId: string
}

/**
 * Host context passed into every bound renderer.
 * Semantic owners keep their own APIs; the host does not own notes/consent.
 * `application` is Application Workspace only. Entity host passes `entity`.
 */
export type WorkspaceCapabilityRenderContext = {
  host?: WorkspaceCapabilityHostId
  application?: Application
  entity?: WorkspaceEntityRef
  patching: boolean
  onClose: () => void
  onRefresh: () => void
  onStage?: (stage: RecruitmentApplicationStage) => void | Promise<void>
}
