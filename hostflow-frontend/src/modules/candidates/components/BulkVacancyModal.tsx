import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'
import type { Vacancy } from '../../../api/types'

interface BulkVacancyModalProps {
  open: boolean
  onClose: () => void
  vacancies: Vacancy[]
  bulkVacancyId: string
  onVacancyIdChange: (id: string) => void
  onApply: () => void
  loading: boolean
  canManage?: boolean
}

export function BulkVacancyModal({
  open,
  onClose,
  vacancies,
  bulkVacancyId,
  onVacancyIdChange,
  onApply,
  loading,
  canManage = true,
}: BulkVacancyModalProps) {
  const { t } = useI18n()

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) {
          onClose()
        }
      }}
      title={t('app.candidates.modals.vacancy.title')}
    >
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_vacancy_loading')}</span>
          </div>
        )}
        <div>
          <div className="label">{t('app.candidates.modals.vacancy.label')}</div>
          <select
            className="input"
            value={bulkVacancyId}
            onChange={(e) => onVacancyIdChange(e.target.value)}
            disabled={loading}
          >
            <option value="">{t('app.candidates.select.placeholder')}</option>
            {vacancies.map((v) => (
              <option key={v.id} value={v.id}>
                {(v as any).title || t('app.candidates.labels.untitled')}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={onApply} disabled={loading || !bulkVacancyId}>
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
