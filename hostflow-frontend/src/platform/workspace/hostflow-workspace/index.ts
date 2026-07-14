import type { RequirementsWorkspaceResponse } from '../../../api/candidateRequirements'

export const WORKSPACE_CONTRACTS_SCHEMA_VERSION = 'workspace_status_v1' as const
export const RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY = 'recruitment.requirements' as const

export type ModuleKey = 'recruitment' | 'sales' | 'documents'
export type WorkspacePermission =
  | 'candidates.view'
  | 'candidates.read'
  | 'candidates.manage'
  | 'candidates.update'

export type WorkspaceSession = {
  context: 'recruitment' | 'sales' | 'documents'
  anchor: {
    anchor_kind: 'candidate' | 'lead' | 'company'
    anchor_id: string
    tenant_id: string
  }
  enabled_modules: ModuleKey[]
}

export type WorkspaceSeverity = 'ok' | 'warn' | 'blocked'

export type WorkspaceBlocker = {
  block_id: string
  label_key: string
  severity: WorkspaceSeverity
}

export type WorkspaceNextAction = {
  action_id: string
  module_key: ModuleKey
  label_key: string
  permission: WorkspacePermission
  priority: number
  handler_kind: 'navigation' | 'command'
  handler_ref: string
}

export type WorkspaceContribution = {
  module_key: ModuleKey
  context: WorkspaceSession['context']
  priority: number
  severity: WorkspaceSeverity
  summary_key: string
  blockers?: WorkspaceBlocker[]
  next_action?: WorkspaceNextAction
}

export type WorkspaceStatusSnapshot = {
  schema_version: typeof WORKSPACE_CONTRACTS_SCHEMA_VERSION
  session: WorkspaceSession
  contributions: WorkspaceContribution[]
  displayed_next_action?: WorkspaceNextAction
  aggregated_severity: WorkspaceSeverity
}

export type WorkspaceSection = {
  capability_key: string
  required_permissions: WorkspacePermission[]
}

export type SectionRegistry = {
  register(section: WorkspaceSection): void
  listSections(session: WorkspaceSession, userPermissions: WorkspacePermission[]): WorkspaceSection[]
}

export function createSectionRegistry(): SectionRegistry {
  const sections: WorkspaceSection[] = []
  return {
    register(section) {
      sections.push(section)
    },
    listSections(_session, userPermissions) {
      return sections.filter((section) =>
        section.required_permissions.every((perm) => userPermissions.includes(perm)),
      )
    },
  }
}

export function registerRecruitmentWorkspaceSectionsP0(registry: SectionRegistry): void {
  registry.register({
    capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
    required_permissions: ['candidates.view'],
  })
}

type RecruitmentReadinessOptions = {
  context: WorkspaceSession['context']
  candidateRequirementsPath: string
}

export function recruitmentReadinessFromWorkspace(
  workspace: RequirementsWorkspaceResponse,
  options: RecruitmentReadinessOptions,
): WorkspaceContribution {
  const blockers =
    workspace.pipeline_blockers?.unfulfilled_requirements?.map((req) => ({
      block_id: `requirement:${req.requirement_code}`,
      label_key: req.public_name || req.requirement_code,
      severity: 'blocked' as const,
    })) ?? []

  const firstCode = workspace.pipeline_blockers?.unfulfilled_requirements?.[0]?.requirement_code
  const nextAction: WorkspaceNextAction | undefined = firstCode
    ? {
        action_id: `close_requirement:${firstCode}`,
        module_key: 'recruitment',
        label_key: 'Upload passport',
        permission: 'candidates.manage',
        priority: 10,
        handler_kind: 'navigation',
        handler_ref: `${options.candidateRequirementsPath}?requirement=${encodeURIComponent(firstCode)}`,
      }
    : undefined

  return {
    module_key: 'recruitment',
    context: options.context,
    priority: 10,
    severity: blockers.length > 0 ? 'blocked' : 'ok',
    summary_key: 'workspace.recruitment.readiness.summary',
    blockers,
    next_action: nextAction,
  }
}

const SEVERITY_RANK: Record<WorkspaceSeverity, number> = {
  ok: 0,
  warn: 1,
  blocked: 2,
}

export async function aggregateWorkspaceStatusFromContributors(
  session: WorkspaceSession,
  contributors: Array<() => WorkspaceContribution | Promise<WorkspaceContribution>>,
  _userPermissions: string[],
): Promise<WorkspaceStatusSnapshot> {
  const contributions: WorkspaceContribution[] = []
  for (const load of contributors) {
    contributions.push(await load())
  }

  let aggregated_severity: WorkspaceSeverity = 'ok'
  for (const contribution of contributions) {
    if (SEVERITY_RANK[contribution.severity] > SEVERITY_RANK[aggregated_severity]) {
      aggregated_severity = contribution.severity
    }
  }

  const displayed_next_action = contributions
    .map((c) => c.next_action)
    .filter((action): action is WorkspaceNextAction => Boolean(action))
    .sort((a, b) => b.priority - a.priority)[0]

  return {
    schema_version: WORKSPACE_CONTRACTS_SCHEMA_VERSION,
    session,
    contributions,
    displayed_next_action,
    aggregated_severity,
  }
}
