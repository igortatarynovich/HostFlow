// src/modules/candidates/components/CandidatesBulkModalsCluster.tsx
//
// Aggregator component for the seven bulk-action modals + the activities
// modal that the Candidates page renders at the end of its tree.
//
// Each modal already lives in its own file (`BulkManagerModal`,
// `BulkVacancyModal`, `BulkHandoffModal`, `BulkTagsModal`,
// `BulkActivitiesModal`, `BulkDeleteModal`, `BulkStageModal`); this wrapper
// just centralises the wiring so the page-level orchestrator no longer has
// to repeat the same `open / onClose / loading / canManage` boilerplate
// seven times. Extracted from `src/pages/Candidates.tsx` as part of the
// Phase 1 #4 god-component split.

import { Modal } from '../../../components/Modal'
import { ActivitiesPanel } from '../../../components/activities/ActivitiesPanel'
import type { TranslateFn } from '../../../i18n'
import type { AvailableClientOut } from '../../../api/handoffs'
import type { MetaStages, Vacancy } from '../../../api/types'
import type { CandidatesBulkActions } from '../hooks/useCandidatesBulkActions'
import type { ManagerItem } from '../types'
import {
  BulkManagerModal,
  BulkVacancyModal,
  BulkHandoffModal,
  BulkTagsModal,
  BulkActivitiesModal,
  BulkDeleteModal,
  BulkStageModal,
} from './index'

export interface CandidatesBulkModalsClusterProps {
  // ---- shared --------------------------------------------------------
  t: TranslateFn
  canManage: boolean
  canViewActivities: boolean
  bulkOperationLoading: string | null
  /** Selection map; only `Object.values(checked).filter(Boolean).length` is read. */
  checked: Record<string, boolean>

  // ---- bulk action handlers (from useCandidatesBulkActions) ----------
  actions: CandidatesBulkActions

  // ---- BulkManagerModal ---------------------------------------------
  bulkManagerOpen: boolean
  setBulkManagerOpen: (b: boolean) => void
  managers: ManagerItem[]
  bulkManagerId: string
  setBulkManagerId: (s: string) => void

  // ---- BulkVacancyModal ---------------------------------------------
  bulkVacancyOpen: boolean
  setBulkVacancyOpen: (b: boolean) => void
  vacancies: Vacancy[]
  bulkVacancyId: string
  setBulkVacancyId: (s: string) => void

  // ---- BulkHandoffModal ---------------------------------------------
  bulkHandoffOpen: boolean
  setBulkHandoffOpen: (b: boolean) => void
  handoffClients: AvailableClientOut[]
  handoffClientsLoading: boolean
  bulkHandoffClientId: string
  setBulkHandoffClientId: (s: string) => void

  // ---- BulkTagsModal -------------------------------------------------
  bulkTagsOpen: boolean
  setBulkTagsOpen: (b: boolean) => void
  bulkTagsOperation: 'add' | 'remove'
  setBulkTagsOperation: (op: 'add' | 'remove') => void
  bulkTagsList: string
  setBulkTagsList: (s: string) => void

  // ---- BulkActivitiesModal ------------------------------------------
  bulkActivitiesOpen: boolean
  setBulkActivitiesOpen: (b: boolean) => void
  bulkActivityTitle: string
  setBulkActivityTitle: (s: string) => void
  bulkActivityDueAt: string
  setBulkActivityDueAt: (s: string) => void
  bulkActivityOffsetMinutes: number
  setBulkActivityOffsetMinutes: (n: number) => void
  bulkActivityType: string
  setBulkActivityType: (s: string) => void

  // ---- BulkDeleteModal ----------------------------------------------
  bulkDeleteOpen: boolean
  setBulkDeleteOpen: (b: boolean) => void

  // ---- BulkStageModal -----------------------------------------------
  bulkOpen: boolean
  setBulkOpen: (b: boolean) => void
  bulkStage: string
  setBulkStage: (s: string) => void
  bulkReasons: string[]
  setBulkReasons: (rs: string[]) => void
  stageOptions: string[]
  meta: MetaStages | null

  // ---- Activities (read-only, embedded ActivitiesPanel) -------------
  activitiesModalOpen: boolean
  setActivitiesModalOpen: (b: boolean) => void
  activitiesModalRefresh: number
}

