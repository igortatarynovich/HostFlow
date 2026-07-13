import { Link } from 'react-router-dom'
import { useToast } from '../Toast'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import { downloadQrPng } from '../../utils/clientInquiryUrl'

type ClientChannelReadyPanelProps = {
  channelId: string
  channelName: string
  publicUrl: string
}

export { clientAcquisitionChannelPath }

export function ClientChannelReadyPanel({ channelId, channelName, publicUrl }: ClientChannelReadyPanelProps) {
  const { notify } = useToast()

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(publicUrl)
      notify({ title: 'Ссылка скопирована', variant: 'success' })
    } catch {
      notify({ title: 'Не удалось скопировать', variant: 'error' })
    }
  }

  async function downloadQr() {
    try {
      await downloadQrPng(publicUrl, `hostflow-client-channel-${channelId.slice(0, 8)}.png`)
      notify({ title: 'QR скачан', variant: 'success' })
    } catch {
      notify({ title: 'Не удалось скачать QR', variant: 'error' })
    }
  }

  return (
    <div className="space-y-6" data-testid="m1-client-channel-ready">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Канал готов</h2>
        <p className="mt-2 text-sm text-slate-600">
          Скопируйте ссылку или QR и разместите там, где компании увидят предложение: реклама, сайт, email, визитка.
        </p>
      </div>

      <div className="space-y-4 rounded-xl border border-brand-100 bg-brand-50/40 p-5">
        <p className="text-sm font-medium text-slate-900">Ссылка для компаний</p>
        <p className="break-all text-xs text-slate-600">{publicUrl}</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="m1-client-channel-copy-link"
            onClick={() => void copyLink()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Копировать ссылку
          </button>
          <button
            type="button"
            data-testid="m1-client-channel-download-qr"
            onClick={() => void downloadQr()}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Скачать QR
          </button>
        </div>
      </div>

      <p className="text-sm text-slate-600">
        Когда компания оставит заявку, на рабочем столе появится «Следующее действие» — обычно «Позвонить».
      </p>

      <Link
        to={clientAcquisitionChannelPath(channelId)}
        data-testid="m1-client-channel-open"
        className="inline-flex w-full items-center justify-center rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
      >
        Открыть рабочий стол
      </Link>

      <p className="text-center text-xs text-slate-400">{channelName}</p>
    </div>
  )
}
