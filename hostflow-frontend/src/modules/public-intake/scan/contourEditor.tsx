/**
 * 6-point contour editor component
 * Allows manual adjustment of document contour points
 */

import { useState, useCallback, useRef, useEffect } from 'react'

export type ContourPoint = {
  x: number
  y: number
  id: number
}

export type Contour6Points = {
  p1: ContourPoint // top-left corner
  p2: ContourPoint // top-right corner
  p3: ContourPoint // right center
  p4: ContourPoint // bottom-right corner
  p5: ContourPoint // bottom-left corner
  p6: ContourPoint // left center
}

type ContourEditorProps = {
  imageUrl: string
  initialContour?: Contour6Points | null
  onContourChange: (contour: Contour6Points) => void
  onValidate: (contour: Contour6Points) => { valid: boolean; errors: string[] }
  snapToEdge?: boolean
  snapDistance?: number
  onClose?: () => void
  onConfirm?: (contour: Contour6Points) => void
}

export function ContourEditor({
  imageUrl,
  initialContour,
  onContourChange,
  onValidate,
  snapToEdge = true,
  snapDistance = 10,
  onClose,
  onConfirm,
}: ContourEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [contour, setContour] = useState<Contour6Points | null>(initialContour || null)
  const [draggingPoint, setDraggingPoint] = useState<number | null>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const initializedRef = useRef<boolean>(false) // Track if contour was initialized
  const [loading, setLoading] = useState<boolean>(true)
  const [imageSize, setImageSize] = useState<{ width: number; height: number }>({ width: 0, height: 0 })
  const overlayRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number | null>(null)
  const pendingUpdateRef = useRef<{ x: number; y: number } | null>(null)
  // Removed unused zoom and pan states

  const drawContour = useCallback((ctx: CanvasRenderingContext2D, c: Contour6Points) => {
    const points = [c.p1, c.p2, c.p3, c.p4, c.p5, c.p6]

    // Overlay darkened area outside contour
    ctx.save()
    ctx.fillStyle = 'rgba(0, 0, 0, 0.45)'
    ctx.beginPath()
    ctx.rect(0, 0, imageSize.width, imageSize.height)
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.closePath()
    ctx.fill('evenodd')
    ctx.restore()

    // Gradient contour for visibility
    const grad = ctx.createLinearGradient(points[0].x, points[0].y, points[2].x, points[2].y)
    grad.addColorStop(0, '#22d3ee')
    grad.addColorStop(1, '#22c55e')
    ctx.strokeStyle = grad
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.closePath()
    ctx.stroke()

    // Points
    points.forEach((p) => {
      ctx.fillStyle = draggingPoint === p.id ? '#f97316' : '#22d3ee'
      ctx.beginPath()
      ctx.arc(p.x, p.y, 9, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2
      ctx.stroke()
    })
  }, [draggingPoint, imageSize.height, imageSize.width])

  // Initialize contour and load image - combined to avoid infinite loops
  useEffect(() => {
    if (initializedRef.current) return
    const img = new Image()
    img.onload = () => {
      setImageSize({ width: img.naturalWidth, height: img.naturalHeight })
      if (initialContour) {
        setContour(initialContour)
      } else {
        const w = img.naturalWidth
        const h = img.naturalHeight
        const defaultContour: Contour6Points = {
          p1: { x: w * 0.1, y: h * 0.1, id: 1 },
          p2: { x: w * 0.9, y: h * 0.1, id: 2 },
          p3: { x: w * 0.9, y: h * 0.5, id: 3 },
          p4: { x: w * 0.9, y: h * 0.9, id: 4 },
          p5: { x: w * 0.1, y: h * 0.9, id: 5 },
          p6: { x: w * 0.1, y: h * 0.5, id: 6 },
        }
        setContour(defaultContour)
      }
      initializedRef.current = true
      setLoading(false)
    }
    img.src = imageUrl
  }, [imageUrl, initialContour])

  // Separate effect to draw/redraw when contour or image changes
  useEffect(() => {
    if (!canvasRef.current || !contour) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Only draw if canvas has dimensions (image loaded)
    if (canvas.width === 0 || canvas.height === 0) return

    // Redraw image and contour
    const img = new Image()
    img.onload = () => {
      ctx.drawImage(img, 0, 0)
      drawContour(ctx, contour)
    }
    img.src = imageUrl
  }, [contour, imageUrl]) // Redraw when contour changes

  const handlePointerDown = useCallback(
    (clientX: number, clientY: number, rect: DOMRect) => {
      if (!contour) return
      const x = (clientX - rect.left) * (imageSize.width / rect.width)
      const y = (clientY - rect.top) * (imageSize.height / rect.height)

      // Find closest point (tolerate 30px to make grabbing easy)
      const points = [contour.p1, contour.p2, contour.p3, contour.p4, contour.p5, contour.p6]
      let minDist = Infinity
      let closestIdx = -1

      for (let i = 0; i < points.length; i++) {
        const dist = Math.sqrt((x - points[i].x) ** 2 + (y - points[i].y) ** 2)
        if (dist < minDist && dist < 30) {
          minDist = dist
          closestIdx = i
        }
      }

      if (closestIdx >= 0) {
        setDraggingPoint(points[closestIdx].id)
        if ('vibrate' in navigator) {
          // haptic feedback on grab
          try {
            navigator.vibrate?.(10)
          } catch (_) {
            // ignore
          }
        }
      }
    },
    [contour, imageSize.height, imageSize.width],
  )
  const updatePoint = useCallback(
    (clientX: number, clientY: number, rect: DOMRect) => {
      if (!contour || draggingPoint === null) return

      let x = (clientX - rect.left) * (imageSize.width / rect.width)
      let y = (clientY - rect.top) * (imageSize.height / rect.height)

      // Snap to edges if enabled
      if (snapToEdge) {
        if (Math.abs(x) < snapDistance) x = 0
        if (Math.abs(x - imageSize.width) < snapDistance) x = imageSize.width
        if (Math.abs(y) < snapDistance) y = 0
        if (Math.abs(y - imageSize.height) < snapDistance) y = imageSize.height
      }
      // Clamp to image bounds with soft margins (5%)
      const marginX = imageSize.width * 0.05
      const marginY = imageSize.height * 0.05
      x = Math.min(Math.max(x, marginX), imageSize.width - marginX)
      y = Math.min(Math.max(y, marginY), imageSize.height - marginY)

      // Defer updates to next animation frame + simple smoothing
      pendingUpdateRef.current = { x, y }
      if (rafRef.current) return
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null
        const pending = pendingUpdateRef.current
        pendingUpdateRef.current = null
        if (!pending || !contour || draggingPoint === null) return

        const updatedContour = { ...contour }
        const pointKey = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'][draggingPoint - 1] as keyof Contour6Points
        const current = updatedContour[pointKey]
        let smoothed = {
          x: current.x + (pending.x - current.x) * 0.3,
          y: current.y + (pending.y - current.y) * 0.3,
        }
        // Enforce minimum document size (40% of frame)
        const minW = imageSize.width * 0.4
        const minH = imageSize.height * 0.4
        const draft = { ...updatedContour, [pointKey]: { ...updatedContour[pointKey], ...smoothed } }
        const boxPoints = [draft.p1, draft.p2, draft.p3, draft.p4, draft.p5, draft.p6]
        const minBoxX = Math.min(...boxPoints.map((p) => p.x))
        const maxBoxX = Math.max(...boxPoints.map((p) => p.x))
        const minBoxY = Math.min(...boxPoints.map((p) => p.y))
        const maxBoxY = Math.max(...boxPoints.map((p) => p.y))
        let width = maxBoxX - minBoxX
        let height = maxBoxY - minBoxY
        if (width < minW || height < minH) {
          const cx = (minBoxX + maxBoxX) / 2
          const cy = (minBoxY + maxBoxY) / 2
          const halfW = Math.max(minW / 2, width / 2)
          const halfH = Math.max(minH / 2, height / 2)
          // Clamp smoothed point to preserve min size around center
          smoothed = {
            x: Math.min(Math.max(smoothed.x, cx - halfW), cx + halfW),
            y: Math.min(Math.max(smoothed.y, cy - halfH), cy + halfH),
          }
        }
        updatedContour[pointKey] = { ...updatedContour[pointKey], ...smoothed }

        setContour(updatedContour)
        onContourChange(updatedContour)

        const validation = onValidate(updatedContour)
        setValidationErrors(validation.errors)
      })
    },
    [contour, draggingPoint, snapToEdge, snapDistance, onContourChange, onValidate, imageSize.width, imageSize.height],
  )

  // Pointer handlers with capture so dragging continues outside overlay
  const handlePointerDownEvent = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!overlayRef.current) return
      const rect = overlayRef.current.getBoundingClientRect()
      handlePointerDown(e.clientX, e.clientY, rect)
    },
    [handlePointerDown],
  )

  const handlePointerMoveEvent = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (draggingPoint === null) return
      if (!overlayRef.current) return
      updatePoint(e.clientX, e.clientY, overlayRef.current.getBoundingClientRect())
    },
    [updatePoint, draggingPoint],
  )

  const handlePointerUpEvent = useCallback(() => {
    setDraggingPoint(null)
  }, [])

  const handleReset = useCallback(() => {
    if (imageSize.width && imageSize.height) {
      const defaultContour: Contour6Points = {
        p1: { x: imageSize.width * 0.1, y: imageSize.height * 0.1, id: 1 },
        p2: { x: imageSize.width * 0.9, y: imageSize.height * 0.1, id: 2 },
        p3: { x: imageSize.width * 0.9, y: imageSize.height * 0.5, id: 3 },
        p4: { x: imageSize.width * 0.9, y: imageSize.height * 0.9, id: 4 },
        p5: { x: imageSize.width * 0.1, y: imageSize.height * 0.9, id: 5 },
        p6: { x: imageSize.width * 0.1, y: imageSize.height * 0.5, id: 6 },
      }
      setContour(defaultContour)
      onContourChange(defaultContour)
    }
  }, [onContourChange, imageSize.height, imageSize.width])

  if (!contour) {
    return (
      <div className="flex h-full items-center justify-center text-white">
        {loading ? 'Загрузка изображения…' : 'Контур недоступен'}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/90">
      {/* Mobile-optimized header */}
      <div className="flex items-center justify-between border-b border-white/10 bg-black/80 px-4 py-3">
        <h2 className="text-lg font-semibold text-white">Подправьте контур документа</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-full bg-white/20 p-2 text-white active:bg-white/30"
            aria-label="Закрыть"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Canvas area - full screen on mobile */}
      <div className="flex-1 overflow-auto p-2 sm:p-4">
        <div className="relative mx-auto max-w-4xl">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-slate-900/80 text-white">
              Загрузка изображения…
            </div>
          )}
          <canvas
            ref={canvasRef}
            className="w-full max-h-[calc(100vh-200px)] border border-white/20 rounded-lg bg-white"
            style={{ display: 'none' }}
          />
          {imageSize.width > 0 && (
            <div
              className="relative w-full max-h-[calc(100vh-200px)]"
              style={{ touchAction: 'none' }}
              ref={overlayRef}
              onPointerDown={handlePointerDownEvent}
              onPointerMove={handlePointerMoveEvent}
              onPointerUp={handlePointerUpEvent}
              onPointerCancel={handlePointerUpEvent}
            >
              <img
                src={imageUrl}
                alt="Документ"
                className="w-full h-auto rounded-lg pointer-events-none select-none"
                draggable={false}
              />
              {contour && (
                <svg
                  className="absolute inset-0 w-full h-full"
                  viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
                  preserveAspectRatio="xMidYMid meet"
                >
                  <path
                    d={`M ${contour.p1.x} ${contour.p1.y} L ${contour.p2.x} ${contour.p2.y} L ${contour.p3.x} ${contour.p3.y} L ${contour.p4.x} ${contour.p4.y} L ${contour.p5.x} ${contour.p5.y} L ${contour.p6.x} ${contour.p6.y} Z`}
                    fill="rgba(16,185,129,0.15)"
                    stroke="#10b981"
                    strokeWidth={4}
                    pointerEvents="none"
                  />
                  {[contour.p1, contour.p2, contour.p3, contour.p4, contour.p5, contour.p6].map((p, idx) => (
                    <circle
                      key={p.id}
                      cx={p.x}
                      cy={p.y}
                      r={18}
                      fill="rgba(16,185,129,0.9)"
                      stroke="#fff"
                      strokeWidth={3}
                      className="pointer-events-auto"
                      onPointerDown={(e) => {
                        e.stopPropagation()
                        e.preventDefault()
                        if (overlayRef.current) {
                          overlayRef.current.setPointerCapture(e.pointerId)
                        }
                        // Directly set dragging point to this circle id for deterministic drag start
                        setDraggingPoint(p.id)
                        const parentRect =
                          (e.currentTarget.ownerSVGElement as SVGSVGElement | null)?.getBoundingClientRect() ||
                          overlayRef.current?.getBoundingClientRect()
                        if (!parentRect) return
                        updatePoint(e.clientX, e.clientY, parentRect)
                      }}
                    />
                  ))}
                </svg>
              )}
            </div>
          )}

          {validationErrors.length > 0 && (
            <div className="mt-2 rounded-lg bg-red-500/90 p-3 text-sm text-white">
              {validationErrors.map((err, idx) => (
                <div key={idx}>• {err}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Mobile-optimized footer */}
      <div className="border-t border-white/10 bg-black/80 px-4 py-3">
        <div className="mx-auto max-w-4xl flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            onClick={handleReset}
            className="min-h-[48px] rounded-full border-2 border-white/30 bg-white/10 px-6 py-3 text-base font-medium text-white active:bg-white/20 sm:min-h-[auto] sm:py-2"
          >
            Сбросить
          </button>
          <button
            onClick={() => {
              if (contour) {
                const validation = onValidate(contour)
                setValidationErrors(validation.errors)
                // Даже при предупреждениях отправляем контур
                onConfirm?.(contour)
              }
            }}
            className="min-h-[48px] rounded-full bg-emerald-500 px-6 py-3 text-base font-semibold text-white shadow-lg active:bg-emerald-600 sm:min-h-[auto] sm:py-2"
          >
            Готово
          </button>
        </div>
      </div>
    </div>
  )
}
