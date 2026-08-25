import { useCallback, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { EntityContextRailModel, EntityWorkspaceSectionId } from '../platform/entity-workspace'
import {
  CANDIDATE_COMPOSITION_CONSUMER_ID,
  CANDIDATE_COMPOSITION_SLOTS,
  assertCandidateCompositionSlots,
} from '../platform/entity-workspace'
import { CandidateEntityWorkspacePanel } from '../platform/entity-workspace/CandidateEntityWorkspacePanel'
import { projectEntityContextRail } from '../platform/entity-workspace/projectEntityWorkspaceView'
import { useI18n } from '../i18n'
import { useCandidateEntityWorkspace } from '../modules/candidates/hooks/useCandidateEntityWorkspace'
import { buildCandidateEntityWorkspaceSectionRenderers } from '../modules/candidates/candidateEntityWorkspaceSections'
import { buildCandidateEntityWorkspaceHeaderExtension } from '../modules/candidates/candidateEntityWorkspaceChrome'
import { buildCandidateEntityWorkspaceSummary } from '../modules/candidates/candidateEntityWorkspaceSummary'
import { CandidateEntityWorkspaceHeaderActions } from '../modules/candidates/candidateEntityWorkspaceHeaderActions'

function candidateWorkspaceLabels(t: (key: string, options?: Record<string, unknown>) => string) {
  return {
    summaryHeading: t('app.entity_workspace.summary', { defaultValue: 'Сводка' }),
    navigationHeading: t('app.entity_workspace.sections', { defaultValue: 'Разделы' }),
    sections: {
      overview: t('app.entity_workspace.section.overview', { defaultValue: 'Обзор' }),
      contacts: t('app.entity_workspace.section.contacts', { defaultValue: 'Контакты' }),
      documents: t('app.entity_workspace.section.documents', { defaultValue: 'Документы' }),
      timeline: t('app.entity_workspace.section.history', { defaultValue: 'История' }),
      relations: t('app.entity_workspace.section.vacancy', { defaultValue: 'Вакансия' }),
      tasks: t('app.entity_workspace.section.tasks', { defaultValue: 'Задачи' }),
      outcome: t('app.entity_workspace.section.outcome', { defaultValue: 'Итог' }),
    },
    contextRail: {
      next_actions: t('app.entity_workspace.rail.next_action', { defaultValue: 'Следующее действие' }),
      tasks: t('app.entity_workspace.rail.tasks', { defaultValue: 'Задачи' }),
      reminders: t('app.entity_workspace.rail.reminders', { defaultValue: 'Напоминания' }),
      processes: t('app.entity_workspace.rail.processes', { defaultValue: 'Процессы' }),
      recent_events: t('app.entity_workspace.rail.recent_events', { defaultValue: 'Недавние события' }),
    },
  }
}

/**
 * Candidate Entity Workspace — mockup-aligned consumer (5 zones, semantic content).
 * Composition path: EntityWorkspaceCapabilityHost. Shell is chrome adapter.
 * Not G4 — G4 remains Recruitment Application.
 */
export function CandidateEntityWorkspacePage() {
  const { t, locale } = useI18n()
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const [activeSectionId, setActiveSectionId] = useState<EntityWorkspaceSectionId>('overview')

  const {
    candidate,
    entityModel,
    passport,
    enrichLoading,
    error,
    buildActionConfig,
    workPanel,
    candidateProfile,
    effectiveLayout,
    reloadCandidate,
  } = useCandidateEntityWorkspace(id)

  const originPath =
    typeof (location.state as { originPath?: string } | null)?.originPath === 'string'
      ? (location.state as { originPath: string }).originPath
      : CRM_APP_PATHS.candidates

  const openDocuments = useCallback(() => setActiveSectionId('documents'), [])
  const openTimeline = useCallback(() => setActiveSectionId('timeline'), [])
  const openTasks = useCallback(() => setActiveSectionId('tasks'), [])

  const sectionRenderers = useMemo(() => {
    if (!passport || !candidate || !id) return undefined
    assertCandidateCompositionSlots(CANDIDATE_COMPOSITION_SLOTS)
    return buildCandidateEntityWorkspaceSectionRenderers({
      passport,
      candidate,
      candidateId: id,
      locale,
      candidateProfile,
      effectiveLayout,
    })
  }, [candidate, candidateProfile, effectiveLayout, id, locale, passport])

  const actionConfig = useMemo(() => buildActionConfig(openDocuments) ?? {}, [buildActionConfig, openDocuments])

  const docsPercentReady = workPanel.previewDocumentsSummarySnapshot?.percent_ready

  const summaryOverride = useMemo(() => {
    if (!passport) return undefined
    return buildCandidateEntityWorkspaceSummary(passport, docsPercentReady)
  }, [docsPercentReady, passport])

  const contextRail = useMemo((): EntityContextRailModel | undefined => {
    if (!passport) return undefined
    const projected = projectEntityContextRail(passport)
    return {
      ...projected,
      actions: actionConfig.contextActions ?? projected.actions,
      onShowAllEvents: projected.recentEvents?.length ? openTimeline : undefined,
      onCreateTask: openTasks,
      createTaskLabel: 'Создать задачу',
    }
  }, [actionConfig, openTasks, openTimeline, passport])

  const headerExtension = useMemo(() => {
    if (!candidate || !passport) return undefined
    const base = buildCandidateEntityWorkspaceHeaderExtension({
      candidate,
      passport,
      backHref: originPath,
      backLabel: t('app.candidates.back_to_list', { defaultValue: '← Кандидаты' }),
      locale,
    })
    return {
      ...base,
      actionsSlot: actionConfig.headerActions?.length ? (
        <CandidateEntityWorkspaceHeaderActions actions={actionConfig.headerActions} />
      ) : undefined,
    }
  }, [actionConfig, candidate, locale, originPath, passport, t])

  if (enrichLoading && !passport) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center text-sm text-slate-500">
        {t('common.loading', { defaultValue: 'Загрузка…' })}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm text-rose-700">{error}</p>
        <Link to={CRM_APP_PATHS.candidates} className="text-sm font-medium text-brand-700 hover:underline">
          {t('app.candidates.back_to_list', { defaultValue: 'К списку кандидатов' })}
        </Link>
      </div>
    )
  }

  if (!passport || !candidate || !id) {
    return null
  }

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden"
      data-candidate-entity-workspace="mockup-v1"
      data-entity-workspace-consumer={CANDIDATE_COMPOSITION_CONSUMER_ID}
    >
      <CandidateEntityWorkspacePanel
        entityId={id}
        onClose={() => navigate(originPath)}
        onRefresh={() => void reloadCandidate()}
        model={entityModel}
        passport={passport}
        resourceTypeLabel={t('app.candidates.entity_type', { defaultValue: 'Кандидат' })}
        sectionRenderers={sectionRenderers}
        actionConfig={actionConfig}
        contextRail={contextRail}
        headerExtension={headerExtension}
        summaryOverride={summaryOverride}
        activeSectionId={activeSectionId}
        onSectionChange={setActiveSectionId}
        labels={candidateWorkspaceLabels(t)}
      />
    </div>
  )
}
