import { useMemo, useState } from 'react'
import { EntityWorkspace } from '../../components/ui/EntityWorkspace'
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
 * Passport adapter over the public kit `EntityWorkspace`.
 * Not a second chrome — new entity pages must import from `components/ui`.
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
    <EntityWorkspace
      data-entity-workspace-shell="v2"
      header={
        <EntityWorkspaceHeaderZone
          header={header}
          resourceTypeLabel={resourceTypeLabel}
          extension={headerExtension}
          navigationPeers={navigationPeers}
        />
      }
      summary={<EntityWorkspaceSummaryStrip summary={summary} />}
      navigation={
        <EntityWorkspaceNavTabs
          sections={enabledSections}
          activeSectionId={activeSectionId}
          onSectionChange={setSection}
          sectionLabel={sectionLabel}
          ariaLabel={labels.navigationHeading ?? 'Sections'}
        />
      }
      rail={<EntityWorkspaceContextRail model={contextRailModel} labels={labels.contextRail} />}
    >
      {activeContent}
    </EntityWorkspace>
  )
}
