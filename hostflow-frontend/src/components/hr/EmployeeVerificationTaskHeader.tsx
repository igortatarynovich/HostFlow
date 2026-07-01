import { useMemo } from 'react'
import type { HrReviewPanel } from '../../api/workforce'
import BlockerPanel from '../surfaces/BlockerPanel'
import { humanVerificationBlockingMessages } from './hrVerificationBlockingHuman'
import {
  countVerifiedDocuments,
  documentsFromPanel,
  requiredPlanDocuments,
  sequentialDocumentQueue,
  isDocumentVerified,
} from './hrDocumentVerificationFields'
import { useI18n } from '../../i18n'

type Props = {
  panel: HrReviewPanel | null
}

/** Plain status strip: verify documents and data — no hero, no packs. */
export function EmployeeVerificationTaskHeader({ panel }: Props) {
  const { t } = useI18n()

  const { progress, pendingLabels, blockingMessages, nextStepTitle } = useMemo(() => {
    if (!panel) {
      return {
        progress: { verified: 0, total: 0 },
        pendingLabels: [] as string[],
        blockingMessages: [] as string[],
        nextStepTitle: null as string | null,
      }
    }
    const docs = documentsFromPanel(panel)
    const queue = sequentialDocumentQueue(requiredPlanDocuments(docs))
    const progress = countVerifiedDocuments(docs)
    const pendingLabels = queue.filter((d) => !isDocumentVerified(d)).map((d) => d.label || d.document_key)
    const blockingMessages = humanVerificationBlockingMessages(panel, docs, t)
    const planReady = panel.verification_plan?.can_approve === true
    const nextStepTitle = planReady ? panel.next_action?.title ?? panel.next_required_action ?? null : null
    return { progress, pendingLabels, blockingMessages, nextStepTitle }
  }, [panel, t])

  if (!panel) return null

  const allDone = progress.total > 0 && progress.verified >= progress.total

  return (
    <div id="employee-verification-task" className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-900">
        {t('app.hr.verify_task.title', { defaultValue: 'Verify documents and data' })}
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        {progress.total > 0
          ? t('app.hr.verify_task.progress', {
              defaultValue: '{verified} of {total} required documents confirmed',
              values: { verified: progress.verified, total: progress.total },
            })
          : t('app.hr.verify_task.no_docs', { defaultValue: 'No required documents in the verification plan yet.' })}
      </p>

      {!allDone && pendingLabels.length > 0 ? (
        <p className="mt-2 text-sm text-amber-900">
          {t('app.hr.verify_task.pending_list', {
            defaultValue: 'Not confirmed yet: {list}',
            values: { list: pendingLabels.join(', ') },
          })}
        </p>
      ) : null}

      {!allDone && blockingMessages.length > 0 ? (
        <BlockerPanel
          className="mt-3"
          title={t('app.hr.verify_task.blockers', { defaultValue: 'Still needed' })}
          severity="blocker"
          items={blockingMessages.map((msg, index) => ({
            id: `${index}-${msg}`,
            label: msg,
            severity: 'blocker' as const,
          }))}
        />
      ) : null}

      {allDone ? (
        <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          {t('app.hr.verify_task.all_confirmed', {
            defaultValue: 'All required documents are confirmed.',
          })}
          {nextStepTitle ? (
            <p className="mt-1 font-medium">
              {t('app.hr.verify_task.next_step', {
                defaultValue: 'Next step: {step}',
                values: { step: nextStepTitle },
              })}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
