import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  IconChevronDown,
  IconChevronUp,
  IconCopy,
  IconExternalLink,
  IconLink,
  IconPlus,
} from '@tabler/icons-react'
import {
  createCompanyIntakeSourceProfile,
  listCompanyIntakeSourceProfiles,
  patchCompanyIntakeSourceProfile,
  type CompanyIntakeSourceProfile,
  type CompanyIntakeSourceProfileInput,
} from '../../api/companyIntakeSourceProfiles'
import { listOwnCompanies, type OwnCompanyRecord } from '../../api/client'
import { listTenantManagers } from '../../api/users'
import type { ManagerOption } from '../../api/types'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useToast } from '../Toast'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type Language = 'pl' | 'en' | 'ru'
type Draft = CompanyIntakeSourceProfileInput

const LANGUAGES: Language[] = ['pl', 'en', 'ru']

const SOURCE_OPTIONS = [
  { value: 'website', label: 'Website' },
  { value: 'meta_ads', label: 'Meta Ads' },
  { value: 'manual', label: 'Manual' },
  { value: 'company_intake_form', label: 'Direct form' },
]

function publicUrl(path: string): string {
  if (typeof window === 'undefined') return path
  return `${window.location.origin}${path}`
}

function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 64)
}

function emptyDraft(ownCompanyId = ''): Draft {
  return {
    name: '',
    own_company_id: ownCompanyId,
    public_slug: '',
    source: 'website',
    default_language: 'pl',
    supported_languages: ['pl', 'en', 'ru'],
    default_assignee_id: null,
    is_active: true,
  }
}

function languagesLabel(values: Language[]): string {
  return values.map((item) => item.toUpperCase()).join(', ')
}

function draftFromProfile(row: CompanyIntakeSourceProfile): Draft {
  return {
    name: row.name,
    own_company_id: row.own_company_id,
    public_slug: row.public_slug,
    source: row.source,
    default_language: row.default_language,
    supported_languages: row.supported_languages,
    default_assignee_id: row.default_assignee_id,
    is_active: row.is_active,
  }
}

