import { useMemo, useState } from 'react'
import type { EntityWorkspaceShellProps } from './types'
import { DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS } from './types'
import {
  projectEntityContextRail,
  projectEntityWorkspaceHeader,
  projectEntityWorkspaceSummary,
  resolveEnabledWorkspaceSections,
} from './projectEntityWorkspaceView'
import { EntityWorkspaceDefaultSectionContent } from './EntityWorkspaceDefaultSectionContent'
import { EntityWorkspaceContextRail } from './EntityWorkspaceContextRail'
import { EntityWorkspaceHeaderZone, EntityWorkspaceNavTabs, EntityWorkspaceSummaryStrip } from './EntityWorkspaceZones'

function mergeActions(
  projected: ReturnType<typeof projectEntityContextRail>,
  actionConfig?: EntityWorkspaceShellProps['actionConfig'],
) {
  if (!actionConfig?.contextActions && !actionConfig?.headerActions) return projected
  return {
    ...projected,
    actions: actionConfig.contextActions ?? projected.actions,
  }
}

/**
 * Universal Entity Workspace Shell — five fixed zones, resource-agnostic.
 *
 * STATUS: SCAFFOLD (geometry only) — not Reference.
 * Shell executes Universal Entity Schema; it does not decide widgets, sections, or actions.
 * See docs/specs/architecture/hostflow-entity-workspace-v1.md §2 (Entity Schema).
 */
export function EntityWorkspaceShell({
  model,
  passport,
  resourceTypeLabel,
  sectionRenderers,
  actionConfig,
  contextRail,
  headerExtension,
  summaryOverride,
  labels: labelsProp,
  activeSectionId: controlledSectionId,
  defaultSectionId,
  onSectionChange,
  navigationPeers,
}: EntityWorkspaceShellProps) {
  const labels = {
    ...DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS,
    ...labelsProp,
    sections: { ...DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS.sections, ...labelsProp?.sections },
  }

  const enabledSections = useMemo(() => resolveEnabledWorkspaceSections(model, passport), [model, passport])
  const initialSection = defaultSectionId && enabledSections.includes(defaultSectionId) ? defaultSectionId : enabledSections[0] ?? 'overview'

  const [internalSectionId, setInternalSectionId] = useState(initialSection)
  const activeSectionId = controlledSectionId ?? internalSectionId

  const setSection = (id: typeof activeSectionId) => {
    if (!controlledSectionId) setInternalSectionId(id)
    onSectionChange?.(id)
  }

  const header = useMemo(() => {
    const h = projectEntityWorkspaceHeader({ passport, resourceTypeLabel })
    return {
      ...h,
      quickActions: actionConfig?.headerActions ?? h.quickActions,
    }
  }, [actionConfig?.headerActions, passport, resourceTypeLabel])

  const summary = useMemo(() => summaryOverride ?? projectEntityWorkspaceSummary(passport), [passport, summaryOverride])
  const contextRailModel = useMemo(
    () => mergeActions(contextRail ?? projectEntityContextRail(passport), actionConfig),
    [actionConfig, contextRail, passport],
  )

  const sectionLabel = (id: typeof activeSectionId) => labels.sections?.[id] ?? id

  const activeContent = (() => {
    const custom = sectionRenderers?.[activeSectionId]
    if (custom) return custom()
    return <EntityWorkspaceDefaultSectionContent sectionId={activeSectionId} passport={passport} />
  })()

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-slate-100" data-entity-workspace-shell="v2">
      <EntityWorkspaceHeaderZone
        header={header}
        resourceTypeLabel={resourceTypeLabel}
        extension={headerExtension}
        navigationPeers={navigationPeers}
      />

      <EntityWorkspaceSummaryStrip summary={summary} />

      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <EntityWorkspaceNavTabs
            sections={enabledSections}
            activeSectionId={activeSectionId}
            onSectionChange={setSection}
            sectionLabel={sectionLabel}
            ariaLabel={labels.navigationHeading ?? 'Разделы'}
          />

          <main
            className="min-h-0 flex-1 overflow-y-auto bg-slate-100 p-3"
            data-entity-workspace-zone="content"
          >
            <div className="mx-auto max-w-5xl">{activeContent}</div>
          </main>
        </div>

        <EntityWorkspaceContextRail model={contextRailModel} labels={labels.contextRail} />
      </div>
    </div>
  )
}
