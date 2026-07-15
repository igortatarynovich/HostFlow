import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { IconForms, IconPlayerPlay } from '@tabler/icons-react'
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
import { QuestionnaireCard } from '../../components/admin/QuestionnaireCard'
import IntakeFormAnswersRoutingCard from '../../components/admin/IntakeFormAnswersRoutingCard'
import { IntakeFormMappingEditor } from '../../components/admin/IntakeFormMappingEditor'
import { capabilityForProfileCode } from '../../utils/intakeCapabilities'
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

type ViewMode = 'card' | 'edit'

export default function IntakeFormDetailPage() {
  const { formId = '' } = useParams<{ formId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { t } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const canMutate = role === 'administrator'

  const initialMode: ViewMode = searchParams.get('mode') === 'edit' ? 'edit' : 'card'
  const [viewMode, setViewMode] = useState<ViewMode>(initialMode)
  const [detail, setDetail] = useState<IntakeFormDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [smokeRunning, setSmokeRunning] = useState(false)
  const [smokeResult, setSmokeResult] = useState<IntakeFormSmokeTestResult | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editSlug, setEditSlug] = useState('')
  const [editActive, setEditActive] = useState(true)
  const [entityProfileCode, setEntityProfileCode] = useState('')
  const [presentationFields, setPresentationFields] = useState<PresentationFieldInput[]>([])
  const [presentationDraft, setPresentationDraft] = useState<PresentationFieldDraft[]>([])
  const [metaSaving, setMetaSaving] = useState(false)
  const [presentationSaving, setPresentationSaving] = useState(false)

  const justCreated = searchParams.get('created') === '1'

  const load = useCallback(async () => {
    if (!formId) return
    setPageError(null)
    try {
      setLoading(true)
      const payload = await getIntakeFormDetail(formId)
      setDetail(payload)
      setEditTitle(payload.form.title || '')
      setEditSlug(payload.form.public_slug || '')
      setEditActive(Boolean(payload.form.is_active))
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

  useEffect(() => {
    if (!justCreated) return
    const next = new URLSearchParams(searchParams)
    next.delete('created')
    setSearchParams(next, { replace: true })
  }, [justCreated, searchParams, setSearchParams])

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

  const openEditMode = () => {
    setViewMode('edit')
    const next = new URLSearchParams(searchParams)
    next.set('mode', 'edit')
    setSearchParams(next, { replace: true })
  }

  const backToCard = () => {
    setViewMode('card')
    const next = new URLSearchParams(searchParams)
    next.delete('mode')
    setSearchParams(next, { replace: true })
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
        is_active: editActive,
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
      backToCard()
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

  const publicSlug = detail?.form.public_slug?.trim() || ''
  const publicUrl = publicSlug ? publicIntakeUrlForSlug(publicSlug) : ''

  const capability = useMemo(
    () => (detail ? capabilityForProfileCode(detail.entity_profile.code) : undefined),
    [detail],
  )

  const capabilityLabel = capability
    ? t(capability.defaultTitleKey, { defaultValue: capability.defaultTitleFallback })
    : detail?.entity_profile.name

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.intake_forms.back_list', { defaultValue: 'Все анкеты' })}
      backHref={CRM_APP_PATHS.settingsLeadForms}
      kicker={t('admin.intake_forms.header_kicker', { defaultValue: 'Intake sources' })}
      title={
        <span className="inline-flex items-center gap-2">
          <IconForms size={22} stroke={1.9} className="text-brand-600" />
          {detail?.form.title || t('admin.intake_forms.detail_title', { defaultValue: 'Intake form' })}
        </span>
      }
      subtitle={
        viewMode === 'card'
          ? t('admin.questionnaire_card.subtitle', {
              defaultValue: 'Отправьте анкету клиенту или скопируйте публичную ссылку.',
            })
          : t('admin.questionnaire.edit_subtitle', { defaultValue: 'Измените вопросы и сохраните.' })
      }
    >
      <section className="settings-panel">
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

        {justCreated && !loading && detail ? (
          <p className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50/80 px-3 py-2 text-sm text-emerald-900">
            {t('admin.questionnaire.created_banner', {
              defaultValue: 'Анкета готова. Выберите действие ниже — отправить клиенту или скопировать ссылку.',
            })}
          </p>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : !detail ? null : viewMode === 'card' ? (
          <div className="space-y-6">
            <QuestionnaireCard
              title={detail.form.title || ''}
              capabilityLabel={capabilityLabel}
              isActive={Boolean(detail.form.is_active)}
              publicUrl={publicUrl}
              entityProfileCode={detail.entity_profile.code}
              onCopyLink={() => void copyText(publicUrl)}
              onEditQuestions={openEditMode}
            />

            <details className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.lead_forms.advanced_settings', { defaultValue: 'Расширенные настройки' })}
              </summary>
              <div className="mt-4 space-y-6">
                <IntakeFormAnswersRoutingCard
                  definition={detail.form_definition}
                  entityProfileCode={detail.entity_profile.code}
                  entityProfileName={detail.entity_profile.name}
                />

                {canMutate ? (
                  <div className="rounded-xl border border-slate-100 bg-white p-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.intake_forms.sections.form_edit', { defaultValue: 'Form metadata' })}
                    </h3>
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
                      <label className="flex items-center gap-2 text-sm sm:col-span-2">
                        <input
                          type="checkbox"
                          className="rounded border-slate-300"
                          checked={editActive}
                          onChange={(event) => setEditActive(event.target.checked)}
                        />
                        <span className="text-slate-700">
                          {t('admin.lead_forms.fields.active', { defaultValue: 'Active (available in Sales picker)' })}
                        </span>
                      </label>
                      <div className="sm:col-span-2">
                        <button type="button" className="btn-secondary" disabled={metaSaving} onClick={() => void saveMetadata()}>
                          {metaSaving ? t('common.loading') : t('admin.intake_forms.save_metadata', { defaultValue: 'Save metadata' })}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : null}

                {canMutate && (
                  <div className="rounded-xl border border-slate-100 bg-white p-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.intake_forms.sections.smoke', { defaultValue: 'Smoke test submit' })}
                    </h3>
                    <button
                      type="button"
                      className="btn-secondary mt-3 inline-flex items-center gap-2"
                      disabled={smokeRunning || !detail.form.is_active || !publicSlug}
                      onClick={() => void runSmokeTest()}
                    >
                      <IconPlayerPlay size={16} />
                      {smokeRunning
                        ? t('common.loading')
                        : t('admin.intake_forms.smoke_run', { defaultValue: 'Send test lead draft' })}
                    </button>
                    {smokeResult?.lead_id ? (
                      <Link
                        to={`${CRM_APP_PATHS.leads}/${smokeResult.lead_id}`}
                        className="mt-2 block text-xs font-medium text-brand-700 hover:underline"
                      >
                        {t('admin.intake_forms.open_lead', { defaultValue: 'Open lead' })}
                      </Link>
                    ) : null}
                  </div>
                )}

                {canMutate && (
                  <div className="rounded-xl border border-brand-100 bg-white p-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {t('admin.intake_forms.sections.mapping_edit', { defaultValue: 'Provider field mapping (P9)' })}
                    </h3>
                    <div className="mt-4">
                      <IntakeFormMappingEditor formId={formId} entityProfileCode={entityProfileCode} />
                    </div>
                  </div>
                )}
              </div>
            </details>
          </div>
        ) : (
          <div className="space-y-6">
            <button type="button" className="btn-secondary btn-sm" onClick={backToCard}>
              {t('admin.questionnaire.back_to_card', { defaultValue: '← К карточке анкеты' })}
            </button>

            {canMutate && (
              <div className="rounded-xl border border-brand-100 bg-white p-4 shadow-sm">
                <IntakeFormPresentationEditor
                  entityProfileCode={entityProfileCode}
                  initialFields={presentationDraft}
                  onEntityProfileChange={setEntityProfileCode}
                  onChange={setPresentationFields}
                  wizardMode
                />
                <div className="mt-4 flex flex-wrap gap-2">
                  <SavePresentationButton saving={presentationSaving} onClick={() => void savePresentation()} />
                  <button type="button" className="btn-secondary" onClick={backToCard}>
                    {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </SettingsSubpageHeader>
  )
}
