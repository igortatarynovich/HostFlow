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
    return audienceLabel(audience)
  }, [channelConfig])

  const hasInquiries = inquiries.length > 0
  const recentInquiries = inquiries.slice(0, 10)

  async function copyLink() {
    if (!publicUrl) return
    try {
      await navigator.clipboard.writeText(publicUrl)
      notify({
        title: t('app.client_channel_home.link_copied', { defaultValue: 'Ссылка скопирована' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.client_channel_home.link_copy_failed', { defaultValue: 'Не удалось скопировать' }),
        variant: 'error',
      })
    }
  }

  async function downloadQr() {
    if (!publicUrl) return
    try {
      await downloadQrPng(publicUrl, `hostflow-client-channel-${channelId.slice(0, 8)}.png`)
      notify({
        title: t('app.client_channel_home.qr_downloaded', { defaultValue: 'QR скачан' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.client_channel_home.qr_download_failed', { defaultValue: 'Не удалось скачать QR' }),
        variant: 'error',
      })
    }
  }

  return (
    <div className="space-y-4" data-testid="m1-client-channel-home">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {audienceHint ? <p className="text-sm text-slate-600">{audienceHint}</p> : null}

        {pulse?.status?.today_inquiries ? (
          <p className="mt-2 text-sm font-medium text-slate-800">
            {t('app.client_channel_home.today_count', {
              defaultValue: 'Сегодня: {count} новых запросов',
              values: { count: pulse.status.today_inquiries },
            })}
          </p>
        ) : null}

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.sources_link', { defaultValue: 'Ссылка для компаний' })}
            </p>
            <p className="mt-2 break-all text-xs text-slate-600">{publicUrl || '—'}</p>
            <button
              type="button"
              onClick={() => void copyLink()}
              disabled={!publicUrl}
              className="mt-3 inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
              data-testid="m1-client-channel-home-copy"
            >
              <IconCopy size={14} />
              {t('app.client_channel_home.copy', { defaultValue: 'Копировать' })}
            </button>
          </div>
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.sources_qr', { defaultValue: 'QR-код' })}
            </p>
            <p className="mt-2 text-sm text-slate-600">
              {t('app.client_channel_home.qr_hint', { defaultValue: 'Для печати и офлайн-рекламы' })}
            </p>
            <button
              type="button"
              onClick={() => void downloadQr()}
              disabled={!publicUrl}
              className="mt-3 inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
            >
              <IconDownload size={14} />
              {t('app.client_channel_home.download_qr', { defaultValue: 'Скачать' })}
            </button>
          </div>
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.client_channel_home.inquiries_title', { defaultValue: 'Последние запросы' })}
            </p>
            <span className="text-xs text-slate-500">
              {loading
                ? t('common.loading')
                : t('app.client_channel_home.inquiries_count', {
                    defaultValue: '{count} запросов',
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
                    {t('app.client_channel_home.open_inquiry', { defaultValue: 'Открыть' })}
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-600">
              {t('app.client_channel_home.inquiries_empty', {
                defaultValue: 'Пока пусто. Как только компания оставит заявку — она появится здесь.',
              })}
            </p>
          )}
        </div>
      </section>

      {!hasInquiries && publicUrl ? (
        <section className="rounded-xl border border-brand-100 bg-brand-50/40 p-4 text-sm text-slate-700">
          <p className="font-medium text-slate-900">
            {t('app.sales_channel.share_hint_title', { defaultValue: 'Куда вставить ссылку' })}
          </p>
          <p className="mt-1">
            {t('app.sales_channel.share_hint_body', {
              defaultValue:
                'Реклама Meta или Google, сайт компании, email-подпись, QR на визитке. Компания откроет форму и оставит заявку — она появится здесь.',
            })}
          </p>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-600">
        <p className="font-medium text-slate-800">
          {t('app.client_channel_home.not_candidate_title', {
            defaultValue: 'Это не анкета для кандидатов',
          })}
        </p>
        <p className="mt-1">
          {t('app.client_channel_home.not_candidate_body', {
            defaultValue:
              'Эта ссылка ведёт компании на заявку о подборе персонала. Анкета для кандидатов — отдельный поток в Launchpad.',
          })}
        </p>
        <p className="mt-2 text-xs text-slate-500">{channelName}</p>
      </section>
    </div>
  )
}
