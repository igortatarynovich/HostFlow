/**
 * ADR-036 FE mirror of backend.app.auth.trust_roles.
 * Canonical trust: superadmin | administrator | employee | viewer.
 * Legacy job/portal strings normalize here; do not invent new system roles.
 */

export type TrustRole = 'superadmin' | 'administrator' | 'employee' | 'viewer'
export type AccessContext = 'tenant' | 'portal'
export type PermissionPresetId =
  | 'recruiter'
  | 'team_lead'
  | 'hr'
  | 'compliance'
  | 'portal_guest'

export const TRUST_ROLES = ['superadmin', 'administrator', 'employee', 'viewer'] as const

export const TRUST_ROLE_NORMALIZE: Record<string, TrustRole> = {
  superadmin: 'superadmin',
  super_admin: 'superadmin',
  administrator: 'administrator',
  admin: 'administrator',
  owner: 'administrator',
  employee: 'employee',
  recruiter: 'employee',
  supervisor: 'employee',
  manager: 'employee',
  lead: 'employee',
  hr: 'employee',
  hr_officer: 'employee',
  people_ops: 'employee',
  compliance_officer: 'employee',
  compliance: 'employee',
  docs_officer: 'employee',
  viewer: 'viewer',
  user: 'viewer',
  client_manager: 'viewer',
  client_processor: 'viewer',
  client: 'viewer',
  processor: 'viewer',
}

export const LEGACY_TO_PRESET: Record<string, PermissionPresetId> = {
  recruiter: 'recruiter',
  hr: 'hr',
  hr_officer: 'hr',
  people_ops: 'hr',
  supervisor: 'team_lead',
  manager: 'team_lead',
  lead: 'team_lead',
  compliance_officer: 'compliance',
  compliance: 'compliance',
  docs_officer: 'compliance',
  client_manager: 'portal_guest',
  client_processor: 'portal_guest',
  client: 'portal_guest',
  processor: 'portal_guest',
}

export const PORTAL_LEGACY_ROLES = new Set([
  'client_manager',
  'client_processor',
  'client',
  'processor',
])

export const JOB_PROXY_ROLES = new Set([
  'recruiter',
  'supervisor',
  'manager',
  'lead',
  'hr',
  'hr_officer',
  'people_ops',
  'compliance_officer',
  'compliance',
  'docs_officer',
])

export function normalizeTrustRole(role: string | null | undefined): TrustRole {
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  if (!raw) return 'viewer'
  return TRUST_ROLE_NORMALIZE[raw] ?? 'viewer'
}

export function inferAccessContext(
  role: string | null | undefined,
  explicit?: string | null,
): AccessContext {
  if (explicit === 'tenant' || explicit === 'portal') return explicit
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  if (PORTAL_LEGACY_ROLES.has(raw)) return 'portal'
  return 'tenant'
}

export function inferPresetId(
  role: string | null | undefined,
  explicit?: string | null,
): PermissionPresetId | null {
  const fromExplicit = String(explicit || '')
    .trim()
    .toLowerCase()
  if (
    fromExplicit === 'recruiter' ||
    fromExplicit === 'team_lead' ||
    fromExplicit === 'hr' ||
    fromExplicit === 'compliance' ||
    fromExplicit === 'portal_guest'
  ) {
    return fromExplicit
  }
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  return LEGACY_TO_PRESET[raw] ?? null
}

export function isPortalActor(
  role: string | null | undefined,
  accessContext?: string | null,
): boolean {
  return inferAccessContext(role, accessContext) === 'portal'
}

export function isHrWorkspaceActor(
  role: string | null | undefined,
  presetId?: string | null,
): boolean {
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  if (raw === 'hr_officer' || raw === 'hr' || raw === 'people_ops') return true
  const preset = inferPresetId(role, presetId)
  return preset === 'hr'
}

export function isTeamLeadOrgActor(
  role: string | null | undefined,
  presetId?: string | null,
): boolean {
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  if (raw === 'supervisor' || raw === 'manager' || raw === 'lead') return true
  return inferPresetId(role, presetId) === 'team_lead'
}

export function expandAllowedRolesForTrust(allowed: Iterable<string>): Set<string> {
  const out = new Set(
    [...allowed]
      .map((x) => String(x).trim().toLowerCase())
      .filter(Boolean),
  )
  for (const role of out) {
    if (JOB_PROXY_ROLES.has(role)) {
      out.add('employee')
      break
    }
  }
  return out
}

export function actorSatisfiesRoleAllowlist(args: {
  role: string | null | undefined
  allowed: Iterable<string>
  accessContext?: string | null
}): boolean {
  const ur = String(args.role || '')
    .trim()
    .toLowerCase()
  if (!ur) return false
  const allowedValues = expandAllowedRolesForTrust(args.allowed)
  if (allowedValues.has(ur)) return true

  const trust = normalizeTrustRole(ur)
  if (trust === 'employee' && allowedValues.has('employee')) return true
  if (trust === 'viewer' && allowedValues.has('viewer')) return true

  const portalOnly = [...allowedValues].some((r) => PORTAL_LEGACY_ROLES.has(r))
  const viewerAllowed = allowedValues.has('viewer')
  if (portalOnly && !viewerAllowed) {
    if (trust === 'viewer' && isPortalActor(ur, args.accessContext)) return true
    if (PORTAL_LEGACY_ROLES.has(ur)) return true
  }
  return false
}

