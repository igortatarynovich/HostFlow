/**
 * Preview modal with filter selection and re-edit option
 */

import { useState, useEffect } from 'react'
import { ContourEditorModal } from './ContourEditorModal'
import type { Contour6Points } from '../../modules/public-intake/scan/contourEditor'

type EnhancementFilter = 'standard' | 'strong' | 'photo'

type PreviewModalProps = {
  imageUrl: string
  onConfirm: (filter: EnhancementFilter, contour: Contour6Points | null) => void
  onRetake: () => void
  initialContour?: Contour6Points | null
  uploading?: boolean
}

export function PreviewModal({
  imageUrl,
  onConfirm,
  onRetake,
  initialContour,
  uploading = false,
}: PreviewModalProps) {
  const [selectedFilter, setSelectedFilter] = useState<EnhancementFilter>('standard')
  const [showContourEditor, setShowContourEditor] = useState(false)
  const [contour, setContour] = useState<Contour6Points | null>(initialContour || null)
  
  // Update contour when initialContour changes
  useEffect(() => {
    if (initialContour) {
      setContour(initialContour)
    }
  }, [initialContour])
  
  // DEBUG: Log when filter changes
  useEffect(() => {
    console.log('[PreviewModal] Filter changed to:', selectedFilter)
  }, [selectedFilter])
  
  // DEBUG: Log when contour changes
  useEffect(() => {
    console.log('[PreviewModal] Contour changed:', contour ? 'present' : 'null')
  }, [contour])

  const filters: Array<{ key: EnhancementFilter; label: string; description: string }> = [
    {
      key: 'standard',
      label: 'Стандартный',
      description: 'Автоконтраст, шумоподавление',
    },
    {
      key: 'strong',
      label: 'Черно-белый',
      description: 'Бинаризация для документов',
    },
    {
      key: 'photo',
      label: 'Фото',
      description: 'Для фото и ID карт',
    },
  ]

  return (
    <>
      <div className="fixed inset-0 z-50 flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 bg-black/40 px-4 py-4 backdrop-blur-sm">
          <h2 className="text-xl font-bold text-white">Предпросмотр документа</h2>
          <button
            onClick={onRetake}
            disabled={uploading}
            className="rounded-full bg-white/10 p-2 text-white transition hover:bg-white/20 disabled:opacity-50"
            aria-label="Закрыть"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <div className="mx-auto max-w-4xl p-4 sm:p-6">
            {/* Image preview */}
            <div className="mb-6 overflow-hidden rounded-2xl border-2 border-white/20 bg-black/40 shadow-2xl">
              <img
                src={imageUrl}
                alt="Document preview"
                className="h-auto w-full object-contain"
              />
            </div>

            {/* Filter selection */}
            <div className="mb-6">
              <h3 className="mb-3 text-lg font-semibold text-white">Выберите режим обработки</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                {filters.map((filter) => (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={() => {
                      console.log('[PreviewModal] Filter button clicked:', filter.key)
                      setSelectedFilter(filter.key)
                    }}
                    disabled={uploading}
                    className={`rounded-xl border-2 p-4 text-left transition-all ${
                      selectedFilter === filter.key
                        ? 'border-emerald-400 bg-emerald-500/20 shadow-lg shadow-emerald-500/20'
                        : 'border-white/20 bg-white/5 hover:border-white/30 hover:bg-white/10'
                    } disabled:opacity-50`}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <span className="font-semibold text-white">{filter.label}</span>
                      {selectedFilter === filter.key && (
                        <svg className="h-5 w-5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                    <p className="text-sm text-white/70">{filter.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer with actions */}
        <div className="border-t border-white/10 bg-black/40 px-4 py-4 backdrop-blur-sm">
          <div className="mx-auto flex max-w-4xl flex-col gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => {
                console.log('[PreviewModal] Retake button clicked')
                onRetake()
              }}
              disabled={uploading}
              className="min-h-[48px] rounded-full border-2 border-white/30 bg-white/10 px-6 py-3 text-base font-medium text-white transition hover:bg-white/20 disabled:opacity-50 sm:min-h-[auto] sm:py-2"
            >
              Переснять
            </button>
            <button
              type="button"
              onClick={() => setShowContourEditor(true)}
              disabled={uploading}
              className="min-h-[48px] rounded-full border-2 border-white/30 bg-white/10 px-6 py-3 text-base font-medium text-white transition hover:bg-white/20 disabled:opacity-50 sm:min-h-[auto] sm:py-2"
            >
              Редактировать контур
            </button>
            <button
              type="button"
              onClick={() => {
                console.log('[scanner] PreviewModal: Send button clicked', { filter: selectedFilter, contour: contour ? 'present' : 'null' })
                onConfirm(selectedFilter, contour)
              }}
              disabled={uploading}
              className="min-h-[48px] rounded-full bg-gradient-to-r from-emerald-500 to-emerald-600 px-8 py-3 text-base font-semibold text-white shadow-lg shadow-emerald-500/30 transition hover:from-emerald-600 hover:to-emerald-700 disabled:opacity-50 sm:min-h-[auto] sm:py-2"
            >
              {uploading ? 'Отправка...' : 'Отправить'}
            </button>
          </div>
        </div>
      </div>

      {/* Contour editor modal */}
      {showContourEditor && (
        <ContourEditorModal
          imageUrl={imageUrl}
          initialContour={contour}
          onConfirm={(newContour) => {
            setContour(newContour)
            setShowContourEditor(false)
          }}
          onCancel={() => setShowContourEditor(false)}
        />
      )}
    </>
  )
}

