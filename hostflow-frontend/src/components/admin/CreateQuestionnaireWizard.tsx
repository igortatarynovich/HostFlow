import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IconArrowLeft, IconEye } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { settingsLeadFormDetailPath } from '../../app/crmAppPaths'
import { createIntakeForm, listIntakeFormEntityProfiles, type PresentationFieldInput } from '../../api/intakeForms'
import { IntakeFormPresentationEditor } from './IntakeFormPresentationEditor'
import {
  defaultSlugForCapability,
  filterAvailableCapabilities,
  type IntakeCapability,
} from '../../utils/intakeCapabilities'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type WizardStep = 'pick' | 'edit' | 'preview'

type Props = {
  onCancel: () => void
}

export function CreateQuestionnaireWizard({ onCancel }: Props) {
  const { t } = useI18n()
  const { notify } = useToast()
  const navigate = useNavigate()

  const [step, setStep] = useState<WizardStep>('pick')
  const [capabilities, setCapabilities] = useState<IntakeCapability[]>([])
  const [loadingCapabilities, setLoadingCapabilities] = useState(true)
  const [selected, setSelected] = useState<IntakeCapability | null>(null)
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [fields, setFields] = useState<PresentationFieldInput[]>([])
  const [creating, setCreating] = useState(false)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    void listIntakeFormEntityProfiles()
      .then((items) => {
        const codes = items.map((item) => item.code)
        setCapabilities(filterAvailableCapabilities(codes))
      })
      .catch(() => setCapabilities([]))
      .finally(() => setLoadingCapabilities(false))
  }, [])

  const capabilityLabel = useCallback(
    (capability: IntakeCapability) =>
      t(capability.defaultTitleKey, { defaultValue: capability.defaultTitleFallback }),
    [t],
  )

  const capabilityDescription = useCallback(
    (capability: IntakeCapability) =>
      t(capability.descriptionKey, { defaultValue: capability.descriptionFallback }),
    [t],
  )

  const pickCapability = (capability: IntakeCapability) => {
    setSelected(capability)
    setTitle(capabilityLabel(capability))
    setSlug(defaultSlugForCapability(capability))
    setFields([])
    setStep('edit')
    setPageError(null)
  }

  const previewFields = useMemo(
    () => [...fields].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [fields],
  )

  const handleSave = async () => {
    if (!selected) return
    if (fields.length < 1) {
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
        title: title.trim() || capabilityLabel(selected),
        public_slug: slug.trim(),
        entity_profile_code: selected.entityProfileCode,
        fields,
        is_active: true,
      })
      notify({
        title: t('admin.questionnaire.toast.created', { defaultValue: 'Анкета создана и готова к отправке' }),
        variant: 'success',
      })
      navigate(`${settingsLeadFormDetailPath(created.form.id)}?created=1`)
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

  if (step === 'pick') {
    return (
      <div className="space-y-4 rounded-xl border border-brand-100 bg-white p-4 shadow-sm" data-testid="create-questionnaire-wizard">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('admin.questionnaire.pick_direction', { defaultValue: 'Выберите направление' })}
          </h3>
          <button type="button" className="btn-secondary btn-sm" onClick={onCancel}>
            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
          </button>
        </div>

        {pageError ? (
          <ErrorRecoveryBanner
            info={pageError}
            {...friendlyErrorBannerSecondary(pageError, CRM_APP_PATHS.settingsBilling, t('admin.settings.cards.billing.label'))}
          />
        ) : null}

        {loadingCapabilities ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : capabilities.length === 0 ? (
          <p className="text-sm text-amber-800">
            {t('admin.questionnaire.no_capabilities', {
              defaultValue: 'Направления пока недоступны. Обратитесь в поддержку или попробуйте позже.',
            })}
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {capabilities.map((capability) => (
              <button
                key={capability.id}
                type="button"
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-left transition hover:border-brand-300 hover:bg-brand-50/40"
                onClick={() => pickCapability(capability)}
              >
                <p className="font-semibold text-slate-900">{capabilityLabel(capability)}</p>
                <p className="mt-1 text-sm text-slate-600">{capabilityDescription(capability)}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-xl border border-brand-100 bg-white p-4 shadow-sm" data-testid="create-questionnaire-wizard">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50"
            onClick={() => {
              if (step === 'preview') {
                setStep('edit')
                return
              }
              setStep('pick')
              setSelected(null)
            }}
          >
            <IconArrowLeft size={16} />
          </button>
          <h3 className="text-sm font-semibold text-slate-900">
            {selected ? capabilityLabel(selected) : t('admin.questionnaire.create_title', { defaultValue: 'Создание анкеты' })}
          </h3>
        </div>
        <button type="button" className="btn-secondary btn-sm" onClick={onCancel}>
          {t('common.actions.cancel', { defaultValue: 'Cancel' })}
        </button>
      </div>

      {pageError ? (
        <ErrorRecoveryBanner
          info={pageError}
          {...friendlyErrorBannerSecondary(pageError, CRM_APP_PATHS.settingsBilling, t('admin.settings.cards.billing.label'))}
        />
      ) : null}

      {step === 'edit' ? (
        <>
          <p className="text-sm text-slate-600">
            {t('admin.questionnaire.reassurance', {
              defaultValue:
                'Ответы попадут в обращения Sales. Если отправите с заявки — прикрепятся к ней.',
            })}
          </p>

          <label className="block text-sm">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('admin.questionnaire.fields.title', { defaultValue: 'Название анкеты' })}
            </span>
            <input
              className="input mt-1 w-full"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          {selected ? (
            <IntakeFormPresentationEditor
              entityProfileCode={selected.entityProfileCode}
              onChange={setFields}
              wizardMode
              autoLoadPreset
              selectedQuestionsOnly
            />
          ) : null}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex items-center gap-2"
              disabled={fields.length === 0}
              onClick={() => setStep('preview')}
            >
              <IconEye size={16} />
              {t('admin.questionnaire.preview', { defaultValue: 'Предпросмотр' })}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={creating || fields.length === 0}
              onClick={() => void handleSave()}
            >
              {creating
                ? t('common.saving', { defaultValue: 'Saving…' })
                : t('admin.questionnaire.save', { defaultValue: 'Сохранить' })}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-slate-900">
            {t('admin.questionnaire.preview_title', { defaultValue: 'Так клиент увидит вопросы' })}
          </p>
          <ol className="space-y-2 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
            {previewFields.map((field, index) => (
              <li key={field.qualified_code} className="text-sm text-slate-800">
                <span className="font-medium text-slate-500">{index + 1}. </span>
                {field.label_override || field.qualified_code.split('.').slice(-1)[0]}
                {field.intake_level === 'required' ? (
                  <span className="ml-1 text-rose-600">*</span>
                ) : null}
              </li>
            ))}
          </ol>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => setStep('edit')}>
              {t('admin.questionnaire.back_to_edit', { defaultValue: 'Вернуться к редактированию' })}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={creating || fields.length === 0}
              onClick={() => void handleSave()}
            >
              {creating
                ? t('common.saving', { defaultValue: 'Saving…' })
                : t('admin.questionnaire.save', { defaultValue: 'Сохранить' })}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
