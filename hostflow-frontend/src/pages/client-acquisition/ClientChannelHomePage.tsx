import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconCopy, IconDownload } from '@tabler/icons-react'
import { listCompanyIntakeSourceProfiles } from '../../api/companyIntakeSourceProfiles'
import { listLeads } from '../../api/client'
import type { Lead } from '../../api/types'
import { clientAcquisitionChannelPath, clientAcquisitionInquiryPath } from '../../app/clientAcquisitionPaths'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import {
  formatInquiryTime,
  inquiryCompanyName,
  inquiryNeedSummary,
  isOpenClientInquiry,
  leadSourceProfileId,
} from '../../utils/clientInquiryLead'
import { inquiryMetaAttribution } from '../../utils/metaLeadB2b'
import type { ClientChannelConfig } from '../../utils/clientAcquisitionDefaults'
import { audienceLabel } from '../../utils/clientAcquisitionDefaults'
import { downloadQrPng } from '../../utils/clientInquiryUrl'
import { useClientChannelWorkspace } from './clientChannelWorkspaceContext'

export default function ClientChannelHomePage() {
  const { channelId, channelName, publicUrl, pulse, refreshPulse } = useClientChannelWorkspace()
  const { notify } = useToast()
  const { t } = useI18n()

  const [inquiries, setInquiries] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [channelConfig, setChannelConfig] = useState<ClientChannelConfig | null>(null)

  const loadInquiries = useCallback(async () => {
    if (!channelId) return
    setLoading(true)
    try {
      const profiles = await listCompanyIntakeSourceProfiles()
      const profile = profiles.find((p) => p.id === channelId)
      setChannelConfig(profile?.channel_config ?? null)

      const { items = [] } = await listLeads({ limit: 50, offset: 0 })
      const filtered = (items as Lead[])
        .filter((lead) => lead.lead_target_type === 'client_lead' || lead.lead_type === 'client')
        .filter((lead) => leadSourceProfileId(lead) === channelId)
        .filter(isOpenClientInquiry)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      setInquiries(filtered)
      void refreshPulse()
    } catch {
      setInquiries([])
    } finally {
      setLoading(false)
    }
  }, [channelId, refreshPulse])

  useEffect(() => {
    void loadInquiries()
  }, [loadInquiries])

  const audienceHint = useMemo(() => {
    const audience = channelConfig?.audience
    if (!audience) return channelConfig?.landing?.headline ?? null
    return t(`app.client_acquisition.audience.${audience}.title`, {
      defaultValue: audienceLabel(audience),
    })
  }, [channelConfig, t])

  const hasInquiries = inquiries.length > 0
  const recentInquiries = inquiries.slice(0, 10)

  async function copyLink() {
    if (!publicUrl) return
    try {
      await navigator.clipboard.writeText(publicUrl)
      notify({
        title: t('app.client_channel_home.link_copied', { defaultValue: 'Link copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.client_channel_home.link_copy_failed', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  async function downloadQr() {
    if (!publicUrl) return
    try {
      await downloadQrPng(publicUrl, `hostflow-client-channel-${channelId.slice(0, 8)}.png`)
      notify({
        title: t('app.client_channel_home.qr_downloaded', { defaultValue: 'QR downloaded' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.client_channel_home.qr_download_failed', { defaultValue: 'Could not download QR' }),
        variant: 'error',
      })
    }
  }

  return (
    <div className="space-y-4" data-testid="m1-client-channel-home">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {audienceHint ? <p className="text-sm text-slate-600">{audienceHint}</p> : null}

        {pulse?.status?.today_inquiries ? (
          <p className="mt-2 text-sm font-medium text-slate-800">
            {t('app.client_channel_home.today_count', {
              defaultValue: 'Today: {count} new inquiries',
              values: { count: pulse.status.today_inquiries },
            })}
          </p>
        ) : null}

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.sources_link', { defaultValue: 'Link for companies' })}
            </p>
            <p className="mt-2 break-all text-xs text-slate-600">{publicUrl || '—'}</p>
            <button
              type="button"
              onClick={() => void copyLink()}
              disabled={!publicUrl}
              className="mt-3 inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
              data-testid="m1-client-channel-home-copy"
            >
              <IconCopy size={14} />
              {t('app.client_channel_home.copy', { defaultValue: 'Copy' })}
            </button>
          </div>
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.sources_qr', { defaultValue: 'QR code' })}
            </p>
            <p className="mt-2 text-sm text-slate-600">
              {t('app.client_channel_home.qr_hint', { defaultValue: 'For print and offline ads' })}
            </p>
            <button
              type="button"
              onClick={() => void downloadQr()}
              disabled={!publicUrl}
              className="mt-3 inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
            >
              <IconDownload size={14} />
              {t('app.client_channel_home.download_qr', { defaultValue: 'Download' })}
            </button>
          </div>
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.inquiries_title', { defaultValue: 'Recent inquiries' })}
            </p>
            <span className="text-xs text-slate-500">
              {loading
                ? t('common.loading')
                : t('app.client_channel_home.inquiries_count', {
                    defaultValue: '{count} inquiries',
                    values: { count: inquiries.length },
                  })}
            </span>
          </div>
          {hasInquiries ? (
            <ul className="mt-3 space-y-2">
              {recentInquiries.map((row) => (
                <li
                  key={row.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <div>
                    <span className="font-medium text-slate-900">{inquiryCompanyName(row)}</span>
                    <p className="text-xs text-slate-500">{inquiryNeedSummary(row)}</p>
                    {(() => {
                      const attr = inquiryMetaAttribution(row)
                      return attr ? <p className="text-xs text-slate-400">{attr.line}</p> : null
                    })()}
                    {row.created_at ? (
                      <p className="text-xs text-slate-500">{formatInquiryTime(row.created_at)}</p>
                    ) : null}
                  </div>
                  <Link
                    to={clientAcquisitionInquiryPath(channelId, row.id)}
                    className="text-brand-700 hover:underline"
                  >
                    {t('app.client_channel_home.open_inquiry', { defaultValue: 'Open' })}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-600">
              {t('app.client_channel_home.inquiries_empty', {
                defaultValue: 'Nothing yet. When a company submits an inquiry, it will show up here.',
              })}
            </p>
          )}
        </div>
      </section>

      {!hasInquiries && publicUrl ? (
        <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4 text-sm text-slate-700">
          <p className="font-medium text-slate-900">
            {t('app.sales_channel.share_hint_title', { defaultValue: 'Where to place the link' })}
          </p>
          <p className="mt-1">
            {t('app.sales_channel.share_hint_body', {
              defaultValue:
                'Meta or Google ads, company website, email signature, QR on a business card. The company opens the form and submits an inquiry — it appears here.',
            })}
          </p>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-600">
        <p className="font-medium text-slate-800">
          {t('app.client_channel_home.not_candidate_title', {
            defaultValue: 'This is not a candidate form',
          })}
        </p>
        <p className="mt-1">
          {t('app.client_channel_home.not_candidate_body', {
            defaultValue:
              'This link sends companies to a staffing inquiry. The candidate questionnaire is a separate Launchpad flow.',
          })}
        </p>
        <p className="mt-2 text-xs text-slate-500">{channelName}</p>
      </section>
    </div>
  )
}
