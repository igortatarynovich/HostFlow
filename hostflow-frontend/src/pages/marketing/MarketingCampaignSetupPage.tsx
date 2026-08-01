/**
 * Create Campaign — Client (Company) → subject type → primary target.
 * Sources connect later via MarketingConnectSourcePage.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS, marketingCampaignPath } from '../../app/crmAppPaths'
import { listAdditionalServices, listServiceOrders } from '../../api/additionalServices'
import { listClientAccounts, type ClientAccount } from '../../api/clientAccounts'
import {
  listCompanies,
  listOwnCompanies,
  ownCompanySettings,
  type OwnCompanyRecord,
} from '../../api/client'
import { createCampaign } from '../../api/platformCampaigns'
import { listVacancies, type Vacancy } from '../../api/vacancies'
import type { AdditionalService, AdditionalServiceOrder, Company } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  SUBJECT_PRESETS,
  subjectKindFromFlowParam,
  type MarketingSubjectKind,
  type SubjectPreset,
} from './marketingPresentation'
import { MarketingOptionCard } from './MarketingOptionCard'

const TOTAL_STEPS = 4

function asCompanyList(data: unknown): Company[] {
  if (Array.isArray(data)) return data as Company[]
  if (data && typeof data === 'object' && Array.isArray((data as { items?: unknown }).items)) {
    return (data as { items: Company[] }).items
  }
  return []
}

function orderLabel(order: AdditionalServiceOrder): string {
  const notes = String(order.notes || '').trim()
  const status = String(order.status || '').trim()
  const short = String(order.id || '').slice(0, 8)
  if (notes) return `${notes.slice(0, 80)}${notes.length > 80 ? '…' : ''}`
  return `Заказ ${short}${status ? ` · ${status}` : ''}`
}

export default function MarketingCampaignSetupPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [step, setStep] = useState(1)
  const [name, setName] = useState(() => (searchParams.get('name') || '').trim().slice(0, 160))
  const [description, setDescription] = useState('')
  const [subjectKind, setSubjectKind] = useState<MarketingSubjectKind | ''>(() =>
    subjectKindFromFlowParam(searchParams.get('flow') || ''),
  )
  const [targetId, setTargetId] = useState(() => {
    const targetType = (searchParams.get('target_type') || '').trim()
    const id = (searchParams.get('target_id') || '').trim()
    return targetType === 'vacancy' && id ? id : ''
  })
  const [clientCompanyId, setClientCompanyId] = useState('')
  const [ownCompanyId, setOwnCompanyId] = useState(() => ownCompanySettings.get() || '')
  const prefilledFromSearch =
    Boolean(targetId) && (searchParams.get('target_type') || '').trim() === 'vacancy'

  const [ownCompanies, setOwnCompanies] = useState<OwnCompanyRecord[]>([])
  const [clientCompanies, setClientCompanies] = useState<Company[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [services, setServices] = useState<AdditionalService[]>([])
  const [orders, setOrders] = useState<AdditionalServiceOrder[]>([])
  const [clientAccounts, setClientAccounts] = useState<ClientAccount[]>([])
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const preset: SubjectPreset | null = useMemo(
    () => SUBJECT_PRESETS.find((p) => p.kind === subjectKind) || null,
    [subjectKind],
  )

  const loadOptions = useCallback(async () => {
    setOptionsLoading(true)
    setError(null)
    try {
      const [ownRes, companiesRaw, vacs, svcs, ords, accounts] = await Promise.all([
        listOwnCompanies().catch(() => ({ items: [] as OwnCompanyRecord[] })),
        listCompanies({ limit: 500 }).catch(() => [] as Company[]),
        listVacancies().catch(() => [] as Vacancy[]),
        listAdditionalServices().catch(() => [] as AdditionalService[]),
        listServiceOrders({}).catch(() => [] as AdditionalServiceOrder[]),
        listClientAccounts({ limit: 200 }).catch(() => [] as ClientAccount[]),
      ])
      const ownItems = Array.isArray(ownRes?.items) ? ownRes.items : []
      setOwnCompanies(ownItems)
      if (!ownCompanyId && ownItems.length) {
        const active =
          ownItems.find((c) => c.id === ownCompanySettings.get()) || ownItems[0]
        if (active?.id) setOwnCompanyId(active.id)
      }
      setClientCompanies(
        asCompanyList(companiesRaw).filter((c) => !c.is_archived),
      )
      setVacancies(Array.isArray(vacs) ? vacs.filter((v) => !v.is_archived) : [])
      setServices(Array.isArray(svcs) ? svcs.filter((s) => s.is_active !== false) : [])
      setOrders(Array.isArray(ords) ? ords : [])
      setClientAccounts(Array.isArray(accounts) ? accounts : [])
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
    if (step === 2) return 'Клиент'
    if (step === 3) return 'Тип и предмет кампании'
    return 'Проверка'
  }, [step])

  const selectedClient = clientCompanies.find((c) => c.id === clientCompanyId)

  const linkedClientAccountId = useMemo(() => {
    if (!clientCompanyId) return ''
    const byPrimary = clientAccounts.find((a) => {
      if (String(a.primary_company_id || '') !== clientCompanyId) return false
      const oc = String(a.own_company_id || '').trim()
      return !oc || oc === ownCompanyId
    })
    return byPrimary?.id || ''
  }, [clientCompanyId, clientAccounts, ownCompanyId])

  const vacanciesForClient = useMemo(() => {
    if (!clientCompanyId) return [] as Vacancy[]
    return vacancies.filter((v) => String(v.company_id || '') === clientCompanyId)
  }, [clientCompanyId, vacancies])

  const canNext = useMemo(() => {
    if (step === 1) return name.trim().length >= 2 && Boolean(ownCompanyId)
    if (step === 2) return Boolean(clientCompanyId)
    if (step === 3) return Boolean(targetId && preset)
    return Boolean(
      preset && targetId && ownCompanyId && clientCompanyId && name.trim().length >= 2,
    )
  }, [step, name, ownCompanyId, clientCompanyId, targetId, preset])

  async function handleCreate() {
    if (!preset || !targetId || !ownCompanyId || !clientCompanyId) return
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
      ]
      // Optional Sales context when Client Account exists for this Company.
      if (linkedClientAccountId) {
        targets.push({
          target_type: 'client_account',
          target_id: linkedClientAccountId,
          route_intent: 'sales_inquiry',
          role: 'context',
          sort_order: 1,
        })
      }
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
  const selectedOrder = orders.find((o) => o.id === targetId)
  const selectedOwnCompany = ownCompanies.find((c) => c.id === ownCompanyId)

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
            Вакансия подставлена из Подбора. Дальше задайте клиента и тип предмета — источник
            подключите на странице кампании.
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
                {ownCompanies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.id}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-slate-500">
                Владелец кампании (ваша юрлицо). Клиент выбирается на следующем шаге.
              </span>
            </label>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              Кого обслуживает кампания — клиент из справочника «Клиенты» (Company).
            </p>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">Клиент (обязательно)</span>
              <select
                className="input w-full"
                value={clientCompanyId}
                onChange={(e) => {
                  setClientCompanyId(e.target.value)
                  setTargetId('')
                }}
                data-testid="marketing-setup-client-company"
              >
                <option value="">Выберите клиента</option>
                {clientCompanies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.id}
                  </option>
                ))}
              </select>
            </label>
            {!clientCompanies.length ? (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Нет клиентов.{' '}
                <Link to={CRM_APP_PATHS.clientNew} className="underline">
                  Создать клиента
                </Link>
              </p>
            ) : (
              <p className="text-xs text-slate-500">
                Для вакансий список будет только этого клиента. Заказы и услуги — полный каталог
                (не привязаны к клиенту в архитектуре).{' '}
                <Link to={CRM_APP_PATHS.clientNew} className="underline">
                  Новый клиент
                </Link>
              </p>
            )}
          </div>
        ) : null}

        {step === 3 && clientCompanyId ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Клиент: <span className="font-medium text-slate-800">{selectedClient?.name}</span>.
              Выберите тип предмета — списки не смешиваются.
            </p>

            <div className="grid gap-2" role="radiogroup" aria-label="Тип предмета">
              {SUBJECT_PRESETS.map((p) => (
                <MarketingOptionCard
                  key={p.kind}
                  selected={subjectKind === p.kind}
                  onClick={() => {
                    setSubjectKind(p.kind)
                    setTargetId('')
                  }}
                  testId={`marketing-setup-subject-${p.kind}`}
                >
                  <span className="font-medium text-slate-900">{p.label}</span>
                  <span className="mt-1 block text-slate-600">{p.description}</span>
                </MarketingOptionCard>
              ))}
            </div>

            {preset ? (
              <div className="border-t border-slate-200 pt-4 space-y-3">
                <p className="text-sm font-medium text-slate-800">
                  {preset.destinationLabel}
                  {preset.scopedToClient ? ' · только этого клиента' : ' · весь каталог'}
                </p>
                {preset.kind === 'vacancy' ? (
                  !vacanciesForClient.length ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      Нет вакансий у этого клиента.{' '}
                      <Link to={CRM_APP_PATHS.vacancyNew} className="underline">
                        Создать вакансию
                      </Link>{' '}
                      в Recruitment.
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
                ) : null}

                {preset.kind === 'service_order' ? (
                  !orders.length ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      Нет заказов.{' '}
                      <Link to={CRM_APP_PATHS.services} className="underline">
                        Открыть услуги / заказы
                      </Link>
                    </p>
                  ) : (
                    <div className="grid gap-2" role="radiogroup" aria-label="Заказ">
                      {orders.map((o) => (
                        <MarketingOptionCard
                          key={o.id}
                          selected={targetId === o.id}
                          onClick={() => setTargetId(o.id)}
                          testId={`marketing-setup-order-${o.id}`}
                        >
                          <span className="font-medium text-slate-900">{orderLabel(o)}</span>
                          <span className="mt-0.5 block text-xs text-slate-500">
                            {[o.status, o.company_id ? `client ${String(o.company_id).slice(0, 8)}` : null]
                              .filter(Boolean)
                              .join(' · ')}
                          </span>
                        </MarketingOptionCard>
                      ))}
                    </div>
                  )
                ) : null}

                {preset.kind === 'service' ? (
                  !services.length ? (
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
                          {s.code ? (
                            <span className="mt-0.5 block text-xs text-slate-500">{s.code}</span>
                          ) : null}
                        </MarketingOptionCard>
                      ))}
                    </div>
                  )
                ) : null}
              </div>
            ) : (
              <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                Выберите тип: вакансия, заказ или услуга.
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
                {selectedOwnCompany?.name || ownCompanyId}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Клиент</div>
              <div className="font-medium text-slate-900">
                {selectedClient?.name || clientCompanyId}
              </div>
              {linkedClientAccountId ? (
                <div className="text-xs text-slate-500">
                  + Client Account context · {linkedClientAccountId.slice(0, 8)}…
                </div>
              ) : (
                <div className="text-xs text-slate-500">
                  Client Account не найден — контекст не пишется; Primary Target достаточен.
                </div>
              )}
            </div>
            <div>
              <div className="text-xs text-slate-500">Тип · Primary Target</div>
              <div className="font-medium text-slate-900">
                {preset.label}
                {' · '}
                {preset.kind === 'vacancy'
                  ? selectedVacancy?.title || targetId
                  : preset.kind === 'service_order'
                    ? selectedOrder
                      ? orderLabel(selectedOrder)
                      : targetId
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
