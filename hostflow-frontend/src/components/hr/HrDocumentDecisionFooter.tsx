import { useState } from 'react'
import clsx from 'clsx'
import HrDocumentCorrectionForm from './HrDocumentCorrectionForm'
import HrDocumentRejectForm from './HrDocumentRejectForm'
import { useI18n } from '../../i18n'

export type DecisionFooterMode = 'idle' | 'correction' | 'reject'

type Props = {
  activeIndex: number
  queueLength: number
  documentLabel: string
  busy: boolean
  canConfirm: boolean
  confirmLabel: string
  allFieldsHaveValues: boolean
  canManage: boolean
  canRejectCase: boolean
  onPrevious: () => void
  onNext: () => void
  onConfirm: () => void
  onRequestCorrection: (note: string) => Promise<void>
  onRejectCandidate: (reason: string) => Promise<void>
}

export default function HrDocumentDecisionFooter({
  activeIndex,
  queueLength,
  documentLabel,
  busy,
  canConfirm,
  confirmLabel,
  allFieldsHaveValues,
  canManage,
  canRejectCase,
  onPrevious,
  onNext,
  onConfirm,
  onRequestCorrection,
  onRejectCandidate,
}: Props) {
  const { t } = useI18n()
  const [mode, setMode] = useState<DecisionFooterMode>('idle')

  const closePanels = () => setMode('idle')

  const handleCorrectionSubmit = async (note: string) => {
    await onRequestCorrection(note)
    closePanels()
  }

  const handleRejectSubmit = async (reason: string) => {
    await onRejectCandidate(reason)
    closePanels()
  }

  if (!canManage) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={activeIndex <= 0}
          onClick={onPrevious}
        >
          {t('app.hr.verify_shell.previous', { defaultValue: 'Previous document' })}
        </button>
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={activeIndex >= queueLength - 1}
          onClick={onNext}
        >
          {t('app.hr.verify_shell.next', { defaultValue: 'Next document' })}
        </button>
      </div>
    )
  }

  return (
    <div>
      {mode === 'correction' ? (
        <HrDocumentCorrectionForm
          documentLabel={documentLabel}
          busy={busy}
          onCancel={closePanels}
          onSubmit={(note) => void handleCorrectionSubmit(note)}
        />
      ) : null}
      {mode === 'reject' ? (
        <HrDocumentRejectForm busy={busy} onCancel={closePanels} onSubmit={(reason) => void handleRejectSubmit(reason)} />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={activeIndex <= 0 || busy}
          onClick={onPrevious}
        >
          {t('app.hr.verify_shell.previous', { defaultValue: 'Previous document' })}
        </button>
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={activeIndex >= queueLength - 1 || busy}
          onClick={onNext}
        >
          {t('app.hr.verify_shell.next', { defaultValue: 'Next document' })}
        </button>
      </div>

      <div
        className={clsx(
          'mt-3 flex flex-wrap items-center gap-2',
          mode !== 'idle' && 'pointer-events-none opacity-40',
        )}
      >
        {canConfirm ? (
          <button
            type="button"
            className="btn-primary min-w-[10rem] flex-1 sm:flex-none"
            disabled={busy || !allFieldsHaveValues || mode !== 'idle'}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        ) : null}
        <button
          type="button"
          className={clsx(
            'btn-secondary flex-1 sm:flex-none',
            mode === 'correction' && 'ring-2 ring-amber-400',
          )}
          disabled={busy || mode === 'reject'}
          onClick={() => setMode((m) => (m === 'correction' ? 'idle' : 'correction'))}
        >
          {t('app.hr.decisions.request_correction', { defaultValue: 'Request correction' })}
        </button>
        {canRejectCase ? (
          <button
            type="button"
            className={clsx(
              'rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-800 hover:bg-rose-50',
              mode === 'reject' && 'ring-2 ring-rose-400',
            )}
            disabled={busy || mode === 'correction'}
            onClick={() => setMode((m) => (m === 'reject' ? 'idle' : 'reject'))}
          >
            {t('app.hr.decisions.reject_candidate', { defaultValue: 'Reject candidate' })}
          </button>
        ) : null}
      </div>
    </div>
  )
}
