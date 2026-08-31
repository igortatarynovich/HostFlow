import { Link } from 'react-router-dom'
import { useToast } from '../Toast'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import { downloadQrPng } from '../../utils/clientInquiryUrl'
import { useI18n } from '../../i18n'

type ClientChannelReadyPanelProps = {
  channelId: string
  channelName: string
  publicUrl: string
}

export { clientAcquisitionChannelPath }

export function ClientChannelReadyPanel({ channelId, channelName, publicUrl }: ClientChannelReadyPanelProps) {
  const { notify } = useToast()
  const { t } = useI18n()

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(publicUrl)
      notify({ title: t('app.client_acquisition.channel_ready.copied'), variant: 'success' })
    } catch {
      notify({ title: t('app.client_acquisition.channel_ready.copy_failed'), variant: 'error' })
    }
  }

  async function downloadQr() {
    try {
      await downloadQrPng(publicUrl, `hostflow-client-channel-${channelId.slice(0, 8)}.png`)
      notify({ title: t('app.client_acquisition.channel_ready.qr_downloaded'), variant: 'success' })
    } catch {
      notify({ title: t('app.client_acquisition.channel_ready.qr_failed'), variant: 'error' })
    }
  }

  return (
    <div className="space-y-6" data-testid="m1-client-channel-ready">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">{t('app.client_acquisition.channel_ready.title')}</h2>
        <p className="mt-2 text-sm text-slate-600">{t('app.client_acquisition.channel_ready.subtitle')}</p>
      </div>

      <div className="space-y-4 rounded-xl border border-brand-100 bg-brand-50/40 p-4">
        <p className="text-sm font-medium text-slate-900">{t('app.client_acquisition.channel_ready.link_label')}</p>
        <p className="break-all text-xs text-slate-600">{publicUrl}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="m1-client-channel-copy-link"
            onClick={() => void copyLink()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t('app.client_acquisition.channel_ready.copy')}
          </button>
          <button
            type="button"
            data-testid="m1-client-channel-download-qr"
            onClick={() => void downloadQr()}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.client_acquisition.channel_ready.download_qr')}
          </button>
        </div>
      </div>

      <p className="text-sm text-slate-600">{t('app.client_acquisition.channel_ready.next_hint')}</p>

      <Link
        to={clientAcquisitionChannelPath(channelId)}
        data-testid="m1-client-channel-open"
        className="inline-flex w-full items-center justify-center rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
      >
        {t('app.client_acquisition.channel_ready.open')}
      </Link>

      <p className="text-center text-xs text-slate-400">{channelName}</p>
    </div>
  )
}
