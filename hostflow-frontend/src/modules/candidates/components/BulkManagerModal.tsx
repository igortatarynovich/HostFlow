import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'
import type { ManagerItem } from '../types'

interface BulkManagerModalProps {
  open: boolean
  onClose: () => void
  managers: ManagerItem[]
  bulkManagerId: string
  onManagerIdChange: (id: string) => void
  onApply: () => void
  loading: boolean
  canManage?: boolean
}

export function BulkManagerModal({
  open,
  onClose,
  managers,
  bulkManagerId,
  onManagerIdChange,
  onApply,
  loading,
  canManage = true,
}: BulkManagerModalProps) {
  const { t } = useI18n()

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) {
          onClose()
        }
      }}
      title={t('app.candidates.modals.manager.title')}
    >
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_manager_loading')}</span>
          </div>
        )}
        <div>
          <div className="label">{t('app.candidates.modals.manager.label')}</div>
          <select
            className="input"
            value={bulkManagerId}
            onChange={(e) => onManagerIdChange(e.target.value)}
            disabled={loading}
          >
            <option value="">{t('app.candidates.select.placeholder')}</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={onApply} disabled={loading || !bulkManagerId}>
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {t('common.loading') || 'Загрузка...'}
              </>
            ) : (
              t('common.actions.apply')
            )}
          </button>
          <button className="btn-ghost" onClick={onClose} disabled={loading}>
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
