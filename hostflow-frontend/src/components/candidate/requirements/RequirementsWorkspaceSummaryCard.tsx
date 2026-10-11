import clsx from 'clsx'
import { useEffect, type ReactNode } from 'react'
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
  /** Next step and blockers. Replaces the retired workspace link. */
  children?: ReactNode
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
  children,
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
      {children}

      {loading && !workspace && !children ? (
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

      {workspace && !children ? (
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
