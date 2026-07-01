import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import CandidateDocuments from '../../modules/documents/CandidateDocuments'
import type { CandidateProfile } from '../../api/candidate_profiles'

export default function CandidateDocsWorkspacePanel({
  candidateId,
  candidateProfile,
  ownerContext,
  isNew,
  disabled,
  uploadingBusy,
  exportingBusy,
  onCreateUploadLink,
  onExportBundle,
}: {
  candidateId: string
  candidateProfile?: CandidateProfile | null
  ownerContext?: Record<string, any>
  isNew: boolean
  disabled?: boolean
  uploadingBusy?: boolean
  exportingBusy?: boolean
  onCreateUploadLink?: () => void
  onExportBundle?: () => void
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (!open) return
    if (mounted) return
    setMounted(true)
  }, [mounted, open])

  const isDisabled = disabled || isNew || !candidateId

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-700">
            {t('app.candidate_card.docs_workspace.title', { defaultValue: 'Documents' })}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">
            {t('app.candidate_card.docs_workspace.hint', { defaultValue: 'Checklist, uploads, checks.' })}
          </div>
        </div>

        <div className="shrink-0 flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="text-[11px] text-slate-500 hover:text-slate-700"
            onClick={() => setOpen((v) => !v)}
            disabled={isDisabled}
            title={isDisabled ? t('app.candidate_card.docs.disabled') : undefined}
          >
            {open ? t('common.actions.collapse') : t('common.actions.expand')}
          </button>
        </div>
      </div>

      {open ? (
        <div className={clsx('mt-3', isDisabled && 'opacity-60')}>
          {isDisabled ? (
            <div className="text-sm text-slate-500">{t('app.candidate_card.docs.disabled')}</div>
          ) : mounted ? (
            <>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                {onCreateUploadLink ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={onCreateUploadLink}
                    disabled={isDisabled || Boolean(uploadingBusy)}
                  >
                    {uploadingBusy
                      ? t('app.candidate_card.actions.upload_link_creating')
                      : t('app.candidate_card.actions.upload_link')}
                  </button>
                ) : null}
                {onExportBundle ? (
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={onExportBundle}
                    disabled={isDisabled || Boolean(exportingBusy)}
                  >
                    {exportingBusy
                      ? t('app.candidate_card.actions.exporting_bundle')
                      : t('app.candidate_card.actions.export_bundle')}
                  </button>
                ) : null}
              </div>
              <CandidateDocuments
                key={String(candidateId)}
                candidateId={String(candidateId)}
                hideHeader
                candidateProfile={candidateProfile}
                {...({
                  ownerContext: ownerContext || {},
                } as any)}
              />
            </>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

