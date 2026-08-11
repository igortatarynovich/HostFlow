import { Link } from 'react-router-dom'
import { useToast } from '../Toast'
import { recruitmentSearchPath, recruitmentSearchAcquisitionPath } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { downloadQrPng } from '../../utils/publicIntakeUrl'

type SearchReadyPanelProps = {
  searchId: string
  searchName: string
  publicUrl: string
}

export function SearchReadyPanel({ searchId, searchName, publicUrl }: SearchReadyPanelProps) {
  const { notify } = useToast()
  const { t } = useI18n()

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(publicUrl)
      notify({
        title: t('app.search_ready.link_copied', { defaultValue: 'Link copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.search_ready.link_copy_failed', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  async function downloadQr() {
    try {
      await downloadQrPng(publicUrl, `hostflow-search-${searchId.slice(0, 8)}.png`)
      notify({
        title: t('app.search_ready.qr_downloaded', { defaultValue: 'QR downloaded' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.search_ready.qr_download_failed', { defaultValue: 'Could not download QR' }),
        variant: 'error',
      })
    }
  }

  return (
    <div className="space-y-6" data-testid="m1-search-ready">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">
          {t('app.search_ready.title', { defaultValue: 'Search is ready' })}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.search_ready.body', {
            defaultValue: 'Copy the link and launch ads — candidates will appear in the search.',
          })}
        </p>
      </div>

      <div className="space-y-4 border-t border-slate-100 pt-4">
        <div>
          <p className="text-sm font-medium text-slate-900">
            {t('app.search_ready.step1', { defaultValue: 'Step 1' })}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.search_ready.step1_body', { defaultValue: 'Copy the candidate link' })}
          </p>
          <p className="mt-2 break-all text-xs text-slate-500">{publicUrl}</p>
          <button
            type="button"
            data-testid="m1-search-copy-link"
            onClick={() => void copyLink()}
            className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t('app.search_ready.copy', { defaultValue: 'Copy' })}
          </button>
          <p className="mt-3 text-sm text-slate-500">
            {t('app.search_ready.or_qr', { defaultValue: 'or download QR' })}
          </p>
          <button
            type="button"
            data-testid="m1-search-download-qr"
            onClick={() => void downloadQr()}
            className="mt-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t('app.search_ready.download', { defaultValue: 'Download' })}
          </button>
        </div>

        <div>
          <p className="text-sm font-medium text-slate-900">
            {t('app.search_ready.step2', { defaultValue: 'Step 2' })}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {t('app.search_ready.step2_body', {
              defaultValue: 'Set up acquisition sources — Meta, link, QR',
            })}
          </p>
          <div className="mt-3">
            <Link
              to={recruitmentSearchAcquisitionPath(searchId)}
              className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-medium text-brand-800 hover:bg-brand-100"
            >
              {t('app.search_ready.add_source', { defaultValue: 'Add source' })}
            </Link>
          </div>
        </div>
      </div>

      <p className="text-sm text-slate-600">
        {t('app.search_ready.hint', {
          defaultValue:
            'Paste the link into ads or send it to candidates. Responses will appear on the search page.',
        })}
      </p>

      <Link
        to={recruitmentSearchPath(searchId)}
        data-testid="m1-search-open"
        className="inline-flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
      >
        {t('app.search_ready.open', { defaultValue: 'Open search' })}
      </Link>

      <p className="text-center text-xs text-slate-400">{searchName}</p>
    </div>
  )
}
