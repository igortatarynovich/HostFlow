import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
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

export interface CreateUserFormValues {
  email: string
  role: UserRole
  preset_id?: string | null
  full_name?: string | null
  short_id?: string | null
  password?: string | null
  supervisor_id?: string | null
  company_ids?: string[]
}

interface UserFormCreateProps {
  loading?: boolean
  managerOptions: ManagerOption[]
  companyOptions: Company[]
  onSubmit: (values: CreateUserFormValues) => Promise<void> | void
}

export function UserFormCreate({ loading, managerOptions, companyOptions, onSubmit }: UserFormCreateProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<TrustRoleOption>('employee')
  const [presetId, setPresetId] = useState<PermissionPresetId | ''>('recruiter')
  const [fullName, setFullName] = useState('')
  const [shortId, setShortId] = useState('')
  const [password, setPassword] = useState('')
  const [supervisorId, setSupervisorId] = useState('')
  const [companyIds, setCompanyIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const { t } = useI18n()

  const presetChoices = presetsForTrustRole(role)
  const showSupervisorSelect = role === 'employee' && (presetId === 'recruiter' || presetId === 'team_lead')
  const supervisorRequired = presetId === 'recruiter'
  const showCompanySelect = role !== 'administrator'

  const companyOptionsMemo = useMemo(() => companyOptions ?? [], [companyOptions])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextEmail = email.trim()
    if (!nextEmail) {
      setError(t('app.admin.users.errors.email_required'))
      return
    }
    const trimmedPassword = password.trim()
    if (trimmedPassword && trimmedPassword.length < 8) {
      setError(t('app.admin.users.errors.password_short'))
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
      full_name: fullName.trim() || undefined,
      short_id: shortId.trim() || undefined,
      password: trimmedPassword || undefined,
      supervisor_id: supervisorId || undefined,
      company_ids: showCompanySelect ? companyIds : [],
    })

    setEmail('')
    setFullName('')
    setShortId('')
    setPassword('')
    setSupervisorId('')
    setCompanyIds([])
    setRole('employee')
    setPresetId('recruiter')
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="grid gap-3">
        <label className="block">
          <div className="label">{t('app.admin.users.form.email_label')}</div>
          <input
            type="email"
            required
            className="input w-full"
            placeholder={t('app.admin.users.form.email_placeholder')}
            autoComplete="off"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="block">
          <div className="label">{t('app.admin.users.form.full_name_label')}</div>
          <input
            type="text"
            className="input w-full"
            placeholder={t('app.admin.users.form.full_name_placeholder')}
            autoComplete="off"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </label>

        <label className="block">
          <div className="label">{t('app.admin.users.form.short_id_label')}</div>
          <input
            type="text"
            className="input w-full"
            placeholder={t('app.admin.users.form.short_id_placeholder')}
            autoComplete="off"
            value={shortId}
            onChange={(event) => setShortId(event.target.value)}
          />
        </label>

        <label className="block">
          <div className="label">{t('app.admin.users.form.role_label')}</div>
          <select
            className="input w-full"
            value={role}
            onChange={(event) => {
              const nextRole = event.target.value as TrustRoleOption
              setRole(nextRole)
              setPresetId(defaultPresetForTrustRole(nextRole))
              setSupervisorId('')
            }}
          >
            {TRUST_ROLE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(TRUST_ROLE_LABEL_KEYS[option])}
              </option>
            ))}
          </select>
        </label>

        {presetChoices.length > 0 && (
          <label className="block">
            <div className="label">
              {t('app.admin.users.form.preset_label', { defaultValue: 'Permission preset' })}
            </div>
            <select
              className="input w-full"
              value={presetId}
              onChange={(event) => {
                const next = event.target.value as PermissionPresetId | ''
                setPresetId(next)
                if (next !== 'recruiter') setSupervisorId('')
              }}
            >
              <option value="">
                {t('app.admin.users.form.preset_none', { defaultValue: 'None (role defaults)' })}
              </option>
              {presetChoices.map((option) => (
                <option key={option} value={option}>
                  {t(PRESET_LABEL_KEYS[option], { defaultValue: option })}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              {t('app.admin.users.form.preset_help', {
                defaultValue: 'Fills module permissions for this user — does not create a system role.',
              })}
            </p>
          </label>
        )}

        {showSupervisorSelect && (
          <label className="block">
            <div className="label">
              {t('app.admin.users.form.supervisor_label')}{' '}
              {supervisorRequired && <span className="text-red-500">*</span>}
            </div>
            <select
              className="input w-full"
              value={supervisorId}
              required={supervisorRequired}
              onChange={(event) => setSupervisorId(event.target.value)}
            >
              <option value="">
                {supervisorRequired
                  ? t('app.admin.users.form.supervisor_placeholder_required')
                  : t('app.admin.users.form.supervisor_placeholder_optional')}
              </option>
              {managerOptions.map((manager) => (
                <option key={manager.id} value={manager.id}>
                  {manager.label || manager.full_name || manager.email}
                </option>
              ))}
            </select>
          </label>
        )}

        {showCompanySelect && (
          <label className="block">
            <div className="label">{t('app.admin.users.form.companies_label')}</div>
            <select
              multiple
              className="input w-full h-28"
              value={companyIds}
              onChange={(event) =>
                setCompanyIds(Array.from(event.target.selectedOptions).map((opt) => opt.value))
              }
            >
              {companyOptionsMemo.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <div className="label">{t('app.admin.users.form.password_label')}</div>
          <input
            type="password"
            className="input w-full"
            placeholder={t('app.admin.users.form.password_placeholder')}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
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
        {loading ? t('app.admin.users.form.submitting') : t('app.admin.users.form.submit')}
      </button>
    </form>
  )
}
