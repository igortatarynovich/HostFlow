import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'
import { ACTIVITY_TEMPLATES } from '../activityTemplates'

type BulkActivitiesModalProps = {
  open: boolean
  onClose: () => void
  title: string
  dueAt: string
  offsetMinutes: number
  onTitleChange: (v: string) => void
  onDueAtChange: (v: string) => void
  onOffsetMinutesChange: (v: number) => void
  onApply: () => void
  loading: boolean
  canManage?: boolean
  /** Activity type sent to API (call, email, document_request, follow_up, custom) */
  activityType?: string
  onActivityTypeChange?: (type: string) => void
}

export function BulkActivitiesModal({
  open,
  onClose,
  title,
  dueAt,
  offsetMinutes,
  onTitleChange,
  onDueAtChange,
  onOffsetMinutesChange,
  onApply,
  loading,
  canManage = true,
  activityType = 'custom',
  onActivityTypeChange,
}: BulkActivitiesModalProps) {
  const { t } = useI18n()

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) onClose()
      }}
      title={t('app.candidates.modals.activities.title', { defaultValue: 'Create activities for selected' })}
    >
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_activities_loading', { defaultValue: 'Creating…' })}</span>
          </div>
        )}

        <div>
          <div className="label">{t('app.leads.bulk.activities.template_label', { defaultValue: 'Quick type' })}</div>
          <div className="flex flex-wrap gap-2">
            {ACTIVITY_TEMPLATES.map((tmpl) => (
              <button
                key={tmpl.key}
                type="button"
                disabled={loading}
                className={
                  activityType === tmpl.type
                    ? 'rounded-lg border border-brand-500 bg-brand-100 px-3 py-1.5 text-xs font-medium text-brand-800'
                    : 'rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50'
                }
                onClick={() => {
                  onTitleChange(tmpl.defaultTitle)
                  onOffsetMinutesChange(tmpl.defaultOffsetMinutes)
                  onActivityTypeChange?.(tmpl.type)
                }}
              >
                {t(`app.activities.templates.${tmpl.key}`, { defaultValue: tmpl.defaultTitle })}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="label">{t('app.candidates.modals.activities.title_label', { defaultValue: 'Activity title' })}</div>
          <input className="input w-full" value={title} onChange={(e) => onTitleChange(e.target.value)} disabled={loading} />
        </div>

        <div>
          <div className="label">{t('app.candidates.modals.activities.due_label', { defaultValue: 'Due at' })}</div>
          <input
            className="input w-full"
            type="datetime-local"
            value={dueAt}
            onChange={(e) => onDueAtChange(e.target.value)}
            disabled={loading}
          />
        </div>

        <div>
          <div className="label">{t('app.candidates.modals.activities.offset_label', { defaultValue: 'Reminder offset (minutes before)' })}</div>
          <input
            className="input w-full"
            type="number"
            min={0}
            step={5}
            value={String(offsetMinutes)}
            onChange={(e) => onOffsetMinutesChange(Number(e.target.value || 0))}
            disabled={loading}
          />
        </div>

        <div className="flex gap-2">
          <button className="btn-primary" onClick={onApply} disabled={loading || !title.trim() || !dueAt.trim()}>
            {loading ? t('common.loading', { defaultValue: 'Loading…' }) : t('common.actions.apply', { defaultValue: 'Apply' })}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
          </button>
        </div>
      </div>
    </Modal>
  )
}

