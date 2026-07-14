import type { RequirementsWorkspaceResponse } from '../../api/candidateRequirements'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  aggregateWorkspaceStatusFromContributors,
  createSectionRegistry,
  recruitmentReadinessFromWorkspace,
  registerRecruitmentWorkspaceSectionsP0,
  type ModuleKey,
  type WorkspaceSession,
  type WorkspaceStatusSnapshot,
} from '@hostflow/workspace'

let sectionRegistrySingleton: ReturnType<typeof createSectionRegistry> | null = null

export function getWorkspaceSectionRegistry() {
  if (!sectionRegistrySingleton) {
    sectionRegistrySingleton = createSectionRegistry()
    registerRecruitmentWorkspaceSectionsP0(sectionRegistrySingleton)
  }
  return sectionRegistrySingleton
}

export function buildCandidateRecruitmentSession(
  candidateId: string,
  tenantId: string,
  enabledModules: ModuleKey[] = ['recruitment'],
): WorkspaceSession {
  return {
    context: 'recruitment',
    anchor: {
      anchor_kind: 'candidate',
      anchor_id: candidateId,
      tenant_id: tenantId,
    },
    enabled_modules: enabledModules,
  }
}

export async function aggregateRecruitmentRequirementsStatus(
  workspace: RequirementsWorkspaceResponse,
  session: WorkspaceSession,
  userPermissions: string[],
): Promise<WorkspaceStatusSnapshot> {
  const requirementsPath = `${CRM_APP_PATHS.candidates}/${encodeURIComponent(workspace.candidate_id)}/requirements`
  const contribution = recruitmentReadinessFromWorkspace(workspace, {
    context: 'recruitment',
    candidateRequirementsPath: requirementsPath,
  })

  return aggregateWorkspaceStatusFromContributors(
    session,
    [async () => contribution],
    userPermissions,
  )
}
