import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import type { Company, ManagerOption, UserRole } from '../../api/types'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'

export interface CreateUserFormValues {
  email: string
  role: UserRole
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

const ROLE_OPTIONS: UserRole[] = [
  'administrator',
  'supervisor',
  'recruiter',
  'client_manager',
  'client_processor',
  'compliance_officer',
  'hr_officer',
  'viewer',
]
const ROLE_LABELS: Record<UserRole, string> = {
  administrator: 'app.admin.users.roles.administrator',
  supervisor: 'app.admin.users.roles.supervisor',
  recruiter: 'app.admin.users.roles.recruiter',
  client_manager: 'app.admin.users.roles.client_manager',
  client_processor: 'app.admin.users.roles.client_processor',
  compliance_officer: 'app.admin.users.roles.compliance_officer',
  hr_officer: 'app.admin.users.roles.hr_officer',
  viewer: 'app.admin.users.roles.viewer',
}

export function UserFormCreate({ loading, managerOptions, companyOptions, onSubmit }: UserFormCreateProps) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<UserRole>('supervisor')
  const [fullName, setFullName] = useState('')
  const [shortId, setShortId] = useState('')
  const [password, setPassword] = useState('')
  const [supervisorId, setSupervisorId] = useState('')
  const [companyIds, setCompanyIds] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const { t } = useI18n()

  const showSupervisorSelect = role === 'recruiter' || role === 'supervisor'
  const supervisorRequired = role === 'recruiter'
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
      role,
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
    setRole('supervisor')
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
              const nextRole = event.target.value as UserRole
              setRole(nextRole)
              if (nextRole !== 'recruiter') {
                setSupervisorId('')
              }
            }}
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(ROLE_LABELS[option])}
              </option>
            ))}
          </select>
        </label>

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
