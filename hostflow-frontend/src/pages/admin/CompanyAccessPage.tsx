import type { FormEvent } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { listCompanies } from '../../api/client'
import { grantCompanyAccess, listCompanyAccess, revokeCompanyAccess } from '../../api/access'
import { listAdminUsers } from '../../api/users'
import type { AdminUser, Company, CompanyAccessEntry } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'

interface AccessFormState {
  userId: string
  canEdit: boolean
}

function toCompanyOptions(data: any): Company[] {
  const items: Company[] = []
  const source = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
  for (const item of source) {
    const id = item?.id || item?.uuid || item?.company_id
    if (!id) continue
    items.push({
      id,
      name: item?.name || item?.title || id,
      country: item?.country ?? null,
      city: item?.city ?? null,
    })
  }
  return items
}

export default function CompanyAccessPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const canManage = can('admin.companyAcl')

  const [companies, setCompanies] = useState<Company[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('')
  const [accessList, setAccessList] = useState<CompanyAccessEntry[]>([])
  const [loadingAccess, setLoadingAccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [allUsers, setAllUsers] = useState<AdminUser[]>([])
  const [form, setForm] = useState<AccessFormState>({ userId: '', canEdit: false })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!canManage) return
    const loadInitial = async () => {
      try {
        const [companiesResp, usersResp] = await Promise.all([
          listCompanies({ limit: 500 }),
          listAdminUsers(),
        ])
        const companyItems = toCompanyOptions(companiesResp)
        setCompanies(companyItems)
        if (companyItems.length > 0) {
          setSelectedCompanyId(companyItems[0].id)
        }
        setAllUsers(Array.isArray(usersResp) ? usersResp.filter((user) => !!user.user_id) : [])
      } catch (err) {
        console.error('[CompanyAccessPage] initial load failed', err)
        setError(t('admin.company_access.load_source_failed'))
      }
    }
    void loadInitial()
  }, [canManage])

  const availableUsers = useMemo(() => {
    return allUsers.filter((user) => user.user_id && user.status !== 'invited')
  }, [allUsers])

  const loadAccess = useCallback(
    async (companyId: string) => {
      if (!companyId) return
      setLoadingAccess(true)
      setError(null)
      try {
        const data = await listCompanyAccess(companyId)
        setAccessList(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('[CompanyAccessPage] access load failed', err)
        setError(t('admin.company_access.load_list_failed'))
      } finally {
        setLoadingAccess(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (selectedCompanyId) {
      void loadAccess(selectedCompanyId)
    }
  }, [selectedCompanyId, loadAccess])

  const handleGrant = useCallback(
    async (event: FormEvent) => {
      event.preventDefault()
      if (!selectedCompanyId || !form.userId) return
      setSaving(true)
      setError(null)
      try {
        await grantCompanyAccess(selectedCompanyId, {
          user_id: form.userId,
          can_edit: form.canEdit,
        })
        setForm({ userId: '', canEdit: false })
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] grant failed', err)
        setError(t('admin.company_access.grant_failed'))
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, form, loadAccess],
  )

  const handleToggle = useCallback(
    async (entry: CompanyAccessEntry) => {
      if (!selectedCompanyId) return
      setSaving(true)
      setError(null)
      try {
        if (!entry.user_id) {
          throw new Error(t('admin.company_access.missing_user'));
        }
        await grantCompanyAccess(selectedCompanyId, {
          user_id: entry.user_id,
          can_edit: !entry.can_edit,
        })
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] toggle failed', err)
        setError(t('admin.company_access.update_failed'))
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, loadAccess],
  )

  const handleRevoke = useCallback(
    async (entry: CompanyAccessEntry) => {
      if (!selectedCompanyId) return
      if (!entry.user_id) {
        setError(t('admin.company_access.missing_user'));
        return;
      }
      if (!window.confirm(t('admin.company_access.confirm_revoke', { values: { email: entry.email } }))) return
      setSaving(true)
      setError(null)
      try {
        await revokeCompanyAccess(selectedCompanyId, entry.user_id)
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] revoke failed', err)
        setError(t('admin.company_access.revoke_failed'))
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, loadAccess],
  )

  if (!canManage) {
    return (
      <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        {t('admin.company_access.no_acl')}
      </div>
    )
  }

  if (companies.length === 0) {
    return <div className="text-sm text-slate-600">{t('admin.company_access.no_companies')}</div>
  }

  const selectedCompany = companies.find((company) => company.id === selectedCompanyId)

  const accessPageErrorBanner: FriendlyErrorInfo | null = error
    ? {
        title: error,
        hint: t('admin.company_access.retry_hint'),
      }
    : null

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settings}
      backLabel={t('admin.settings.subpage.back_all', { defaultValue: '← All settings' })}
      kicker={t('admin.settings.subpage.kicker_workspace_setup', { defaultValue: 'Team & access' })}
      title={t('admin.company_access.title')}
      subtitle={
        selectedCompany
          ? t('admin.company_access.subtitle_with_company', {
              values: { name: selectedCompany.name },
            })
          : t('admin.company_access.subtitle')
      }
      actions={
        <select
          className="input w-full max-w-sm"
          value={selectedCompanyId}
          onChange={(event) => setSelectedCompanyId(event.target.value)}
          aria-label={t('admin.company_access.company_select_label')}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      }
    >

      {accessPageErrorBanner && (
        <ErrorRecoveryBanner
          info={accessPageErrorBanner}
          onRetry={() => selectedCompanyId && void loadAccess(selectedCompanyId)}
          retryLabel={t('common.refresh')}
          {...friendlyErrorBannerSecondary(
            accessPageErrorBanner,
            CRM_APP_PATHS.settingsCompanyAccess,
            t('admin.company_access.title'),
          )}
          compact
        />
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-6 space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">{t('admin.company_access.current')}</h2>
        {loadingAccess ? (
          <div className="text-sm text-slate-500">{t('common.loading')}</div>
        ) : accessList.length === 0 ? (
          <div className="text-sm text-slate-500">{t('admin.company_access.empty_users')}</div>
        ) : (
          <ul className="space-y-2 text-sm">
            {accessList.map((entry) => (
              <li key={entry.user_id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-100 px-3 py-2">
                <div>
                  <div className="font-medium text-slate-900">{entry.email}</div>
                  <div className="text-xs text-slate-500">
                    {t('admin.company_access.role_rights', {
                      values: {
                        role: entry.role,
                        rights: entry.can_edit
                          ? t('admin.company_access.rights_edit')
                          : t('admin.company_access.rights_view'),
                      },
                    })}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn-secondary text-xs"
                    disabled={saving}
                    onClick={() => void handleToggle(entry)}
                  >
                    {entry.can_edit ? t('admin.company_access.view_only') : t('admin.company_access.allow_edits')}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-xs"
                    disabled={saving}
                    onClick={() => void handleRevoke(entry)}
                  >
                    {t('admin.company_access.revoke')}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">{t('admin.company_access.grant_title')}</h2>
        <form className="space-y-3" onSubmit={handleGrant}>
          <label className="block text-sm">
            <span className="label">{t('admin.company_access.user')}</span>
            <select
              className="input w-full"
              value={form.userId}
              onChange={(event) => setForm((prev) => ({ ...prev, userId: event.target.value }))}
              required
            >
              <option value="">{t('admin.company_access.pick_user')}</option>
              {availableUsers.map((user) => (
                <option key={user.user_id} value={user.user_id!}>
                  {user.email} ({user.role})
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.canEdit}
              onChange={(event) => setForm((prev) => ({ ...prev, canEdit: event.target.checked }))}
            />
            <span>{t('admin.company_access.allow_company_edit')}</span>
          </label>

          <button type="submit" className="btn-primary" disabled={saving || !form.userId}>
            {saving ? t('admin.company_access.saving') : t('admin.company_access.grant')}
          </button>
        </form>
      </section>
    </SettingsSubpageHeader>
  )
}
