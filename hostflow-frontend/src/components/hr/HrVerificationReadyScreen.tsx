import { useMemo } from 'react'
import type { HrReviewPanel } from '../../api/workforce'
import { useI18n } from '../../i18n'
import HrReviewPanelCard from './HrReviewPanel'
import BlockerPanel from '../surfaces/BlockerPanel'
import { humanVerificationBlockingMessages } from './hrVerificationBlockingHuman'
import { countVerifiedDocuments, documentsFromPanel } from './hrDocumentVerificationFields'
import { isHrApproveAllowed } from '../../utils/hrReviewApprove'
import { isVerificationPlanReady, verificationReadyGroups } from './hrVerificationReadySummary'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
  onReviewDocuments?: () => void
}

export default function HrVerificationReadyScreen({
  panel,
  employeeId,
  handoffId,
  manage,
  onPanelUpdated,
  onReviewDocuments,
}: Props) {
  const { t } = useI18n()
  const docs = useMemo(() => documentsFromPanel(panel), [panel])
  const progress = useMemo(() => countVerifiedDocuments(docs), [docs])
  const groups = useMemo(() => verificationReadyGroups(panel), [panel])
  const blockingMessages = useMemo(
    () => humanVerificationBlockingMessages(panel, docs, t),
    [panel, docs, t],
  )
  const approveAllowed = isHrApproveAllowed(panel)
  const planReady = isVerificationPlanReady(panel)

  return (
    <section id="hr-document-verification" className="scroll-mt-24 space-y-4">
      <div className="overflow-hidden rounded-xl border border-emerald-200 bg-gradient-to-b from-emerald-50/90 to-white shadow-md">
        <header className="border-b border-emerald-100 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
            {t('app.hr.ready.phase', { defaultValue: 'Document verification' })}
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">
            {t('app.hr.ready.title', { defaultValue: 'Verification complete' })}
          </h2>
          <p className="mt-1 text-sm text-emerald-900">
            {t('app.hr.ready.headline_confirmed', {
              defaultValue: 'All required documents confirmed',
            })}
          </p>
          <p className="text-sm text-slate-600">
            {t('app.hr.ready.headline_decision', {
              defaultValue: 'The candidate is ready for an employment decision.',
            })}
          </p>
          {progress.total > 0 ? (
            <p className="mt-2 text-sm font-medium text-slate-700">
              {t('app.hr.ready.progress', {
                defaultValue: '{verified} of {total} required documents confirmed',
                values: { verified: progress.verified, total: progress.total },
              })}
            </p>
          ) : null}
          {manage && onReviewDocuments ? (
            <button type="button" className="btn-secondary btn-xs mt-3" onClick={onReviewDocuments}>
              {t('app.hr.ready.review_documents', { defaultValue: 'Review confirmed documents' })}
            </button>
          ) : null}
        </header>

        <div className="grid gap-4 p-4 sm:grid-cols-2">
          {groups.confirmed.length > 0 ? (
            <div className="rounded-lg border border-emerald-100 bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                {t('app.hr.ready.summary_confirmed', { defaultValue: 'Confirmed' })}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-slate-800">
                {groups.confirmed.map((row) => (
                  <li key={row.key}>✓ {row.label}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {groups.waived.length > 0 ? (
            <div className="rounded-lg border border-amber-100 bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
                {t('app.hr.ready.summary_waived', { defaultValue: 'Exceptions (waived)' })}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-slate-800">
                {groups.waived.map((row) => (
                  <li key={row.key}>
                    {row.label}
                    {row.reason ? (
                      <span className="block text-xs text-slate-500">
                        {t('app.hr.ready.waive_reason', {
                          defaultValue: 'Reason: {reason}',
                          values: { reason: row.reason },
                        })}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {groups.hrRequested.length > 0 ? (
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                {t('app.hr.ready.summary_hr_requested', { defaultValue: 'HR-requested documents' })}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-slate-800">
                {groups.hrRequested.map((row) => (
                  <li key={row.key}>
                    {row.label}
                    {row.reason === 'pending' ? (
                      <span className="ml-1 text-xs text-amber-800">
                        ({t('app.hr.exceptions.hr_requested_pending', { defaultValue: 'Pending' })})
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {groups.recommendedPending.length > 0 ? (
            <div className="rounded-lg border border-slate-100 bg-slate-50/80 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                {t('app.hr.ready.summary_recommended', { defaultValue: 'Recommended (optional)' })}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {groups.recommendedPending.map((row) => (
                  <li key={row.key}>{row.label}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">
                {t('app.hr.ready.recommended_hint', {
                  defaultValue: 'Still missing — does not block employment approval.',
                })}
              </p>
            </div>
          ) : null}
        </div>

        {!approveAllowed && blockingMessages.length > 0 ? (
          <div className="border-t border-emerald-100 px-4 pb-4">
            <BlockerPanel
              title={t('app.hr.ready.still_needed', { defaultValue: 'Still needed before approval' })}
              severity="blocker"
              items={blockingMessages.map((msg, index) => ({
                id: `${index}-${msg}`,
                label: msg,
                severity: 'blocker' as const,
              }))}
            />
          </div>
        ) : null}
      </div>

      {planReady ? (
        <HrReviewPanelCard
          panel={panel}
          manage={manage}
          onUpdated={onPanelUpdated || (() => {})}
          employeeId={employeeId}
          handoffId={handoffId}
          hideDocuments
          caseDecisionMode
        />
      ) : null}
    </section>
  )
}
