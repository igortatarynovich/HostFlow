import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import {
  changeUserRole,
  createTenantUser,
  createUserInvite,
  fetchUserAudit,
  fetchUserDetail,
  listAdminUsers,
  listTenantManagers,
  revokeRefreshTokens,
  setUserActive,
  updateUserSupervisor,
  updateUserCompanies,
  resetUserPassword,
  changeUserPasswordAdmin,
  deleteUserAdmin,
} from '../../api/users'
import type {
  AdminUser,
  AdminUserDetail,
  Company,
  ManagerOption,
  PlatformTenant,
  UserAuditEntry,
  UserInvite,
  UserRole,
} from '../../api/types'
import type { AdminUserCreateResponse } from '../../api/users'
import { listCompanies } from '../../api/client'
import { getPlatformTenant, listPlatformTenants } from '../../api/tenants'
import { useAuth } from '../../store/useAuth'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { UserFormCreate } from '../../components/admin/UserFormCreate'
import { UserFormInvite } from '../../components/admin/UserFormInvite'
import { useI18n } from '../../i18n'
import { TeamManagementPanel } from './BillingTeamPage'
import {
  ROLE_LABEL_KEYS,
  ROLE_BADGE_CLASSES,
  USER_STATUS_BADGES,
  USER_STATUS_LABELS,
} from '../../modules/users/constants'
import type { DetailTab, AuditState } from '../../modules/users/types'
import { EMPTY_AUDIT } from '../../modules/users/types'
import { normalizeList, parseCompanies, extractErrorDetail } from '../../modules/users/utils'

interface UserDetailCardProps {
  detail: AdminUserDetail
  loading: boolean
  error: string | null
  tab: DetailTab
  onTabChange: (tab: DetailTab) => void
  managers: ManagerOption[]
  canManage: boolean
  onRefresh: () => void
  onUpdateSupervisor: (supervisorId: string | null) => Promise<void>
  audit: AuditState
  onRefreshAudit: () => void
  companyOptions: Company[]
  onUpdateCompanies: (companyIds: string[]) => Promise<void>
  onChangeRole?: (role: UserRole) => Promise<void>
  onToggleActive?: (active: boolean) => Promise<void>
  onRevokeRefresh?: () => Promise<void>
  onResetPassword?: () => Promise<void>
  onChangePassword?: (newPassword: string) => Promise<void>
  onDeleteUser?: () => Promise<void>
}

