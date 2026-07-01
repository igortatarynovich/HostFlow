import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  IconArrowLeft,
  IconClipboardCheck,
  IconCopy,
  IconExternalLink,
  IconForms,
  IconPlayerPlay,
} from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  getIntakeFormDetail,
  patchIntakeForm,
  putIntakeFormPresentation,
  smokeTestIntakeForm,
  type IntakeFormDetail,
  type IntakeFormSmokeTestResult,
  type PresentationFieldInput,
} from '../../api/intakeForms'
import {
  detailFieldsToDraft,
  IntakeFormPresentationEditor,
  SavePresentationButton,
  type PresentationFieldDraft,
} from '../../components/admin/IntakeFormPresentationEditor'
import { IntakeFormMappingEditor } from '../../components/admin/IntakeFormMappingEditor'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

function publicIntakeUrlForSlug(slug: string): string {
  if (typeof window === 'undefined') return `/public/intake?lead_form_slug=${encodeURIComponent(slug)}`
  const q = new URLSearchParams({ lead_form_slug: slug })
  return `${window.location.origin}/public/intake?${q.toString()}`
}

export default function IntakeFormDetailPage() {
  const { formId = '' } = useParams<{ formId: string }>()
  const { t } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const canMutate = role === 'administrator'

  const [detail, setDetail] = useState<IntakeFormDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [smokeRunning, setSmokeRunning] = useState(false)
  const [smokeResult, setSmokeResult] = useState<IntakeFormSmokeTestResult | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editSlug, setEditSlug] = useState('')
  const [entityProfileCode, setEntityProfileCode] = useState('')
  const [presentationFields, setPresentationFields] = useState<PresentationFieldInput[]>([])
  const [presentationDraft, setPresentationDraft] = useState<PresentationFieldDraft[]>([])
  const [metaSaving, setMetaSaving] = useState(false)
  const [presentationSaving, setPresentationSaving] = useState(false)

  const load = useCallback(async () => {
    if (!formId) return
    setPageError(null)
    try {
      setLoading(true)
      const payload = await getIntakeFormDetail(formId)
      setDetail(payload)
      setEditTitle(payload.form.title || '')
      setEditSlug(payload.form.public_slug || '')
      setEntityProfileCode(payload.entity_profile.code)
      setPresentationDraft(detailFieldsToDraft(payload))
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.intake_forms.errors.load_detail', { defaultValue: 'Failed to load intake form' }),
          t,
        ),
      )
      setDetail(null)
    } finally {
      setLoading(false)
    }
  }, [formId, t])

  useEffect(() => {
    void load()
  }, [load])

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      notify({
        title: t('admin.intake_forms.toast.copied', { defaultValue: 'Copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('admin.intake_forms.errors.copy', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  const runSmokeTest = async () => {
    if (!canMutate || !formId) return
    setPageError(null)
    setSmokeRunning(true)
    setSmokeResult(null)
    try {
      const result = await smokeTestIntakeForm(formId)
      setSmokeResult(result)
      notify({
        title: t('admin.intake_forms.toast.smoke_ok', { defaultValue: 'Smoke test lead draft created' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.intake_forms.errors.smoke', { defaultValue: 'Smoke test failed' }),
          t,
        ),
      )
    } finally {
      setSmokeRunning(false)
    }
  }

  const saveMetadata = async () => {
    if (!canMutate || !formId) return
    setPageError(null)
    setMetaSaving(true)
    try {
      const updated = await patchIntakeForm(formId, {
        title: editTitle.trim() || undefined,
        public_slug: editSlug.trim() || undefined,
        entity_profile_code: entityProfileCode || undefined,
      })
      setDetail(updated)
      notify({
        title: t('admin.intake_forms.toast.saved', { defaultValue: 'Form settings saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(err, t('admin.intake_forms.errors.save', { defaultValue: 'Failed to save form' }), t),
      )
    } finally {
      setMetaSaving(false)
    }
  }

  const savePresentation = async () => {
    if (!canMutate || !formId || !entityProfileCode) return
    if (presentationFields.length === 0) {
      notify({
        title: t('admin.intake_forms.errors.no_fields', { defaultValue: 'Select at least one field' }),
        variant: 'error',
      })
      return
    }
    setPageError(null)
    setPresentationSaving(true)
    try {
      const updated = await putIntakeFormPresentation(formId, {
        entity_profile_code: entityProfileCode,
        fields: presentationFields,
      })
      setDetail(updated)
      setPresentationDraft(detailFieldsToDraft(updated))
      notify({
        title: t('admin.intake_forms.toast.presentation_saved', { defaultValue: 'Presentation saved' }),
        variant: 'success',
      })
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.intake_forms.errors.save_presentation', { defaultValue: 'Failed to save presentation' }),
          t,
        ),
      )
    } finally {
      setPresentationSaving(false)
    }
  }

  const sortedFields = useMemo(
    () => [...(detail?.presentation.fields ?? [])].sort((a, b) => a.sort_order - b.sort_order),
    [detail?.presentation.fields],
  )

  const publicSlug = detail?.form.public_slug?.trim() || ''
  const publicUrl = publicSlug ? publicIntakeUrlForSlug(publicSlug) : ''

  return (
    <div className="space-y-4">
      <section className="settings-panel">
        <SettingsSubpageHeader
          backLabel={t('admin.intake_forms.back_list', { defaultValue: 'All intake forms' })}
          backHref={CRM_APP_PATHS.settingsLeadForms}
          kicker={t('admin.intake_forms.header_kicker', { defaultValue: 'Intake sources' })}
          title={
            <span className="inline-flex items-center gap-2">
              <IconForms size={22} stroke={1.9} className="text-brand-600" />
              {detail?.form.title || t('admin.intake_forms.detail_title', { defaultValue: 'Intake form' })}
            </span>
          }
          subtitle={t('admin.intake_forms.detail_subtitle', {
            defaultValue:
              'Configure Entity Profile presentation fields, public link, and submit pipeline. UI selects canon fields only.',
          })}
        />

        {pageError && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={pageError}
              {...friendlyErrorBannerSecondary(
                pageError,
                CRM_APP_PATHS.settingsLeadForms,
                t('admin.intake_forms.back_list', { defaultValue: 'All intake forms' }),
              )}
            />
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : !detail ? null : (
          <div className="space-y-6">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.form', { defaultValue: 'Lead form slot' })}
                </h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.status', { defaultValue: 'Status' })}</dt>
                    <dd className="font-medium text-slate-900">
                      {detail.form.is_active
                        ? t('admin.intake_forms.status.active', { defaultValue: 'Active' })
                        : t('admin.intake_forms.status.inactive', { defaultValue: 'Inactive' })}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.slug', { defaultValue: 'Public slug' })}</dt>
                    <dd className="font-mono text-xs text-slate-900">{publicSlug || '—'}</dd>
                  </div>
                </dl>
                {!detail.form.is_active && (
                  <p className="mt-3 text-xs text-amber-800">
                    {t('admin.intake_forms.inactive_hint', {
                      defaultValue: 'Activate the form in list settings before sharing or smoke testing.',
                    })}
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-brand-100 bg-brand-50/30 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.entity_profile', { defaultValue: 'Entity Profile' })}
                </h3>
                <dl className="mt-3 space-y-2 text-sm">
                  <div>
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.profile_code', { defaultValue: 'Profile code' })}</dt>
                    <dd className="mt-0.5 font-mono text-xs text-slate-900">{detail.entity_profile.code}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.profile_name', { defaultValue: 'Name' })}</dt>
                    <dd className="font-medium text-slate-900">{detail.entity_profile.name || '—'}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">
                      {t('admin.intake_forms.fields.presentation', { defaultValue: 'Presentation' })}
                    </dt>
                    <dd className="mt-0.5 font-mono text-xs text-slate-900">{detail.presentation.presentation_code}</dd>
                  </div>
                </dl>
              </div>
            </div>

            {detail.intake_source_profile && (
              <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.intake_source', { defaultValue: 'Intake Source profile' })}
                </h3>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.route_intent', { defaultValue: 'Route intent' })}</dt>
                    <dd className="font-medium">{detail.intake_source_profile.route_intent}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.provider', { defaultValue: 'Provider' })}</dt>
                    <dd className="font-medium">{detail.intake_source_profile.provider}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">{t('admin.intake_forms.fields.assignee', { defaultValue: 'Default assignee' })}</dt>
                    <dd className="font-mono text-xs">{detail.intake_source_profile.default_assignee_id || '—'}</dd>
                  </div>
                </dl>
              </div>
            )}

            <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.intake_forms.sections.form_edit', { defaultValue: 'Form metadata' })}
              </h3>
              {canMutate ? (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="block text-sm">
                    <span className="text-slate-500">{t('admin.lead_forms.fields.title', { defaultValue: 'Title' })}</span>
                    <input
                      className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                      value={editTitle}
                      onChange={(event) => setEditTitle(event.target.value)}
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-slate-500">{t('admin.intake_forms.fields.slug', { defaultValue: 'Public slug' })}</span>
                    <input
                      className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 font-mono text-sm"
                      value={editSlug}
                      onChange={(event) => setEditSlug(event.target.value)}
                    />
                  </label>
                  <div className="sm:col-span-2">
                    <button type="button" className="btn-secondary" disabled={metaSaving} onClick={() => void saveMetadata()}>
                      {metaSaving ? t('common.loading') : t('admin.intake_forms.save_metadata', { defaultValue: 'Save metadata' })}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>

            {canMutate && (
              <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.presentation_edit', { defaultValue: 'Presentation fields (P8)' })}
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  {t('admin.intake_forms.presentation_edit_hint', {
                    defaultValue: 'Select fields from Entity Profile, set labels and required level. Does not create canonical fields.',
                  })}
                </p>
                <div className="mt-4">
                  <IntakeFormPresentationEditor
                    entityProfileCode={entityProfileCode}
                    initialFields={presentationDraft}
                    onEntityProfileChange={setEntityProfileCode}
                    onChange={setPresentationFields}
                  />
                </div>
                <div className="mt-4">
                  <SavePresentationButton saving={presentationSaving} onClick={() => void savePresentation()} />
                </div>
              </div>
            )}

            {canMutate && (
              <div className="rounded-2xl border border-brand-100 bg-white p-4 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.mapping_edit', { defaultValue: 'Provider field mapping (P9)' })}
                </h3>
                <div className="mt-4">
                  <IntakeFormMappingEditor formId={formId} entityProfileCode={entityProfileCode} />
                </div>
              </div>
            )}

            <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.intake_forms.sections.preview', { defaultValue: 'Field preview (P5A runtime)' })}
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                {t('admin.intake_forms.preview_hint', {
                  defaultValue: 'Display-only fields returned by Form Presentation Runtime after save.',
                })}
              </p>
              {sortedFields.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">{t('admin.intake_forms.preview_empty', { defaultValue: 'No fields' })}</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2">{t('admin.intake_forms.columns.label', { defaultValue: 'Label' })}</th>
                        <th className="px-2 py-2">{t('admin.intake_forms.columns.field', { defaultValue: 'Field code' })}</th>
                        <th className="px-2 py-2">{t('admin.intake_forms.columns.level', { defaultValue: 'Intake level' })}</th>
                        <th className="px-2 py-2">{t('admin.intake_forms.columns.widget', { defaultValue: 'Widget' })}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedFields.map((field) => (
                        <tr key={field.qualified_code} className="border-b border-slate-50">
                          <td className="px-2 py-2 font-medium text-slate-900">{field.label}</td>
                          <td className="px-2 py-2 font-mono text-xs text-slate-600">{field.qualified_code}</td>
                          <td className="px-2 py-2 text-slate-700">{field.intake_level}</td>
                          <td className="px-2 py-2 text-slate-700">{field.widget_hint || field.field_type || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/40 p-4">
              <h3 className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-emerald-800">
                <IconClipboardCheck size={16} />
                {t('admin.intake_forms.sections.submit', { defaultValue: 'Submit destination' })}
              </h3>
              <p className="mt-2 text-sm text-emerald-950">{detail.submit_destination.pipeline}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-emerald-900">
                <li>
                  {t('admin.intake_forms.submit.lead_draft', {
                    defaultValue: 'Create: Lead draft only (no Candidate on POST /public/intake)',
                  })}
                </li>
                <li>
                  {t('admin.intake_forms.submit.outcome', {
                    defaultValue: 'Submit: Decision Layer → Outcome Executor (Candidate only on create_candidate)',
                  })}
                </li>
              </ul>
            </div>

            {publicUrl && (
              <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.public_link', { defaultValue: 'Public link' })}
                </h3>
                <div className="mt-2 flex flex-wrap items-center gap-2 break-all font-mono text-xs text-slate-800">
                  <span className="flex-1">{publicUrl}</span>
                  <button
                    type="button"
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                    onClick={() => void copyText(publicUrl)}
                  >
                    <IconCopy size={14} />
                    {t('admin.intake_forms.copy', { defaultValue: 'Copy' })}
                  </button>
                  <a
                    href={publicUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-brand-700 hover:bg-slate-50"
                  >
                    <IconExternalLink size={14} />
                    {t('admin.intake_forms.open_public', { defaultValue: 'Open' })}
                  </a>
                </div>
              </div>
            )}

            {canMutate && (
              <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.intake_forms.sections.smoke', { defaultValue: 'Smoke test submit' })}
                </h3>
                <p className="mt-1 text-sm text-slate-600">
                  {t('admin.intake_forms.smoke_hint', {
                    defaultValue:
                      'Creates a test Lead draft using the same pipeline as public intake. Verifies no direct Candidate INSERT.',
                  })}
                </p>
                <button
                  type="button"
                  className="btn-primary mt-3 inline-flex items-center gap-2"
                  disabled={smokeRunning || !detail.form.is_active || !publicSlug}
                  onClick={() => void runSmokeTest()}
                >
                  <IconPlayerPlay size={16} />
                  {smokeRunning
                    ? t('common.loading')
                    : t('admin.intake_forms.smoke_run', { defaultValue: 'Send test lead draft' })}
                </button>
                {smokeResult && (
                  <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 text-sm">
                    <p className="font-medium text-emerald-900">{smokeResult.message}</p>
                    <dl className="mt-2 grid gap-1 text-xs text-emerald-950 sm:grid-cols-2">
                      <div>
                        <dt className="text-emerald-700">lead_id</dt>
                        <dd className="font-mono">{smokeResult.lead_id}</dd>
                      </div>
                      <div>
                        <dt className="text-emerald-700">candidate_id</dt>
                        <dd className="font-mono">{smokeResult.candidate_id ?? 'null'}</dd>
                      </div>
                      <div className="sm:col-span-2">
                        <dt className="text-emerald-700">token</dt>
                        <dd className="break-all font-mono">{smokeResult.token}</dd>
                      </div>
                    </dl>
                    {smokeResult.lead_id && (
                      <Link
                        to={`${CRM_APP_PATHS.leads}/${smokeResult.lead_id}`}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
                      >
                        <IconArrowLeft size={14} className="rotate-180" />
                        {t('admin.intake_forms.open_lead', { defaultValue: 'Open lead' })}
                      </Link>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
