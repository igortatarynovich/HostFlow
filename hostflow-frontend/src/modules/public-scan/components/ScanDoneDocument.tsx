import { memo } from 'react'
import type { TranslateFn } from '@i18n'

type ScanDoneDocumentProps = {
  pdfUrl?: string | null
  onClose: () => void
  translate: TranslateFn
}

export const ScanDoneDocument = memo(function ScanDoneDocument({
  pdfUrl,
  onClose,
  translate,
}: ScanDoneDocumentProps) {
  return (
    <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-900">
            {translate('public.scan.status.done_document', 'Документ готов')}
          </p>
          {pdfUrl && (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-brand-700 underline"
            >
              {translate('public.scan.actions.open_pdf', 'Открыть PDF')}
            </a>
          )}
        </div>
        <div className="flex gap-2">
          {pdfUrl && (
            <a
              href={pdfUrl}
              download
              className="min-h-[44px] rounded-full border border-emerald-200 bg-white px-4 py-2 text-sm font-semibold text-emerald-700 active:scale-95"
            >
              {translate('public.scan.viewer.download', 'Скачать PDF')}
            </a>
          )}
          <button
            type="button"
            className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
            onClick={onClose}
          >
            {translate('public.scan.actions.done', 'Готово / Вернуться')}
          </button>
        </div>
      </div>
    </div>
  )
})