function UserDetailCard({
  detail,
  loading,
  error,
  tab,
  onTabChange,
  managers,
  canManage,
  onRefresh,
  onUpdateSupervisor,
  audit,
  onRefreshAudit,
  companyOptions,
  onUpdateCompanies,
  onChangeRole,
  onToggleActive,
  onRevokeRefresh,
  onResetPassword,
  onChangePassword,
  onDeleteUser,
}: UserDetailCardProps) {
  const [updatingSupervisor, setUpdatingSupervisor] = useState(false)
  const [companySelection, setCompanySelection] = useState<string[]>(detail.company_ids || [])
  const [companySaving, setCompanySaving] = useState(false)
  const [companyError, setCompanyError] = useState<string | null>(null)
  const [roleUpdating, setRoleUpdating] = useState(false)
  const [statusUpdating, setStatusUpdating] = useState(false)
  const [revokingRefresh, setRevokingRefresh] = useState(false)
  const [passwordNote, setPasswordNote] = useState<string | null>(null)
  const { t } = useI18n()
  const notAvailableLabel = t('common.labels.not_available')
  const canManageUser = canManage && Boolean(detail.user_id)

  const supervisorOptions = useMemo(() => managers ?? [], [managers])
  useEffect(() => {
    setCompanySelection(detail.company_ids || [])
    setCompanyError(null)
  }, [detail.user_id, JSON.stringify(detail.company_ids || [])])
  const tabs = useMemo(
    () => [
      { key: 'overview' as DetailTab, label: t('app.admin.users.detail.tabs.overview') },
      { key: 'companies' as DetailTab, label: t('app.admin.users.detail.tabs.companies') },
      { key: 'audit' as DetailTab, label: t('app.admin.users.detail.tabs.audit') },
    ],
    [t],
  )

  const handleSupervisorChange = async (value: string) => {
    try {
      setUpdatingSupervisor(true)
      await onUpdateSupervisor(value || null)
    } finally {
      setUpdatingSupervisor(false)
    }
  }

  const handleCompanyAccessSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!detail.user_id) return
    setCompanySaving(true)
    setCompanyError(null)
    try {
      await onUpdateCompanies(companySelection)
    } catch (err) {
      console.error('[UserDetailCard] company update failed', err)
      setCompanyError(t('app.admin.users.errors.company_update_failed'))
    } finally {
      setCompanySaving(false)
    }
  }

  const handleRoleSelect = async (value: UserRole) => {
    if (!onChangeRole) return
    setRoleUpdating(true)
    try {
      await onChangeRole(value)
    } finally {
      setRoleUpdating(false)
    }
  }

  const handleStatusToggle = async () => {
    if (!onToggleActive) return
    setStatusUpdating(true)
    try {
      await onToggleActive(!isActive)
    } finally {
      setStatusUpdating(false)
    }
  }

  const handleRevokeTokens = async () => {
    if (!onRevokeRefresh) return
    setRevokingRefresh(true)
    try {
      await onRevokeRefresh()
    } finally {
      setRevokingRefresh(false)
    }
  }

  const handleResetPassword = async () => {
    if (!onResetPassword || !detail.user_id) return
    setPasswordNote(null)
    try {
      await onResetPassword()
      setPasswordNote(t('app.admin.users.actions.password_reset_link_sent', { defaultValue: 'Link do zresetowania hasła wysłany na adres e-mail użytkownika.' }))
    } catch (err) {
      console.error('[UserDetailCard] reset password failed', err)
      setPasswordNote(t('app.admin.users.errors.password_reset_failed', { defaultValue: 'Failed to reset password' }))
    }
  }

  const handleChangePassword = async () => {
    if (!onChangePassword || !detail.user_id) return
    const next = window.prompt(t('app.admin.users.actions.enter_new_password', { defaultValue: 'Enter new password' }))
    if (!next) return
    setPasswordNote(null)
    try {
      await onChangePassword(next)
      setPasswordNote(t('app.admin.users.actions.password_change_success', { defaultValue: 'Password updated' }))
    } catch (err) {
      console.error('[UserDetailCard] change password failed', err)
      setPasswordNote(t('app.admin.users.errors.password_change_failed', { defaultValue: 'Failed to change password' }))
    }
  }

  const handleDeleteUser = async () => {
    if (!onDeleteUser || !detail.user_id) return
    const confirmed = window.confirm(
      t('app.admin.users.actions.confirm_delete', {
        defaultValue: 'Delete this user? Sessions will be revoked.',
      }),
    )
    if (!confirmed) return
    try {
      await onDeleteUser()
      setPasswordNote(t('app.admin.users.actions.delete_success', { defaultValue: 'User deleted' }))
    } catch (err) {
      console.error('[UserDetailCard] delete user failed', err)
      setPasswordNote(t('app.admin.users.errors.delete_failed', { defaultValue: 'Failed to delete user' }))
    }
  }

  const selectedSupervisor = supervisorOptions.find((m) => m.id === detail.supervisor_id)
  const supervisorName = selectedSupervisor
    ? selectedSupervisor.label || selectedSupervisor.full_name || selectedSupervisor.email
    : null
  const statusKey = detail.status === 'active' ? 'active' : detail.status === 'invited' ? 'invited' : 'inactive'
  const isActive = detail.status === 'active' && detail.is_active

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{t('app.admin.users.detail.title')}</h2>
          <p className="text-sm text-slate-500">{detail.email}</p>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span>
            {t('app.admin.users.detail.status_prefix')}
            <span className="ml-1 font-medium text-slate-900">
              {statusKey === 'active'
                ? t('app.admin.users.table.status.active')
                : statusKey === 'invited'
                ? t('app.admin.users.table.status.invited')
                : t('app.admin.users.table.status.inactive')}
            </span>
          </span>
          <button type="button" className="btn-secondary" onClick={onRefresh} disabled={loading}>
            {loading ? t('app.admin.users.detail.refresh.loading') : t('app.admin.users.detail.refresh.action')}
          </button>
        </div>
      </div>

      <div className="mt-4 border-b border-slate-200">
        <nav className="-mb-px flex gap-4 text-sm">
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              className={[
                'border-b-2 px-2 py-2 font-medium',
                tab === item.key ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-indigo-600',
              ].join(' ')}
              onClick={() => onTabChange(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      {error && (
        <div className="mt-3">
          <ErrorRecoveryBanner
            info={{
              title: error,
              hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
            }}
            onRetry={onRefresh}
            retryLabel={t('common.actions.refresh', { defaultValue: 'Обновить' })}
            secondaryTo="/app/settings/team"
            secondaryLabel={t('common.navigation.settings', { defaultValue: 'Настройки' })}
            compact
          />
        </div>
      )}

      {tab === 'overview' && (
        <div className="mt-4 space-y-4 text-sm text-slate-700">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs uppercase text-slate-400">{t('app.admin.users.detail.fields.name')}</div>
              <div className="font-medium text-slate-900">{detail.full_name || notAvailableLabel}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400">{t('app.admin.users.detail.fields.code')}</div>
              <div className="font-medium text-slate-900">{detail.short_id || notAvailableLabel}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400">{t('app.admin.users.table.columns.status')}</div>
              <span
                className={[
                  'inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold',
                  USER_STATUS_BADGES[statusKey as AdminUser['status']] ?? USER_STATUS_BADGES.active,
                ].join(' ')}
              >
                {t(USER_STATUS_LABELS[statusKey as AdminUser['status']] ?? USER_STATUS_LABELS.active)}
              </span>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400">{t('app.admin.users.detail.fields.created_at')}</div>
              <div>{detail.created_at ? new Date(detail.created_at).toLocaleString() : notAvailableLabel}</div>
            </div>
          </div>

          {canManageUser && (
            <div className="rounded border border-slate-100 bg-slate-50/80 p-3 space-y-3">
              <label className="text-xs font-medium text-slate-500">
                {t('app.admin.users.detail.fields.role')}
                <select
                  className="input mt-1"
                  value={detail.role}
                  disabled={roleUpdating}
                  onChange={(event) => handleRoleSelect(event.target.value as UserRole)}
                >
                  {(Object.keys(ROLE_LABEL_KEYS) as UserRole[]).map((role) => (
                    <option key={role} value={role}>
                      {t(ROLE_LABEL_KEYS[role])}
                    </option>
                  ))}
                </select>
              </label>
              {detail.role === 'recruiter' && !detail.supervisor_id && (
                <div className="text-[11px] text-amber-600">
                  {t('app.admin.users.errors.supervisor_required_for_recruiter', {
                    defaultValue: 'Назначьте супервайзера для рекрутёра',
                  })}
                </div>
              )}
              <div className="flex flex-wrap gap-2 text-xs">
                <button type="button" className="btn-secondary" onClick={handleStatusToggle} disabled={statusUpdating}>
                  {statusUpdating
                    ? t('common.saving')
                    : isActive
                    ? t('app.admin.users.table.actions.deactivate')
                    : t('app.admin.users.table.actions.activate')}
                </button>
                <button type="button" className="btn-secondary" onClick={() => onTabChange('audit')}>
                  {t('app.admin.users.table.actions.audit')}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleRevokeTokens}
                  disabled={revokingRefresh}
                >
                  {revokingRefresh ? t('common.loading') : t('app.admin.users.table.actions.revoke_refresh')}
                </button>
                {onResetPassword && (
                  <button type="button" className="btn-secondary" onClick={handleResetPassword}>
                    {t('app.admin.users.table.actions.reset_password', { defaultValue: 'Reset password' })}
                  </button>
                )}
                {onChangePassword && (
                  <button type="button" className="btn-secondary" onClick={handleChangePassword}>
                    {t('app.admin.users.table.actions.change_password', { defaultValue: 'Change password' })}
                  </button>
                )}
                {onDeleteUser && (
                  <button type="button" className="btn-danger" onClick={handleDeleteUser}>
                    {t('common.actions.delete')}
                  </button>
                )}
              </div>
              {passwordNote && <div className="text-xs text-slate-600">{passwordNote}</div>}
            </div>
          )}

          {canManage && (
            <div className="mt-3">
              <label className="label" htmlFor="detail-supervisor">
                {t('app.admin.users.form.supervisor_label')}
              </label>
              <select
                id="detail-supervisor"
                className="input w-full max-w-md"
                value={detail.supervisor_id || ''}
                onChange={(event) => handleSupervisorChange(event.target.value)}
                disabled={updatingSupervisor}
              >
                <option value="">{t('app.admin.users.form.supervisor_placeholder_optional')}</option>
                {supervisorOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label || option.full_name || option.email}
                  </option>
                ))}
              </select>
              {supervisorName && (
                <p className="mt-1 text-xs text-slate-500">
                  {t('app.admin.users.detail.supervisor_current', { values: { name: supervisorName } })}
                </p>
              )}
            </div>
          )}

          {canManageUser && (
            <form className="mt-4 space-y-2" onSubmit={handleCompanyAccessSubmit}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-xs uppercase text-slate-400">
                    {t('app.admin.users.detail.company_access.title')}
                  </div>
                  <p className="text-[11px] text-slate-500">
                    {t('app.admin.users.detail.company_access.subtitle')}
                  </p>
                </div>
                <button
                  type="submit"
                  className="btn-primary btn-sm"
                  disabled={companySaving || companyOptions.length === 0}
                >
                  {companySaving ? t('common.saving') : t('common.actions.save')}
                </button>
              </div>

              {companyOptions.length === 0 ? (
                <div className="rounded border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  {t('app.admin.users.detail.company_access.empty')}
                </div>
              ) : (
                <select
                  multiple
                  className="input w-full min-h-[120px]"
                  value={companySelection}
                  onChange={(event) =>
                    setCompanySelection(Array.from(event.target.selectedOptions).map((option) => option.value))
                  }
                >
                  {companyOptions.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              )}
              {companyError && <div className="text-xs text-red-600">{companyError}</div>}
            </form>
          )}

          {detail.recruiters && detail.recruiters.length > 0 && (
            <div className="mt-4">
              <div className="text-xs uppercase text-slate-400">{t('app.admin.users.detail.recruiters.title')}</div>
              <ul className="mt-2 space-y-1 text-sm">
                {detail.recruiters.map((recruiter) => (
                  <li key={recruiter.user_id} className="flex justify-between rounded border border-slate-100 px-3 py-2">
                    <span>{recruiter.email}</span>
                    <span className="text-xs text-slate-500">{recruiter.status}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === 'companies' && (
        <div className="mt-4 space-y-3 text-sm text-slate-700">
          {detail.companies.length === 0 ? (
            <div className="text-slate-500">{t('app.admin.users.detail.companies.empty')}</div>
          ) : (
            <ul className="space-y-2">
              {detail.companies.map((company) => (
                <li key={company.company_id} className="flex items-center justify-between rounded border border-slate-100 px-3 py-2">
                  <div>
                    <div className="font-medium text-slate-900">{company.company_id}</div>
                    <div className="text-xs text-slate-500">
                      {t('app.admin.users.detail.companies.permissions', {
                        values: {
                          permission: t(
                            company.can_edit
                              ? 'app.admin.users.detail.companies.permission_edit'
                              : 'app.admin.users.detail.companies.permission_read',
                          ),
                        },
                      })}
                    </div>
                  </div>
                  <Link className="btn-secondary btn-xs" to={`/app/settings/company-access?company=${company.company_id}`}>
                    {t('app.admin.users.detail.companies.configure_acl')}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === 'audit' && (
        <div className="mt-4 space-y-3 text-sm text-slate-700">
          <button type="button" className="btn-secondary" onClick={onRefreshAudit} disabled={audit.loading}>
            {audit.loading
              ? t('app.admin.users.detail.audit.refresh_loading')
              : t('app.admin.users.detail.audit.refresh')}
          </button>
          {audit.error && (
            <ErrorRecoveryBanner
              info={{
                title: audit.error,
                hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
              }}
              onRetry={onRefreshAudit}
              retryLabel={t('common.actions.refresh', { defaultValue: 'Обновить' })}
              secondaryTo="/app/settings/team"
              secondaryLabel={t('app.admin.users.detail.audit.title', { defaultValue: 'Аудит' })}
              compact
            />
          )}
          {!audit.loading && !audit.error && audit.entries.length === 0 && (
            <div className="text-slate-500">{t('app.admin.users.detail.audit.no_entries')}</div>
          )}
          {!audit.loading && audit.entries.length > 0 && (
            <ul className="space-y-2">
              {audit.entries.map((entry) => (
                <li key={entry.id} className="rounded border border-slate-100 px-3 py-2">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{new Date(entry.created_at).toLocaleString()}</span>
                    <span>{entry.actor_id || t('app.admin.users.detail.audit.system_actor')}</span>
                  </div>
                  <div className="text-sm font-medium text-slate-800">{entry.action}</div>
                  {entry.payload && Object.keys(entry.payload).length > 0 && (
                    <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                      {JSON.stringify(entry.payload, null, 2)}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

// extractErrorDetail is now imported from modules/users/utils

export default function UsersPage() {
  const { me } = useAuth()
  const { can } = usePermissions()
  const [searchParams, setSearchParams] = useSearchParams()
  const { t } = useI18n()
  const notAvailableLabel = t('common.labels.not_available')

  const canViewAdmin = can('admin.users') || can('users.view')
  const canManage = can('users.manage') || can('admin.users')
  const isSuperAdmin = (me?.role || '').toLowerCase() === 'superadmin'
  const requestedTenant = (searchParams.get('tenant') || '').trim()
  const tenantOverride = isSuperAdmin && requestedTenant ? requestedTenant : null
  const tenantOptions = useMemo(() => (tenantOverride ? { tenantId: tenantOverride } : undefined), [tenantOverride])
  const [actionTab, setActionTab] = useState<'create' | 'invite' | 'team'>('create')
  const [tenantInput, setTenantInput] = useState(requestedTenant)
  const [tenantSuggestions, setTenantSuggestions] = useState<PlatformTenant[]>([])
  const [tenantSearchLoading, setTenantSearchLoading] = useState(false)
  const [tenantLookupError, setTenantLookupError] = useState<string | null>(null)

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [forbidden, setForbidden] = useState(false)

  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteResult, setInviteResult] = useState<UserInvite | null>(null)
  const [createLoading, setCreateLoading] = useState(false)
  const [createResult, setCreateResult] = useState<AdminUserCreateResponse | null>(null)

  const [managerOptions, setManagerOptions] = useState<ManagerOption[]>([])
  const [companies, setCompanies] = useState<Company[]>([])

  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AdminUserDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<DetailTab>('overview')
  const [audit, setAudit] = useState<AuditState>(EMPTY_AUDIT)
  const [overrideTenant, setOverrideTenant] = useState<PlatformTenant | null>(null)
  const [overrideError, setOverrideError] = useState<string | null>(null)
  const sortedUsers = useMemo(() => {
    const roleOrder: Record<UserRole, number> = {
      administrator: 0,
      supervisor: 1,
      recruiter: 2,
      client_processor: 3,
      viewer: 4,
    }
    return [...users].sort((a, b) => {
      const aOrder = roleOrder[a.role] ?? 9
      const bOrder = roleOrder[b.role] ?? 9
      if (aOrder !== bOrder) return aOrder - bOrder
      return (a.email || '').localeCompare(b.email || '')
    })
  }, [users])
  const formatError = useCallback(
    (key: string, detail?: string | null) => (detail ? `${t(key)}: ${detail}` : t(key)),
    [t],
  )
  const updateTenantParam = useCallback(
    (nextTenant: string | null) => {
      const next = new URLSearchParams(searchParams)
      if (nextTenant) {
        next.set('tenant', nextTenant)
      } else {
        next.delete('tenant')
      }
      setSearchParams(next)
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    if (!isSuperAdmin) {
      setTenantInput('')
      setTenantSuggestions([])
      setTenantLookupError(null)
      setTenantSearchLoading(false)
      return
    }
    setTenantInput(requestedTenant)
  }, [isSuperAdmin, requestedTenant])

  useEffect(() => {
    if (!isSuperAdmin) return
    const term = tenantInput.trim()
    if (!term || term.length < 2) {
      setTenantSuggestions([])
      setTenantLookupError(null)
      setTenantSearchLoading(false)
      return
    }
    let cancelled = false
    setTenantSearchLoading(true)
    setTenantLookupError(null)
    listPlatformTenants({ search: term, limit: 5 })
      .then((data) => {
        if (!cancelled) {
          setTenantSuggestions(data.items ?? [])
        }
      })
      .catch((err) => {
        console.warn('[UsersPage] tenant lookup failed', err)
        if (!cancelled) {
          setTenantLookupError(t('app.admin.users.errors.tenant_lookup_failed'))
          setTenantSuggestions([])
        }
      })
      .finally(() => {
        if (!cancelled) setTenantSearchLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isSuperAdmin, tenantInput, t])

  const handleTenantOverrideSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      if (!isSuperAdmin) return
      const nextTenant = tenantInput.trim()
      updateTenantParam(nextTenant || null)
    },
    [isSuperAdmin, tenantInput, updateTenantParam],
  )

  const handleTenantSuggestionClick = useCallback(
    (tenantId: string) => {
      setTenantInput(tenantId)
      updateTenantParam(tenantId)
    },
    [updateTenantParam],
  )

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError(null)
    setForbidden(false)
    try {
      const data = await listAdminUsers(tenantOptions)
      setUsers(Array.isArray(data) ? data : [])
    } catch (err: any) {
      console.error('[UsersPage] list error', err)
      const status = err?.response?.status
      setForbidden(status === 403)
      setError(
        status === 404
          ? t('app.admin.users.errors.list_missing_endpoint')
          : t('app.admin.users.errors.list_failed'),
      )
    } finally {
      setLoading(false)
    }
  }, [t, tenantOptions])

  const loadManagers = useCallback(async () => {
    try {
      const data = await listTenantManagers(tenantOptions)
      setManagerOptions(Array.isArray(data) ? data : [])
    } catch (err) {
      console.warn('[UsersPage] managers load failed', err)
      setManagerOptions([])
    }
  }, [tenantOptions])

  const loadCompanies = useCallback(async () => {
    try {
      const data = await listCompanies({ limit: 500, tenantId: tenantOverride || undefined })
      setCompanies(parseCompanies(data))
    } catch (err) {
      console.warn('[UsersPage] companies load failed', err)
      setCompanies([])
    }
  }, [tenantOverride])

  const loadDetail = useCallback(async (userId: string) => {
    setDetailLoading(true)
    setDetailError(null)
    try {
      const data = await fetchUserDetail(userId, tenantOptions)
      setDetail(data)
    } catch (err) {
      console.error('[UsersPage] detail error', err)
      setDetailError(t('app.admin.users.errors.detail_load'))
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }, [t, tenantOptions])

  const refreshAudit = useCallback(async (userId: string) => {
    setAudit({ loading: true, entries: [], error: null })
    try {
      const entries = await fetchUserAudit(userId, 100, tenantOptions)
      setAudit({ loading: false, entries, error: null })
    } catch (err) {
      console.error('[UsersPage] audit error', err)
      setAudit({ loading: false, entries: [], error: t('app.admin.users.errors.audit_load') })
    }
  }, [t, tenantOptions])

  useEffect(() => {
    void loadUsers()
    void loadManagers()
    void loadCompanies()
  }, [loadUsers, loadManagers, loadCompanies])

  useEffect(() => {
    if (!tenantOverride) {
      setOverrideTenant(null)
      setOverrideError(null)
      return
    }
    let cancelled = false
    setOverrideTenant(null)
    setOverrideError(null)
    getPlatformTenant(tenantOverride)
      .then((tenant) => {
        if (!cancelled) setOverrideTenant(tenant)
      })
      .catch((err) => {
        console.error('[UsersPage] tenant override load failed', err)
        if (!cancelled) setOverrideError(t('app.admin.users.errors.tenant_override_load'))
      })
    return () => {
      cancelled = true
    }
  }, [tenantOverride, t])

  useEffect(() => {
    if (detailTab === 'audit' && selectedUserId && !audit.loading && audit.entries.length === 0 && !audit.error) {
      void refreshAudit(selectedUserId)
    }
  }, [detailTab, selectedUserId, audit, refreshAudit])

  const handleSelectUser = useCallback(
    async (user: AdminUser) => {
      if (!user.user_id) {
        setSelectedUserId(null)
        setDetail(null)
        setAudit(EMPTY_AUDIT)
        return
      }
      setSelectedUserId(user.user_id)
      setDetailTab('overview')
      setAudit(EMPTY_AUDIT)
      await loadDetail(user.user_id)
    },
    [loadDetail],
  )

  const handleChangeRole = useCallback(
    async (userId: string, role: UserRole) => {
      setError(null)
      try {
        await changeUserRole(userId, role, tenantOptions)
        await loadUsers()
        if (selectedUserId === userId) {
          await loadDetail(userId)
        }
      } catch (err) {
        console.error('[UsersPage] change role error', err)
        const detail = extractErrorDetail(err)
        const msg =
          detail &&
          (String(detail).toLowerCase().includes('supervisor') || String(detail).toLowerCase().includes('assign'))
            ? t('app.admin.users.errors.supervisor_required_for_recruiter', {
                defaultValue: 'Назначьте супервайзера перед переводом в рекрутёры',
              })
            : formatError('app.admin.users.errors.change_role', detail)
        setError(msg)
      }
    },
    [formatError, loadUsers, loadDetail, selectedUserId, tenantOptions, detail, t],
  )

  const handleToggleActive = useCallback(
    async (userId: string, value: boolean) => {
      setError(null)
      try {
        await setUserActive(userId, value, tenantOptions)
        await loadUsers()
        if (selectedUserId === userId) {
          await loadDetail(userId)
        }
      } catch (err) {
        console.error('[UsersPage] toggle active error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.toggle_status', detail))
      }
    },
    [formatError, loadUsers, loadDetail, selectedUserId, tenantOptions],
  )

  const handleRevokeRefresh = useCallback(
    async (userId: string) => {
      setError(null)
      try {
        await revokeRefreshTokens(userId, tenantOptions)
        if (detailTab === 'audit' && selectedUserId === userId) {
          await refreshAudit(userId)
        }
      } catch (err) {
        console.error('[UsersPage] revoke refresh error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.revoke_refresh', detail))
      }
    },
    [detailTab, formatError, refreshAudit, selectedUserId, tenantOptions],
  )

  const handleResetPassword = useCallback(
    async (userId: string) => {
      setError(null)
      try {
        await resetUserPassword(userId, tenantOptions)
      } catch (err) {
        console.error('[UsersPage] reset password error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.password_reset_failed', detail))
        throw err
      }
    },
    [formatError, tenantOptions],
  )

  const handleChangePasswordAdmin = useCallback(
    async (userId: string, newPassword: string) => {
      setError(null)
      try {
        await changeUserPasswordAdmin(userId, { new_password: newPassword }, tenantOptions)
      } catch (err) {
        console.error('[UsersPage] change password error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.password_change_failed', detail))
        throw err
      }
    },
    [formatError, tenantOptions],
  )

  const handleDeleteUser = useCallback(
    async (userId: string) => {
      setError(null)
      try {
        await deleteUserAdmin(userId, tenantOptions)
        await loadUsers()
        if (selectedUserId === userId) {
          setSelectedUserId(null)
          setDetail(null)
        }
      } catch (err) {
        console.error('[UsersPage] delete user error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.delete_failed', detail))
        throw err
      }
    },
    [formatError, loadUsers, selectedUserId, tenantOptions],
  )

  const handleInvite = useCallback(
    async (payload: { email: string; role: UserRole; supervisor_id?: string | null; company_ids?: string[]; expires_in_hours?: number }) => {
      setInviteLoading(true)
      setInviteResult(null)
      setCreateResult(null)
      setError(null)
      try {
        const invite = await createUserInvite(payload, tenantOptions)
        setInviteResult(invite)
        await loadUsers()
      } catch (err) {
        console.error('[UsersPage] invite error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.invite', detail))
      } finally {
        setInviteLoading(false)
      }
    },
    [formatError, loadUsers, tenantOptions],
  )

  const handleCreateUser = useCallback(
    async (values: {
      email: string
      role: UserRole
      full_name?: string | null
      short_id?: string | null
      password?: string | null
      supervisor_id?: string | null
      company_ids?: string[]
    }) => {
      setCreateLoading(true)
      setCreateResult(null)
      setInviteResult(null)
      setError(null)
      try {
        const created = await createTenantUser(values, tenantOptions)
        setCreateResult(created)
        await loadUsers()
      } catch (err) {
        console.error('[UsersPage] create user error', err)
        const detail = extractErrorDetail(err)
        setError(formatError('app.admin.users.errors.create', detail))
      } finally {
        setCreateLoading(false)
      }
    },
    [formatError, loadUsers, tenantOptions],
  )

  const handleUpdateSupervisor = useCallback(
    async (supervisorId: string | null) => {
      if (!selectedUserId) return
      try {
        await updateUserSupervisor(selectedUserId, supervisorId, tenantOptions)
        await loadUsers()
        await loadDetail(selectedUserId)
      } catch (err) {
        console.error('[UsersPage] update supervisor error', err)
        setDetailError(t('app.admin.users.errors.supervisor_update'))
      }
    },
    [selectedUserId, loadUsers, loadDetail, t, tenantOptions],
  )

  const handleUpdateCompanies = useCallback(
    async (userId: string, companyIds: string[]) => {
      try {
        const updated = await updateUserCompanies(userId, companyIds, tenantOptions)
        setDetail(updated)
        setUsers((prev) =>
          prev.map((entry) => (entry.user_id === updated.user_id ? { ...entry, company_ids: updated.company_ids } : entry)),
        )
      } catch (err) {
        console.error('[UsersPage] update company access error', err)
        setDetailError(t('app.admin.users.errors.company_update_failed'))
        throw err
      }
    },
    [tenantOptions, t],
  )

  if (!me) {
    return <Navigate to="/login" replace />
  }

  if (!canViewAdmin) {
    return (
      <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        {t('app.admin.users.page.access_denied')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {forbidden && (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {t('app.admin.users.page.access_denied_forbidden')}
        </div>
      )}
      {isSuperAdmin && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 space-y-3 shadow-sm">
          <div>
            <div className="font-semibold text-slate-900">
              {t('app.admin.users.page.tenant_override.heading')}
            </div>
            <p className="text-xs text-slate-500">{t('app.admin.users.page.tenant_override.description')}</p>
          </div>
          <form className="flex flex-wrap items-center gap-2" onSubmit={handleTenantOverrideSubmit}>
            <input
              className="input min-w-[220px] flex-1"
              placeholder={t('app.admin.users.page.tenant_override.placeholder')}
              autoComplete="off"
              value={tenantInput}
              onChange={(event) => setTenantInput(event.target.value)}
            />
            <button type="submit" className="btn-primary text-xs sm:text-sm">
              {t('app.admin.users.page.tenant_override.apply')}
            </button>
            <button
              type="button"
              className="btn-secondary btn-xs sm:text-sm"
              onClick={() => updateTenantParam(null)}
              disabled={!tenantOverride}
            >
              {t('app.admin.users.page.tenant_override.clear')}
            </button>
          </form>
          {tenantLookupError && <p className="text-xs text-rose-600">{tenantLookupError}</p>}
          {overrideError && <p className="text-xs text-rose-600">{overrideError}</p>}
          <div className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            {tenantOverride ? (
              <>
                <div className="font-semibold text-slate-900">
                  {t('app.admin.users.page.tenant_override.title', {
                    values: {
                      name: overrideTenant?.workspace_label || overrideTenant?.name || tenantOverride,
                    },
                  })}
                </div>
                <p className="text-[11px] text-indigo-700">{t('app.admin.users.page.tenant_override.subtitle')}</p>
              </>
            ) : (
              <p className="text-[11px] text-slate-500">{t('app.admin.users.page.tenant_override.inactive')}</p>
            )}
          </div>
          <div className="space-y-2">
            {tenantInput.trim().length < 2 ? (
              <p className="text-xs text-slate-500">{t('app.admin.users.page.tenant_override.search_hint')}</p>
            ) : tenantSearchLoading ? (
              <p className="text-xs text-slate-500">{t('common.loading')}</p>
            ) : tenantSuggestions.length === 0 ? (
              <p className="text-xs text-slate-500">{t('app.admin.users.page.tenant_override.no_results')}</p>
            ) : (
              <div>
                <p className="text-[11px] uppercase text-slate-400">
                  {t('app.admin.users.page.tenant_override.suggestions')}
                </p>
                <ul className="mt-1 divide-y divide-slate-200 rounded border border-slate-100 bg-white">
                  {tenantSuggestions.map((tenant) => (
                    <li key={tenant.id} className="flex items-center justify-between px-3 py-2 text-xs text-slate-700">
                      <div>
                        <div className="font-semibold text-slate-900">
                          {tenant.workspace_label || tenant.name}
                        </div>
                        <div className="text-[11px] text-slate-500">{tenant.slug}</div>
                      </div>
                      <button
                        type="button"
                        className="btn-secondary btn-xs"
                        onClick={() => handleTenantSuggestionClick(tenant.id)}
                      >
                        {t('app.admin.users.page.tenant_override.apply')}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{t('app.admin.users.page.title')}</h1>
          <p className="text-sm text-slate-500">{t('app.admin.users.page.subtitle')}</p>
        </div>
        <button className="btn-secondary" onClick={() => void loadUsers()} disabled={loading}>
          {loading ? t('app.admin.users.page.refresh.loading') : t('app.admin.users.page.refresh.action')}
        </button>
      </header>

      {error && (
        <ErrorRecoveryBanner
          info={{
            title: error,
            hint: t('app.common.retry_hint', { defaultValue: 'Повторите действие или обновите страницу.' }),
          }}
          onRetry={() => void loadUsers()}
          retryLabel={t('app.admin.users.page.refresh.action')}
          secondaryTo="/app/settings/team"
          secondaryLabel={t('common.navigation.settings', { defaultValue: 'Настройки' })}
          compact
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(260px,340px),minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {t('app.admin.users.table.title')}
              </h2>
              <p className="text-xs text-slate-400">
                {t('app.admin.users.table.count', { values: { count: users.length } })}
              </p>
            </div>
            <button className="btn-secondary btn-xs" onClick={() => void loadUsers()} disabled={loading}>
              {loading ? t('app.admin.users.page.refresh.loading') : t('app.admin.users.page.refresh.action')}
            </button>
          </div>
          <div className="mt-3 max-h-[520px] space-y-2 overflow-y-auto pr-1">
            {sortedUsers.length ? (
              sortedUsers.map((user) => {
                const roleKey = ROLE_LABEL_KEYS[user.role] ?? ROLE_LABEL_KEYS.viewer
                const roleBadge = ROLE_BADGE_CLASSES[user.role] ?? ROLE_BADGE_CLASSES.viewer
                const statusBadge = USER_STATUS_BADGES[user.status]
                const isSelected = selectedUserId === user.user_id
                const metaName = user.full_name || user.short_id || notAvailableLabel
                const companiesCount = user.company_ids?.length ?? user.companies?.length ?? 0
                const recruitersCount = user.recruiters?.length ?? 0
                const invitedLabel = user.invited_at
                  ? t('app.admin.users.list.meta.invited', {
                      values: { date: new Date(user.invited_at).toLocaleDateString() },
                    })
                  : null
                const createdLabel = user.created_at
                  ? t('app.admin.users.list.meta.created', {
                      values: { date: new Date(user.created_at).toLocaleDateString() },
                    })
                  : null
                return (
                  <button
                    key={user.user_id ?? user.invite_id ?? user.email}
                    type="button"
                    onClick={() => handleSelectUser(user)}
                    className={[
                      'w-full rounded-lg border px-3 py-3 text-left text-sm transition',
                      isSelected ? 'border-brand-400 bg-brand-50 shadow-sm' : 'border-slate-200 hover:border-brand-200',
                    ].join(' ')}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{user.email}</div>
                        <div className="text-xs text-slate-500">{metaName}</div>
                      </div>
                      <span className={['inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold', roleBadge].join(' ')}>
                        {t(roleKey)}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      <span
                        className={[
                          'inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold',
                          statusBadge,
                        ].join(' ')}
                      >
                        {t(USER_STATUS_LABELS[user.status] ?? USER_STATUS_LABELS.active)}
                      </span>
                      {companiesCount > 0 && (
                        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                          {t('app.admin.users.list.meta.companies', { values: { count: companiesCount } })}
                        </span>
                      )}
                      {recruitersCount > 0 && (
                        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                          {t('app.admin.users.list.meta.recruiters', { values: { count: recruitersCount } })}
                        </span>
                      )}
                    </div>
                    {(invitedLabel || createdLabel) && (
                      <div className="mt-2 text-[11px] text-slate-500">
                        {invitedLabel && <span>{invitedLabel}</span>}
                        {invitedLabel && createdLabel && <span className="mx-1 text-slate-400">•</span>}
                        {createdLabel && <span>{createdLabel}</span>}
                      </div>
                    )}
                  </button>
                )
              })
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500">
                {t('app.admin.users.table.empty')}
              </div>
            )}
          </div>
        </section>

        <div className="space-y-4">
          {detail ? (
            <UserDetailCard
              detail={detail}
              loading={detailLoading}
              error={detailError}
              tab={detailTab}
              onTabChange={setDetailTab}
              managers={managerOptions}
              canManage={canManage}
              onRefresh={() => {
                if (selectedUserId) {
                  void loadDetail(selectedUserId)
                }
              }}
              onUpdateSupervisor={handleUpdateSupervisor}
              audit={audit}
              onRefreshAudit={() => {
                if (selectedUserId) {
                  void refreshAudit(selectedUserId)
                }
              }}
              companyOptions={companies}
              onUpdateCompanies={(companyIds) => {
                if (!detail.user_id) return Promise.resolve()
                return handleUpdateCompanies(detail.user_id, companyIds)
              }}
              onChangeRole={
                detail.user_id
                  ? (role) => handleChangeRole(detail.user_id, role)
                  : undefined
              }
              onToggleActive={
                detail.user_id
                  ? (active) => handleToggleActive(detail.user_id, active)
                  : undefined
              }
              onRevokeRefresh={
                detail.user_id ? () => handleRevokeRefresh(detail.user_id) : undefined
              }
              onResetPassword={
                detail.user_id ? () => handleResetPassword(detail.user_id) : undefined
              }
              onChangePassword={
                detail.user_id ? (pwd) => handleChangePasswordAdmin(detail.user_id!, pwd) : undefined
              }
              onDeleteUser={detail.user_id ? () => handleDeleteUser(detail.user_id) : undefined}
            />
          ) : (
            <section className="rounded-lg border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
              {t('app.admin.users.detail.empty')}
            </section>
          )}

          {canManage && (
            <section className="rounded-lg border border-slate-200 bg-white p-0">
              <div className="flex flex-wrap items-center justify-between border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.admin.users.page.actions.title')}
                </h2>
                <div className="flex gap-2 text-sm">
                  {(['create', 'invite', 'team'] as Array<typeof actionTab>).map((key) => (
                    <button
                      key={key}
                      type="button"
                      className={[
                        'rounded-md px-3 py-1 transition',
                        actionTab === key ? 'bg-brand-100 text-brand-700' : 'text-slate-500 hover:text-brand-700',
                      ].join(' ')}
                      onClick={() => setActionTab(key)}
                    >
                      {t(`app.admin.users.page.actions.tabs.${key}`)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-4 p-4">
                {actionTab === 'create' && (
                  <>
                    <UserFormCreate
                      onSubmit={handleCreateUser}
                      loading={createLoading}
                      managerOptions={managerOptions}
                      companyOptions={companies}
                    />
                    {createResult && (
                      <div className="rounded-md border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">
                        <div className="font-semibold">{t('app.admin.users.success.create.title')}</div>
                        <div>{t('app.admin.users.success.labels.email', { values: { value: createResult.email } })}</div>
                        <div>{t('app.admin.users.success.labels.role', { values: { value: createResult.role } })}</div>
                        {createResult.full_name && (
                          <div>{t('app.admin.users.success.labels.name', { values: { value: createResult.full_name } })}</div>
                        )}
                        {createResult.temporary_password && (
                          <div className="mt-2 text-xs">
                            {t('app.admin.users.success.labels.temp_password')}
                            <code className="ml-1 rounded bg-white/70 px-1 py-0.5 font-mono">{createResult.temporary_password}</code>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {actionTab === 'invite' && (
                  <>
                    <UserFormInvite
                      onSubmit={handleInvite}
                      loading={inviteLoading}
                      managerOptions={managerOptions}
                      companyOptions={companies}
                    />
                    {inviteResult && (
                      <div className="rounded-md border border-indigo-100 bg-indigo-50 p-4 text-sm text-indigo-700">
                        <div className="font-semibold">{t('app.admin.users.success.invite.title')}</div>
                        <div>{t('app.admin.users.success.labels.email', { values: { value: inviteResult.email } })}</div>
                        <div>{t('app.admin.users.success.labels.role', { values: { value: inviteResult.role } })}</div>
                        <div>
                          {t('app.admin.users.success.labels.valid_until', {
                            values: { value: new Date(inviteResult.expires_at).toLocaleString() },
                          })}
                        </div>
                        <div className="mt-2 text-xs">
                          {t('app.admin.users.success.labels.token')}
                          <code className="ml-1 rounded bg-white/70 px-1 py-0.5 font-mono">{inviteResult.token}</code>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {actionTab === 'team' && (
                  <div className="space-y-4">
                    <p className="text-sm text-slate-500">{t('app.admin.users.page.actions.team_help')}</p>
                    <TeamManagementPanel tenantId={tenantOverride} showHeader={false} compact />
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
