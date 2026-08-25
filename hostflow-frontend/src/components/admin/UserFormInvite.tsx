import type { FormEvent } from 'react'
import { useState } from 'react'
import type { Company, ManagerOption, UserRole } from '../../api/types'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import {
  TRUST_ROLE_LABEL_KEYS,
  TRUST_ROLE_OPTIONS,
  PRESET_LABEL_KEYS,
  asAssignableUserRole,
  defaultPresetForTrustRole,
  presetsForTrustRole,
  type PermissionPresetId,
  type TrustRoleOption,
} from '../../modules/users/roleOptions'

type InviteFormPayload = {
  email: string
  role: UserRole
  preset_id?: string | null
  supervisor_id?: string | null
  company_ids?: string[]
  expires_in_hours?: number
}

interface UserFormInviteProps {
  onSubmit: (payload: InviteFormPayload) => Promise<void> | void
  loading?: boolean
  managerOptions: ManagerOption[]
  companyOptions: Company[]
}

export function UserFormInvite({ onSubmit, loading, managerOptions, companyOptions }: UserFormInviteProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<TrustRoleOption>('employee')
  const [presetId, setPresetId] = useState<PermissionPresetId | ''>('recruiter')
  const [expiresIn, setExpiresIn] = useState(72)
  const [supervisorId, setSupervisorId] = useState('')
  const [companyIds, setCompanyIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const { t } = useI18n()

  const presetChoices = presetsForTrustRole(role)
  const showSupervisorSelect = role === 'employee' && (presetId === 'recruiter' || presetId === 'team_lead')
  const supervisorRequired = presetId === 'recruiter'
  const showCompanySelect = role !== 'administrator'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextEmail = email.trim()
    if (!nextEmail) {
      setError(t('app.admin.users.errors.email_required'))
      return
    }
    if (supervisorRequired && !supervisorId) {
      setError(t('app.admin.users.errors.supervisor_required'))
      return
    }

    setError(null)
    await onSubmit({
      email: nextEmail,
      role: asAssignableUserRole(role),
      preset_id: presetId || undefined,
      supervisor_id: supervisorId || undefined,
      company_ids: showCompanySelect ? companyIds : [],
      expires_in_hours: expiresIn || undefined,
    })
    setEmail('')
    setRole('employee')
    setPresetId('recruiter')
    setExpiresIn(72)
    setSupervisorId('')
    setCompanyIds([])
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <label className="label" htmlFor="invite-email">{t('app.admin.users.form.email_label')}</label>
        <input
          id="invite-email"
          type="email"
          required
          placeholder={t('app.admin.users.form.email_placeholder')}
          autoComplete="off"
          value={email}
          onChange={(ev) => setEmail(ev.target.value)}
          className="input w-full"
        />
      </div>

      <div>
        <label className="label" htmlFor="invite-role">{t('app.admin.users.form.role_label')}</label>
        <select
          id="invite-role"
          className="input w-full"
          value={role}
          onChange={(ev) => {
            const nextRole = ev.target.value as TrustRoleOption
            setRole(nextRole)
            setPresetId(defaultPresetForTrustRole(nextRole))
            setSupervisorId('')
          }}
        >
          {TRUST_ROLE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {t(TRUST_ROLE_LABEL_KEYS[opt])}
            </option>
          ))}
        </select>
      </div>

      {presetChoices.length > 0 && (
        <div>
          <label className="label" htmlFor="invite-preset">
            {t('app.admin.users.form.preset_label', { defaultValue: 'Permission preset' })}
          </label>
          <select
            id="invite-preset"
            className="input w-full"
            value={presetId}
            onChange={(ev) => {
              const next = ev.target.value as PermissionPresetId | ''
              setPresetId(next)
              if (next !== 'recruiter') setSupervisorId('')
            }}
          >
            <option value="">
              {t('app.admin.users.form.preset_none', { defaultValue: 'None (role defaults)' })}
            </option>
            {presetChoices.map((opt) => (
              <option key={opt} value={opt}>
                {t(PRESET_LABEL_KEYS[opt], { defaultValue: opt })}
              </option>
            ))}
          </select>
        </div>
      )}

      {showSupervisorSelect && (
        <div>
          <label className="label" htmlFor="invite-supervisor">
            {t('app.admin.users.form.supervisor_label')} {supervisorRequired && <span className="text-red-500">*</span>}
          </label>
          <select
            id="invite-supervisor"
            className="input w-full"
            value={supervisorId}
            required={supervisorRequired}
            onChange={(ev) => setSupervisorId(ev.target.value)}
          >
            <option value="">
              {supervisorRequired
                ? t('app.admin.users.form.supervisor_placeholder_required')
                : t('app.admin.users.form.supervisor_placeholder_optional')}
            </option>
            {managerOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label || opt.full_name || opt.email}
              </option>
            ))}
          </select>
        </div>
      )}

      {showCompanySelect && (
        <div>
          <label className="label" htmlFor="invite-companies">{t('app.admin.users.form.companies_label')}</label>
          <select
            id="invite-companies"
            multiple
            className="input w-full h-24"
            value={companyIds}
            onChange={(ev) => setCompanyIds(Array.from(ev.target.selectedOptions).map((opt) => opt.value))}
          >
            {companyOptions.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className="label" htmlFor="invite-expiry">{t('app.admin.users.invite.expiry_label')}</label>
        <input
          id="invite-expiry"
          type="number"
          min={1}
          max={720}
          autoComplete="off"
          value={expiresIn}
          onChange={(ev) => setExpiresIn(Number(ev.target.value))}
          className="input w-full"
        />
      </div>

      {error && (
        <ErrorRecoveryBanner
          info={{
            title: error,
            hint: t('app.common.retry_hint'),
          }}
          onRetry={() => setError(null)}
          retryLabel={t('common.actions.close', { defaultValue: 'Close' })}
          compact
        />
      )}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? t('app.admin.users.invite.submitting') : t('app.admin.users.invite.submit')}
      </button>
    </form>
  )
}
