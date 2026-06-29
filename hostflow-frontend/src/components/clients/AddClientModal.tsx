import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import {
  createTenantLink,
  searchCompaniesForLink,
  type CompanySearchHit,
  type TenantLink,
  type TenantLinkCreate,
} from '../../api/tenantLinks'

type AddClientModalProps = {
  tenantId: string
  onClose: () => void
  onCreated: (link: TenantLink) => void
  onError: (msg: string) => void
}

export function AddClientModal({ tenantId, onClose, onCreated, onError }: AddClientModalProps) {
  const { t } = useI18n()
  const { entitySingular } = useBusinessTerminology()
  const entitySingularLower = entitySingular.toLowerCase()
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
    const timer = setTimeout(runSearch, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, runSearch])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const name = displayName.trim()
    if (!name && !selected) {
      onError(t('app.clients.errors.name_or_link', { defaultValue: 'Enter a name or link to an existing company.' }))
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
          {t('app.clients.add_entity_dynamic', {
            defaultValue: 'Add {entity}',
            values: { entity: entitySingularLower },
          })}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {t('app.clients.add_modal_hint', {
            defaultValue: 'Creates the client profile and access settings in one step.',
          })}
        </p>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('app.clients.display_name_dynamic', {
                defaultValue: '{entity} name',
                values: { entity: entitySingular },
              })}
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t('app.clients.display_name_placeholder', { defaultValue: 'e.g. Northwind Logistics' })}
              className="input mt-1 block w-full"
              disabled={!!selected}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {t('app.clients.link_existing', { defaultValue: 'Or link to an existing employer tenant' })}
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setSelected(null)
              }}
              placeholder={t('app.clients.search_placeholder', { defaultValue: 'Search by name or domain…' })}
              className="input mt-1 block w-full"
            />
            {searching && <p className="mt-1 text-xs text-slate-500">{t('common.loading')}</p>}
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
                {t('app.clients.linked_to', { defaultValue: 'Link to' })}: <strong>{selected.name}</strong>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(null)
                    setDisplayName('')
                  }}
                  className="ml-2 text-slate-500 hover:underline"
                >
                  {t('common.clear', { defaultValue: 'Clear' })}
                </button>
              </p>
            )}
          </div>
          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-slate-500">{t('app.clients.quick_defaults')}</p>
              <button type="button" className="btn-secondary btn-xs" onClick={() => setAdvancedOpen((prev) => !prev)}>
                {advancedOpen ? t('common.actions.collapse') : t('common.actions.advanced')}
              </button>
            </div>
            {advancedOpen && (
              <div className="mt-3 flex flex-wrap gap-6">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={handoffEnabled} onChange={(e) => setHandoffEnabled(e.target.checked)} />
                  <span className="text-sm">{t('app.clients.handoff_label')}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={seeVacancies} onChange={(e) => setSeeVacancies(e.target.checked)} />
                  <span className="text-sm">{t('app.clients.see_vacancies_label')}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={seeReducedProfiles}
                    onChange={(e) => setSeeReducedProfiles(e.target.checked)}
                  />
                  <span className="text-sm">{t('app.clients.see_reduced_label')}</span>
                </label>
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary">
              {t('common.cancel')}
            </button>
            <button type="submit" disabled={saving || (!displayName.trim() && !selected)} className="btn-primary">
              {saving ? t('common.saving') : t('common.actions.add')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