export function CompanyIntakeLinksPanel() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [expanded, setExpanded] = useState(false)
  const [profiles, setProfiles] = useState<CompanyIntakeSourceProfile[]>([])
  const [ownCompanies, setOwnCompanies] = useState<OwnCompanyRecord[]>([])
  const [managers, setManagers] = useState<ManagerOption[]>([])
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [editDrafts, setEditDrafts] = useState<Record<string, Draft>>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [errorInfo, setErrorInfo] = useState<FriendlyErrorInfo | null>(null)
  const [forbidden, setForbidden] = useState(false)

  const defaultOwnCompanyId = ownCompanies[0]?.id || ''

  const load = useCallback(async () => {
    setLoading(true)
    setErrorInfo(null)
    setForbidden(false)
    try {
      const [profileRows, ownRows, managerRows] = await Promise.all([
        listCompanyIntakeSourceProfiles(),
        listOwnCompanies(),
        listTenantManagers().catch(() => []),
      ])
      const ownItems = Array.isArray(ownRows?.items) ? ownRows.items : []
      setProfiles(profileRows)
      setOwnCompanies(ownItems)
      setManagers(managerRows)
      setDraft((prev) => ({
        ...prev,
        own_company_id: prev.own_company_id || ownItems[0]?.id || '',
      }))
      setEditDrafts(
        profileRows.reduce<Record<string, Draft>>((acc, row) => {
          acc[row.id] = draftFromProfile(row)
          return acc
        }, {}),
      )
    } catch (err: any) {
      if (err?.response?.status === 403) {
        setForbidden(true)
        return
      }
      setErrorInfo(getFriendlyErrorInfo(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!draft.own_company_id && defaultOwnCompanyId) {
      setDraft((prev) => ({ ...prev, own_company_id: defaultOwnCompanyId }))
    }
  }, [defaultOwnCompanyId, draft.own_company_id])

  const sortedProfiles = useMemo(
    () => [...profiles].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [profiles],
  )

  const activeProfiles = useMemo(() => sortedProfiles.filter((row) => row.is_active), [sortedProfiles])
  const primaryProfile = activeProfiles[0] ?? sortedProfiles[0] ?? null

  const copyText = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
      notify({ type: 'success', message: t('app.companies.intake_links.copied', { defaultValue: 'Link copied' }) })
    } catch {
      notify({ type: 'error', message: t('common.errors.request_failed', { defaultValue: 'Request failed' }) })
    }
  }

  const toggleLanguage = (values: Language[], lang: Language): Language[] => {
    const next = values.includes(lang) ? values.filter((item) => item !== lang) : [...values, lang]
    return next.length > 0 ? next : values
  }

  const createProfile = async () => {
    setSaving(true)
    setErrorInfo(null)
    try {
      const payload = {
        ...draft,
        public_slug: draft.public_slug || slugFromName(draft.name),
      }
      const created = await createCompanyIntakeSourceProfile(payload)
      setProfiles((prev) => [created, ...prev])
      setEditDrafts((prev) => ({ ...prev, [created.id]: draftFromProfile(created) }))
      setDraft(emptyDraft(defaultOwnCompanyId))
      notify({
        type: 'success',
        message: t('app.companies.intake_links.created', { defaultValue: 'Public questionnaire link created' }),
      })
    } catch (err) {
      setErrorInfo(getFriendlyErrorInfo(err))
    } finally {
      setSaving(false)
    }
  }

  const saveProfile = async (row: CompanyIntakeSourceProfile) => {
    const next = editDrafts[row.id]
    if (!next) return
    setSavingId(row.id)
    setErrorInfo(null)
    try {
      const updated = await patchCompanyIntakeSourceProfile(row.id, next)
      setProfiles((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setEditDrafts((prev) => ({ ...prev, [updated.id]: draftFromProfile(updated) }))
      notify({ type: 'success', message: t('common.messages.saved', { defaultValue: 'Saved' }) })
    } catch (err) {
      setErrorInfo(getFriendlyErrorInfo(err))
    } finally {
      setSavingId(null)
    }
  }

  const updateEdit = (id: string, patch: Partial<Draft>) => {
    setEditDrafts((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }))
  }

  const primaryUrl = primaryProfile ? publicUrl(primaryProfile.public_url_path) : ''
  const canCreate = Boolean(draft.name.trim() && draft.own_company_id && draft.public_slug.trim())

  if (forbidden) return null

  return (
    <section className="app-surface border-x-0 border-t-0 p-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <IconLink size={18} className="text-brand-700" />
            <h2 className="text-base font-semibold text-slate-900">
              {t('app.companies.intake_links.title', { defaultValue: 'Questionnaire link for a new client' })}
            </h2>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {activeProfiles.length
                ? t('app.companies.intake_links.active_count', {
                    defaultValue: '{count} active',
                    values: { count: activeProfiles.length },
                  })
                : t('app.companies.intake_links.no_active', { defaultValue: 'No active link' })}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.companies.intake_links.subtitle', {
              defaultValue:
                'Use this link in ads, email, website or manual outreach. Submitted forms create Client Leads, not active clients.',
            })}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {primaryProfile ? (
            <>
              <button
                type="button"
                className="btn-secondary inline-flex items-center gap-2"
                onClick={() => void copyText(primaryUrl)}
              >
                <IconCopy size={16} />
                {t('common.copy', { defaultValue: 'Copy' })}
              </button>
              <a className="btn-secondary inline-flex items-center gap-2" href={primaryUrl} target="_blank" rel="noreferrer">
                <IconExternalLink size={16} />
                {t('common.actions.open', { defaultValue: 'Open' })}
              </a>
            </>
          ) : null}
          <button
            type="button"
            className="btn-primary inline-flex items-center gap-2"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
            {expanded
              ? t('app.companies.intake_links.hide', { defaultValue: 'Hide links' })
              : t('app.companies.intake_links.manage', { defaultValue: 'Create / manage link' })}
          </button>
        </div>
      </div>

      {primaryProfile ? (
        <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span className="font-semibold text-slate-700">{primaryProfile.name}</span>
            <span className="font-mono break-all">{primaryUrl}</span>
          </div>
        </div>
      ) : null}

      {expanded ? (
        <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
          {errorInfo ? (
            <ErrorRecoveryBanner
              info={errorInfo}
              onRetry={() => void load()}
            />
          ) : null}

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  {t('app.companies.intake_links.create_title', { defaultValue: 'Create a public questionnaire link' })}
                </h3>
                <p className="text-xs text-slate-500">
                  {t('app.companies.intake_links.create_hint', {
                    defaultValue: 'The owner company is taken from your workspace, not from the public form payload.',
                  })}
                </p>
              </div>
            </div>

            <div className="grid gap-3 lg:grid-cols-[1.2fr_0.9fr_0.8fr_0.8fr]">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.companies.intake_links.fields.name', { defaultValue: 'Link name' })}
                </span>
                <input
                  className="input w-full"
                  value={draft.name}
                  onChange={(event) => {
                    const name = event.target.value
                    setDraft((prev) => ({
                      ...prev,
                      name,
                      public_slug: prev.public_slug ? prev.public_slug : slugFromName(name),
                    }))
                  }}
                  placeholder="Work Host Business - B2B Transport"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.companies.intake_links.fields.owner', { defaultValue: 'Owner company' })}
                </span>
                <select
                  className="input w-full"
                  value={draft.own_company_id}
                  onChange={(event) => setDraft((prev) => ({ ...prev, own_company_id: event.target.value }))}
                >
                  <option value="">{t('common.select', { defaultValue: 'Select' })}</option>
                  {ownCompanies.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.companies.intake_links.fields.source', { defaultValue: 'Source' })}
                </span>
                <select
                  className="input w-full"
                  value={draft.source}
                  onChange={(event) => setDraft((prev) => ({ ...prev, source: event.target.value }))}
                >
                  {SOURCE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.companies.intake_links.fields.manager', { defaultValue: 'Manager' })}
                </span>
                <select
                  className="input w-full"
                  value={draft.default_assignee_id || ''}
                  onChange={(event) => setDraft((prev) => ({ ...prev, default_assignee_id: event.target.value || null }))}
                >
                  <option value="">{t('common.select', { defaultValue: 'Select' })}</option>
                  {managers.map((manager) => (
                    <option key={manager.id} value={manager.id}>
                      {manager.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto_auto]">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('app.companies.intake_links.fields.slug', { defaultValue: 'Public slug' })}
                </span>
                <input
                  className="input w-full font-mono text-sm"
                  value={draft.public_slug}
                  onChange={(event) => setDraft((prev) => ({ ...prev, public_slug: slugFromName(event.target.value) }))}
                  placeholder="work-host-business"
                />
              </label>
              <select
                className="input self-end"
                value={draft.default_language}
                onChange={(event) => setDraft((prev) => ({ ...prev, default_language: event.target.value as Language }))}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang.toUpperCase()}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-primary inline-flex items-center gap-2 self-end"
                disabled={saving || !canCreate}
                onClick={() => void createProfile()}
              >
                <IconPlus size={16} />
                {saving ? t('common.saving', { defaultValue: 'Saving...' }) : t('common.actions.create', { defaultValue: 'Create' })}
              </button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang}
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                    draft.supported_languages.includes(lang)
                      ? 'border-brand-600 bg-brand-50 text-brand-800'
                      : 'border-slate-200 bg-white text-slate-600'
                  }`}
                  onClick={() => setDraft((prev) => ({ ...prev, supported_languages: toggleLanguage(prev.supported_languages, lang) }))}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
              <span className="text-xs text-slate-500">
                {t('app.companies.intake_links.languages_hint', { defaultValue: 'Form languages' })}:{' '}
                {languagesLabel(draft.supported_languages)}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {loading ? (
              <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</p>
            ) : sortedProfiles.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                {t('app.companies.intake_links.empty', {
                  defaultValue: 'No questionnaire links yet. Create the first one for website, ads or direct outreach.',
                })}
              </p>
            ) : (
              sortedProfiles.map((row) => {
                const d = editDrafts[row.id]
                if (!d) return null
                const url = publicUrl(row.public_url_path)
                return (
                  <div key={row.id} className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="grid gap-3 lg:grid-cols-[1.1fr_0.8fr_0.75fr_0.75fr]">
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.intake_links.fields.name', { defaultValue: 'Link name' })}
                        </span>
                        <input className="input w-full" value={d.name} onChange={(event) => updateEdit(row.id, { name: event.target.value })} />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.intake_links.fields.owner', { defaultValue: 'Owner company' })}
                        </span>
                        <select className="input w-full" value={d.own_company_id} onChange={(event) => updateEdit(row.id, { own_company_id: event.target.value })}>
                          {ownCompanies.map((company) => (
                            <option key={company.id} value={company.id}>
                              {company.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.intake_links.fields.source', { defaultValue: 'Source' })}
                        </span>
                        <select className="input w-full" value={d.source} onChange={(event) => updateEdit(row.id, { source: event.target.value })}>
                          {SOURCE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.intake_links.fields.manager', { defaultValue: 'Manager' })}
                        </span>
                        <select
                          className="input w-full"
                          value={d.default_assignee_id || ''}
                          onChange={(event) => updateEdit(row.id, { default_assignee_id: event.target.value || null })}
                        >
                          <option value="">{t('common.select', { defaultValue: 'Select' })}</option>
                          {managers.map((manager) => (
                            <option key={manager.id} value={manager.id}>
                              {manager.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
                      <label className="block">
                        <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.companies.intake_links.fields.slug', { defaultValue: 'Public slug' })}
                        </span>
                        <input className="input w-full font-mono text-sm" value={d.public_slug} onChange={(event) => updateEdit(row.id, { public_slug: slugFromName(event.target.value) })} />
                      </label>
                      <select className="input self-end" value={d.default_language} onChange={(event) => updateEdit(row.id, { default_language: event.target.value as Language })}>
                        {LANGUAGES.map((lang) => (
                          <option key={lang} value={lang}>
                            {lang.toUpperCase()}
                          </option>
                        ))}
                      </select>
                      <label className="inline-flex items-center gap-2 self-end text-sm text-slate-700">
                        <input type="checkbox" checked={d.is_active} onChange={(event) => updateEdit(row.id, { is_active: event.target.checked })} />
                        {t('app.companies.intake_links.fields.active', { defaultValue: 'Active' })}
                      </label>
                      <button type="button" className="btn-primary self-end" disabled={savingId === row.id} onClick={() => void saveProfile(row)}>
                        {savingId === row.id ? t('common.saving', { defaultValue: 'Saving...' }) : t('common.actions.save', { defaultValue: 'Save' })}
                      </button>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {LANGUAGES.map((lang) => (
                        <button
                          key={lang}
                          type="button"
                          className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                            d.supported_languages.includes(lang)
                              ? 'border-brand-600 bg-brand-50 text-brand-800'
                              : 'border-slate-200 bg-white text-slate-600'
                          }`}
                          onClick={() => updateEdit(row.id, { supported_languages: toggleLanguage(d.supported_languages, lang) })}
                        >
                          {lang.toUpperCase()}
                        </button>
                      ))}
                      <span className="text-xs text-slate-500">
                        {t('app.companies.intake_links.languages_hint', { defaultValue: 'Form languages' })}: {languagesLabel(d.supported_languages)}
                      </span>
                    </div>

                    <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-3">
                      <div className="flex flex-wrap items-center gap-2 break-all font-mono text-xs text-slate-800">
                        <IconLink size={15} className="shrink-0 text-slate-500" />
                        <span className="flex-1">{url}</span>
                        <button type="button" className="btn-secondary btn-sm inline-flex items-center gap-1" onClick={() => void copyText(url)}>
                          <IconCopy size={14} />
                          {t('common.copy', { defaultValue: 'Copy' })}
                        </button>
                        <a className="btn-secondary btn-sm inline-flex items-center gap-1" href={url} target="_blank" rel="noreferrer">
                          <IconExternalLink size={14} />
                          {t('common.actions.open', { defaultValue: 'Open' })}
                        </a>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}
