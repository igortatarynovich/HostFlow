import { useMemo, useState } from 'react'
import clsx from 'clsx'
import type { HrReviewPanel, WorkforceEmployee, WorkforceEmployeeOperationalProfile } from '../../api/workforce'
import HrDataVerificationWorkspace from './HrDataVerificationWorkspace'
import { EmployeeDossierDocumentBlock } from './EmployeeDossierDocumentBlock'
import { EmployeeDossierPreviewRail } from './EmployeeDossierPreviewRail'
import {
  countVerifiedDocuments,
  documentsFromPanel,
  dossierDocumentList,
  isDocumentVerified,
} from './hrDocumentVerificationFields'
import { humanVerificationBlockingMessages } from './hrVerificationBlockingHuman'
import { formatShortDateIso } from './hrEmployeeUiFormat'
import { useI18n } from '../../i18n'
import { EmployeeDossierHrActions } from './EmployeeDossierHrActions'
import { isVerificationPlanReady } from './hrVerificationReadySummary'

type Props = {
  employeeId: string
  employee: WorkforceEmployee
  profile: WorkforceEmployeeOperationalProfile
  hrReview: HrReviewPanel | null
  manage: boolean
  caseMode?: boolean
  onHrPanelUpdated: (panel: HrReviewPanel) => void
  onScrollTo?: (anchor: string) => void
}

/**
 * Employee dossier: PR14 sequential verification in case mode;
 * per-document blocks in operational profile after approval.
 */
