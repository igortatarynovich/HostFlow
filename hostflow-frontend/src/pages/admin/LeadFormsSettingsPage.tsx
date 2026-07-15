import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { IconClipboardList, IconCopy, IconPlus } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS, settingsLeadFormDetailPath } from '../../app/crmAppPaths'
import {
  createIntakeForm,
  listIntakeFormEntityProfiles,
  type PresentationFieldInput,
} from '../../api/intakeForms'
import { listLeadForms, patchLeadForm, type TenantLeadForm } from '../../api/leadForms'
import IntakeFormAnswersRoutingCard from '../../components/admin/IntakeFormAnswersRoutingCard'
import { IntakeFormPresentationEditor } from '../../components/admin/IntakeFormPresentationEditor'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'
import {
  defaultProfileForPurpose,
  filterProfilesForPurpose,
  PURPOSE_WIZARD_OPTIONS,
  slugifyFormTitle,
  type FormPurposeKey,
} from '../../utils/intakeFormRoutingSummary'

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
  const navigate = useNavigate()
  const canMutate = role === 'administrator'

  const [forms, setForms] = useState<TenantLeadForm[]>([])
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [createPurpose, setCreatePurpose] = useState<FormPurposeKey>('inquiry')
  const [profileOptions, setProfileOptions] = useState<Array<{ code: string; name: string }>>([])
  const [createTitle, setCreateTitle] = useState('')
  const [createSlug, setCreateSlug] = useState('')
  const [createProfileCode, setCreateProfileCode] = useState('service_sales.targeted_advertising')
  const [createFields, setCreateFields] = useState<PresentationFieldInput[]>([])
  const [creating, setCreating] = useState(false)

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

  useEffect(() => {
    if (!canMutate) return
    void listIntakeFormEntityProfiles()
      .then((items) => {
        const mapped = items.map((item) => ({ code: item.code, name: item.name }))
        setProfileOptions(mapped)
        setCreateProfileCode((current) => current || defaultProfileForPurpose(mapped, createPurpose))
      })
      .catch(() => undefined)
  }, [canMutate, createPurpose])

  const filteredProfiles = useMemo(
    () => filterProfilesForPurpose(profileOptions, createPurpose),
    [profileOptions, createPurpose],
  )

  useEffect(() => {
    if (filteredProfiles.length === 0) return
    if (!filteredProfiles.some((row) => row.code === createProfileCode)) {
      setCreateProfileCode(defaultProfileForPurpose(filteredProfiles, createPurpose))
    }
  }, [createProfileCode, createPurpose, filteredProfiles])

  useEffect(() => {
    if (!createSlug.trim() && createTitle.trim()) {
      const next = slugifyFormTitle(createTitle)
      if (next.length >= 2) setCreateSlug(next)
    }
  }, [createSlug, createTitle])

  const handleCreateForm = async () => {
    if (!canMutate) return
    if (createFields.length < 1) {
      notify({
        title: t('admin.intake_forms.errors.no_fields', { defaultValue: 'Select at least one question' }),
        variant: 'error',
      })
      return
    }
    setPageError(null)
    setCreating(true)
    try {
      const created = await createIntakeForm({
        title: createTitle.trim() || 'New form',
        public_slug: createSlug.trim(),
        entity_profile_code: createProfileCode,
        fields: createFields,
        is_active: true,
      })
      notify({
        title: t('admin.intake_forms.toast.created', { defaultValue: 'Form created and activated' }),
        variant: 'success',
      })
      setShowCreate(false)
      setCreateTitle('')
      setCreateSlug('')
      setCreateFields([])
      navigate(settingsLeadFormDetailPath(created.form.id))
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.intake_forms.errors.create', { defaultValue: 'Failed to create form' }),
          t,
        ),
      )
    } finally {
      setCreating(false)
    }
  }

  const updateDraft = (id: string, patch: Partial<Draft>) => {
    setDrafts((prev) => {
      const cur = prev[id]
      if (!cur) return prev
      return { ...prev, [id]: { ...cur, ...patch } }
    })
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

  const wizardDefinition = useMemo(
    () => ({
      purpose: createPurpose,
      target_entity_profile_code: createProfileCode,
      submission_policy: { mode: 'match_or_create' },
    }),
    [createProfileCode, createPurpose],
  )

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('admin.lead_forms.header_kicker')}
      title={
        <span className="inline-flex items-center gap-2">
          <IconClipboardList size={22} stroke={1.9} className="text-brand-600" />
          {t('admin.lead_forms.title', { defaultValue: 'Lead forms' })}
        </span>
      }
      subtitle={t('admin.lead_forms.subtitle_b1', {
        defaultValue:
          'Create and configure questionnaires. Pick a purpose, add questions, then send from Sales inquiries.',
      })}
      actions={
        <Link className="text-sm font-medium text-brand-700 hover:underline" to={CRM_APP_PATHS.settingsBilling}>
          {t('admin.lead_forms.link_billing', { defaultValue: 'Billing & limits' })}
        </Link>
      }
    >
      <section className="settings-panel">
        {pageError && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={pageError}
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
          <div className="mb-6">
            {!showCreate ? (
              <button type="button" className="btn-primary inline-flex items-center gap-2" onClick={() => setShowCreate(true)}>
                <IconPlus size={16} />
                {t('admin.lead_forms.create_form', { defaultValue: 'Create form' })}
              </button>
            ) : (
              <div className="space-y-4 rounded-xl border border-brand-100 bg-white p-4 shadow-sm" data-testid="lead-form-create-wizard">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">
                    {t('admin.lead_forms.wizard_title', { defaultValue: 'New form' })}
                  </h3>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setShowCreate(false)}>
                    {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                  </button>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('admin.lead_forms.wizard.purpose', { defaultValue: '1. Purpose' })}
                  </p>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {PURPOSE_WIZARD_OPTIONS.map((option) => (
                      <label
                        key={option.purpose}
                        className={`cursor-pointer rounded-xl border p-3 text-sm ${
                          createPurpose === option.purpose
                            ? 'border-brand-300 bg-brand-50/60'
                            : 'border-slate-200 bg-white hover:border-slate-300'
                        }`}
                      >
                        <input
                          type="radio"
                          className="sr-only"
                          name="form-purpose"
                          checked={createPurpose === option.purpose}
                          onChange={() => setCreatePurpose(option.purpose)}
                        />
                        <span className="font-semibold text-slate-900">{option.label}</span>
                        <p className="mt-1 text-xs text-slate-600">{option.hint}</p>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block text-sm sm:col-span-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.lead_forms.wizard.profile', { defaultValue: '2. Entity profile' })}
                    </span>
                    <select
                      className="input mt-1 w-full"
                      value={createProfileCode}
                      onChange={(event) => setCreateProfileCode(event.target.value)}
                    >
                      {filteredProfiles.map((profile) => (
                        <option key={profile.code} value={profile.code}>
                          {profile.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.lead_forms.fields.title', { defaultValue: '3. Form title' })}
                    </span>
                    <input
                      className="input mt-1 w-full"
                      value={createTitle}
                      onChange={(event) => setCreateTitle(event.target.value)}
                      placeholder={t('admin.lead_forms.placeholders.b2b_title', {
                        defaultValue: 'e.g. B2B advertising questionnaire',
                      })}
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.intake_forms.fields.slug', { defaultValue: 'Public slug' })}
                    </span>
                    <input
                      className="input mt-1 w-full font-mono text-sm"
                      value={createSlug}
                      onChange={(event) => setCreateSlug(event.target.value)}
                      placeholder="my-b2b-form"
                    />
                  </label>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('admin.lead_forms.wizard.questions', { defaultValue: '4. Questions' })}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {t('admin.lead_forms.wizard.questions_hint', {
                      defaultValue: 'Select fields, edit labels, order, required level, and show-if rules.',
                    })}
                  </p>
                  <div className="mt-3">
                    <IntakeFormPresentationEditor
                      entityProfileCode={createProfileCode}
                      onEntityProfileChange={setCreateProfileCode}
                      onChange={setCreateFields}
                    />
                  </div>
                </div>

                <IntakeFormAnswersRoutingCard definition={wizardDefinition} entityProfileCode={createProfileCode} />

                <button
                  type="button"
                  className="btn-primary"
                  disabled={creating || createFields.length === 0 || createSlug.trim().length < 2}
                  onClick={() => void handleCreateForm()}
                >
                  {creating
                    ? t('common.saving', { defaultValue: 'Saving…' })
                    : t('admin.lead_forms.wizard.save_activate', { defaultValue: 'Save and activate form' })}
                </button>
              </div>
            )}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
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
                <li key={row.id} className="rounded-xl border border-brand-100 bg-white p-4 shadow-sm">
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
                        disabled={!canMutate}
                      />
                    </label>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="rounded border-slate-300"
                        checked={d.is_active}
                        onChange={(e) => updateDraft(row.id, { is_active: e.target.checked })}
                        disabled={!canMutate}
                      />
                      <span className="text-sm text-slate-700">
                        {t('admin.lead_forms.fields.active', { defaultValue: 'Active' })}
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
                    <Link
                      to={settingsLeadFormDetailPath(row.id)}
                      className="btn-secondary btn-sm inline-flex items-center gap-1"
                    >
                      {t('admin.lead_forms.configure', { defaultValue: 'Configure questions & routing' })}
                    </Link>
                  </div>
                  {slugOk && (
                    <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/80 p-3">
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {t('admin.lead_forms.share_url', { defaultValue: 'Public intake URL' })}
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
    </SettingsSubpageHeader>
  )
}
