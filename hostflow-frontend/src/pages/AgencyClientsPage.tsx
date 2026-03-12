import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import {
  listTenantLinks,
  createTenantLink,
  updateTenantLink,
  createPortalLink,
  revokePortalLink,
  searchCompaniesForLink,
  type TenantLink,
  type TenantLinkCreate,
  type CompanySearchHit,
} from '../api/tenantLinks'
import { useToast } from '../components/Toast'
import EmptyStatePanel from '../components/EmptyStatePanel'

export default function AgencyClientsPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { notify } = useToast()
  const tenantId = (me as { tenant_id?: string })?.tenant_id ?? ''

  const [links, setLinks] = useState<TenantLink[]>([])
  const [loading, setLoading] = useState(true)
  const [addOpen, setAddOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [portalLoadingId, setPortalLoadingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!tenantId) return
    try {
      setLoading(true)
      const data = await listTenantLinks(tenantId)
      setLinks(data)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      notify({ title: msg, variant: 'error' })
      setLinks([])
    } finally {
      setLoading(false)
    }
  }, [tenantId, notify])

  useEffect(() => {
    void load()
  }, [load])

  if (!tenantId) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('app.clients.title', { defaultValue: 'Клиенты' })}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('app.clients.subtitle', { defaultValue: 'Клиенты агентства и настройки доступа.' })}
          </p>
        </div>
        <button type="button" onClick={() => setAddOpen(true)} className="btn-primary">
          {t('app.clients.add_client', { defaultValue: 'Добавить клиента' })}
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка...' })}</p>
      ) : links.length === 0 && !addOpen ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <EmptyStatePanel
            title={t('app.clients.empty_title', { defaultValue: 'No clients linked yet' })}
            description={t('app.clients.empty_desc', {
              defaultValue: 'Add the first client to enable handoff, visibility rules and shared workflows.',
            })}
            primaryAction={{
              label: t('app.clients.add_client', { defaultValue: 'Add client' }),
              onClick: () => setAddOpen(true),
            }}
            secondaryAction={{
              label: t('app.clients.empty_cta_companies', { defaultValue: 'Open companies' }),
              to: '/app/clients',
            }}
          />
        </div>
      ) : (
        <ul className="space-y-3">
          {links.map((link) => (
            <ClientRow
              key={link.id}
              link={link}
              tenantId={tenantId}
              saving={savingId === link.id}
              portalLoading={portalLoadingId === link.id}
              editing={editId === link.id}
              onToggleEdit={() => setEditId((id) => (id === link.id ? null : link.id))}
              onUpdate={async (payload) => {
                setSavingId(link.id)
                try {
                  const updated = await updateTenantLink(tenantId, link.id, payload)
                  setLinks((prev) => prev.map((l) => (l.id === link.id ? updated : l)))
                  setEditId(null)
                  notify({ title: t('common.saved', { defaultValue: 'Сохранено' }), variant: 'success' })
                } catch (e: unknown) {
                  const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
                  notify({ title: msg, variant: 'error' })
                } finally {
                  setSavingId(null)
                }
              }}
              onPortalCreated={(updated) => {
                setLinks((prev) => prev.map((l) => (l.id === link.id ? updated : l)))
                setPortalLoadingId(null)
                notify({ title: t('app.clients.portal_created', { defaultValue: 'Ссылка создана' }), variant: 'success' })
              }}
              onPortalRevoked={(updated) => {
                setLinks((prev) => prev.map((l) => (l.id === link.id ? updated : l)))
                setPortalLoadingId(null)
                notify({ title: t('app.clients.portal_revoked', { defaultValue: 'Ссылка отозвана' }), variant: 'success' })
              }}
              onPortalStart={() => setPortalLoadingId(link.id)}
              onPortalError={(msg) => {
                setPortalLoadingId(null)
                notify({ title: msg, variant: 'error' })
              }}
            />
          ))}
        </ul>
      )}

      {addOpen && (
        <AddClientModal
          tenantId={tenantId}
          onClose={() => setAddOpen(false)}
          onCreated={(link) => {
            setLinks((prev) => [...prev, link])
            setAddOpen(false)
            notify({ title: t('app.clients.created', { defaultValue: 'Клиент добавлен' }), variant: 'success' })
          }}
          onError={(msg) => notify({ title: msg, variant: 'error' })}
        />
      )}
    </div>
  )
}

