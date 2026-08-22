import type { Application } from '../../api/types/application'

export type RecruitmentApplicationStage = 'contacted' | 'qualified' | 'lost'

/**
 * Host context passed into every bound renderer.
 * Semantic owners keep their own APIs; the host does not own notes/consent.
 */
export type WorkspaceCapabilityRenderContext = {
  application: Application
  patching: boolean
  onClose: () => void
  onRefresh: () => void
  onStage: (stage: RecruitmentApplicationStage) => void | Promise<void>
}