export function CandidatesBulkModalsCluster(props: CandidatesBulkModalsClusterProps) {
  const {
    t,
    canManage,
    canViewActivities,
    bulkOperationLoading,
    checked,
    actions,
  } = props

  const selectedCount = Object.values(checked).filter(Boolean).length
  const closeIfIdle = (set: (b: boolean) => void) => () => {
    if (!bulkOperationLoading) set(false)
  }

  return (
    <>
      <BulkManagerModal
        open={props.bulkManagerOpen}
        onClose={closeIfIdle(props.setBulkManagerOpen)}
        managers={props.managers}
        bulkManagerId={props.bulkManagerId}
        onManagerIdChange={props.setBulkManagerId}
        onApply={actions.doBulkAssign}
        loading={bulkOperationLoading === 'manager'}
        canManage={canManage}
      />

      <BulkVacancyModal
        open={props.bulkVacancyOpen}
        onClose={closeIfIdle(props.setBulkVacancyOpen)}
        vacancies={props.vacancies}
        bulkVacancyId={props.bulkVacancyId}
        onVacancyIdChange={props.setBulkVacancyId}
        onApply={actions.doBulkAssignVacancy}
        loading={bulkOperationLoading === 'vacancy'}
        canManage={canManage}
      />

      <BulkHandoffModal
        open={props.bulkHandoffOpen}
        onClose={closeIfIdle(props.setBulkHandoffOpen)}
        clients={props.handoffClients}
        clientsLoading={props.handoffClientsLoading}
        selectedClient={props.bulkHandoffClientId}
        onSelectedClientChange={props.setBulkHandoffClientId}
        onApply={actions.doBulkHandoff}
        loading={bulkOperationLoading === 'handoff'}
        canManage={canManage}
        count={selectedCount}
      />

      <BulkTagsModal
        open={props.bulkTagsOpen}
        onClose={closeIfIdle(props.setBulkTagsOpen)}
        bulkTagsOperation={props.bulkTagsOperation}
        bulkTagsList={props.bulkTagsList}
        onOperationChange={props.setBulkTagsOperation}
        onTagsListChange={props.setBulkTagsList}
        onApply={actions.doBulkTags}
        loading={bulkOperationLoading === 'tags'}
        canManage={canManage}
      />

      <BulkActivitiesModal
        open={props.bulkActivitiesOpen}
        onClose={closeIfIdle(props.setBulkActivitiesOpen)}
        title={props.bulkActivityTitle}
        dueAt={props.bulkActivityDueAt}
        offsetMinutes={props.bulkActivityOffsetMinutes}
        onTitleChange={props.setBulkActivityTitle}
        onDueAtChange={props.setBulkActivityDueAt}
        onOffsetMinutesChange={props.setBulkActivityOffsetMinutes}
        onApply={actions.doBulkActivities}
        loading={bulkOperationLoading === 'activities'}
        canManage={canManage}
        activityType={props.bulkActivityType}
        onActivityTypeChange={props.setBulkActivityType}
      />

      <BulkDeleteModal
        open={props.bulkDeleteOpen}
        onClose={closeIfIdle(props.setBulkDeleteOpen)}
        onApply={actions.doBulkDelete}
        loading={bulkOperationLoading === 'delete'}
        count={selectedCount}
        canManage={canManage}
      />

      <BulkStageModal
        open={props.bulkOpen}
        onClose={() => {
          if (!bulkOperationLoading) {
            props.setBulkOpen(false)
            props.setBulkReasons([])
          }
        }}
        stageOptions={props.stageOptions}
        bulkStage={props.bulkStage}
        bulkReasons={props.bulkReasons}
        onStageChange={props.setBulkStage}
        onReasonsChange={props.setBulkReasons}
        onApply={actions.doBulk}
        loading={bulkOperationLoading === 'stage'}
        meta={props.meta}
        canManage={canManage}
      />

      {canViewActivities ? (
        <Modal
          open={props.activitiesModalOpen}
          onClose={() => props.setActivitiesModalOpen(false)}
          title={t('app.activities.title', { defaultValue: 'Activities' })}
          size="2xl"
          surfaceClassName="max-h-[min(92vh,900px)] flex flex-col"
        >
          <p className="mb-3 text-sm text-slate-600">
            {t('app.candidates.activities_modal.subtitle', {
              defaultValue: 'Your planned work — same list as on the Tasks page.',
            })}
          </p>
          <div className="min-h-0 flex-1 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <ActivitiesPanel
              embedded
              compact
              showFullPageLink
              refreshToken={props.activitiesModalRefresh}
            />
          </div>
        </Modal>
      ) : null}
    </>
  )
}
