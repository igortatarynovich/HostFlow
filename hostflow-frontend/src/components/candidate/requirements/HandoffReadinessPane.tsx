import clsx from 'clsx'
import { Link } from 'react-router-dom'
import type { TransferReadinessReport } from '../../../api/candidates'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { useI18n } from '../../../i18n'
import TransferReadinessReport from '../TransferReadinessReport'
import { useTransferReadiness } from '../useTransferReadiness'

type Props = {
  candidateId: string
  refreshTrigger?: number
  canEdit?: boolean
  showCreateAction?: boolean
  className?: string
  transferReport?: TransferReadinessReport | null
  transferReportLoading?: boolean
}

export default function HandoffReadinessPane({
  candidateId,
  refreshTrigger = 0,
  canEdit = true,
  showCreateAction = true,
  className,
  transferReport: transferReportProp,
  transferReportLoading: transferReportLoadingProp,
}: Props) {
  const { t } = useI18n()
  const shouldFetch = transferReportProp === undefined
  const { report: fetchedReport, loading: fetchedLoading } = useTransferReadiness(
    shouldFetch ? candidateId : null,
    refreshTrigger,
  )
  const report = transferReportProp === undefined ? fetchedReport : transferReportProp
  const loading = transferReportLoadingProp ?? (shouldFetch ? fetchedLoading : false)

  const handoffCreateAllowed = Boolean(report?.handoff_create_allowed)
  const cardPath = `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}?handoff=1`

  return (
    <section className={clsx('space-y-3', className)}>
      <div>
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.candidate_requirements.workspace.handoff_title', { defaultValue: 'Handoff readiness' })}
        </h2>
        <p className="mt-0.5 text-xs text-slate-600">
          {t('app.candidate_requirements.workspace.handoff_subtitle', {
            defaultValue: 'Transfer Policy decision — same data as the handoff modal on the candidate card.',
          })}
        </p>
      </div>

      <TransferReadinessReport report={report} loading={loading} canConfirm={canEdit} />

      {showCreateAction ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          {handoffCreateAllowed ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate-700">
                {t('app.candidate_requirements.workspace.handoff_ready_hint', {
                  defaultValue: 'Requirements and policy checks passed — you can create a handoff.',
                })}
              </p>
              <Link to={cardPath} className="btn-primary btn-sm shrink-0">
                {t('app.candidate_requirements.workspace.create_handoff', { defaultValue: 'Create handoff' })}
              </Link>
            </div>
          ) : (
            <p className="text-sm text-amber-900">
              {t('app.candidate_requirements.workspace.handoff_blocked_hint', {
                defaultValue: 'Handoff is blocked until all blockers above are resolved.',
              })}
            </p>
          )}
        </div>
      ) : null}
    </section>
  )
}
