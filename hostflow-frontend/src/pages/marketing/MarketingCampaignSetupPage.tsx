/**
 * Marketing Campaign Setup — one finished operator flow (no raw UUIDs / JSON).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CRM_APP_PATHS, marketingCampaignPath } from '../../app/crmAppPaths'
import { listAdditionalServices } from '../../api/additionalServices'
import { listLeadForms, type TenantLeadForm } from '../../api/leadForms'
import {
  attachCampaignForm,
  attachCampaignIntakeSource,
  createCampaign,
  currentFlight,
  launchFlight,
  listIntakeSourceOptions,
  type IntakeSourceOption,
} from '../../api/platformCampaigns'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import type { AdditionalService } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  FLOW_PRESETS,
  formPublicUrl,
  type FlowPreset,
  type MarketingFlowKind,
  type MarketingSourceKind,
} from './marketingPresentation'

const TOTAL_STEPS = 6

function OptionCard({
  selected,
  onClick,
  children,
  disabled,
  testId,
}: {
  selected: boolean
  onClick: () => void
  children: React.ReactNode
  disabled?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      data-testid={testId}
      onClick={onClick}
      className={`w-full rounded-xl border-2 p-4 text-left text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
        selected
          ? 'border-brand-400 bg-brand-50/80 ring-2 ring-brand-200'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {children}
    </button>
  )
}

export default function MarketingCampaignSetupPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [flowKind, setFlowKind] = useState<MarketingFlowKind | ''>('')
  const [formId, setFormId] = useState('')
  const [sourceKind, setSourceKind] = useState<MarketingSourceKind | ''>('')
  const [metaSourceId, setMetaSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [launchNow, setLaunchNow] = useState(true)

  const [forms, setForms] = useState<TenantLeadForm[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [services, setServices] = useState<AdditionalService[]>([])
  const [metaSources, setMetaSources] = useState<IntakeSourceOption[]>([])
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const preset: FlowPreset | null = useMemo(
    () => FLOW_PRESETS.find((p) => p.kind === flowKind) || null,
    [flowKind],
  )

  const loadOptions = useCallback(async () => {
    setOptionsLoading(true)
    try {
      const [formRows, vacRows, svcRows, metaRows] = await Promise.all([
        listLeadForms(),
        listVacancies({ limit: 100 }),
        listAdditionalServices(false),
        listIntakeSourceOptions('meta').catch(() => [] as IntakeSourceOption[]),
      ])
      setForms((formRows || []).filter((f) => f.is_active))
      setVacancies(Array.isArray(vacRows) ? vacRows : [])
      setServices(Array.isArray(svcRows) ? svcRows.filter((s) => s.is_active !== false) : [])
      setMetaSources(Array.isArray(metaRows) ? metaRows : [])
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.setup.errors.options', {
            defaultValue: 'Не удалось загрузить формы и назначения',
          }),
          t,
        ),
      )
    } finally {
      setOptionsLoading(false)
    }
  }, [t])

  useEffect(() => {
    void loadOptions()
  }, [loadOptions])

  const selectedForm = forms.find((f) => f.id === formId) || null
  const selectedVacancy = vacancies.find((v) => v.id === targetId) || null
  const selectedService = services.find((s) => s.id === targetId) || null
  const selectedMeta = metaSources.find((s) => s.id === metaSourceId) || null

  const canNext = (): boolean => {
    if (step === 1) return name.trim().length >= 2
    if (step === 2) return Boolean(flowKind)
    if (step === 3) return Boolean(formId)
    if (step === 4) {
      if (sourceKind === 'public_form') return true
      if (sourceKind === 'meta') return Boolean(metaSourceId)
      return false
    }
    if (step === 5) return Boolean(targetId && preset)
    return true
  }

  async function onSubmit() {
    if (!preset || !formId || !targetId || !sourceKind) return
    setSubmitting(true)
    setError(null)
    try {
      let campaign = await createCampaign({
        name: name.trim(),
        goal_type: preset.goal_type,
        primary_kpi: preset.primary_kpi,
        targets: [
          {
            target_type: preset.target_type,
            target_id: targetId,
            route_intent: preset.route_intent,
            role: 'primary',
          },
        ],
      })
      campaign = await attachCampaignForm(campaign.id, formId, 'primary')
      if (sourceKind === 'meta' && metaSourceId) {
        campaign = await attachCampaignIntakeSource(campaign.id, metaSourceId, 'primary')
      }
      const flight = currentFlight(campaign)
      if (launchNow && flight) {
        const launched = await launchFlight(campaign.id, flight.id)
        campaign = launched.campaign
      }
      navigate(marketingCampaignPath(campaign.id))
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.setup.errors.create', {
            defaultValue: 'Не удалось создать кампанию',
          }),
          t,
        ),
      )
    } finally {
      setSubmitting(false)
    }
  }

  const stepTitle =
    [
      'Название кампании',
      'Тип потока',
      'Форма',
      'Источник',
      'Куда направлять заявки',
      'Проверка и запуск',
    ][step - 1] || 'Создание кампании'

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.marketing.setup.title', { defaultValue: 'Новая кампания' })}
          subtitle={`${step} / ${TOTAL_STEPS} · ${stepTitle}`}
          kind="action"
          secondaryActions={
            <Link to={CRM_APP_PATHS.marketing} className="btn-secondary btn-sm">
              {t('common.actions.cancel', { defaultValue: 'Отмена' })}
            </Link>
          }
        />
      </PageShellHeader>

      <div className="mx-auto w-full max-w-2xl flex-1 space-y-4 overflow-y-auto px-4 pb-8">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void loadOptions()} /> : null}
        {optionsLoading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : null}

        {step === 1 ? (
          <div className="space-y-3">
            <label className="block text-sm font-medium text-slate-800">
              Как назвать кампанию?
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Например: Водители CE — Meta апрель"
                data-testid="marketing-setup-name"
                autoFocus
              />
            </label>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="grid gap-3" role="radiogroup" aria-label="Тип потока">
            {FLOW_PRESETS.map((p) => (
              <OptionCard
                key={p.kind}
                selected={flowKind === p.kind}
                onClick={() => {
                  setFlowKind(p.kind)
                  setTargetId('')
                }}
                testId={`marketing-setup-flow-${p.kind}`}
              >
                <span className="font-medium text-slate-900">{p.label}</span>
                <span className="mt-1 block text-slate-600">{p.description}</span>
              </OptionCard>
            ))}
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Выберите готовую форму из Form Builder. Нет формы?{' '}
              <Link to={CRM_APP_PATHS.settingsLeadForms} className="text-brand-600 underline">
                Открыть формы
              </Link>
            </p>
            {!forms.length ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Активных форм нет. Создайте форму в настройках, затем вернитесь сюда.
              </p>
            ) : (
              <div className="grid gap-2" role="radiogroup" aria-label="Форма">
                {forms.map((f) => (
                  <OptionCard
                    key={f.id}
                    selected={formId === f.id}
                    onClick={() => setFormId(f.id)}
                    testId={`marketing-setup-form-${f.id}`}
                  >
                    <span className="font-medium text-slate-900">{f.title || 'Без названия'}</span>
                    {f.public_slug ? (
                      <span className="mt-1 block text-xs text-slate-500">Публичная ссылка готова</span>
                    ) : (
                      <span className="mt-1 block text-xs text-amber-700">Нет public slug — ссылка появится после публикации</span>
                    )}
                  </OptionCard>
                ))}
              </div>
            )}
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-3">
            <div className="grid gap-3" role="radiogroup" aria-label="Источник">
              <OptionCard
                selected={sourceKind === 'public_form'}
                onClick={() => {
                  setSourceKind('public_form')
                  setMetaSourceId('')
                }}
                testId="marketing-setup-source-public"
              >
                <span className="font-medium text-slate-900">Публичная ссылка</span>
                <span className="mt-1 block text-slate-600">
                  Заявки приходят через публичную форму HostFlow.
                </span>
              </OptionCard>
              <OptionCard
                selected={sourceKind === 'meta'}
                onClick={() => setSourceKind('meta')}
                disabled={!metaSources.length}
                testId="marketing-setup-source-meta"
              >
                <span className="font-medium text-slate-900">Meta</span>
                <span className="mt-1 block text-slate-600">
                  {metaSources.length
                    ? 'Привязать существующий источник Meta.'
                    : 'Нет активных Meta-источников в компании — настройте интеграцию Meta.'}
                </span>
              </OptionCard>
            </div>
            {sourceKind === 'meta' && metaSources.length ? (
              <div className="grid gap-2" role="radiogroup" aria-label="Meta источник">
                {metaSources.map((s) => (
                  <OptionCard
                    key={s.id}
                    selected={metaSourceId === s.id}
                    onClick={() => setMetaSourceId(s.id)}
                    testId={`marketing-setup-meta-${s.id}`}
                  >
                    <span className="font-medium text-slate-900">{s.name}</span>
                    <span className="mt-1 block text-xs text-slate-500">{s.code || s.provider}</span>
                  </OptionCard>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {step === 5 && preset ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">Выберите {preset.destinationLabel.toLowerCase()}.</p>
            {preset.target_type === 'vacancy' ? (
              !vacancies.length ? (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Нет вакансий.{' '}
                  <Link to={CRM_APP_PATHS.vacancyNew} className="underline">
                    Создать вакансию
                  </Link>
                </p>
              ) : (
                <div className="grid max-h-80 gap-2 overflow-y-auto" role="radiogroup">
                  {vacancies.map((v) => (
                    <OptionCard
                      key={v.id}
                      selected={targetId === v.id}
                      onClick={() => setTargetId(v.id)}
                      testId={`marketing-setup-vacancy-${v.id}`}
                    >
                      <span className="font-medium text-slate-900">{v.title}</span>
                      {v.company_name ? (
                        <span className="mt-1 block text-xs text-slate-500">{v.company_name}</span>
                      ) : null}
                    </OptionCard>
                  ))}
                </div>
              )
            ) : !services.length ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Нет услуг в каталоге.{' '}
                <Link to={CRM_APP_PATHS.services} className="underline">
                  Открыть услуги
                </Link>
              </p>
            ) : (
              <div className="grid max-h-80 gap-2 overflow-y-auto" role="radiogroup">
                {services.map((s) => (
                  <OptionCard
                    key={s.id}
                    selected={targetId === s.id}
                    onClick={() => setTargetId(s.id)}
                    testId={`marketing-setup-service-${s.id}`}
                  >
                    <span className="font-medium text-slate-900">{s.name}</span>
                    {s.code ? <span className="mt-1 block text-xs text-slate-500">{s.code}</span> : null}
                  </OptionCard>
                ))}
              </div>
            )}
          </div>
        ) : null}

        {step === 6 && preset ? (
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <dl className="grid gap-2">
              <div>
                <dt className="text-xs text-slate-500">Кампания</dt>
                <dd className="font-medium text-slate-900">{name.trim()}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Поток</dt>
                <dd className="font-medium text-slate-900">{preset.label}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Форма</dt>
                <dd className="font-medium text-slate-900">{selectedForm?.title || '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Источник</dt>
                <dd className="font-medium text-slate-900">
                  {sourceKind === 'public_form'
                    ? 'Публичная ссылка'
                    : selectedMeta?.name || 'Meta'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Куда</dt>
                <dd className="font-medium text-slate-900">
                  {preset.target_type === 'vacancy'
                    ? selectedVacancy?.title || '—'
                    : selectedService?.name || '—'}
                </dd>
              </div>
              {sourceKind === 'public_form' && selectedForm?.public_slug ? (
                <div>
                  <dt className="text-xs text-slate-500">Ссылка для теста</dt>
                  <dd className="break-all font-mono text-xs text-slate-700">
                    {formPublicUrl(selectedForm.public_slug)}
                  </dd>
                </div>
              ) : null}
            </dl>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={launchNow}
                onChange={(e) => setLaunchNow(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300"
              />
              <span className="font-medium text-slate-800">Запустить Flight сразу после создания</span>
            </label>
          </div>
        ) : null}

        <div className="flex flex-wrap justify-between gap-3 pt-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={step === 1 || submitting}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
          >
            Назад
          </button>
          {step < TOTAL_STEPS ? (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!canNext() || optionsLoading}
              onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
              data-testid="marketing-setup-next"
            >
              Далее
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!canNext() || submitting}
              onClick={() => void onSubmit()}
              data-testid="marketing-setup-submit"
            >
              {submitting
                ? t('common.loading')
                : launchNow
                  ? 'Создать и запустить'
                  : 'Создать кампанию'}
            </button>
          )}
        </div>
      </div>
    </PageShell>
  )
}
