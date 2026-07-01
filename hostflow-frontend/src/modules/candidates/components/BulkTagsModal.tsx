import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'

interface BulkTagsModalProps {
  open: boolean
  onClose: () => void
  bulkTagsOperation: 'add' | 'remove'
  bulkTagsList: string
  onOperationChange: (operation: 'add' | 'remove') => void
  onTagsListChange: (tags: string) => void
  onApply: () => void
  loading: boolean
  canManage?: boolean
}

export function BulkTagsModal({
  open,
  onClose,
  bulkTagsOperation,
  bulkTagsList,
  onOperationChange,
  onTagsListChange,
  onApply,
  loading,
  canManage = true,
}: BulkTagsModalProps) {
  const { t } = useI18n()

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) {
          onClose()
        }
      }}
      title={t('app.candidates.modals.tags.title')}
    >
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_tags_loading')}</span>
          </div>
        )}
        <div>
          <div className="label">{t('app.candidates.modals.tags.operation_label')}</div>
          <select
            className="input"
            value={bulkTagsOperation}
            onChange={(e) => onOperationChange(e.target.value as 'add' | 'remove')}
            disabled={loading}
          >
            <option value="add">{t('app.candidates.modals.tags.operation_add')}</option>
            <option value="remove">{t('app.candidates.modals.tags.operation_remove')}</option>
          </select>
        </div>
        <div>
          <div className="label">{t('app.candidates.modals.tags.tags_label')}</div>
          <input
            className="input w-full"
            value={bulkTagsList}
            onChange={(e) => onTagsListChange(e.target.value)}
            placeholder={t('app.candidates.modals.tags.tags_placeholder')}
            disabled={loading}
          />
          <p className="mt-1.5 text-xs text-slate-500">{t('app.candidates.modals.tags.tags_hint')}</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={onApply} disabled={loading || !bulkTagsList.trim()}>
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {t('common.loading') || 'Загрузка...'}
              </>
            ) : (
              t('common.actions.apply')
            )}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
