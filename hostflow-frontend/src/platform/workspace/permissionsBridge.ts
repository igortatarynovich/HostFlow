import type { Permission } from '../../hooks/usePermissions'
import type { WorkspacePermission } from '@hostflow/workspace'

const PERMISSION_BRIDGE: Record<WorkspacePermission, Permission | null> = {
  'candidates.view': 'candidates.view',
  'candidates.read': 'candidates.view',
  'candidates.manage': 'candidates.manage',
  'candidates.update': 'candidates.manage',
}

export function workspacePermissionsFromCan(can: (perm: Permission) => boolean): WorkspacePermission[] {
  const granted: WorkspacePermission[] = []
  for (const [workspacePerm, appPerm] of Object.entries(PERMISSION_BRIDGE)) {
    if (appPerm && can(appPerm)) {
      granted.push(workspacePerm)
    }
  }
  return granted
}

export function workspaceSectionAllowed(
  required: WorkspacePermission[],
  can: (perm: Permission) => boolean,
): boolean {
  return required.every((perm) => {
    const mapped = PERMISSION_BRIDGE[perm]
    if (!mapped) return false
    return can(mapped)
  })
}
