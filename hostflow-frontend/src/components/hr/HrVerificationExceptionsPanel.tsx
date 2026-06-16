import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { useI18n } from '../../i18n'

type Props = {
  panel: HrReviewPanel
  activeDoc: HrReviewDocumentRow
  canManage: boolean
  busy: boolean
  onWaive: () => void
  onRequestAdditional: () => void
}

export default function HrVerificationExceptionsPanel({
  panel,
  activeDoc,
  canManage,
  busy,
  onWaive,
  onRequestAdditional,
}: Props) {
  const { t } = useI18n()
  if (!canManage) return null
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
        {t('app.hr.verify_shell.exceptions', { defaultValue: 'Exceptions' })}
      </p>
      <p className="mt-1 text-xs text-slate-600">
        {t('app.hr.verify_shell.exceptions_hint', {
          defaultValue: 'If this requirement is not applicable or extra proof is needed, use actions below.',
        })}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button type="button" className="btn-secondary btn-xs" disabled={busy} onClick={onWaive}>
          {t('app.hr.verify_shell.waive_requirement', { defaultValue: 'Waive requirement' })}
        </button>
        <button type="button" className="btn-secondary btn-xs" disabled={busy} onClick={onRequestAdditional}>
          {t('app.hr.verify_shell.request_additional', { defaultValue: 'Request additional document' })}
        </button>
      </div>
      {(panel.return_reason || activeDoc.verification_note) && (
        <p className="mt-2 text-xs text-slate-500">
          {activeDoc.verification_note || panel.return_reason}
        </p>
      )}
    </div>
  )
}

