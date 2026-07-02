import clsx from 'clsx'
import { useCallback, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { RequirementsChecklistResponse } from '../../api/candidateRequirements'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { isRequirementsWorkspaceEnabled } from '../../utils/featureFlags'
import { useCandidateRequirementsChecklist } from '../../hooks/useCandidateRequirementsChecklist'
import { useCandidateRequirementDocuments } from '../../hooks/useCandidateRequirementDocuments'
import { useToast } from '../Toast'
import { mapRequirementsChecklistToBlockers } from '../../utils/requirementsPipelineBlockers'
import { resolveRequirementRowStatus } from './requirementsChecklistPresentation'
import RequirementDetailPane, { useRequirementLabelForType } from './requirements/RequirementDetailPane'

type Props = {
  candidateId: string
  refreshTrigger?: number
  canEdit?: boolean
  onOpenDocs?: (docType?: string) => void
  onUpload?: () => void
  primaryStepHighlight?: boolean
  className?: string
  onChecklistLoaded?: (checklist: RequirementsChecklistResponse | null) => void
  onChanged?: () => void
  onPipelineBlockersChange?: (blockers: import('../../utils/candidateStageDocPolicy').DocBlockersPayload, loading: boolean) => void
}

export default function CandidateRequirementsChecklist({
  candidateId,
  refreshTrigger = 0,
  canEdit = true,
  onOpenDocs,
  onUpload,
  primaryStepHighlight = false,
  className,
  onChecklistLoaded,
  onChanged,
  onPipelineBlockersChange,
}: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const {
    checklist,
    loading,
    error,
    actionBusy,
    selectEvidence,
    linkDocument,
    approveEvidence,
    rejectEvidence,
    replaceEvidence,
  } = useCandidateRequirementsChecklist(candidateId, refreshTrigger, onChanged)

  const { candidateDocuments, docsLoading } = useCandidateRequirementDocuments(candidateId, refreshTrigger)
  const labelForType = useRequirementLabelForType()

  useEffect(() => {
    onChecklistLoaded?.(checklist)
  }, [checklist, onChecklistLoaded])

  useEffect(() => {
    onPipelineBlockersChange?.(mapRequirementsChecklistToBlockers(checklist), loading)
  }, [checklist, loading, onPipelineBlockersChange])

  const applicableRequirements = useMemo(
    () => (checklist?.requirements || []).filter((item) => resolveRequirementRowStatus(item) !== 'not_applicable'),
    [checklist],
  )
  const fulfilledCount = useMemo(
    () => (checklist?.requirements || []).filter((item) => item.fulfilled).length,
    [checklist],
  )
  const totalCount = checklist?.requirements?.length ?? 0
  const pendingCount = useMemo(
    () =>
      (checklist?.requirements || []).filter((item) => {
        const status = resolveRequirementRowStatus(item)
        return status !== 'approved' && status !== 'not_applicable'
      }).length,
    [checklist],
  )

  const wrapAction = useCallback(
    async (fn: () => Promise<unknown>, successKey: string, defaultSuccess: string) => {
      const result = await fn()
      if (result !== null && result !== undefined) {
        notify({
          variant: 'success',
          title: t(successKey, { defaultValue: defaultSuccess }),
        })
        onChanged?.()
      }
      return result
    },
    [notify, onChanged, t],
  )

  const primary = Boolean(primaryStepHighlight)

  return (
    <section
      className={clsx(
        'rounded-2xl border border-slate-200 bg-white p-3 transition-shadow duration-200',
        primary && 'ring-2 ring-amber-400/95 ring-offset-2 ring-offset-white shadow-sm shadow-amber-500/10',
        className,
      )}
      data-rail-primary-step={primary ? 'true' : undefined}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs font-semibold text-slate-800">
              {t('app.candidate_card.requirements_checklist.title', {
                defaultValue: 'Requirements',
              })}
            </div>
            {primary ? (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-950">
                {t('app.candidate_card.rail.primary_step_badge', { defaultValue: 'Next step' })}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[11px] text-slate-600">
            {t('app.candidate_card.requirements_checklist.subtitle', {
              defaultValue: 'Confirm each requirement — choose evidence, link documents, then approve.',
            })}
          </p>
          {isRequirementsWorkspaceEnabled() && candidateId ? (
            <Link
              to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}/requirements`}
              className="mt-1 inline-flex text-[11px] font-semibold text-brand-700 hover:text-brand-800"
            >
              {t('app.candidate_requirements.workspace.open_from_card', { defaultValue: 'Open workspace' })}
            </Link>
          ) : null}
        </div>
        <span
          className={clsx(
            'rounded-full px-2.5 py-1 text-xs font-semibold',
            checklist?.all_fulfilled
              ? 'bg-emerald-100 text-emerald-900'
              : 'bg-amber-100 text-amber-900',
          )}
        >
          {loading
            ? t('common.loading')
            : checklist?.all_fulfilled
              ? t('app.candidate_card.requirements_checklist.all_confirmed', {
                  defaultValue: 'All confirmed',
                })
              : t('app.candidate_card.requirements_checklist.pending_count', {
                  defaultValue: '{count} open',
                  values: { count: pendingCount },
                })}
        </span>
      </div>

      {!loading && totalCount > 0 ? (
        <div className="mt-1 text-[11px] font-medium text-slate-700">
          {t('app.candidate_card.requirements_checklist.progress', {
            defaultValue: '{fulfilled}/{total} confirmed',
            values: { fulfilled: fulfilledCount, total: totalCount },
          })}
        </div>
      ) : null}

      <div className="mt-3 space-y-2">
        {loading ? (
          <div className="text-xs text-slate-500">{t('common.loading')}</div>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-2 py-2 text-xs text-rose-800">
            {error}
          </div>
        ) : applicableRequirements.length ? (
          applicableRequirements.map((item) => (
            <RequirementDetailPane
              key={item.requirement_code}
              item={item}
              canEdit={canEdit}
              actionBusy={actionBusy}
              labelForType={labelForType}
              candidateDocuments={candidateDocuments}
              docsLoading={docsLoading}
              layout="compact"
              onSelectVariant={(variantCode) =>
                wrapAction(
                  () => selectEvidence(item.requirement_code, variantCode),
                  'app.candidate_card.requirements_checklist.toast_selected',
                  'Evidence selected',
                )
              }
              onLinkDocument={(evidenceId, documentId) =>
                wrapAction(
                  () => linkDocument(evidenceId, documentId),
                  'app.candidate_card.requirements_checklist.toast_linked',
                  'Document linked',
                )
              }
              onApprove={(evidenceId) =>
                wrapAction(
                  () => approveEvidence(evidenceId),
                  'app.candidate_card.requirements_checklist.toast_approved',
                  'Requirement approved',
                )
              }
              onReject={(evidenceId, reason) =>
                wrapAction(
                  () => rejectEvidence(evidenceId, reason),
                  'app.candidate_card.requirements_checklist.toast_rejected',
                  'Evidence rejected',
                )
              }
              onReplace={(variantCode) =>
                wrapAction(
                  () => replaceEvidence(item.requirement_code, variantCode),
                  'app.candidate_card.requirements_checklist.toast_replaced',
                  'Evidence replaced',
                )
              }
              onOpenDocs={onOpenDocs}
              onUpload={onUpload}
            />
          ))
        ) : (
          <div className="text-xs text-slate-500">
            {t('app.candidate_card.requirements_checklist.empty', {
              defaultValue: 'No requirements for this candidate profile.',
            })}
          </div>
        )}
      </div>
    </section>
  )
}
