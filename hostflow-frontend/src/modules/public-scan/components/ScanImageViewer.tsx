import { memo } from 'react'
import type { TranslateFn } from '@i18n'

type ScanImageViewerProps = {
  image: { url: string; pageCode: string; label: string } | null
  onClose: () => void
  translate: TranslateFn
  onImageError?: (e: React.SyntheticEvent<HTMLImageElement, Event>) => void
}

export const ScanImageViewer = memo(function ScanImageViewer({
  image,
  onClose,
  translate,
  onImageError,
}: ScanImageViewerProps) {
  if (!image) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black" onClick={onClose}>
      {/* Mobile header */}
      <div className="flex items-center justify-between border-b border-white/10 bg-black/80 px-4 py-3 sm:hidden">
        <h3 className="text-base font-semibold text-white">{image.label}</h3>
        <button
          type="button"
          onClick={onClose}
          className="rounded-full bg-white/20 p-2 text-white active:bg-white/30"
          aria-label={translate('public.scan.viewer.close', 'Close')}
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Image container */}
      <div
        className="flex flex-1 items-center justify-center overflow-auto p-2 sm:p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative w-full max-w-full">
          {/* Desktop close button */}
          <button
            type="button"
            onClick={onClose}
            className="absolute -right-2 -top-2 z-10 hidden rounded-full bg-white p-2 shadow-lg transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-white sm:block"
            aria-label={translate('public.scan.viewer.close', 'Close')}
          >
            <svg className="h-6 w-6 text-slate-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>

          {/* Image wrapper */}
          <div className="rounded-lg bg-white p-2 shadow-2xl sm:p-4">
            {/* Desktop header */}
            <div className="mb-3 hidden text-center sm:block">
              <h3 className="text-lg font-semibold text-slate-900">{image.label}</h3>
              <p className="text-xs text-slate-500">
                {translate('public.scan.viewer.processed', 'Processed image')}
              </p>
            </div>

            {/* Image */}
            <div className="max-h-[calc(100vh-200px)] max-w-[95vw] overflow-auto rounded-lg border border-slate-200 sm:max-h-[80vh] sm:max-w-[90vw]">
              <img
                src={image.url}
                alt={image.label}
                className="h-auto w-full object-contain"
                onError={onImageError}
              />
            </div>

            {/* Action buttons */}
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:justify-center">
              <a
                href={image.url}
                download
                className="min-h-[44px] flex items-center justify-center gap-2 rounded-full border border-brand-200 bg-white px-4 py-2.5 text-sm font-medium text-brand-700 active:scale-95 active:bg-brand-50 sm:min-h-[auto] sm:py-2"
                onClick={(e) => e.stopPropagation()}
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                {translate('public.scan.viewer.download', 'Download')}
              </a>
              <button
                type="button"
                onClick={onClose}
                className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white active:scale-95 active:bg-brand-700 sm:min-h-[auto] sm:py-2"
              >
                {translate('public.scan.viewer.close', 'Close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
})

