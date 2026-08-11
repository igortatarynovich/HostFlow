import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconBrandMeta, IconCheck, IconCircle } from '@tabler/icons-react'
import {
  getMetaLeadSelfServeOnboarding,
  listMetaLeadCredentials,
  startMetaOAuth,
} from '../../api/metaLeads'
import type { MetaLeadCredential } from '../../api/types'
import {
  bindSearchMetaCampaigns,
  getSearchMetaInventory,
  type MetaSearchCampaign,
  type MetaSearchInventory,
} from '../../api/searchMetaBinding'
import {
  CRM_APP_PATHS,
  recruitmentSearchAcquisitionPath,
  recruitmentSearchMetaSourcePath,
} from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'
import { useToast } from '../../components/Toast'
import { setMetaOAuthReturnPath } from '../../utils/metaOAuthReturn'
import { useSearchWorkspace } from './SearchWorkspaceLayout'

export default function SearchMetaSourcePage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const { me } = useAuth()
  const { searchId, searchName } = useSearchWorkspace()
  const [loading, setLoading] = useState(true)
  const [oauthBusy, setOauthBusy] = useState(false)
  const [bindBusy, setBindBusy] = useState(false)
  const [credentials, setCredentials] = useState<MetaLeadCredential[]>([])
  const [inventory, setInventory] = useState<MetaSearchInventory | null>(null)
  const [selectedCampaignIds, setSelectedCampaignIds] = useState<string[]>([])
  const [oauthEnabled, setOauthEnabled] = useState(false)

  const load = useCallback(async () => {
    if (!searchId) return
    setLoading(true)
    try {
      const [creds, selfServe, inv] = await Promise.all([
        listMetaLeadCredentials(),
        getMetaLeadSelfServeOnboarding().catch(() => null),
        getSearchMetaInventory(searchId).catch(() => null),
      ])
      setCredentials(creds)
      setOauthEnabled(Boolean(selfServe?.oauth_quick_connect_enabled))
      setInventory(inv)
      const preselected =
        inv?.campaigns?.filter((c) => c.bound_to_search).map((c) => c.id) ??
        inv?.bound_campaign_ids ??
        []
      setSelectedCampaignIds(preselected)
    } catch {
      setCredentials([])
      setInventory(null)
    } finally {
      setLoading(false)
    }
  }, [searchId])

  useEffect(() => {
    void load()
  }, [load])

  const activeCredentials = useMemo(
    () => credentials.filter((row) => row.status === 'active'),
    [credentials],
  )
  const isAdmin = me?.role === 'administrator'
  const metaConnected = activeCredentials.length > 0
  const boundCampaigns = useMemo(
    () => inventory?.campaigns?.filter((c) => c.bound_to_search) ?? [],
    [inventory],
  )
  const setupDone = metaConnected && boundCampaigns.length > 0

  const steps = useMemo(() => {
    const hasCampaigns = boundCampaigns.length > 0
    return [
      {
        key: 'connect',
        title: t('app.search_meta.steps.connect_title', { defaultValue: 'Connect Meta' }),
        body: t('app.search_meta.steps.connect_body_v2', {
          defaultValue: 'Log in with Facebook — HostFlow gets access to your ads and leads.',
        }),
        done: metaConnected,
      },
      {
        key: 'campaigns',
        title: t('app.search_meta.steps.campaigns_title', {
          defaultValue: 'Choose ads for this search',
        }),
        body: t('app.search_meta.steps.campaigns_body', {
          defaultValue: 'Select campaigns — HostFlow will link ads, forms and the lead route.',
        }),
        done: hasCampaigns,
      },
      {
        key: 'done',
        title: t('app.search_meta.steps.done_title', { defaultValue: 'Done' }),
        body: t('app.search_meta.steps.done_body', {
          defaultValue: 'New applications from the selected ads will land in this search.',
        }),
        done: setupDone,
      },
    ]
  }, [boundCampaigns.length, metaConnected, setupDone, t])

  async function handleConnectMeta() {
    setOauthBusy(true)
    try {
      setMetaOAuthReturnPath(recruitmentSearchMetaSourcePath(searchId))
      const { authorize_url } = await startMetaOAuth()
      window.location.assign(authorize_url)
    } catch {
      notify({
        title: t('app.search_meta.connect_error', { defaultValue: 'Could not start Meta connection' }),
        variant: 'error',
      })
      setOauthBusy(false)
    }
  }

  function toggleCampaign(campaign: MetaSearchCampaign) {
    setSelectedCampaignIds((prev) =>
      prev.includes(campaign.id) ? prev.filter((id) => id !== campaign.id) : [...prev, campaign.id],
    )
  }

  async function handleBindCampaigns() {
    if (!searchId || selectedCampaignIds.length === 0) return
    setBindBusy(true)
    try {
      const result = await bindSearchMetaCampaigns(searchId, selectedCampaignIds)
      setInventory(result.inventory)
      setSelectedCampaignIds(
        result.inventory.campaigns.filter((c) => c.bound_to_search).map((c) => c.id),
      )
      notify({
        title: t('app.search_meta.bind_success', {
          defaultValue: 'Ads linked to search',
          values: { ads: result.bound_ads },
        }),
        variant: 'success',
      })
      if (result.skipped.length > 0) {
        notify({
          title: t('app.search_meta.bind_partial', {
            defaultValue: 'Some campaigns were skipped — check Meta permissions',
          }),
          variant: 'warning',
        })
      }
    } catch {
      notify({
        title: t('app.search_meta.bind_error', { defaultValue: 'Could not link ads to search' }),
        variant: 'error',
      })
    } finally {
      setBindBusy(false)
    }
  }

  return (
    <div className="space-y-5" data-testid="m1-search-meta-source">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#0081FB]/10 text-[#0081FB]">
            <IconBrandMeta size={24} stroke={1.75} />
          </span>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              {t('app.search_meta.title', { defaultValue: 'Meta Ads' })}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {t('app.search_meta.subtitle_v2', {
                defaultValue: 'Link Meta ads to search “{name}” — HostFlow will set up the lead route.',
                values: { name: searchName },
              })}
            </p>
          </div>
        </div>
      </section>

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t('app.search_meta.checklist_title', { defaultValue: 'What to do' })}
            </h3>
            <ol className="mt-4 space-y-4">
              {steps.map((step, index) => (
                <li key={step.key} className="flex gap-3">
                  <span
                    className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      step.done ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {step.done ? <IconCheck size={14} /> : index + 1}
                  </span>
                  <div>
                    <p className="font-medium text-slate-900">{step.title}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>

            {!metaConnected ? (
              <div className="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-center">
                <p className="text-sm text-slate-600">
                  {t('app.search_meta.connect_prompt', {
                    defaultValue: 'Start by connecting Meta — then pick ads for this search.',
                  })}
                </p>
                {isAdmin && oauthEnabled ? (
                  <button
                    type="button"
                    disabled={oauthBusy}
                    onClick={() => void handleConnectMeta()}
                    className="mt-4 inline-flex rounded-lg bg-[#0081FB] px-4 py-3 text-sm font-semibold text-white hover:bg-[#006FE0] disabled:opacity-50"
                    data-testid="m1-search-meta-connect"
                  >
                    {oauthBusy
                      ? t('common.loading', { defaultValue: 'Loading…' })
                      : t('app.search_meta.connect_cta', { defaultValue: 'Log in with Facebook' })}
                  </button>
                ) : (
                  <p className="mt-3 text-sm text-amber-900">
                    {!isAdmin
                      ? t('app.search_meta.admin_only', {
                          defaultValue: 'Meta connection is available to the workspace administrator.',
                        })
                      : t('app.search_meta.oauth_unavailable', {
                          defaultValue: 'Quick Meta connection is unavailable on the current plan or server.',
                        })}
                  </p>
                )}
              </div>
            ) : null}
          </section>

          {metaConnected ? (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    {t('app.search_meta.campaign_picker_title', { defaultValue: 'Ads for this search' })}
                  </h3>
                  {inventory?.ad_account_name ? (
                    <p className="mt-1 text-sm text-slate-600">
                      {t('app.search_meta.ad_account_label_named', {
                        defaultValue: 'Ad account: {name}',
                        values: { name: inventory.ad_account_name },
                      })}
                    </p>
                  ) : null}
                </div>
                {setupDone ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
                    <IconCheck size={14} />
                    {t('app.search_meta.ready_badge', { defaultValue: 'Configured' })}
                  </span>
                ) : null}
              </div>

              {inventory?.empty_message && (inventory.campaigns?.length ?? 0) === 0 ? (
                <div className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  <p>{inventory.empty_message}</p>
                  {inventory.needs_marketing_reconnect && isAdmin && oauthEnabled ? (
                    <button
                      type="button"
                      disabled={oauthBusy}
                      onClick={() => void handleConnectMeta()}
                      className="mt-4 inline-flex rounded-lg bg-[#0081FB] px-4 py-2 text-sm font-semibold text-white hover:bg-[#006FE0] disabled:opacity-50"
                    >
                      {oauthBusy
                        ? t('common.loading', { defaultValue: 'Loading…' })
                        : t('app.search_meta.reconnect_cta', { defaultValue: 'Refresh Meta access' })}
                    </button>
                  ) : null}
                  {!inventory.needs_marketing_reconnect ? (
                    <p className="mt-2 text-xs text-slate-500">
                      {t('app.search_meta.empty_hint', {
                        defaultValue: 'Create a Lead Ad in Meta Ads Manager or come back later.',
                      })}
                    </p>
                  ) : (
                    <p className="mt-2 text-xs text-slate-500">
                      {t('app.search_meta.reconnect_page_hint', {
                        defaultValue:
                          'When signing in, choose the Facebook Page that runs ads for this search (not any page from the list).',
                      })}
                    </p>
                  )}
                </div>
              ) : null}

              {(inventory?.campaigns?.length ?? 0) > 0 ? (
                <ul className="mt-4 space-y-2">
                  {inventory!.campaigns.map((campaign) => {
                    const checked = selectedCampaignIds.includes(campaign.id)
                    return (
                      <li key={campaign.id}>
                        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 px-4 py-3 hover:bg-slate-50">
                          <input
                            type="checkbox"
                            className="mt-1"
                            checked={checked}
                            onChange={() => toggleCampaign(campaign)}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block font-medium text-slate-900">{campaign.name}</span>
                            <span className="mt-0.5 block text-xs text-slate-500">
                              {campaign.status || '—'}
                              {campaign.ads_count != null
                                ? ` · ${t('app.search_meta.ads_count', {
                                    defaultValue: '{count} ads',
                                    values: { count: campaign.ads_count },
                                  })}`
                                : ''}
                            </span>
                          </span>
                          {campaign.bound_to_search ? (
                            <IconCheck size={18} className="shrink-0 text-emerald-600" aria-label="bound" />
                          ) : (
                            <IconCircle size={18} className="shrink-0 text-slate-300" aria-label="pending" />
                          )}
                        </label>
                      </li>
                    )
                  })}
                </ul>
              ) : null}

              {(inventory?.campaigns?.length ?? 0) > 0 ? (
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    disabled={bindBusy || selectedCampaignIds.length === 0}
                    onClick={() => void handleBindCampaigns()}
                    className="inline-flex rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                  >
                    {bindBusy
                      ? t('common.loading', { defaultValue: 'Loading…' })
                      : t('app.search_meta.bind_cta', { defaultValue: 'Link to search' })}
                  </button>
                  {setupDone ? (
                    <Link
                      to={recruitmentSearchAcquisitionPath(searchId)}
                      className="inline-flex rounded-lg border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      {t('app.search_meta.back_to_acquisition', { defaultValue: 'Back to acquisition' })}
                    </Link>
                  ) : null}
                </div>
              ) : null}
            </section>
          ) : null}
        </>
      )}
    </div>
  )
}
