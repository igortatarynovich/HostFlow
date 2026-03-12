import { useState } from 'react'
import type { Contour6Points } from '../../modules/public-intake/scan/contourEditor'

type PreviewModalProps = {
  imageUrl: string
  initialContour: Contour6Points | null
  uploading: boolean
  onRetake: () => void
  onConfirm: (filter: 'standard' | 'strong' | 'photo', contour: Contour6Points | null) => void
}

export function PreviewModal({ imageUrl, initialContour, uploading, onRetake, onConfirm }: PreviewModalProps) {
  const [filter, setFilter] = useState<'standard' | 'strong' | 'photo'>('standard')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-6">
      <div className="w-full max-w-4xl rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="text-lg font-semibold text-slate-900">Предпросмотр</h3>
          <button
            type="button"
            onClick={onRetake}
            className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-200"
          >
            Переснять
          </button>
        </div>
        <div className="grid gap-4 p-4 md:grid-cols-[2fr_1fr]">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
            <img src={imageUrl} alt="preview" className="w-full object-contain" />
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-800 mb-2">Фильтр</p>
              <div className="flex flex-col gap-2">
                {(['standard', 'strong', 'photo'] as const).map((f) => (
                  <label key={f} className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="radio"
                      name="filter"
                      value={f}
                      checked={filter === f}
                      onChange={() => setFilter(f)}
                    />
                    {f}
                  </label>
                ))}
              </div>
            </div>
            <div className="mt-auto flex gap-2">
              <button
                type="button"
                onClick={() => onConfirm(filter, initialContour)}
                disabled={uploading}
                className="flex-1 rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                {uploading ? 'Отправка...' : 'Отправить'}
              </button>
              <button
                type="button"
                onClick={onRetake}
                className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-800"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
