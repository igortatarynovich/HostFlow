/**
 * Modal wrapper for contour editor
 */

import { useState } from 'react'
import { ContourEditor, type Contour6Points } from '../../modules/public-intake/scan/contourEditor'

type ContourEditorModalProps = {
  imageUrl: string
  initialContour?: Contour6Points | null
  onConfirm: (contour: Contour6Points) => void
  onCancel: () => void
  loading?: boolean
}

export function ContourEditorModal({
  imageUrl,
  initialContour,
  onConfirm,
  onCancel,
  loading = false,
}: ContourEditorModalProps) {
  const [contour, setContour] = useState<Contour6Points | null>(initialContour || null)
  
  const validateContour = (c: Contour6Points): { valid: boolean; errors: string[] } => {
    const errors: string[] = []
    
    // Check minimum size
    const points = [c.p1, c.p2, c.p3, c.p4, c.p5, c.p6]
    const minX = Math.min(...points.map(p => p.x))
    const maxX = Math.max(...points.map(p => p.x))
    const minY = Math.min(...points.map(p => p.y))
    const maxY = Math.max(...points.map(p => p.y))
    
    const width = maxX - minX
    const height = maxY - minY
    
    if (width < 50 || height < 50) {
      errors.push('Документ слишком маленький (минимум 50px)')
    }
    
    return {
      valid: errors.length === 0,
      errors,
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/80 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-white/10 bg-black/40 px-4 py-3">
        <h3 className="text-lg font-semibold text-white">Редактирование контура (6 точек)</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-white hover:bg-white/20"
          >
            Закрыть
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              const c = contour
              if (!c) {
                onCancel()
                return
              }
              const validation = validateContour(c)
              if (!validation.valid) {
                console.warn('[ContourEditorModal] Validation errors:', validation.errors)
              }
              onConfirm(c)
            }}
            className="rounded-full bg-emerald-500 px-4 py-1 text-sm font-semibold text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {loading ? 'Поиск…' : 'Применить'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-2 sm:p-4">
        <div className="mx-auto max-w-5xl rounded-xl bg-slate-900/40 p-2 shadow-xl">
          <ContourEditor
            imageUrl={imageUrl}
            initialContour={initialContour}
            onContourChange={setContour}
            onValidate={validateContour}
            snapToEdge={true}
            snapDistance={10}
            disabled={loading}
            onClose={onCancel}
            onConfirm={(c) => {
              if (c) {
                const validation = validateContour(c)
                if (!validation.valid) {
                  console.warn('[ContourEditorModal] Contour validation errors:', validation.errors)
                }
                onConfirm(c)
              } else if (contour) {
                onConfirm(contour)
              } else {
                onCancel?.()
              }
            }}
          />
        </div>
      </div>
    </div>
  )
}