/**
 * Legacy permission / Work Hub persona key derived from trust + preset.
 * Keeps ROLE_PERMISSIONS and resolveWorkHubProfile working during migration.
 */
export function resolvePermissionPersona(args: {
  role: string | null | undefined
  accessContext?: string | null
  presetId?: string | null
  /** @deprecated company-tenant recruiter remap; prefer portal access_context */
  isClientTenant?: boolean
}): string {
  const raw = String(args.role || '')
    .trim()
    .toLowerCase()
  const trust = normalizeTrustRole(raw)
  const preset = inferPresetId(raw, args.presetId)
  const portal = isPortalActor(raw, args.accessContext) || preset === 'portal_guest'

  if (trust === 'superadmin' || trust === 'administrator') return 'administrator'
  if (portal) {
    if (raw === 'client_manager') return 'client_manager'
    return 'client_processor'
  }
  if (trust === 'viewer') return 'viewer'
  if (preset === 'team_lead') return 'team_lead'
  if (preset === 'hr') return 'hr'
  if (preset === 'compliance') return 'compliance_officer'
  if (preset === 'recruiter') {
    if (args.isClientTenant) return 'client_processor'
    return 'recruiter'
  }
  // Bare employee (canonical membership) — operational CRM lane
  if (args.isClientTenant) return 'client_processor'
  return 'employee'
}

export type ActorTrustContext = {
  rawRole: string
  trustRole: TrustRole
  accessContext: AccessContext
  presetId: PermissionPresetId | null
  persona: string
}

export function resolveActorTrustContext(me: {
  role?: string | null
  tenant_id?: string | null
  memberships?: Array<{ tenant_id?: string; role?: string }> | null
  preferences?: Record<string, unknown> | null
  access_context?: string | null
} | null): ActorTrustContext {
  const currentTenantId = me?.tenant_id || null
  const membershipRole =
    Array.isArray(me?.memberships) && currentTenantId
      ? me.memberships.find((m) => m?.tenant_id === currentTenantId)?.role
      : undefined
  const rawRole = String(membershipRole || me?.role || 'viewer')
    .trim()
    .toLowerCase() || 'viewer'
  const prefs = me?.preferences && typeof me.preferences === 'object' ? me.preferences : {}
  const explicitCtx =
    (typeof me?.access_context === 'string' && me.access_context) ||
    (typeof prefs.access_context === 'string' ? prefs.access_context : null)
  const explicitPreset = typeof prefs.preset_id === 'string' ? prefs.preset_id : null
  const accessContext = inferAccessContext(rawRole, explicitCtx)
  const presetId = inferPresetId(rawRole, explicitPreset)
  const trustRole = normalizeTrustRole(rawRole)
  return {
    rawRole,
    trustRole,
    accessContext,
    presetId,
    persona: resolvePermissionPersona({
      role: rawRole,
      accessContext,
      presetId,
    }),
  }
}

/** Org / team-overview gates: admin or team-lead lane. */
export function canUseTeamOverviewLane(args: {
  role: string | null | undefined
  presetId?: string | null
  canAdminUsers?: boolean
}): boolean {
  const trust = normalizeTrustRole(args.role)
  if (trust === 'administrator' || trust === 'superadmin') return true
  if (args.canAdminUsers) return true
  return isTeamLeadOrgActor(args.role, args.presetId)
}

/**
 * Membership roles accepted by `/catalogs/managers?roles=` for recruitment assignees.
 * Includes canonical `employee` plus legacy job titles still present in DB.
 */
export const RECRUITMENT_ASSIGNEE_CATALOG_ROLES =
  'employee,recruiter,supervisor,compliance_officer' as const

/** True when membership role can own candidates / appear in recruiter pickers. */
export function isRecruitmentAssigneeRole(role: string | null | undefined): boolean {
  const raw = String(role || '')
    .trim()
    .toLowerCase()
  if (!raw) return false
  if (raw === 'recruiter' || raw === 'supervisor' || raw === 'compliance_officer') return true
  const trust = normalizeTrustRole(raw)
  if (trust === 'employee') {
    // HR-only lane is not a recruitment assignee by default.
    if (isHrWorkspaceActor(raw)) return false
    return true
  }
  return false
}

/** Team-scope assignee UI (Reminders / Candidates work panel / Topbar). */
export function canUseTeamAssigneeScope(args: {
  role: string | null | undefined
  presetId?: string | null
}): boolean {
  return canUseTeamOverviewLane(args)
}
