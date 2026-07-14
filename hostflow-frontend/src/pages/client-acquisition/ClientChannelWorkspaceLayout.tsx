import { useCallback, useEffect, useState } from 'react'
import { Link, Outlet, useParams } from 'react-router-dom'
import { IconArrowLeft } from '@tabler/icons-react'
import { listCompanyIntakeSourceProfiles } from '../../api/companyIntakeSourceProfiles'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { ClientNextActionPanel } from '../../components/sales/ClientNextActionPanel'
import { useClientChannelWorkspacePulse } from '../../hooks/useClientChannelWorkspacePulse'
import { useI18n } from '../../i18n'
import { loadClientChannel, persistLastClientChannelId } from '../../services/clientChannelSession'
import { buildPublicClientInquiryUrl } from '../../utils/clientInquiryUrl'
import {
  ClientChannelWorkspaceContext,
  type ClientChannelWorkspaceContextValue,
} from './clientChannelWorkspaceContext'

export default function ClientChannelWorkspaceLayout() {
  const { channelId = '' } = useParams<{ channelId: string }>()
  const { t } = useI18n()
  const cached = loadClientChannel(channelId)
  const [channelName, setChannelName] = useState(cached?.name ?? '')
  const [publicUrl, setPublicUrl] = useState(cached?.publicUrl ?? '')
  const { pulse, loading: pulseLoading, refresh: refreshPulse } = useClientChannelWorkspacePulse(channelId)

  const load = useCallback(async () => {
    if (!channelId) return
    try {
      const profiles = await listCompanyIntakeSourceProfiles()
      const profile = profiles.find((p) => p.id === channelId)
      const slug = profile?.public_slug ?? cached?.publicSlug ?? ''
      setChannelName(
        profile?.name ??
          cached?.name ??
          t('app.client_channel_home.default_title', { defaultValue: 'Привлечение клиентов' }),
      )
      setPublicUrl(slug ? buildPublicClientInquiryUrl(slug) : cached?.publicUrl ?? '')
    } catch {
      if (cached?.name) setChannelName(cached.name)
      if (cached?.publicUrl) setPublicUrl(cached.publicUrl)
    }
  }, [cached?.name, cached?.publicSlug, cached?.publicUrl, channelId, t])

  useEffect(() => {
    if (channelId) persistLastClientChannelId(channelId)
  }, [channelId])

  useEffect(() => {
    void load()
  }, [load])

  const workspaceValue: ClientChannelWorkspaceContextValue = {
    channelId,
    channelName,
    publicUrl: publicUrl || undefined,
    pulse,
    pulseLoading,
    reload: load,
    refreshPulse,
  }

  const status = pulse?.status

  return (
    <ClientChannelWorkspaceContext.Provider value={workspaceValue}>
      <div className="mx-auto max-w-3xl space-y-4 px-1 sm:px-0" data-testid="m1-sales-channel-workspace">
        <Link
          to={CRM_APP_PATHS.clientAcquisitionChannels}
          className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-brand-700"
        >
          <IconArrowLeft size={14} stroke={1.9} />
          {t('app.sales_channels.back_list', { defaultValue: 'Привлечение клиентов' })}
        </Link>

        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                {t('app.client_channel_home.kicker', { defaultValue: 'Привлечение клиентов' })}
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">{channelName || '…'}</h1>
            </div>
            {status?.label ? (
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                {status.label}
              </span>
            ) : null}
          </div>

          {status?.open_inquiries != null ? (
            <p className="text-sm text-slate-600">
              {t('app.sales_workspace.status_line', {
                defaultValue: '{open} открытых запросов · сегодня {today} · клиентов {converted}',
                values: {
                  open: status.open_inquiries ?? 0,
                  today: status.today_inquiries ?? 0,
                  converted: status.converted_clients ?? 0,
                },
              })}
            </p>
          ) : null}

          <ClientNextActionPanel
            pulse={pulse}
            channelId={channelId}
            publicUrl={publicUrl}
            loading={pulseLoading}
          />
        </header>

        <Outlet />
      </div>
    </ClientChannelWorkspaceContext.Provider>
  )
}
