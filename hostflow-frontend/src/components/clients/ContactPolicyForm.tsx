import { useState } from 'react'
import { useI18n } from '../../i18n'
import type { ContactPolicy } from '../../api/tenantLinks'

type ContactPolicyFormProps = {
  policy: ContactPolicy
  stageOptions: string[]
  saving: boolean
  onSave: (policy: ContactPolicy) => void
  compact?: boolean
}

export function ContactPolicyForm({
  policy,
  stageOptions,
  saving,
  onSave,
  compact = false,
}: ContactPolicyFormProps) {
  const { t } = useI18n()
  const [enabled, setEnabled] = useState(policy.enabled)
  const [maxAttempts, setMaxAttempts] = useState(policy.max_attempts)
  const [postAction, setPostAction] = useState<'auto_reject' | 'stage_change'>(policy.post_action)
  const [stageCode, setStageCode] = useState(policy.stage_code ?? '')

  const handleSave = () => {
    onSave({
      enabled,
      max_attempts: maxAttempts,
      post_action: postAction,
      stage_code: postAction === 'stage_change' ? stageCode || undefined : undefined,
    })
  }

  return (
    <div className={compact ? 'space-y-3' : 'mt-4 rounded-xl border border-brand-100 bg-white p-4'}>
      <p className="text-sm font-medium text-slate-700">
        {t('admin.tenant_links.contact_policy_title', { defaultValue: 'Contact attempts' })}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          <span className="text-sm">{t('admin.tenant_links.policy_enabled')}</span>
        </label>
        <div>
          <label className="label">{t('admin.tenant_links.max_attempts')}</label>
          <input
            type="number"
            min={1}
            max={10}
            value={maxAttempts}
            onChange={(e) => setMaxAttempts(Number(e.target.value) || 3)}
            className="input mt-1 w-20"
          />
        </div>
        <div>
          <label className="label">{t('admin.tenant_links.post_action')}</label>
          <select
            value={postAction}
            onChange={(e) => setPostAction(e.target.value as 'auto_reject' | 'stage_change')}
            className="input mt-1"
          >
            <option value="auto_reject">{t('admin.tenant_links.auto_reject')}</option>
            <option value="stage_change">{t('admin.tenant_links.stage_change')}</option>
          </select>
        </div>
        {postAction === 'stage_change' && (
          <div>
            <label className="label">{t('admin.tenant_links.stage_code')}</label>
            <select value={stageCode} onChange={(e) => setStageCode(e.target.value)} className="input mt-1">
              <option value="">—</option>
              {stageOptions.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      <button type="button" onClick={handleSave} disabled={saving} className="btn-primary mt-2">
        {saving ? t('common.saving') : t('common.save')}
      </button>
    </div>
  )
}
