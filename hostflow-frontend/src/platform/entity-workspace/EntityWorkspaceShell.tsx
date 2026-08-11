import { useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import type { EntityWorkspaceShellProps, EntityWorkspaceShellLabels } from './types'
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

function buildShellLabels(
  t: (key: string, opts?: { defaultValue?: string }) => string,
  labelsProp?: EntityWorkspaceShellLabels,
): EntityWorkspaceShellLabels {
  const fromI18n: EntityWorkspaceShellLabels = {
    summaryHeading: t('app.entity_workspace.summary_heading', { defaultValue: 'Summary' }),
    navigationHeading: t('app.entity_workspace.navigation_heading', { defaultValue: 'Sections' }),
    sections: {
      overview: t('app.entity_workspace.sections.overview', { defaultValue: 'Overview' }),
      contacts: t('app.entity_workspace.sections.contacts', { defaultValue: 'Contacts' }),
      documents: t('app.entity_workspace.sections.documents', { defaultValue: 'Documents' }),
      timeline: t('app.entity_workspace.sections.timeline', { defaultValue: 'Timeline' }),
      relations: t('app.entity_workspace.sections.relations', { defaultValue: 'Relations' }),
      tasks: t('app.entity_workspace.sections.tasks', { defaultValue: 'Tasks' }),
      outcome: t('app.entity_workspace.sections.outcome', { defaultValue: 'Outcome' }),
      finance: t('app.entity_workspace.sections.finance', { defaultValue: 'Finance' }),
      comments: t('app.entity_workspace.sections.comments', { defaultValue: 'Comments' }),
      activity: t('app.entity_workspace.sections.activity', { defaultValue: 'Activity' }),
    },
    contextRail: {
      next_actions: t('app.entity_workspace.context_rail.next_actions', { defaultValue: 'Next action' }),
      tasks: t('app.entity_workspace.context_rail.tasks', { defaultValue: 'Tasks' }),
      reminders: t('app.entity_workspace.context_rail.reminders', { defaultValue: 'Reminders' }),
      processes: t('app.entity_workspace.context_rail.processes', { defaultValue: 'Processes' }),
      recent_events: t('app.entity_workspace.context_rail.recent_events', { defaultValue: 'Recent events' }),
    },
  }
  return {
    ...DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS,
    ...fromI18n,
    ...labelsProp,
    sections: {
      ...DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS.sections,
      ...fromI18n.sections,
      ...labelsProp?.sections,
    },
    contextRail: {
      ...DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS.contextRail,
      ...fromI18n.contextRail,
      ...labelsProp?.contextRail,
    },
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
  const { t } = useI18n()
  const labels = useMemo(() => buildShellLabels(t, labelsProp), [t, labelsProp])

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

  const summary = useMemo(
    () => summaryOverride ?? projectEntityWorkspaceSummary(passport, t),
    [passport, summaryOverride, t],
  )
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
            ariaLabel={labels.navigationHeading ?? 'Sections'}
          />

          <main
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-slate-100 p-4"
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
