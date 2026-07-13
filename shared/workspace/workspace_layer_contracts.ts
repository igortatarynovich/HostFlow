/**
 * HostFlow Workspace Layer — platform contracts (P0).
 *
 * Pure types only. No React. No UI. No domain business logic.
 *
 * Canon: docs/specs/platform/workspace-layer-contracts-p0.md
 * ADR:   docs/specs/architecture/ADR-017-workspace-layer.md
 */

/** Bump when breaking contract changes (ADR + doc update required). */
export const WORKSPACE_CONTRACTS_SCHEMA_VERSION = 1 as const

export type WorkspaceContractsSchemaVersion = typeof WORKSPACE_CONTRACTS_SCHEMA_VERSION

/** ADR-004 product module keys relevant to workspace. */
export type ModuleKey =
  | 'recruitment'
  | 'hr'
  | 'fleet'
  | 'services'
  | 'finance'

/**
 * User work context — not entity type.
 * @see ADR-017 §3
 */
export type WorkspaceContextKey =
  | 'intake'
  | 'recruitment'
  | 'hr'
  | 'hr_active'
  | 'fleet'
  | 'finance'
  | 'services'
  | 'company'
  | 'vehicle'
  | 'vacancy'
  | 'client'

/**
 * Stable capability id for section renderer registry.
 * Format: `{module}.{capability}`
 */
export type WorkspaceCapabilityKey = string

/** RBAC atom — enforce remains in module API. */
export type WorkspacePermission = string

/** Workspace Status rail severity — display category, not domain status. */
export type WorkspaceStatusSeverity =
  | 'ready'
  | 'blocked'
  | 'warning'
  | 'not_applicable'
  | 'info'

export type WorkspaceHandlerKind = 'api' | 'navigation' | 'custom'

export type WorkspaceAnchorKind =
  | 'lead'
  | 'candidate'
  | 'workforce_employee'
  | 'company'
  | 'vehicle'
  | 'vacancy'

export interface WorkspaceAnchor {
  anchor_kind: WorkspaceAnchorKind
  anchor_id: string
  tenant_id: string
  own_company_id?: string
}

export interface WorkspaceSession {
  context: WorkspaceContextKey
  anchor: WorkspaceAnchor
  enabled_modules: ModuleKey[]
}

export interface ActionDeclaration {
  action_id: string
  label_key: string
  permission: WorkspacePermission
  handler_kind: WorkspaceHandlerKind
  handler_ref: string
}

/**
 * Module declares a navigable section — not a screen.
 */
export interface SectionDeclaration {
  section_id: string
  module_key: ModuleKey
  capability_key: WorkspaceCapabilityKey
  label_key: string
  icon?: string
  order: number
  contexts: WorkspaceContextKey[]
  permissions: WorkspacePermission[]
  /** When true, module may attach ReadinessContribution for this section. */
  readiness_contribution?: boolean
  actions?: ActionDeclaration[]
}

export interface ReadinessBlock {
  block_id: string
  label_key: string
  severity: WorkspaceStatusSeverity
  capability_key?: WorkspaceCapabilityKey
  section_id?: string
}

/**
 * Module-owned readiness signal for Workspace Status aggregation.
 */
export interface ReadinessContribution {
  module_key: ModuleKey
  context: WorkspaceContextKey
  priority: number
  severity: WorkspaceStatusSeverity
  summary_key: string
  blockers?: ReadinessBlock[]
  next_action?: NextActionDeclaration | null
}

/**
 * Module decides next action; Workspace displays by display policy only.
 */
export interface NextActionDeclaration {
  action_id: string
  module_key: ModuleKey
  label_key: string
  permission: WorkspacePermission
  priority: number
  capability_key?: WorkspaceCapabilityKey
  section_id?: string
  handler_kind: WorkspaceHandlerKind
  handler_ref: string
}

/** Output of platform status aggregation (step 3). */
export interface WorkspaceStatusSnapshot {
  schema_version: WorkspaceContractsSchemaVersion
  session: WorkspaceSession
  contributions: ReadinessContribution[]
  displayed_next_action: NextActionDeclaration | null
  aggregated_severity: WorkspaceStatusSeverity
}

export type ReadinessContributorFn = (
  session: WorkspaceSession,
) => Promise<ReadinessContribution | null>

export interface SectionRegistry {
  register(declaration: SectionDeclaration): void
  unregister(module_key: ModuleKey, section_id: string): void
  listSections(
    session: WorkspaceSession,
    userPermissions: WorkspacePermission[],
  ): SectionDeclaration[]
}

export interface ReadinessRegistry {
  registerContributor(module_key: ModuleKey, fetch: ReadinessContributorFn): void
  unregisterContributor(module_key: ModuleKey): void
}

// --- P0 seed: Recruitment section declarations (step 4) ---

export const RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY =
  'recruitment.requirements' as const satisfies WorkspaceCapabilityKey

export const RECRUITMENT_REQUIREMENTS_SECTION: SectionDeclaration = {
  section_id: 'requirements',
  module_key: 'recruitment',
  capability_key: RECRUITMENT_REQUIREMENTS_CAPABILITY_KEY,
  label_key: 'workspace.recruitment.sections.requirements',
  order: 10,
  contexts: ['recruitment'],
  permissions: ['candidates.view'],
  readiness_contribution: true,
}

/** Registry bootstrap for Recruitment P0 — call from module init, not from Workspace. */
export function registerRecruitmentWorkspaceSectionsP0(registry: SectionRegistry): void {
  registry.register(RECRUITMENT_REQUIREMENTS_SECTION)
}
