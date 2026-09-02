import { Modal } from '../../components/Modal'
import { useI18n } from '../../i18n'

export type LifecycleMessagePurpose = 'rodo' | 'application_received' | 'rejection' | 'moving_forward'

export type LifecycleMessageDraft = {
  name: string
  subject: string
  body: string
}

export function LeadLifecycleMessageModal({
  open,
  purpose,
  draft,
  busy,
  onChange,
  onClose,
  onSaveAndUse,
}: {
  open: boolean
  purpose: LifecycleMessagePurpose
  draft: LifecycleMessageDraft
  busy: boolean
  onChange: (next: LifecycleMessageDraft) => void
  onClose: () => void
  onSaveAndUse: () => void
}) {
  const { t } = useI18n()
  const title =
    purpose === 'rodo'
      ? t('admin.lead_lifecycle_email.composer.title_rodo')
      : t('admin.lead_lifecycle_email.composer.title_ops')
  const canSave = Boolean(draft.name.trim() && draft.subject.trim() && draft.body.trim())

  return (
    <Modal open={open} onClose={onClose} title={title} size="lg">
      <div className="space-y-3">
        <label className="block text-sm text-slate-700">
          {t('admin.lead_lifecycle_email.composer.name')}
          <input
            className="input mt-1 w-full"
            value={draft.name}
            onChange={(e) => onChange({ ...draft, name: e.target.value })}
          />
        </label>
        <label className="block text-sm text-slate-700">
          {t('admin.lead_lifecycle_email.composer.subject')}
          <input
            className="input mt-1 w-full"
            value={draft.subject}
            onChange={(e) => onChange({ ...draft, subject: e.target.value })}
          />
        </label>
        <label className="block text-sm text-slate-700">
          {t('admin.lead_lifecycle_email.composer.body')}
          <textarea
            className="input mt-1 min-h-[180px] w-full"
            value={draft.body}
            onChange={(e) => onChange({ ...draft, body: e.target.value })}
          />
        </label>
        {purpose === 'rodo' ? (
          <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
            {t('admin.lead_lifecycle_email.composer.link_note')}
          </p>
        ) : null}
        <div className="flex flex-wrap justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" disabled={busy} onClick={onClose}>
            {t('admin.lead_lifecycle_email.composer.cancel')}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={busy || !canSave}
            onClick={onSaveAndUse}
          >
            {busy
              ? t('admin.lead_lifecycle_email.composer.saving')
              : t('admin.lead_lifecycle_email.composer.save_and_use')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
