/**
 * Connect Source — bind Meta Lead Form or HostFlow public анкета to current Flight.
 * Does not create Campaign. PR1: only primary slots (no multi-primary promise).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  CRM_APP_PATHS,
  marketingCampaignPath,
} from '../../app/crmAppPaths'
import { createIntakeForm, listIntakeFormEntityProfiles } from '../../api/intakeForms'
import { listLeadForms, type TenantLeadForm } from '../../api/leadForms'
import {
  attachCampaignForm,
  attachCampaignIntakeSource,
  currentFlight,
  getCampaign,
  listIntakeSourceOptions,
  type Campaign,
  type IntakeSourceOption,
} from '../../api/platformCampaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  defaultProfileForPurpose,
  slugifyFormTitle,
} from '../../utils/intakeFormRoutingSummary'
import { launchSearchIntakeFields } from '../../utils/launchSearchIntakeFields'
import {
  canConnectSourceKind,
  type MarketingSourceKind,
} from './marketingPresentation'
import { MarketingOptionCard } from './MarketingOptionCard'

export default function MarketingConnectSourcePage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { role } = usePermissions()
  const canCreateForm = role === 'administrator'
  const { campaignId = '' } = useParams<{ campaignId: string }>()
  const [searchParams] = useSearchParams()
  const kindParam = (searchParams.get('kind') || '').trim()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [sourceKind, setSourceKind] = useState<MarketingSourceKind | ''>(() =>
    kindParam === 'meta' || kindParam === 'public_form' ? kindParam : '',
  )
  const [formId, setFormId] = useState('')
  const [metaSourceId, setMetaSourceId] = useState('')
  const [forms, setForms] = useState<TenantLeadForm[]>([])
  const [metaSources, setMetaSources] = useState<IntakeSourceOption[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createTitle, setCreateTitle] = useState('')
  const [creatingForm, setCreatingForm] = useState(false)

  const flight = campaign ? currentFlight(campaign) : null
  const canMeta = canConnectSourceKind(flight, 'meta')
  const canPublic = canConnectSourceKind(flight, 'public_form')

  const load = useCallback(async () => {
    if (!campaignId) return
    setLoading(true)
    setError(null)
    try {
      const [c, formRows, metaRows] = await Promise.all([
        getCampaign(campaignId),
        listLeadForms().catch(() => [] as TenantLeadForm[]),
        listIntakeSourceOptions('meta').catch(() => [] as IntakeSourceOption[]),
      ])
      setCampaign(c)
      setForms(Array.isArray(formRows) ? formRows.filter((f) => f.is_active) : [])
      setMetaSources(Array.isArray(metaRows) ? metaRows.filter((s) => s.is_active) : [])
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.connect.errors.load', {
            defaultValue: 'Не удалось загрузить кампанию',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }, [campaignId, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!sourceKind) return
    if (sourceKind === 'meta' && !canMeta) setSourceKind('')
    if (sourceKind === 'public_form' && !canPublic) setSourceKind('')
  }, [canMeta, canPublic, sourceKind])

  const canSubmit = useMemo(() => {
    if (!campaign || !flight) return false
    if (sourceKind === 'public_form') return canPublic && Boolean(formId)
    if (sourceKind === 'meta') return canMeta && Boolean(metaSourceId)
    return false
  }, [campaign, flight, sourceKind, canPublic, canMeta, formId, metaSourceId])

  async function handleCreateHostflowForm() {
    if (!canCreateForm || !canPublic) return
    const title = createTitle.trim() || 'New Marketing form'
    const slug = slugifyFormTitle(title)
    if (slug.length < 2) {
      setError(
        getFriendlyErrorInfo(
          new Error('slug'),
          t('app.marketing.connect.errors.create_slug', {
            defaultValue: 'Укажите название анкеты (нужен публичный slug)',
          }),
          t,
        ),
      )
      return
    }
    setCreatingForm(true)
    setError(null)
    try {
      const profiles = await listIntakeFormEntityProfiles().catch(() => [])
      const mapped = profiles.map((item) => ({ code: item.code, name: item.name }))
      const profileCode =
        defaultProfileForPurpose(mapped, 'application') ||
        mapped.find((p) => p.code.startsWith('recruitment.candidate'))?.code ||
        mapped[0]?.code
      if (!profileCode) {
        throw new Error('No entity profile available for candidate form')
      }
      const fields = await launchSearchIntakeFields('other')
      const created = await createIntakeForm({
        title,
        public_slug: slug,
        entity_profile_code: profileCode,
        fields,
        is_active: true,
      })
      const form = created.form
      setForms((prev) => {
        const next = prev.filter((row) => row.id !== form.id)
        next.unshift(form)
        return next
      })
      setFormId(form.id)
      setShowCreateForm(false)
      setCreateTitle('')
      setSourceKind('public_form')
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.connect.errors.create_form', {
            defaultValue: 'Не удалось создать анкету',
          }),
          t,
        ),
      )
    } finally {
      setCreatingForm(false)
    }
  }

  async function handleConnect() {
    if (!campaign || !canSubmit || !sourceKind) return
    setSubmitting(true)
    setError(null)
    try {
      if (sourceKind === 'public_form') {
        await attachCampaignForm(campaign.id, formId, 'primary')
      } else {
        const selected = metaSources.find((s) => s.id === metaSourceId)
        if (selected?.needs_create && selected.meta_form_id) {
          await attachCampaignIntakeSource(campaign.id, {
            meta_form_id: selected.meta_form_id,
            page_id: selected.page_id,
            role: 'primary',
          })
        } else {
          await attachCampaignIntakeSource(campaign.id, metaSourceId, 'primary')
        }
      }
      navigate(marketingCampaignPath(campaign.id))
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.connect.errors.save', {
            defaultValue: 'Не удалось подключить источник',
          }),
          t,
        ),
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (!campaignId) {
    return <Navigate to={CRM_APP_PATHS.marketing} replace />
  }

  const nothingLeft = !loading && campaign && flight && !canMeta && !canPublic

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.marketing.connect.title', { defaultValue: 'Подключить источник' })}
          subtitle={campaign?.name || campaignId}
          kind="browse"
          secondaryActions={
            <Link to={marketingCampaignPath(campaignId)} className="btn-secondary btn-sm">
              {t('app.marketing.connect.back_campaign')}
            </Link>
          }
        />
      </PageShellHeader>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 pb-8">
        {error ? <ErrorRecoveryBanner info={error} onRetry={() => void load()} /> : null}
        {loading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

        {nothingLeft ? (
          <div
            className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            data-testid="marketing-connect-limit"
            role="status"
          >
            <p className="font-medium">{t('app.marketing.connect.primary_limit_title')}</p>
            <p className="mt-1">
              Сейчас можно иметь не больше одной активной primary анкеты HostFlow и одного primary
              Meta-источника. Несколько равноправных источников одного типа появятся позже — UI не
              предлагает заведомо недоступное подключение.
            </p>
            <Link
              to={marketingCampaignPath(campaignId)}
              className="mt-3 inline-flex btn-secondary btn-sm"
            >
              Вернуться к кампании
            </Link>
          </div>
        ) : null}

        {!loading && campaign && flight && (canMeta || canPublic) ? (
          <>
            <p className="text-sm text-slate-600">
              Источник заявок для кампании «{campaign.name}». Routing наследует Primary Target
              кампании ({campaign.targets?.find((x) => x.role === 'primary')?.route_intent || '—'}
              ). Список Meta = Lead Form (не отдельное объявление). Формы, уже приходившие в лидах,
              тоже здесь — даже если профиль ещё не создан. Точечный Ad ID — на карточке кампании.
            </p>

            <div className="grid gap-3" role="radiogroup" aria-label="Тип источника">
              <MarketingOptionCard
                selected={sourceKind === 'public_form'}
                disabled={!canPublic}
                onClick={() => {
                  setSourceKind('public_form')
                  setMetaSourceId('')
                }}
                testId="marketing-connect-kind-public"
              >
                <span className="font-medium text-slate-900">{t('app.marketing.connect.hostflow_form')}</span>
                <span className="mt-1 block text-slate-600">
                  {canPublic
                    ? 'Заявки приходят через публичную ссылку анкеты кандидата.'
                    : 'Primary анкета уже подключена к этому Flight.'}
                </span>
              </MarketingOptionCard>
              <MarketingOptionCard
                selected={sourceKind === 'meta'}
                disabled={!canMeta || !metaSources.length}
                onClick={() => {
                  setSourceKind('meta')
                  setFormId('')
                }}
                testId="marketing-connect-kind-meta"
              >
                <span className="font-medium text-slate-900">Meta Lead Ads</span>
                <span className="mt-1 block text-slate-600">
                  {!canMeta
                    ? 'Primary Meta-источник уже подключён к этому Flight.'
                    : metaSources.length
                      ? 'Привязать Lead Form (Meta) как источник — все объявления формы пойдут в этот Flight.'
                      : 'Нет Meta-форм в каталоге и в лидах — настройте Meta или дождитесь первого лида.'}
                </span>
              </MarketingOptionCard>
            </div>

            {sourceKind === 'public_form' && canPublic ? (
              <div className="space-y-3" data-testid="marketing-connect-public-form">
                {forms.length ? (
                  <div className="grid gap-2" role="radiogroup" aria-label="Анкета HostFlow">
                    {forms.map((f) => (
                      <MarketingOptionCard
                        key={f.id}
                        selected={formId === f.id}
                        onClick={() => setFormId(f.id)}
                        testId={`marketing-connect-form-${f.id}`}
                      >
                        <span className="font-medium text-slate-900">{f.title}</span>
                        {f.public_slug ? (
                          <span className="mt-1 block text-xs text-slate-500">{f.public_slug}</span>
                        ) : null}
                      </MarketingOptionCard>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    Нет активных анкет.{' '}
                    <Link to={CRM_APP_PATHS.marketingForms} className="underline">
                      Открыть анкеты
                    </Link>
                  </p>
                )}

                {canCreateForm ? (
                  showCreateForm ? (
                    <div
                      className="space-y-3 rounded-lg border border-brand-100 bg-white p-3"
                      data-testid="marketing-connect-create-form"
                    >
                      <label className="block text-sm">
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {t('app.marketing.connect.create.title', {
                            defaultValue: 'Название новой анкеты',
                          })}
                        </span>
                        <input
                          className="input mt-1 w-full"
                          value={createTitle}
                          data-testid="marketing-connect-create-title"
                          onChange={(e) => setCreateTitle(e.target.value)}
                          placeholder="Kierowca CE Lead Form"
                        />
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          disabled={creatingForm}
                          data-testid="marketing-connect-create-submit"
                          onClick={() => void handleCreateHostflowForm()}
                        >
                          {t('app.marketing.connect.create.submit', {
                            defaultValue: 'Создать и выбрать',
                          })}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          disabled={creatingForm}
                          data-testid="marketing-connect-create-cancel"
                          onClick={() => {
                            setShowCreateForm(false)
                            setCreateTitle('')
                          }}
                        >
                          {t('common.actions.cancel', { defaultValue: 'Cancel' })}
                        </button>
                      </div>
                      <p className="text-xs text-slate-500">
                        {t('app.marketing.connect.create.hint', {
                          defaultValue:
                            'Создаёт активную HostFlow-анкету (candidate fields) через createIntakeForm и сразу выбирает её.',
                        })}
                      </p>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      data-testid="marketing-connect-create-open"
                      onClick={() => setShowCreateForm(true)}
                    >
                      {t('app.marketing.connect.create.open', {
                        defaultValue: 'Создать новую анкету',
                      })}
                    </button>
                  )
                ) : null}
              </div>
            ) : null}

            {sourceKind === 'meta' && canMeta && metaSources.length ? (
              <div className="grid gap-2" role="radiogroup" aria-label="Lead Form Meta">
                {metaSources.map((s) => {
                  const title =
                    s.lead_form_name ||
                    (s.display_title && !/^Meta form\s+\d+$/i.test(s.display_title)
                      ? s.display_title
                      : null) ||
                    t('app.marketing.connect.meta.lead_form', { defaultValue: 'Lead Form' })
                  const formId = s.meta_form_id || null
                  const pageLabel = s.page_name || s.page_id || null
                  const ads =
                    Array.isArray(s.sample_ads) && s.sample_ads.length
                      ? s.sample_ads
                      : (s.sample_ad_ids || []).map((ad_id) => ({ ad_id, label: null }))
                  return (
                    <MarketingOptionCard
                      key={s.id}
                      selected={metaSourceId === s.id}
                      onClick={() => setMetaSourceId(s.id)}
                      testId={`marketing-connect-meta-${s.id}`}
                    >
                      <span
                        className="font-medium text-slate-900"
                        data-testid={`marketing-connect-meta-title-${s.id}`}
                      >
                        {title}
                        {s.needs_create ? (
                          <span
                            className="ml-2 inline-flex rounded-md bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800 ring-1 ring-inset ring-amber-200"
                            data-testid={`marketing-connect-meta-discovered-${s.id}`}
                          >
                            из лидов
                          </span>
                        ) : null}
                      </span>
                      <span className="mt-1 block text-xs text-slate-600">
                        {formId ? (
                          <>
                            {t('app.marketing.connect.meta.form_id', { defaultValue: 'Form ID' })}
                            {': '}
                            <span data-testid={`marketing-connect-meta-form-id-${s.id}`}>
                              {formId}
                            </span>
                          </>
                        ) : (
                          <span className="text-slate-500">{s.code || s.provider}</span>
                        )}
                      </span>
                      {pageLabel ? (
                        <span className="mt-0.5 block text-xs text-slate-500">
                          {t('app.marketing.connect.meta.page', { defaultValue: 'Page' })}
                          {': '}
                          <span data-testid={`marketing-connect-meta-page-${s.id}`}>
                            {s.page_name ? s.page_name : pageLabel}
                            {s.page_name && s.page_id ? (
                              <span className="text-slate-400"> ({s.page_id})</span>
                            ) : null}
                          </span>
                        </span>
                      ) : null}
                      {ads.length ? (
                        <span className="mt-0.5 block text-xs text-slate-500">
                          {t('app.marketing.connect.meta.ads', { defaultValue: 'Ads' })}
                          {': '}
                          <span data-testid={`marketing-connect-meta-ads-${s.id}`}>
                            {ads
                              .map((a) =>
                                a.label ? `${a.label} (${a.ad_id})` : a.ad_id,
                              )
                              .join(', ')}
                          </span>
                        </span>
                      ) : null}
                      {s.last_submission_at ? (
                        <span className="mt-0.5 block text-xs text-slate-400">
                          {t('app.marketing.connect.meta.last_lead', {
                            defaultValue: 'Last lead',
                          })}
                          {': '}
                          {new Date(s.last_submission_at).toLocaleString()}
                        </span>
                      ) : null}
                    </MarketingOptionCard>
                  )
                })}
              </div>
            ) : null}

            <div className="flex justify-end gap-2 pt-2">
              <Link to={marketingCampaignPath(campaignId)} className="btn-secondary btn-sm">
                {t('app.marketing.connect.cancel')}
              </Link>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={!canSubmit || submitting}
                onClick={() => void handleConnect()}
                data-testid="marketing-connect-submit"
              >
                {submitting ? t('app.marketing.connect.connecting') : t('app.marketing.connect.submit')}
              </button>
            </div>
          </>
        ) : null}

        {!loading && campaign && !flight ? (
          <p className="text-sm text-amber-800">{t('app.marketing.connect.no_flight')}</p>
        ) : null}
      </div>
    </PageShell>
  )
}