export function EmployeeDossierView({
  employeeId,
  employee,
  profile,
  hrReview,
  manage,
  caseMode = false,
  onHrPanelUpdated,
  onScrollTo,
}: Props) {
  const { t } = useI18n()
  const summary = profile.operational_summary
  const [previewDocKey, setPreviewDocKey] = useState<string | null>(null)

  const docs = useMemo(() => (hrReview ? documentsFromPanel(hrReview) : []), [hrReview])
  const documentBlocks = useMemo(() => dossierDocumentList(docs), [docs])
  const progress = useMemo(() => countVerifiedDocuments(docs), [docs])
  const pendingLabels = useMemo(
    () => documentBlocks.filter((d) => !isDocumentVerified(d)).map((d) => d.label || d.document_key),
    [documentBlocks],
  )
  const blockingMessages = useMemo(
    () => (hrReview ? humanVerificationBlockingMessages(hrReview, docs, t) : []),
    [hrReview, docs, t],
  )

  const previewDoc = useMemo(
    () => documentBlocks.find((d) => d.document_key === previewDocKey) ?? null,
    [documentBlocks, previewDocKey],
  )

  const allDocsConfirmed = progress.total > 0 && progress.verified >= progress.total
  const planReady = hrReview ? isVerificationPlanReady(hrReview) : false
  const candidateId = employee.candidate_id ?? hrReview?.candidate_id ?? null
  const useSequentialFlow = caseMode && Boolean(hrReview)

  return (
    <div
      className={clsx(
        'grid gap-6',
        useSequentialFlow ? 'grid-cols-1' : 'xl:grid-cols-[minmax(0,1fr)_min(420px,38%)] xl:items-start',
      )}
    >
      <div className="min-w-0 space-y-6">
        <section id="hr-verification" className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {caseMode
                  ? t('app.hr.review_case.badge', { defaultValue: 'HR review case' })
                  : t('app.hr.dossier.badge', { defaultValue: 'Employee dossier' })}
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">{employee.display_name}</h2>
              <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-slate-500">{t('app.hr.dossier.status', { defaultValue: 'Status' })}</dt>
                  <dd>{employee.status || '—'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.hr.dossier.position', { defaultValue: 'Position' })}</dt>
                  <dd>{summary.position || '—'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.hr.dossier.employer', { defaultValue: 'Employer' })}</dt>
                  <dd>{summary.employer || '—'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('app.hr.dossier.start', { defaultValue: 'Start date' })}</dt>
                  <dd>{formatShortDateIso(employee.hire_date)}</dd>
                </div>
              </dl>
            </div>
            {!useSequentialFlow ? (
              <div
                className={clsx(
                  'rounded-lg border px-4 py-3 text-sm',
                  allDocsConfirmed
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                    : 'border-amber-200 bg-amber-50 text-amber-950',
                )}
              >
                <p className="font-semibold">
                  {t('app.hr.verify_task.title', { defaultValue: 'Verify documents and data' })}
                </p>
                <p className="mt-1">
                  {progress.total > 0
                    ? t('app.hr.verify_task.progress', {
                        defaultValue: '{verified} of {total} required documents confirmed',
                        values: { verified: progress.verified, total: progress.total },
                      })
                    : t('app.hr.verify_task.no_docs', {
                        defaultValue: 'No required documents in the verification plan yet.',
                      })}
                </p>
                {!allDocsConfirmed && pendingLabels.length > 0 ? (
                  <p className="mt-2 text-xs">
                    {t('app.hr.verify_task.pending_list', {
                      defaultValue: 'Not confirmed yet: {list}',
                      values: { list: pendingLabels.join(', ') },
                    })}
                  </p>
                ) : null}
                {allDocsConfirmed && hrReview?.next_action?.title ? (
                  <p className="mt-2 font-medium">
                    {t('app.hr.verify_task.next_step', {
                      defaultValue: 'Next step: {step}',
                      values: { step: hrReview.next_action.title },
                    })}
                  </p>
                ) : null}
              </div>
            ) : planReady ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                <p className="font-semibold">
                  {t('app.hr.ready.title', { defaultValue: 'Verification complete' })}
                </p>
                <p className="mt-1">
                  {t('app.hr.ready.all_done_hint', {
                    defaultValue: 'All required documents are confirmed. You can approve employment.',
                  })}
                </p>
              </div>
            ) : (
              <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-950">
                <p className="font-semibold">
                  {t('app.hr.verify_task.title', { defaultValue: 'Verify documents and data' })}
                </p>
                {progress.total > 0 ? (
                  <p className="mt-1">
                    {t('app.hr.verify_task.progress', {
                      defaultValue: '{verified} of {total} required documents confirmed',
                      values: { verified: progress.verified, total: progress.total },
                    })}
                  </p>
                ) : null}
              </div>
            )}
          </div>

          {!useSequentialFlow && !allDocsConfirmed && blockingMessages.length > 0 ? (
            <ul className="mt-4 space-y-1 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
              {blockingMessages.map((msg) => (
                <li key={msg}>• {msg}</li>
              ))}
            </ul>
          ) : null}
        </section>

        {!hrReview ? (
          <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('app.hr.verify_shell.no_review_context', {
              defaultValue: 'HR review context is not available for this employee yet.',
            })}
          </p>
        ) : useSequentialFlow ? (
          <HrDataVerificationWorkspace
            panel={hrReview}
            employeeId={employeeId}
            candidateId={candidateId}
            manage={manage}
            onPanelUpdated={onHrPanelUpdated}
          />
        ) : documentBlocks.length === 0 ? (
          <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('app.hr.dossier.no_documents', { defaultValue: 'No documents in the verification plan.' })}
          </p>
        ) : (
          <>
            {documentBlocks.map((doc) => (
              <EmployeeDossierDocumentBlock
                key={doc.document_key}
                doc={doc}
                employeeId={employeeId}
                candidateId={candidateId}
                manage={manage}
                previewActive={previewDocKey === doc.document_key}
                onPreview={() => setPreviewDocKey(doc.document_key)}
                onPanelUpdated={onHrPanelUpdated}
              />
            ))}
            {previewDoc ? (
              <div className="xl:hidden">
                <EmployeeDossierPreviewRail
                  doc={previewDoc}
                  onClose={() => setPreviewDocKey(null)}
                  className="block min-h-0"
                />
              </div>
            ) : null}
          </>
        )}

        {hrReview ? (
          <EmployeeDossierHrActions
            employeeId={employeeId}
            hrReview={hrReview}
            manage={manage}
            caseMode={caseMode}
            allDocsConfirmed={allDocsConfirmed}
            onPanelUpdated={onHrPanelUpdated}
            onScrollTo={onScrollTo}
          />
        ) : null}
      </div>

      {!useSequentialFlow ? (
        <EmployeeDossierPreviewRail
          doc={previewDoc}
          onClose={() => setPreviewDocKey(null)}
          className="hidden min-h-[420px] xl:block"
        />
      ) : null}
    </div>
  )
}
