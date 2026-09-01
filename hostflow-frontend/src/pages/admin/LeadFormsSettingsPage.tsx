import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { IconClipboardList, IconCopy, IconForms, IconPlus, IconTrash } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS, settingsLeadFormBuilderPath, settingsLeadFormDetailPath } from '../../app/crmAppPaths'
import {
  createIntakeForm,
  listIntakeFormEntityProfiles,
  patchIntakeForm,
  type PresentationFieldInput,
} from '../../api/intakeForms'
import { listLeadForms, patchLeadForm, type TenantLeadForm } from '../../api/leadForms'
import { IntakeFormPresentationEditor } from '../../components/admin/IntakeFormPresentationEditor'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'
import { intakePresentationProfileTitle } from '../../utils/intakePresentationI18n'
import {
  defaultProfileForPurpose,
  entityProfileLabel,
  filterProfilesForPurpose,
  PURPOSE_WIZARD_OPTIONS,
  slugifyFormTitle,
  type FormPurposeKey,
} from '../../utils/intakeFormRoutingSummary'

type Draft = { title: string; public_slug: string; is_active: boolean }

function publicIntakeUrlForSlug(slug: string, opts?: { applicationKind?: 'client' | 'candidate' }): string {
  const q = new URLSearchParams({ lead_form_slug: slug })
  if (opts?.applicationKind) q.set('application_kind', opts.applicationKind)
  if (typeof window === 'undefined') return `/public/intake?${q.toString()}`
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export default function LeadFormsSettingsPage() {
  const { t, locale } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const isMarketingInventory = location.pathname.includes('/marketing/forms')
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
  const [createProfileCode, setCreateProfileCode] = useState('service_sales.driver_hiring')
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
      const visible = rows.filter((r) => r.lifecycle_status !== 'archived')
      setForms(visible)
      syncDraftsFromRows(visible)
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
      navigate(settingsLeadFormBuilderPath(created.form.id))
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

  const handleArchiveForm = async (row: TenantLeadForm) => {
    if (!canMutate) return
    const title = (drafts[row.id]?.title || row.title || '').trim() || row.id
    const ok = window.confirm(
      t('admin.forms_builder.delete_confirm', {
        defaultValue:
          'Archive “{title}”? It will disappear from Form Builder, Marketing, and Sales. Existing submissions stay.',
        values: { title },
      }),
    )
    if (!ok) return
    setPageError(null)
    setSavingId(row.id)
    try {
      await patchIntakeForm(row.id, { lifecycle_status: 'archived' })
      notify({
        title: t('admin.forms_builder.toast.archived', { defaultValue: 'Form archived' }),
        variant: 'success',
      })
      await load()
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.forms_builder.errors.archive', { defaultValue: 'Failed to archive form' }),
          t,
        ),
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

  const primaryPurposeOptions = useMemo(
    () => PURPOSE_WIZARD_OPTIONS.filter((option) => option.prominence === 'primary'),
    [],
  )
  const secondaryPurposeOptions = useMemo(
    () => PURPOSE_WIZARD_OPTIONS.filter((option) => option.prominence === 'secondary'),
    [],
  )
  const showProfilePicker = filteredProfiles.length > 1
  const titlePlaceholder =
    createPurpose === 'application'
      ? t('admin.lead_forms.wizard.title_placeholder_candidate', {
          defaultValue: 'e.g. Driver C+E application',
        })
      : t('admin.lead_forms.wizard.title_placeholder_company', {
          defaultValue: 'e.g. Questionnaire for companies that need drivers',
        })
  const destinationHint =
    createPurpose === 'application'
      ? t('admin.lead_forms.wizard.destination_candidate', {
          defaultValue: 'Answers land in Recruitment as a candidate application.',
        })
      : t('admin.lead_forms.wizard.destination_company', {
          defaultValue: 'Answers land in Sales → Inquiries. A driver does not fill this form.',
        })

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={
        isMarketingInventory
          ? t('admin.lead_forms.header_kicker')
          : t('admin.forms_builder.kicker', { defaultValue: 'Forms' })
      }
      title={
        <span className="inline-flex items-center gap-2">
          {isMarketingInventory ? (
            <IconClipboardList size={22} stroke={1.9} className="text-brand-600" />
          ) : (
            <IconForms size={22} stroke={1.9} className="text-brand-600" />
          )}
          {isMarketingInventory
            ? t('app.nav.items.marketing_forms', { defaultValue: 'Forms' })
            : t('admin.forms_builder.library_title', { defaultValue: 'Form Builder' })}
        </span>
      }
      subtitle={
        isMarketingInventory
          ? t('admin.lead_forms.subtitle_b1', {
              defaultValue:
                'Campaign inventory: activate a HostFlow form and copy the public URL. The constructor lives in Settings → Form Builder.',
            })
          : t('admin.forms_builder.library_subtitle', {
              defaultValue:
                'Create a form for a company request or for a candidate, then share the public URL.',
            })
      }
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
                    {t('admin.lead_forms.wizard.who_fills', { defaultValue: '1. Who fills this form?' })}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {t('admin.lead_forms.wizard.who_fills_hint', {
                      defaultValue: 'Choose company request if a firm wants you to hire drivers. Choose candidate application only if the driver fills it in themselves.',
                    })}
                  </p>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {primaryPurposeOptions.map((option) => (
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
                        <span className="font-semibold text-slate-900">
                          {t(option.labelKey, { defaultValue: option.label })}
                        </span>
                        <p className="mt-1 text-xs text-slate-600">
                          {t(option.hintKey, { defaultValue: option.hint })}
                        </p>
                        {option.exampleKey ? (
                          <p className="mt-1 text-xs font-medium text-slate-700">
                            {t(option.exampleKey, { defaultValue: option.example || '' })}
                          </p>
                        ) : null}
                      </label>
                    ))}
                  </div>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-medium text-slate-500">
                      {t('admin.lead_forms.wizard.other_types', { defaultValue: 'Other form types' })}
                    </summary>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      {secondaryPurposeOptions.map((option) => (
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
                          <span className="font-semibold text-slate-900">
                            {t(option.labelKey, { defaultValue: option.label })}
                          </span>
                          <p className="mt-1 text-xs text-slate-600">
                            {t(option.hintKey, { defaultValue: option.hint })}
                          </p>
                        </label>
                      ))}
                    </div>
                  </details>
                </div>

                <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  {destinationHint}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {showProfilePicker ? (
                    <label className="block text-sm sm:col-span-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {createPurpose === 'application'
                          ? t('admin.lead_forms.wizard.candidate_role', { defaultValue: 'Candidate role' })
                          : t('admin.lead_forms.wizard.company_questionnaire', {
                              defaultValue: 'What does the company need?',
                            })}
                      </span>
                      <select
                        className="input mt-1 w-full"
                        value={createProfileCode}
                        onChange={(event) => setCreateProfileCode(event.target.value)}
                      >
                        {filteredProfiles.map((profile) => (
                          <option key={profile.code} value={profile.code}>
                            {intakePresentationProfileTitle(
                              t,
                              { entity_profile_code: profile.code, profile_name: entityProfileLabel(profile.code) },
                              locale,
                            )}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  <label className="block text-sm">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.lead_forms.wizard.name', { defaultValue: '2. Form name' })}
                    </span>
                    <input
                      className="input mt-1 w-full"
                      value={createTitle}
                      onChange={(event) => setCreateTitle(event.target.value)}
                      placeholder={titlePlaceholder}
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.lead_forms.fields.public_slug', { defaultValue: 'Public link id' })}
                    </span>
                    <input
                      className="input mt-1 w-full font-mono text-sm"
                      value={createSlug}
                      onChange={(event) => setCreateSlug(event.target.value)}
                      placeholder={t('admin.lead_forms.placeholders.company_slug', {
                        defaultValue: 'company-needs-drivers',
                      })}
                    />
                  </label>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {t('admin.lead_forms.wizard.questions', { defaultValue: '3. Questions' })}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {createPurpose === 'application'
                      ? t('admin.lead_forms.wizard.questions_hint_candidate', {
                          defaultValue: 'These questions are answered by the candidate.',
                        })
                      : t('admin.lead_forms.wizard.questions_hint_company', {
                          defaultValue:
                            'Ready questions for a company. Keep “who are you looking for” if the firm wants drivers.',
                        })}
                  </p>
                  <div className="mt-3">
                    <IntakeFormPresentationEditor
                      key={`${createPurpose}:${createProfileCode}`}
                      entityProfileCode={createProfileCode}
                      hideProfileSelect
                      autoLoadPreset={createPurpose !== 'application'}
                      variant="wizard"
                      onChange={setCreateFields}
                    />
                  </div>
                </div>

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
            {isMarketingInventory
              ? t('admin.lead_forms.empty', { defaultValue: 'No forms yet. Create one to share a public intake URL.' })
              : t('admin.forms_builder.library_empty', {
                  defaultValue: 'No forms yet. Create one, then assemble fields in Form Builder.',
                })}
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
                    <Link
                      to={settingsLeadFormBuilderPath(row.id)}
                      className="btn-primary btn-sm inline-flex items-center gap-1"
                      data-testid="lead-form-open-builder"
                    >
                      <IconForms size={14} />
                      {t('admin.forms_builder.open', { defaultValue: 'Open Builder' })}
                    </Link>
                    {canMutate && (
                      <button
                        type="button"
                        className="btn-secondary btn-sm inline-flex items-center gap-1 text-rose-700"
                        disabled={savingId === row.id}
                        data-testid="lead-form-archive"
                        onClick={() => void handleArchiveForm(row)}
                      >
                        <IconTrash size={14} />
                        {t('common.actions.delete', { defaultValue: 'Delete' })}
                      </button>
                    )}
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
