import { memo } from 'react'
import type { TranslateFn } from '@i18n'

type ScanDonePageProps = {
  pendingStepsCount: number
  onAddPage: () => void
  onFinish: () => void
  translate: TranslateFn
}

export const ScanDonePage = memo(function ScanDonePage({
  pendingStepsCount,
  onAddPage,
  onFinish,
  translate,
}: ScanDonePageProps) {
  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {translate('public.scan.status.done_page', 'Страница сохранена')}
          </p>
          <p className="text-xs text-slate-500">
            {pendingStepsCount > 0
              ? translate('public.scan.status.more_pages', 'Осталось страниц: {count}', {
                  count: pendingStepsCount,
                })
              : translate('public.scan.status.all_pages', 'Все страницы добавлены')}
          </p>
        </div>
        <div className="flex gap-2">
          {pendingStepsCount > 0 && (
            <button
              type="button"
              className="min-h-[44px] rounded-full border border-brand-200 bg-white px-4 py-2 text-sm font-semibold text-brand-700 active:scale-95"
              onClick={onAddPage}
            >
              {translate('public.scan.actions.add_page', 'Добавить страницу')}
            </button>
          )}
          <button
            type="button"
            className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
            onClick={onFinish}
          >
            {translate('public.scan.actions.finish_doc', 'Завершить документ')}
          </button>
        </div>
      </div>
    </div>
  )
})