function ClientRow({
  link,
  tenantId,
  saving,
  portalLoading,
  editing,
  onToggleEdit,
  onUpdate,
  onPortalCreated,
  onPortalRevoked,
  onPortalStart,
  onPortalError,
}: {
  link: TenantLink
  tenantId: string
  saving: boolean
  portalLoading: boolean
  editing: boolean
  onToggleEdit: () => void
  onUpdate: (p: { handoff_enabled?: boolean; see_vacancies?: boolean; see_reduced_profiles?: boolean }) => Promise<void>
  onPortalCreated: (updated: TenantLink) => void
  onPortalRevoked: (updated: TenantLink) => void
  onPortalStart: () => void
  onPortalError: (msg: string) => void
}) {
  const { t } = useI18n()
  const name = link.company_name ?? (link.features_json as Record<string, unknown>)?.client_display_name ?? link.id
  const portalUrl = link.portal_token
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/client-portal?token=${link.portal_token}`
    : ''

  const handleCreatePortal = async () => {
    onPortalStart()
    try {
      const out = await createPortalLink(tenantId, link.id)
      onPortalCreated({ ...link, portal_token: out.token })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onPortalError(typeof msg === 'string' ? msg : 'Error')
    }
  }

  const handleCopyPortal = () => {
    if (!portalUrl) return
    void navigator.clipboard.writeText(portalUrl).then(
      () => {},
      () => {
        onPortalError(t('app.clients.copy_failed', { defaultValue: 'Не удалось скопировать' }))
      }
    )
  }

  const handleRevokePortal = async () => {
    onPortalStart()
    try {
      await revokePortalLink(tenantId, link.id)
      onPortalRevoked({ ...link, portal_token: null })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onPortalError(typeof msg === 'string' ? msg : 'Error')
    }
  }

  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            {link.client_company_id ? (
              <Link
                to={`/app/clients/${link.client_company_id}`}
                className="font-medium text-slate-900 hover:text-brand-600 hover:underline"
              >
                {name}
              </Link>
            ) : (
              <span className="font-medium text-slate-900">{name}</span>
            )}
            {link.client_company_id ? (
              <Link
                to={`/app/clients/${link.client_company_id}`}
                className="text-sm text-brand-600 hover:underline"
              >
                {t('app.clients.open_profile', { defaultValue: 'Профиль' })}
              </Link>
            ) : link.client_tenant_id ? (
              <Link
                to={`/app/clients/link/${link.id}`}
                className="text-sm text-brand-600 hover:underline"
              >
                {t('app.clients.open_profile', { defaultValue: 'Профиль' })}
              </Link>
            ) : null}
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
            {link.client_tenant_id && (
              <span className="badge text-brand-700">
                {t('app.clients.linked_tenant', { defaultValue: 'Привязан к организации' })}
              </span>
            )}
            {link.handoff_enabled && (
              <span className="badge text-green-700">
                {t('app.clients.handoff', { defaultValue: 'Передача' })}
              </span>
            )}
            {link.see_vacancies && (
              <span className="badge text-brand-700">
                {t('app.clients.see_vacancies', { defaultValue: 'Вакансии' })}
              </span>
            )}
            {link.see_reduced_profiles && (
              <span className="badge">
                {t('app.clients.see_reduced', { defaultValue: 'Урезанные профили' })}
              </span>
            )}
          </div>
        </div>
        <button type="button" onClick={onToggleEdit} className="btn-secondary btn-sm">
          {editing ? t('common.cancel', { defaultValue: 'Отмена' }) : t('common.edit', { defaultValue: 'Изменить' })}
        </button>
      </div>
      {/* Portal link: for clients without tenant, create/copy/revoke */}
      <div className="mt-4 border-t border-slate-100 pt-4">
        <span className="text-sm font-medium text-slate-700">
          {t('app.clients.portal_access', { defaultValue: 'Доступ по ссылке' })}
        </span>
        {link.portal_token ? (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              type="text"
              readOnly
              value={portalUrl}
              className="input min-w-[200px] flex-1 bg-slate-50"
            />
            <button
              type="button"
              onClick={handleCopyPortal}
              className="btn-secondary text-sm"
            >
              {t('common.copy', { defaultValue: 'Копировать' })}
            </button>
            <button
              type="button"
              onClick={handleRevokePortal}
              disabled={portalLoading}
              className="btn-danger btn-sm disabled:opacity-50"
            >
              {t('app.clients.revoke_link', { defaultValue: 'Отозвать' })}
            </button>
          </div>
        ) : (
          <div className="mt-2">
            <button
              type="button"
              onClick={handleCreatePortal}
              disabled={portalLoading}
              className="btn-secondary text-sm"
            >
              {portalLoading
                ? t('common.loading', { defaultValue: '…' })
                : t('app.clients.create_portal_link', { defaultValue: 'Создать ссылку' })}
            </button>
          </div>
        )}
      </div>
      {editing && (
        <div className="mt-4 flex flex-wrap gap-6 border-t border-slate-100 pt-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!link.handoff_enabled}
              disabled={saving}
              onChange={(e) => void onUpdate({ handoff_enabled: e.target.checked })}
            />
            <span className="text-sm">{t('app.clients.handoff_label', { defaultValue: 'Передача кандидатов' })}</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!link.see_vacancies}
              disabled={saving}
              onChange={(e) => void onUpdate({ see_vacancies: e.target.checked })}
            />
            <span className="text-sm">{t('app.clients.see_vacancies_label', { defaultValue: 'Видеть вакансии' })}</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!link.see_reduced_profiles}
              disabled={saving}
              onChange={(e) => void onUpdate({ see_reduced_profiles: e.target.checked })}
            />
            <span className="text-sm">{t('app.clients.see_reduced_label', { defaultValue: 'Урезанные профили' })}</span>
          </label>
        </div>
      )}
    </li>
  )
}

function AddClientModal({
  tenantId,
  onClose,
  onCreated,
  onError,
}: {
  tenantId: string
  onClose: () => void
  onCreated: (link: TenantLink) => void
  onError: (msg: string) => void
}) {
  const { t } = useI18n()
  const [displayName, setDisplayName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<CompanySearchHit[]>([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState<CompanySearchHit | null>(null)
  const [handoffEnabled, setHandoffEnabled] = useState(true)
  const [seeVacancies, setSeeVacancies] = useState(false)
  const [seeReducedProfiles, setSeeReducedProfiles] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const runSearch = useCallback(async () => {
    const q = searchQuery.trim()
    if (q.length < 2) {
      setSearchResults([])
      return
    }
    setSearching(true)
    try {
      const data = await searchCompaniesForLink(tenantId, q)
      setSearchResults(data)
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [tenantId, searchQuery])

  useEffect(() => {
    const t = setTimeout(runSearch, 300)
    return () => clearTimeout(t)
  }, [searchQuery, runSearch])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const name = displayName.trim()
    if (!name && !selected) {
      onError(t('app.clients.errors.name_or_link', { defaultValue: 'Введите название или привяжите к компании.' }))
      return
    }
    setSaving(true)
    try {
      const payload: TenantLinkCreate = {
        handoff_enabled: handoffEnabled,
        see_vacancies: seeVacancies,
        see_reduced_profiles: seeReducedProfiles,
      }
      if (selected) {
        payload.client_tenant_id = selected.tenant_id
        payload.handoff_include_company_id = selected.id
      } else {
        payload.display_name = name
      }
      const link = await createTenantLink(tenantId, payload)
      onCreated(link)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Error'
      onError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose} role="dialog">
      <div
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-slate-900">
          {t('app.clients.add_client', { defaultValue: 'Добавить клиента' })}
        </h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('app.clients.display_name', { defaultValue: 'Название клиента' })}
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t('app.clients.display_name_placeholder', { defaultValue: 'ООО «Пример»' })}
              className="input mt-1 block w-full"
              disabled={!!selected}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('app.clients.link_existing', { defaultValue: 'Или привязать к существующей компании' })}
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setSelected(null) }}
              placeholder={t('app.clients.search_placeholder', { defaultValue: 'Поиск по названию или домену...' })}
              className="input mt-1 block w-full"
            />
            {searching && <p className="mt-1 text-xs text-slate-500">{t('common.loading', { defaultValue: 'Поиск...' })}</p>}
            {searchResults.length > 0 && !selected && (
              <ul className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-slate-200">
                {searchResults.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setSelected(c)
                        setDisplayName(c.name)
                        setSearchQuery('')
                        setSearchResults([])
                      }}
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                    >
                      {c.name}
                      {c.website ? ` · ${c.website}` : ''}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {selected && (
              <p className="mt-2 text-sm text-brand-600">
                {t('app.clients.linked_to', { defaultValue: 'Привязать к' })}: <strong>{selected.name}</strong>
                <button type="button" onClick={() => { setSelected(null); setDisplayName('') }} className="ml-2 text-slate-500 hover:underline">
                  {t('common.clear', { defaultValue: 'Сбросить' })}
                </button>
              </p>
            )}
          </div>
          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-slate-500">
                {t('app.clients.quick_defaults', {
                  defaultValue: 'Default settings are applied automatically. Open advanced options only if needed.',
                })}
              </p>
              <button
                type="button"
                className="btn-secondary btn-xs"
                onClick={() => setAdvancedOpen((prev) => !prev)}
              >
                {advancedOpen
                  ? t('common.actions.collapse', { defaultValue: 'Collapse' })
                  : t('common.actions.advanced', { defaultValue: 'Advanced' })}
              </button>
            </div>
            {advancedOpen && (
              <div className="mt-3 flex flex-wrap gap-6">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={handoffEnabled} onChange={(e) => setHandoffEnabled(e.target.checked)} />
                  <span className="text-sm">{t('app.clients.handoff_label', { defaultValue: 'Передача кандидатов' })}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={seeVacancies} onChange={(e) => setSeeVacancies(e.target.checked)} />
                  <span className="text-sm">{t('app.clients.see_vacancies_label', { defaultValue: 'Видеть вакансии' })}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={seeReducedProfiles} onChange={(e) => setSeeReducedProfiles(e.target.checked)} />
                  <span className="text-sm">{t('app.clients.see_reduced_label', { defaultValue: 'Урезанные профили' })}</span>
                </label>
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary">
              {t('common.cancel', { defaultValue: 'Отмена' })}
            </button>
            <button type="submit" disabled={saving || (!displayName.trim() && !selected)} className="btn-primary">
              {saving ? t('common.saving', { defaultValue: 'Сохранение…' }) : t('common.actions.add', { defaultValue: 'Добавить' })}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
