/**
 * In-memory SectionRegistry (P0). No React.
 * @see docs/specs/platform/workspace-layer-contracts-p0.md §4 step 2
 */

import type {
  ModuleKey,
  SectionDeclaration,
  SectionRegistry,
  WorkspacePermission,
  WorkspaceSession,
} from './workspace_layer_contracts'

function declarationKey(module_key: ModuleKey, section_id: string): string {
  return `${module_key}:${section_id}`
}

function hasAllPermissions(
  required: WorkspacePermission[],
  granted: Set<WorkspacePermission>,
): boolean {
  return required.every((p) => granted.has(p))
}

export function createSectionRegistry(): SectionRegistry {
  const byKey = new Map<string, SectionDeclaration>()

  return {
    register(declaration: SectionDeclaration): void {
      byKey.set(
        declarationKey(declaration.module_key, declaration.section_id),
        declaration,
      )
    },

    unregister(module_key: ModuleKey, section_id: string): void {
      byKey.delete(declarationKey(module_key, section_id))
    },

    listSections(
      session: WorkspaceSession,
      userPermissions: WorkspacePermission[],
    ): SectionDeclaration[] {
      const granted = new Set(userPermissions)
      const enabled = new Set(session.enabled_modules)

      return [...byKey.values()]
        .filter((d) => enabled.has(d.module_key))
        .filter((d) => d.contexts.includes(session.context))
        .filter((d) => hasAllPermissions(d.permissions, granted))
        .sort((a, b) => a.order - b.order || a.section_id.localeCompare(b.section_id))
    },
  }
}
