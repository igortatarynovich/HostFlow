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
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import {
  canConnectSourceKind,
  type MarketingSourceKind,
} from './marketingPresentation'
import { MarketingOptionCard } from './MarketingOptionCard'

export default function MarketingConnectSourcePage() {
  const { t } = useI18n()
  const navigate = useNavigate()
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

  const flight = currentFlight(campaign)
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

  async function handleConnect() {
    if (!campaign || !canSubmit || !sourceKind) return
    setSubmitting(true)
    setError(null)
    try {
      if (sourceKind === 'public_form') {
        await attachCampaignForm(campaign.id, formId, 'primary')
      } else {
        await attachCampaignIntakeSource(campaign.id, metaSourceId, 'primary')
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
              К кампании
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
            <p className="font-medium">Лимит primary-источников для этого Flight</p>
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
              ).
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
                <span className="font-medium text-slate-900">Публичная анкета HostFlow</span>
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
                      ? 'Привязать существующий Lead Form (Meta) как источник заявок.'
                      : 'Нет активных Meta-источников — настройте интеграцию Meta.'}
                </span>
              </MarketingOptionCard>
            </div>

            {sourceKind === 'public_form' && canPublic ? (
              forms.length ? (
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
                  <Link to={CRM_APP_PATHS.settingsLeadForms} className="underline">
                    Открыть анкеты
                  </Link>
                </p>
              )
            ) : null}

            {sourceKind === 'meta' && canMeta && metaSources.length ? (
              <div className="grid gap-2" role="radiogroup" aria-label="Lead Form Meta">
                {metaSources.map((s) => (
                  <MarketingOptionCard
                    key={s.id}
                    selected={metaSourceId === s.id}
                    onClick={() => setMetaSourceId(s.id)}
                    testId={`marketing-connect-meta-${s.id}`}
                  >
                    <span className="font-medium text-slate-900">{s.name}</span>
                    <span className="mt-1 block text-xs text-slate-500">{s.code || s.provider}</span>
                  </MarketingOptionCard>
                ))}
              </div>
            ) : null}

            <div className="flex justify-end gap-2 pt-2">
              <Link to={marketingCampaignPath(campaignId)} className="btn-secondary btn-sm">
                Отмена
              </Link>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={!canSubmit || submitting}
                onClick={() => void handleConnect()}
                data-testid="marketing-connect-submit"
              >
                {submitting ? 'Подключение…' : 'Подключить'}
              </button>
            </div>
          </>
        ) : null}

        {!loading && campaign && !flight ? (
          <p className="text-sm text-amber-800">У кампании нет Flight — обратитесь к поддержке.</p>
        ) : null}
      </div>
    </PageShell>
  )
}
