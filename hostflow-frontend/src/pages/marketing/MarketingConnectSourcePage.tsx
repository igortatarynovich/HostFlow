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
            defaultValue: 'Failed to load campaign',
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
            defaultValue: 'Enter a form name (public slug required)',
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
            defaultValue: 'Failed to create form',
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
            defaultValue: 'Failed to connect source',
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
          title={t('app.marketing.connect.title', { defaultValue: 'Connect source' })}
          subtitle={campaign?.name || campaignId}
          kind="browse"
          secondaryActions={
            <Link to={marketingCampaignPath(campaignId)} className="btn-secondary btn-sm">
              {t('app.marketing.connect.back_to_campaign', {
                defaultValue: 'Back to campaign',
              })}
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
            <p className="font-medium">
              {t('app.marketing.connect.limit.title', {
                defaultValue: 'Primary source limit for this Flight',
              })}
            </p>
            <p className="mt-1">
              {t('app.marketing.connect.limit.body', {
                defaultValue:
                  'You can have at most one active primary HostFlow form and one primary Meta source. Multiple equal sources of the same type will come later — the UI does not offer a connection that would fail.',
              })}
            </p>
            <Link
              to={marketingCampaignPath(campaignId)}
              className="mt-3 inline-flex btn-secondary btn-sm"
            >
              {t('app.marketing.connect.limit.back', { defaultValue: 'Return to campaign' })}
            </Link>
          </div>
        ) : null}

        {!loading && campaign && flight && (canMeta || canPublic) ? (
          <>
            <p className="text-sm text-slate-600">
              {t('app.marketing.connect.intro', {
                defaultValue:
                  'Application source for campaign “{name}”. Routing inherits the campaign Primary Target ({intent}). The Meta list is Lead Forms on the connected Facebook Page (not a single ad). Forms from other Pages stay out of this list. Per-ad Ad ID is on the campaign card.',
                values: {
                  name: campaign.name,
                  intent:
                    campaign.targets?.find((x) => x.role === 'primary')?.route_intent || '—',
                },
              })}
            </p>

            <div
              className="grid gap-3"
              role="radiogroup"
              aria-label={t('app.marketing.connect.aria.source_type', {
                defaultValue: 'Source type',
              })}
            >
              <MarketingOptionCard
                selected={sourceKind === 'public_form'}
                disabled={!canPublic}
                onClick={() => {
                  setSourceKind('public_form')
                  setMetaSourceId('')
                }}
                testId="marketing-connect-kind-public"
              >
                <span className="font-medium text-slate-900">
                  {t('app.marketing.connect.kind.public_form.label', {
                    defaultValue: 'HostFlow public form',
                  })}
                </span>
                <span className="mt-1 block text-slate-600">
                  {canPublic
                    ? t('app.marketing.connect.kind.public_form.desc_available', {
                        defaultValue:
                          'Applications arrive via the candidate form public link.',
                      })
                    : t('app.marketing.connect.kind.public_form.desc_taken', {
                        defaultValue:
                          'A primary form is already connected to this Flight.',
                      })}
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
                    ? t('app.marketing.connect.kind.meta.desc_taken', {
                        defaultValue:
                          'A primary Meta source is already connected to this Flight.',
                      })
                    : metaSources.length
                      ? t('app.marketing.connect.kind.meta.desc_available', {
                          defaultValue:
                            'Bind a Lead Form (Meta) as source — all ads for the form go to this Flight.',
                        })
                      : t('app.marketing.connect.kind.meta.desc_empty', {
                          defaultValue:
                            'No Lead Forms on the connected Facebook Page. Reconnect the Page in Settings or confirm the Page has Lead Forms.',
                        })}
                </span>
              </MarketingOptionCard>
            </div>

            {sourceKind === 'public_form' && canPublic ? (
              <div className="space-y-3" data-testid="marketing-connect-public-form">
                {forms.length ? (
                  <div
                    className="grid gap-2"
                    role="radiogroup"
                    aria-label={t('app.marketing.connect.aria.hostflow_form', {
                      defaultValue: 'HostFlow form',
                    })}
                  >
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
                    {t('app.marketing.connect.no_forms', { defaultValue: 'No active forms.' })}{' '}
                    <Link to={CRM_APP_PATHS.marketingForms} className="underline">
                      {t('app.marketing.connect.open_forms', { defaultValue: 'Open forms' })}
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
                            defaultValue: 'New form name',
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
                            defaultValue: 'Create and select',
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
                            'Creates an active HostFlow form (candidate fields) via createIntakeForm and selects it immediately.',
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
                        defaultValue: 'Create new form',
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
                            {s.discovered_from === 'graph'
                              ? t('app.marketing.connect.meta.from_page', {
                                  defaultValue: 'on page',
                                })
                              : t('app.marketing.connect.meta.from_leads', {
                                  defaultValue: 'from leads',
                                })}
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
                {t('app.marketing.connect.cancel', { defaultValue: 'Cancel' })}
              </Link>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={!canSubmit || submitting}
                onClick={() => void handleConnect()}
                data-testid="marketing-connect-submit"
              >
                {submitting
                  ? t('app.marketing.connect.connecting', { defaultValue: 'Connecting…' })
                  : t('app.marketing.connect.connect', { defaultValue: 'Connect' })}
              </button>
            </div>
          </>
        ) : null}

        {!loading && campaign && !flight ? (
          <p className="text-sm text-amber-800">
            {t('app.marketing.connect.no_flight', {
              defaultValue: 'This campaign has no Flight — contact support.',
            })}
          </p>
        ) : null}
      </div>
    </PageShell>
  )
}
