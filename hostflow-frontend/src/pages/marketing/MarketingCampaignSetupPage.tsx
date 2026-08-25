/**
 * Create Campaign — business goal + Primary Target (+ optional context).
 * Sources connect later via MarketingConnectSourcePage.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS, marketingCampaignPath } from '../../app/crmAppPaths'
import { listAdditionalServices } from '../../api/additionalServices'
import { listClientAccounts, type ClientAccount } from '../../api/clientAccounts'
import {
  listOwnCompanies,
  ownCompanySettings,
  type OwnCompanyRecord,
} from '../../api/client'
import { createCampaign } from '../../api/platformCampaigns'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import type { AdditionalService } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  FLOW_PRESETS,
  type FlowPreset,
  type MarketingFlowKind,
} from './marketingPresentation'
import { MarketingOptionCard } from './MarketingOptionCard'

const TOTAL_STEPS = 4

export default function MarketingCampaignSetupPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState(1)
  const [name, setName] = useState(() => (searchParams.get('name') || '').trim().slice(0, 160))
  const [description, setDescription] = useState('')
  const [flowKind, setFlowKind] = useState<MarketingFlowKind | ''>(() => {
    const flow = (searchParams.get('flow') || '').trim()
    return FLOW_PRESETS.some((p) => p.kind === flow) ? (flow as MarketingFlowKind) : ''
  })
  const [targetId, setTargetId] = useState(() => {
    const targetType = (searchParams.get('target_type') || '').trim()
    const id = (searchParams.get('target_id') || '').trim()
    return targetType === 'vacancy' && id ? id : ''
  })
  const [contextClientId, setContextClientId] = useState('')
  const [ownCompanyId, setOwnCompanyId] = useState(() => ownCompanySettings.get() || '')
  const prefilledFromSearch =
    Boolean(targetId) && (searchParams.get('target_type') || '').trim() === 'vacancy'

  const [companies, setCompanies] = useState<OwnCompanyRecord[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [services, setServices] = useState<AdditionalService[]>([])
  const [clients, setClients] = useState<ClientAccount[]>([])
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const preset: FlowPreset | null = useMemo(
    () => FLOW_PRESETS.find((p) => p.kind === flowKind) || null,
    [flowKind],
  )

  const loadOptions = useCallback(async () => {
    setOptionsLoading(true)
    setError(null)
    try {
      const [companyRes, vacs, svcs, accounts] = await Promise.all([
        listOwnCompanies().catch(() => ({ items: [] as OwnCompanyRecord[] })),
        listVacancies().catch(() => [] as Vacancy[]),
        listAdditionalServices().catch(() => [] as AdditionalService[]),
        listClientAccounts({ limit: 200 }).catch(() => [] as ClientAccount[]),
      ])
      const companyItems = Array.isArray(companyRes?.items) ? companyRes.items : []
      setCompanies(companyItems)
      if (!ownCompanyId && companyItems.length) {
        const active =
          companyItems.find((c) => c.id === ownCompanySettings.get()) || companyItems[0]
        if (active?.id) setOwnCompanyId(active.id)
      }
      setVacancies(Array.isArray(vacs) ? vacs.filter((v) => !v.is_archived) : [])
      setServices(Array.isArray(svcs) ? svcs : [])
      setClients(Array.isArray(accounts) ? accounts : [])
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.setup.errors.load_options', {
            defaultValue: 'Не удалось загрузить справочники',
          }),
          t,
        ),
      )
    } finally {
      setOptionsLoading(false)
    }
  }, [ownCompanyId, t])

  useEffect(() => {
    void loadOptions()
  }, [loadOptions])

  const stepTitle = useMemo(() => {
    if (step === 1) return 'Название кампании'
    if (step === 2) return 'Тип потока'
    if (step === 3) return 'Клиент и предмет кампании'
    return 'Проверка'
  }, [step])

  const selectedClient = clients.find((c) => c.id === contextClientId)

  const vacanciesForClient = useMemo(() => {
    if (!contextClientId) return [] as Vacancy[]
    const primaryCompanyId = String(selectedClient?.primary_company_id || '').trim()
    if (!primaryCompanyId) return vacancies
    const matched = vacancies.filter((v) => String(v.company_id || '') === primaryCompanyId)
    return matched.length ? matched : vacancies
  }, [contextClientId, selectedClient, vacancies])

  const canNext = useMemo(() => {
    if (step === 1) return name.trim().length >= 2 && Boolean(ownCompanyId)
    if (step === 2) return Boolean(flowKind)
    if (step === 3) return Boolean(targetId && preset && contextClientId)
    return Boolean(
      preset && targetId && ownCompanyId && contextClientId && name.trim().length >= 2,
    )
  }, [step, name, ownCompanyId, flowKind, targetId, preset, contextClientId])

  async function handleCreate() {
    if (!preset || !targetId || !ownCompanyId || !contextClientId) return
    setSubmitting(true)
    setError(null)
    try {
      const targets: Array<{
        target_type: string
        target_id: string
        route_intent: string
        role: string
        sort_order?: number
      }> = [
        {
          target_type: preset.target_type,
          target_id: targetId,
          route_intent: preset.route_intent,
          role: 'primary',
          sort_order: 0,
        },
        {
          target_type: 'client_account',
          target_id: contextClientId,
          // Registry requires an allowed intent for client_account; routing uses Primary only.
          route_intent: 'sales_inquiry',
          role: 'context',
          sort_order: 1,
        },
      ]
      const campaign = await createCampaign({
        name: name.trim(),
        description: description.trim() || undefined,
        goal_type: preset.goal_type,
        primary_kpi: preset.primary_kpi,
        own_company_id: ownCompanyId,
        targets,
      })
      navigate(marketingCampaignPath(campaign.id))
    } catch (err) {
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

  const selectedVacancy = vacancies.find((v) => v.id === targetId)
  const selectedService = services.find((s) => s.id === targetId)
  const selectedCompany = companies.find((c) => c.id === ownCompanyId)

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.marketing.setup.title', { defaultValue: 'Новая кампания' })}
          subtitle={`${step} / ${TOTAL_STEPS} · ${stepTitle}`}
          kind="browse"
          secondaryActions={
            <Link to={CRM_APP_PATHS.marketing} className="btn-secondary btn-sm">
              К списку
            </Link>
          }
        />
      </PageShellHeader>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 pb-8">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void loadOptions()} /> : null}
        {optionsLoading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

        {prefilledFromSearch ? (
          <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
            Вакансия подставлена из Подбора. Дальше задайте цель кампании — источник подключите на
            странице кампании.
          </p>
        ) : null}

        {step === 1 ? (
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">Название</span>
              <input
                className="input w-full"
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, 160))}
                placeholder="Например: Kierowca CE — Poltrakt"
                data-testid="marketing-setup-name"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">Описание (необязательно)</span>
              <textarea
                className="input w-full min-h-[80px]"
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, 2000))}
                placeholder="Бизнес-цель кампании"
                data-testid="marketing-setup-description"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">Компания (владелец)</span>
              <select
                className="input w-full"
                value={ownCompanyId}
                onChange={(e) => setOwnCompanyId(e.target.value)}
                data-testid="marketing-setup-own-company"
              >
                <option value="">Выберите компанию</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.id}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-slate-500">
                Campaign принадлежит tenant и этой компании. Клиент/заказ — только контекст, не
                владелец.
              </span>
            </label>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="grid gap-3" role="radiogroup" aria-label="Тип потока">
            {FLOW_PRESETS.map((p) => (
              <MarketingOptionCard
                key={p.kind}
                selected={flowKind === p.kind}
                onClick={() => {
                  setFlowKind(p.kind)
                  setTargetId((prev) => {
                    const current = FLOW_PRESETS.find((x) => x.kind === flowKind)
                    if (current && current.target_type !== p.target_type) return ''
                    return prev
                  })
                }}
                testId={`marketing-setup-flow-${p.kind}`}
              >
                <span className="font-medium text-slate-900">{p.label}</span>
                <span className="mt-1 block text-slate-600">{p.description}</span>
              </MarketingOptionCard>
            ))}
          </div>
        ) : null}

        {step === 3 && preset ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Кампания обслуживает <span className="font-medium text-slate-800">клиента</span>. Primary
              Target — вакансия или услуга/заказ этого клиента; routing и KPI идут через него.
            </p>

            <div>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-800">Клиент (обязательно)</span>
                <select
                  className="input w-full"
                  value={contextClientId}
                  onChange={(e) => {
                    setContextClientId(e.target.value)
                    setTargetId('')
                  }}
                  data-testid="marketing-setup-context-client"
                >
                  <option value="">Выберите клиента</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {!clients.length ? (
                <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Нет Client Account.{' '}
                  <Link to={CRM_APP_PATHS.clientNew} className="underline">
                    Создать клиента
                  </Link>{' '}
                  в Sales, затем вернитесь сюда.
                </p>
              ) : (
                <p className="mt-1 text-xs text-slate-500">
                  Сохраняется как CampaignTarget(role=context, client_account). Статистика по клиенту —
                  отсюда.{' '}
                  <Link to={CRM_APP_PATHS.clientNew} className="underline">
                    Новый клиент
                  </Link>
                </p>
              )}
            </div>

            {contextClientId ? (
              <div className="border-t border-slate-200 pt-4 space-y-3">
                <p className="text-sm font-medium text-slate-800">
                  Предмет кампании · {preset.destinationLabel}
                </p>
                <p className="text-xs text-slate-500">
                  Primary Target задаёт <code className="text-xs">route_intent</code> для всех
                  источников кампании.
                </p>
                {preset.target_type === 'vacancy' ? (
                  !vacanciesForClient.length ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      Нет вакансий для этого клиента.{' '}
                      <Link to={CRM_APP_PATHS.vacancyNew} className="underline">
                        Создать вакансию
                      </Link>{' '}
                      в Recruitment (Вакансии).
                    </p>
                  ) : (
                    <div className="grid gap-2" role="radiogroup" aria-label="Вакансия">
                      {vacanciesForClient.map((v) => (
                        <MarketingOptionCard
                          key={v.id}
                          selected={targetId === v.id}
                          onClick={() => setTargetId(v.id)}
                          testId={`marketing-setup-vacancy-${v.id}`}
                        >
                          <span className="font-medium text-slate-900">{v.title || v.id}</span>
                          {v.company_name ? (
                            <span className="mt-0.5 block text-xs text-slate-500">{v.company_name}</span>
                          ) : null}
                        </MarketingOptionCard>
                      ))}
                    </div>
                  )
                ) : !services.length ? (
                  <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    Нет услуг.{' '}
                    <Link to={CRM_APP_PATHS.services} className="underline">
                      Открыть услуги
                    </Link>
                  </p>
                ) : (
                  <div className="grid gap-2" role="radiogroup" aria-label="Услуга">
                    {services.map((s) => (
                      <MarketingOptionCard
                        key={s.id}
                        selected={targetId === s.id}
                        onClick={() => setTargetId(s.id)}
                        testId={`marketing-setup-service-${s.id}`}
                      >
                        <span className="font-medium text-slate-900">{s.name || s.id}</span>
                      </MarketingOptionCard>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                Сначала выберите клиента — затем вакансию (hiring) или услугу (B2B).
              </p>
            )}
          </div>
        ) : null}

        {step === 4 && preset ? (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <div>
              <div className="text-xs text-slate-500">Кампания</div>
              <div className="font-medium text-slate-900">{name.trim()}</div>
              {description.trim() ? (
                <div className="mt-1 text-slate-600">{description.trim()}</div>
              ) : null}
            </div>
            <div>
              <div className="text-xs text-slate-500">Компания-владелец</div>
              <div className="font-medium text-slate-900">
                {selectedCompany?.name || ownCompanyId}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Поток</div>
              <div className="font-medium text-slate-900">{preset.label}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Клиент (обслуживаем)</div>
              <div className="font-medium text-slate-900">
                {selectedClient?.display_name || contextClientId}
              </div>
              <div className="text-xs text-slate-500">CampaignTarget · role=context</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Primary Target · route_intent</div>
              <div className="font-medium text-slate-900">
                {preset.target_type === 'vacancy'
                  ? selectedVacancy?.title || targetId
                  : selectedService?.name || targetId}
              </div>
              <div className="text-xs text-slate-500">{preset.route_intent}</div>
            </div>
            <p className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Источник заявок (Meta Lead Form / публичная анкета) подключается на странице кампании —
              отдельно от создания цели.
            </p>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
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
              disabled={!canNext || optionsLoading}
              onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
              data-testid="marketing-setup-next"
            >
              Далее
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!canNext || submitting}
              onClick={() => void handleCreate()}
              data-testid="marketing-setup-create"
            >
              {submitting ? 'Создание…' : 'Создать кампанию'}
            </button>
          )}
        </div>
      </div>
    </PageShell>
  )
}
