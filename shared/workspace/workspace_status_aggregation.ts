/**
 * Workspace Status aggregation (P0). Display policy only — no domain logic.
 * @see docs/specs/platform/workspace-layer-contracts-p0.md §4 step 3
 */

import {
  WORKSPACE_CONTRACTS_SCHEMA_VERSION,
  type ModuleKey,
  type NextActionDeclaration,
  type ReadinessContribution,
  type ReadinessContributorFn,
  type ReadinessRegistry,
  type WorkspacePermission,
  type WorkspaceSession,
  type WorkspaceStatusSeverity,
  type WorkspaceStatusSnapshot,
} from './workspace_layer_contracts'

const SEVERITY_RANK: Record<WorkspaceStatusSeverity, number> = {
  blocked: 0,
  warning: 1,
  info: 2,
  not_applicable: 3,
  ready: 4,
}

function worstSeverity(contributions: ReadinessContribution[]): WorkspaceStatusSeverity {
  if (contributions.length === 0) return 'info'
  return contributions.reduce((worst, c) =>
    SEVERITY_RANK[c.severity] < SEVERITY_RANK[worst] ? c.severity : worst,
  contributions[0].severity)
}

function pickDisplayedNextAction(
  contributions: ReadinessContribution[],
  granted: Set<WorkspacePermission>,
): NextActionDeclaration | null {
  const candidates: NextActionDeclaration[] = []
  for (const c of contributions) {
    const action = c.next_action
    if (action && granted.has(action.permission)) {
      candidates.push(action)
    }
  }
  if (candidates.length === 0) return null
  candidates.sort((a, b) => a.priority - b.priority || a.action_id.localeCompare(b.action_id))
  return candidates[0]
}

export type ReadinessRegistryWithCollect = ReadinessRegistry & {
  collect(session: WorkspaceSession): ReadinessContributorFn[]
}

export function createReadinessRegistryWithCollect(): ReadinessRegistryWithCollect {
  const contributors = new Map<ModuleKey, ReadinessContributorFn>()

  return {
    registerContributor(module_key: ModuleKey, fetch: ReadinessContributorFn): void {
      contributors.set(module_key, fetch)
    },

    unregisterContributor(module_key: ModuleKey): void {
      contributors.delete(module_key)
    },

    collect(session: WorkspaceSession): ReadinessContributorFn[] {
      const enabled = new Set(session.enabled_modules)
      return [...contributors.entries()]
        .filter(([key]) => enabled.has(key))
        .map(([, fn]) => fn)
    },
  }
}

export async function aggregateWorkspaceStatusFromContributors(
  session: WorkspaceSession,
  fetchers: ReadinessContributorFn[],
  userPermissions: WorkspacePermission[],
): Promise<WorkspaceStatusSnapshot> {
  const results = await Promise.all(fetchers.map((fn) => fn(session)))
  const contributions = results.filter(
    (c): c is ReadinessContribution => c != null && c.context === session.context,
  )

  contributions.sort((a, b) => a.priority - b.priority)

  return {
    schema_version: WORKSPACE_CONTRACTS_SCHEMA_VERSION,
    session,
    contributions,
    displayed_next_action: pickDisplayedNextAction(contributions, new Set(userPermissions)),
    aggregated_severity: worstSeverity(contributions),
  }
}

export async function aggregateWorkspaceStatusForSession(
  session: WorkspaceSession,
  registry: ReadinessRegistryWithCollect,
  userPermissions: WorkspacePermission[],
): Promise<WorkspaceStatusSnapshot> {
  const fetchers = registry.collect(session)
  return aggregateWorkspaceStatusFromContributors(session, fetchers, userPermissions)
}
