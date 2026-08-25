import clsx from 'clsx'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { RequirementsWorkspaceResponse } from '../../../api/candidateRequirements'
import { useRequirementsWorkspace } from '../../../hooks/useRequirementsWorkspace'
import { useI18n } from '../../../i18n'
import type { DocBlockersPayload } from '../../../utils/candidateStageDocPolicy'
import { mapRequirementPipelineBlockers } from '../../../utils/requirementsPipelineBlockers'
import RequirementsWorkspaceSummaryBar from './RequirementsWorkspaceSummaryBar'

type Props = {
  candidateId: string
  refreshTrigger?: number
  canEdit?: boolean
  primaryStepHighlight?: boolean
  className?: string
  workspace?: RequirementsWorkspaceResponse | null
  workspaceLoading?: boolean
  workspaceReload?: () => Promise<RequirementsWorkspaceResponse | null>
  onPipelineBlockersChange?: (blockers: DocBlockersPayload, loading: boolean) => void
}

export default function RequirementsWorkspaceSummaryCard({
  candidateId,
  refreshTrigger = 0,
  canEdit = true,
  primaryStepHighlight = false,
  className,
  workspace: workspaceProp,
  workspaceLoading: workspaceLoadingProp,
  workspaceReload,
  onPipelineBlockersChange,
}: Props) {
  const { t } = useI18n()
  const shouldFetch = workspaceProp === undefined
  const {
    workspace: fetchedWorkspace,
    loading: fetchedLoading,
    error,
    reload: fetchedReload,
  } = useRequirementsWorkspace(shouldFetch ? candidateId : null, refreshTrigger)

  const workspace = workspaceProp === undefined ? fetchedWorkspace : workspaceProp
  const loading = workspaceLoadingProp ?? (shouldFetch ? fetchedLoading : false)
  const reload = workspaceReload ?? fetchedReload

  useEffect(() => {
    if (!onPipelineBlockersChange) return
    if (!workspace) {
      onPipelineBlockersChange({ missing: [], problematic: [], inProgress: [] }, loading)
      return
    }
    onPipelineBlockersChange(mapRequirementPipelineBlockers(workspace.pipeline_blockers), loading)
  }, [workspace, loading, onPipelineBlockersChange])

  const workspacePath = `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}/requirements`
  const primary = Boolean(primaryStepHighlight)

  return (
    <section
      id="section-requirements-workspace"
      className={clsx(
        'scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-3 transition-shadow duration-200',
        primary && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
        className,
      )}
      data-rail-primary-step={primary ? 'true' : undefined}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold text-slate-800">
              {t('app.candidate_requirements.workspace.card_title', { defaultValue: 'Requirements' })}
            </div>
            {primary ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
                {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[11px] text-slate-600">
            {t('app.candidate_requirements.workspace.card_subtitle', {
              defaultValue: 'Close data fields and document evidence in the requirements workspace.',
            })}
          </p>
        </div>
        <Link to={workspacePath} className="btn-primary btn-sm shrink-0">
          {t('app.candidate_requirements.workspace.open_workspace', { defaultValue: 'Open workspace' })}
        </Link>
      </div>

      {loading && !workspace ? (
        <div className="mt-3 text-xs text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</div>
      ) : null}

      {error ? (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-2 py-2 text-xs text-rose-800">
          <p>{error}</p>
          <button
            type="button"
            className="mt-1 font-semibold underline"
            onClick={() => void reload()}
          >
            {t('common.retry', { defaultValue: 'Retry' })}
          </button>
        </div>
      ) : null}

      {workspace ? (
        <div className="mt-3">
          <RequirementsWorkspaceSummaryBar
            summary={workspace.summary}
            transferReadiness={workspace.transfer_readiness}
            canEdit={canEdit && workspace.can_edit}
            className="border-0 p-0 shadow-none"
          />
          {workspace.field_requirements.missing_count > 0 ? (
            <p className="mt-2 text-[11px] text-amber-800">
              {t('app.candidate_requirements.workspace.card_data_missing', {
                defaultValue: '{count} required data field(s) still open',
                values: { count: workspace.field_requirements.missing_count },
              })}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
