import { useI18n } from '../../../i18n'
import CandidateDocuments from '../../../modules/documents/CandidateDocuments'

type Props = {
  open: boolean
  candidateId: string
  initialType?: string
  onClose: () => void
  onDocumentsChanged?: () => void
}

export default function RequirementScopedDocumentsDrawer({
  open,
  candidateId,
  initialType,
  onClose,
  onDocumentsChanged,
}: Props) {
  const { t } = useI18n()

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/50 p-4" onClick={onClose}>
      <div
        className="fixed right-0 top-0 h-full w-full max-w-6xl overflow-hidden rounded-l-2xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-3">
          <div className="min-w-0 truncate text-sm font-semibold text-slate-900">
            {t('app.candidate_card.docs_panel.title', { defaultValue: 'Documents' })}
          </div>
          <button type="button" className="btn-secondary btn-sm" onClick={onClose}>
            {t('common.actions.close', { defaultValue: 'Close' })}
          </button>
        </div>
        <div className="h-[calc(100%-3.25rem)] overflow-auto p-3">
          <CandidateDocuments
            key={`${candidateId}:${initialType || 'default'}`}
            candidateId={candidateId}
            hideHeader
            initialType={initialType}
            onDocumentsChanged={onDocumentsChanged}
          />
        </div>
      </div>
    </div>
  )
}
