import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'

interface BulkDeleteModalProps {
  open: boolean
  onClose: () => void
  onApply: () => Promise<void>
  loading: boolean
  count: number
  canManage: boolean
}

export function BulkDeleteModal({
  open,
  onClose,
  onApply,
  loading,
  count,
  canManage,
}: BulkDeleteModalProps) {
  const { t } = useI18n()

  return (
    <Modal open={canManage && open} onClose={() => !loading && onClose()} title={t('app.candidates.modals.delete.title')}>
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_delete_loading')}</span>
          </div>
        )}
        <div className="text-sm text-slate-700">
          {t('app.candidates.modals.delete.message', { values: { count } })}
        </div>
        <div className="text-xs text-red-600 bg-red-50 p-3 rounded border border-red-200">
          {t('app.candidates.modals.delete.warning')}
        </div>
        <div className="flex gap-2">
          <button
            className="btn-primary bg-red-600 hover:bg-red-700"
            onClick={onApply}
            disabled={loading || count === 0}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {t('common.loading') || 'Загрузка...'}
              </>
            ) : (
              t('app.candidates.modals.delete.confirm')
            )}
          </button>
          <button
            className="btn-ghost"
            onClick={() => onClose()}
            disabled={loading}
          >
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
