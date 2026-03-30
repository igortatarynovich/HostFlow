import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconClipboardList, IconCopy } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  createLeadForm,
  listLeadForms,
  patchLeadForm,
  type TenantLeadForm,
} from '../../api/leadForms'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

type Draft = { title: string; public_slug: string; is_active: boolean }

function publicIntakeUrlForSlug(slug: string): string {
  if (typeof window === 'undefined') return `/public/intake?lead_form_slug=${encodeURIComponent(slug)}`
  const q = new URLSearchParams({ lead_form_slug: slug })
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export default function LeadFormsSettingsPage() {
  const { t } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const canMutate = role === 'administrator'

  const [forms, setForms] = useState<TenantLeadForm[]>([])
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [creating, setCreating] = useState(false)
  const [savingId, setSavingId] = useState<string | null>(null)

  const syncDraftsFromRows = useCallback((rows: TenantLeadForm[]) => {
    setDrafts(
      Object.fromEntries(
        rows.map((r) => [
          r.id,
          {
            title: r.title || '',
            public_slug: (r.public_slug || '').trim(),
            is_active: r.is_active,
          },
        ]),
      ),
    )
  }, [])

  const load = useCallback(async () => {
    setPageError(null)
    try {
      setLoading(true)
      const rows = await listLeadForms()
      setForms(rows)
      syncDraftsFromRows(rows)
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.lead_forms.errors.load', { defaultValue: 'Failed to load lead forms' }), t),
      )
      setForms([])
      setDrafts({})
    } finally {
      setLoading(false)
    }
  }, [syncDraftsFromRows, t])

  useEffect(() => {
    void load()
  }, [load])

  const updateDraft = (id: string, patch: Partial<Draft>) => {
    setDrafts((prev) => {
      const cur = prev[id]
      if (!cur) return prev
      return { ...prev, [id]: { ...cur, ...patch } }
    })
  }

  const handleCreate = async () => {
    if (!canMutate) return
    setPageError(null)
    setCreating(true)
    try {
      const created = await createLeadForm({ title: newTitle.trim() || undefined })
      setForms((prev) => [...prev, created])
      setDrafts((prev) => ({
        ...prev,
        [created.id]: {
          title: created.title || '',
          public_slug: (created.public_slug || '').trim(),
          is_active: created.is_active,
        },
      }))
      setNewTitle('')
      notify({
        title: t('admin.lead_forms.toast.created', { defaultValue: 'Lead form created' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.lead_forms.errors.create', { defaultValue: 'Failed to create form' }), t),
      )
    } finally {
      setCreating(false)
    }
  }

  const handleSaveRow = async (row: TenantLeadForm) => {
    if (!canMutate) return
    const d = drafts[row.id]
    if (!d) return
    setPageError(null)
    setSavingId(row.id)
    try {
      const slugTrim = d.public_slug.trim()
      const updated = await patchLeadForm(row.id, {
        title: d.title.trim() || undefined,
        is_active: d.is_active,
        public_slug: slugTrim === '' ? '' : slugTrim,
      })
      setForms((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
      setDrafts((prev) => ({
        ...prev,
        [updated.id]: {
          title: updated.title || '',
          public_slug: (updated.public_slug || '').trim(),
          is_active: updated.is_active,
        },
      }))
      notify({
        title: t('admin.lead_forms.toast.saved', { defaultValue: 'Saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.lead_forms.errors.save', { defaultValue: 'Failed to save form' }), t),
      )
    } finally {
      setSavingId(null)
    }
  }

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      notify({
        title: t('admin.lead_forms.toast.copied', { defaultValue: 'Copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('admin.lead_forms.errors.copy', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  const isDirty = useCallback(
    (row: TenantLeadForm) => {
      const d = drafts[row.id]
      if (!d) return false
      return (
        d.title !== (row.title || '') ||
        d.public_slug !== (row.public_slug || '').trim() ||
        d.is_active !== row.is_active
      )
    },
    [drafts],
  )

  const sortedForms = useMemo(() => [...forms].sort((a, b) => a.created_at.localeCompare(b.created_at)), [forms])

  return (
    <div className="space-y-4">
      <section className="card p-6">
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="inline-flex items-center gap-2 text-xl font-semibold text-slate-900">
              <IconClipboardList size={22} stroke={1.9} className="text-brand-600" />
              <h1 className="text-xl font-semibold">{t('admin.lead_forms.title', { defaultValue: 'Lead forms' })}</h1>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {t('admin.lead_forms.subtitle', {
                defaultValue:
                  'Intake entry points for the public portal. Set a public slug to address a form from /public/intake.',
              })}
            </p>
          </div>
          <Link className="text-sm font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.settingsBilling}>
            {t('admin.lead_forms.link_billing', { defaultValue: 'Billing & limits' })}
          </Link>
        </header>

        {pageError && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              title={pageError.title}
              detail={pageError.detail}
              hint={pageError.hint}
              {...friendlyErrorBannerSecondary(pageError, CRM_APP_PATHS.settingsBilling, t('admin.settings.cards.billing.label'))}
            />
          </div>
        )}

        {!canMutate && (
          <p className="mb-4 rounded-xl border border-amber-100 bg-amber-50/80 px-3 py-2 text-sm text-amber-900">
            {t('admin.lead_forms.read_only_hint', {
              defaultValue: 'Only workspace administrators can create or edit lead forms.',
            })}
          </p>
        )}

        {canMutate && (
          <div className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-brand-100 bg-brand-50/20 p-4">
            <label className="min-w-[220px] flex-1">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.lead_forms.new_title', { defaultValue: 'New form title' })}
              </span>
              <input
                type="text"
                className="input w-full"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={t('admin.lead_forms.placeholders.title', { defaultValue: 'e.g. Facebook campaigns' })}
                disabled={creating}
              />
            </label>
            <button type="button" className="btn-primary" disabled={creating} onClick={() => void handleCreate()}>
              {creating ? t('common.saving', { defaultValue: 'Saving…' }) : t('admin.lead_forms.create', { defaultValue: 'Create form' })}
            </button>
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        ) : sortedForms.length === 0 ? (
          <p className="text-sm text-slate-500">
            {t('admin.lead_forms.empty', { defaultValue: 'No lead forms yet. Create one to start tracking intake sources.' })}
          </p>
        ) : (
          <ul className="space-y-4">
            {sortedForms.map((row) => {
              const d = drafts[row.id]
              if (!d) return null
              const slugOk = d.public_slug.trim().length >= 2
              const shareUrl = slugOk ? publicIntakeUrlForSlug(d.public_slug.trim()) : ''
              const dirty = isDirty(row)
              return (
                <li key={row.id} className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm">
                  <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
                    <label className="block">
                      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('admin.lead_forms.fields.title', { defaultValue: 'Title' })}
                      </span>
                      <input
                        type="text"
                        className="input w-full"
                        value={d.title}
                        onChange={(e) => updateDraft(row.id, { title: e.target.value })}
                        disabled={!canMutate}
                      />
                    </label>
                    <label className="block">
                      <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('admin.lead_forms.fields.public_slug', { defaultValue: 'Public slug' })}
                      </span>
                      <input
                        type="text"
                        className="input w-full font-mono text-sm"
                        value={d.public_slug}
                        onChange={(e) => updateDraft(row.id, { public_slug: e.target.value })}
                        placeholder={t('admin.lead_forms.placeholders.slug', { defaultValue: 'my-campaign' })}
                        disabled={!canMutate}
                      />
                      <p className="mt-1 text-xs text-slate-500">
                        {t('admin.lead_forms.slug_hint', {
                          defaultValue: 'Lowercase letters, digits, hyphens; 2–64 characters. Leave empty to unpublish.',
                        })}
                      </p>
                    </label>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="rounded border-slate-300"
                        checked={d.is_active}
                        onChange={(e) => updateDraft(row.id, { is_active: e.target.checked })}
                        disabled={!canMutate}
                      />
                      <span className="text-sm text-slate-700">
                        {t('admin.lead_forms.fields.active', { defaultValue: 'Active (counts toward plan limit)' })}
                      </span>
                    </label>
                    {canMutate && (
                      <button
                        type="button"
                        className="btn-secondary btn-sm"
                        disabled={!dirty || savingId === row.id}
                        onClick={() => void handleSaveRow(row)}
                      >
                        {savingId === row.id ? t('common.saving') : t('common.actions.save')}
                      </button>
                    )}
                  </div>
                  {slugOk && (
                    <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/80 p-3">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('admin.lead_forms.share_url', { defaultValue: 'Public intake URL (this host)' })}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 break-all font-mono text-xs text-slate-800">
                        <span className="flex-1">{shareUrl}</span>
                        <button
                          type="button"
                          className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                          onClick={() => void copyText(shareUrl)}
                        >
                          <IconCopy size={14} />
                          {t('admin.lead_forms.copy', { defaultValue: 'Copy' })}
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}
