import { Link } from 'react-router-dom'
import { useToast } from '../Toast'
import { recruitmentSearchPath, recruitmentSearchAcquisitionPath } from '../../app/crmAppPaths'
import { downloadQrPng } from '../../utils/publicIntakeUrl'

type SearchReadyPanelProps = {
  searchId: string
  searchName: string
  publicUrl: string
}

export function SearchReadyPanel({ searchId, searchName, publicUrl }: SearchReadyPanelProps) {
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
      await downloadQrPng(publicUrl, `hostflow-search-${searchId.slice(0, 8)}.png`)
      notify({ title: 'QR скачан', variant: 'success' })
    } catch {
      notify({ title: 'Не удалось скачать QR', variant: 'error' })
    }
  }

  return (
    <div className="space-y-6" data-testid="m1-search-ready">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Подбор готов</h2>
        <p className="mt-2 text-sm text-slate-600">Скопируйте ссылку и запустите рекламу — кандидаты появятся в подборе.</p>
      </div>

      <div className="space-y-4 border-t border-slate-100 pt-4">
        <div>
          <p className="text-sm font-medium text-slate-900">Шаг 1</p>
          <p className="mt-1 text-sm text-slate-600">Скопируйте ссылку для кандидатов</p>
          <p className="mt-2 break-all text-xs text-slate-500">{publicUrl}</p>
          <button
            type="button"
            data-testid="m1-search-copy-link"
            onClick={() => void copyLink()}
            className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Копировать
          </button>
          <p className="mt-3 text-sm text-slate-500">или скачайте QR</p>
          <button
            type="button"
            data-testid="m1-search-download-qr"
            onClick={() => void downloadQr()}
            className="mt-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Скачать
          </button>
        </div>

        <div>
          <p className="text-sm font-medium text-slate-900">Шаг 2</p>
          <p className="mt-1 text-sm text-slate-600">Настройте источники привлечения — Meta, ссылка, QR</p>
          <div className="mt-3">
            <Link
              to={recruitmentSearchAcquisitionPath(searchId)}
              className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-medium text-brand-800 hover:bg-brand-100"
            >
              Добавить источник
            </Link>
          </div>
        </div>
      </div>

      <p className="text-sm text-slate-600">
        Вставьте ссылку в рекламу или отправьте кандидатам. Отклики появятся на странице подбора.
      </p>

      <Link
        to={recruitmentSearchPath(searchId)}
        data-testid="m1-search-open"
        className="inline-flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
      >
        Открыть подбор
      </Link>

      <p className="text-center text-xs text-slate-400">{searchName}</p>
    </div>
  )
}
