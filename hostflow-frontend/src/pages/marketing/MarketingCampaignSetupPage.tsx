/**
 * Create Campaign — business goal + Primary Target (+ optional context).
 * Sources connect later via MarketingConnectSourcePage.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS, marketingCampaignPath } from '../../app/crmAppPaths'
import { listAdditionalServices } from '../../api/additionalServices'
import { ensureClientAccountsFromCompanies, listClientAccounts, type ClientAccount } from '../../api/clientAccounts'
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
        ensureClientAccountsFromCompanies().catch(() => listClientAccounts({ limit: 200 })),
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
            defaultValue: 'Failed to load directories',
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
    if (step === 1)
      return t('app.marketing.setup.steps.name', { defaultValue: 'Campaign name' })
    if (step === 2)
      return t('app.marketing.setup.steps.flow', { defaultValue: 'Flow type' })
    if (step === 3)
      return t('app.marketing.setup.steps.client_subject', {
        defaultValue: 'Client and campaign subject',
      })
    return t('app.marketing.setup.steps.review', { defaultValue: 'Review' })
  }, [step, t])

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
            defaultValue: 'Failed to create campaign',
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
          title={t('app.marketing.setup.title', { defaultValue: 'New campaign' })}
          subtitle={`${step} / ${TOTAL_STEPS} · ${stepTitle}`}
          kind="browse"
          secondaryActions={
            <Link to={CRM_APP_PATHS.marketing} className="btn-secondary btn-sm">
              {t('app.marketing.setup.back_to_list', { defaultValue: 'Back to list' })}
            </Link>
          }
        />
      </PageShellHeader>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 pb-8">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void loadOptions()} /> : null}
        {optionsLoading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

        {prefilledFromSearch ? (
          <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
            {t('app.marketing.setup.prefilled_vacancy', {
              defaultValue:
                'Vacancy was prefilled from Recruitment. Set the campaign goal next — connect a source on the campaign page.',
            })}
          </p>
        ) : null}

        {step === 1 ? (
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">
                {t('app.marketing.setup.fields.name', { defaultValue: 'Name' })}
              </span>
              <input
                className="input w-full"
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, 160))}
                placeholder={t('app.marketing.setup.placeholders.name', {
                  defaultValue: 'e.g. Kierowca CE — Poltrakt',
                })}
                data-testid="marketing-setup-name"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">
                {t('app.marketing.setup.fields.description_optional', {
                  defaultValue: 'Description (optional)',
                })}
              </span>
              <textarea
                className="input w-full min-h-[80px]"
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, 2000))}
                placeholder={t('app.marketing.setup.placeholders.description', {
                  defaultValue: 'Campaign business goal',
                })}
                data-testid="marketing-setup-description"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-800">
                {t('app.marketing.setup.fields.company_owner', {
                  defaultValue: 'Company (owner)',
                })}
              </span>
              <select
                className="input w-full"
                value={ownCompanyId}
                onChange={(e) => setOwnCompanyId(e.target.value)}
                data-testid="marketing-setup-own-company"
              >
                <option value="">
                  {t('app.marketing.setup.select_company', { defaultValue: 'Select a company' })}
                </option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name || c.id}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-slate-500">
                {t('app.marketing.setup.company_owner_hint', {
                  defaultValue:
                    'The campaign belongs to the tenant and this company. Client/order is context only, not the owner.',
                })}
              </span>
            </label>
          </div>
        ) : null}

        {step === 2 ? (
          <div
            className="grid gap-3"
            role="radiogroup"
            aria-label={t('app.marketing.setup.aria.flow_type', { defaultValue: 'Flow type' })}
          >
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
                <span className="font-medium text-slate-900">
                  {t(p.labelKey, { defaultValue: p.label })}
                </span>
                <span className="mt-1 block text-slate-600">
                  {t(p.descriptionKey, { defaultValue: p.description })}
                </span>
              </MarketingOptionCard>
            ))}
          </div>
        ) : null}

        {step === 3 && preset ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              {t('app.marketing.setup.client_intro', {
                defaultValue:
                  'The campaign serves a client. Primary Target is a vacancy or service/order for that client; routing and KPI go through it.',
              })}
            </p>

            <div>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-800">
                  {t('app.marketing.setup.fields.client_required', {
                    defaultValue: 'Client (required)',
                  })}
                </span>
                <select
                  className="input w-full"
                  value={contextClientId}
                  onChange={(e) => {
                    setContextClientId(e.target.value)
                    setTargetId('')
                  }}
                  data-testid="marketing-setup-context-client"
                >
                  <option value="">
                    {t('app.marketing.setup.select_client', { defaultValue: 'Select a client' })}
                  </option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {!clients.length ? (
                <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  {t('app.marketing.setup.no_clients', { defaultValue: 'No Client Account.' })}{' '}
                  <Link to={CRM_APP_PATHS.clientNew} className="underline">
                    {t('app.marketing.setup.create_client', { defaultValue: 'Create client' })}
                  </Link>{' '}
                  {t('app.marketing.setup.in_sales_return', {
                    defaultValue: 'in Sales, then return here.',
                  })}
                </p>
              ) : (
                <p className="mt-1 text-xs text-slate-500">
                  {t('app.marketing.setup.client_context_hint', {
                    defaultValue:
                      'Saved as CampaignTarget(role=context, client_account). Client stats come from here.',
                  })}{' '}
                  <Link to={CRM_APP_PATHS.clientNew} className="underline">
                    {t('app.marketing.setup.new_client', { defaultValue: 'New client' })}
                  </Link>
                </p>
              )}
            </div>

            {contextClientId ? (
              <div className="border-t border-slate-200 pt-4 space-y-3">
                <p className="text-sm font-medium text-slate-800">
                  {t('app.marketing.setup.subject', {
                    defaultValue: 'Campaign subject · {destination}',
                    values: {
                      destination: t(preset.destinationKey, {
                        defaultValue: preset.destinationLabel,
                      }),
                    },
                  })}
                </p>
                <p className="text-xs text-slate-500">
                  {t('app.marketing.setup.primary_target_hint', {
                    defaultValue:
                      'Primary Target sets route_intent for all campaign sources.',
                  })}
                </p>
                {preset.target_type === 'vacancy' ? (
                  !vacanciesForClient.length ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      {t('app.marketing.setup.no_vacancies', {
                        defaultValue: 'No vacancies for this client.',
                      })}{' '}
                      <Link to={CRM_APP_PATHS.vacancyNew} className="underline">
                        {t('app.marketing.setup.create_vacancy', {
                          defaultValue: 'Create vacancy',
                        })}
                      </Link>{' '}
                      {t('app.marketing.setup.in_recruitment', {
                        defaultValue: 'in Recruitment (Vacancies).',
                      })}
                    </p>
                  ) : (
                    <div
                      className="grid gap-2"
                      role="radiogroup"
                      aria-label={t('app.marketing.setup.aria.vacancy', {
                        defaultValue: 'Vacancy',
                      })}
                    >
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
                    {t('app.marketing.setup.no_services', { defaultValue: 'No services.' })}{' '}
                    <Link to={CRM_APP_PATHS.services} className="underline">
                      {t('app.marketing.setup.open_services', { defaultValue: 'Open services' })}
                    </Link>
                  </p>
                ) : (
                  <div
                    className="grid gap-2"
                    role="radiogroup"
                    aria-label={t('app.marketing.setup.aria.service', {
                      defaultValue: 'Service',
                    })}
                  >
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
                {t('app.marketing.setup.select_client_first', {
                  defaultValue:
                    'Select a client first — then a vacancy (hiring) or service (B2B).',
                })}
              </p>
            )}
          </div>
        ) : null}

        {step === 4 && preset ? (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 text-sm">
            <div>
              <div className="text-xs text-slate-500">
                {t('app.marketing.setup.review.campaign', { defaultValue: 'Campaign' })}
              </div>
              <div className="font-medium text-slate-900">{name.trim()}</div>
              {description.trim() ? (
                <div className="mt-1 text-slate-600">{description.trim()}</div>
              ) : null}
            </div>
            <div>
              <div className="text-xs text-slate-500">
                {t('app.marketing.setup.review.owner_company', {
                  defaultValue: 'Owner company',
                })}
              </div>
              <div className="font-medium text-slate-900">
                {selectedCompany?.name || ownCompanyId}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">
                {t('app.marketing.setup.review.flow', { defaultValue: 'Flow' })}
              </div>
              <div className="font-medium text-slate-900">
                {t(preset.labelKey, { defaultValue: preset.label })}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">
                {t('app.marketing.setup.review.client_served', {
                  defaultValue: 'Client (served)',
                })}
              </div>
              <div className="font-medium text-slate-900">
                {selectedClient?.display_name || contextClientId}
              </div>
              <div className="text-xs text-slate-500">CampaignTarget · role=context</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">
                {t('app.marketing.setup.review.primary_target', {
                  defaultValue: 'Primary Target · route_intent',
                })}
              </div>
              <div className="font-medium text-slate-900">
                {preset.target_type === 'vacancy'
                  ? selectedVacancy?.title || targetId
                  : selectedService?.name || targetId}
              </div>
              <div className="text-xs text-slate-500">{preset.route_intent}</div>
            </div>
            <p className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              {t('app.marketing.setup.source_connects_later', {
                defaultValue:
                  'Application source (Meta Lead Form / public form) is connected on the campaign page — separately from creating the goal.',
              })}
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
            {t('app.marketing.setup.back', { defaultValue: 'Back' })}
          </button>
          {step < TOTAL_STEPS ? (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!canNext || optionsLoading}
              onClick={() => setStep((s) => Math.min(TOTAL_STEPS, s + 1))}
              data-testid="marketing-setup-next"
            >
              {t('app.marketing.setup.next', { defaultValue: 'Next' })}
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary btn-sm"
              disabled={!canNext || submitting}
              onClick={() => void handleCreate()}
              data-testid="marketing-setup-create"
            >
              {submitting
                ? t('app.marketing.setup.creating', { defaultValue: 'Creating…' })
                : t('app.marketing.setup.create', { defaultValue: 'Create campaign' })}
            </button>
          )}
        </div>
      </div>
    </PageShell>
  )
}
