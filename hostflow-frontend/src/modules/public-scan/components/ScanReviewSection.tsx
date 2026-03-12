import { memo } from 'react'
import type { TranslateFn } from '@i18n'

type ScanReviewSectionProps = {
  image: { url: string; pageCode: string; label: string } | null
  activePageCode: string
  onEditContour: () => void
  onReshoot: () => void
  onConfirm: () => void
  translate: TranslateFn
}

export const ScanReviewSection = memo(function ScanReviewSection({
  image,
  activePageCode,
  onEditContour,
  onReshoot,
  onConfirm,
  translate,
}: ScanReviewSectionProps) {
  if (!image) return null

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-900">
            {translate('public.scan.viewer.processed', 'Обработанный результат')}
          </p>
          <div className="mt-2 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            <img
              src={image.url}
              alt={image.label}
              className="max-h-[50vh] w-full object-contain"
            />
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:w-48">
          <button
            type="button"
            className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 active:scale-95"
            onClick={onEditContour}
          >
            {translate('public.scan.actions.edit_contour', 'Исправить границы')}
          </button>
          <button
            type="button"
            className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 active:scale-95"
            onClick={onReshoot}
          >
            {translate('public.scan.actions.reshoot', 'Переснять страницу')}
          </button>
          <button
            type="button"
            className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
            onClick={onConfirm}
          >
            {translate('public.scan.actions.finish_doc', 'Подтвердить страницу')}
          </button>
        </div>
      </div>
    </div>
  )
})

