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
  // Removed unused zoom and pan states

  const drawContour = useCallback((ctx: CanvasRenderingContext2D, c: Contour6Points) => {
    const points = [c.p1, c.p2, c.p3, c.p4, c.p5, c.p6]

    // Draw filled mask (semi-transparent)
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.closePath()
    ctx.fill()

    // Draw contour lines
    ctx.strokeStyle = '#10b981'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    ctx.closePath()
    ctx.stroke()

    // Draw points
    points.forEach((p, idx) => {
      ctx.fillStyle = draggingPoint === p.id ? '#ef4444' : '#10b981'
      ctx.beginPath()
      ctx.arc(p.x, p.y, 8, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()

      // Label
      ctx.fillStyle = '#fff'
      ctx.font = '12px sans-serif'
      ctx.fillText(`P${p.id}`, p.x + 10, p.y - 10)
    })
  }, [draggingPoint])

  // Initialize contour and load image - combined to avoid infinite loops
  useEffect(() => {
    if (!canvasRef.current || initializedRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = new Image()
    img.onload = () => {
      // Set canvas size only once
      canvas.width = img.width
      canvas.height = img.height
      
      // Initialize contour only once - use initialContour prop directly
      if (initialContour) {
        setContour(initialContour)
      } else {
        // Create default 6-point contour from image bounds
        const defaultContour: Contour6Points = {
          p1: { x: img.width * 0.1, y: img.height * 0.1, id: 1 },
          p2: { x: img.width * 0.9, y: img.height * 0.1, id: 2 },
          p3: { x: img.width * 0.9, y: img.height * 0.5, id: 3 },
          p4: { x: img.width * 0.9, y: img.height * 0.9, id: 4 },
          p5: { x: img.width * 0.1, y: img.height * 0.9, id: 5 },
          p6: { x: img.width * 0.1, y: img.height * 0.5, id: 6 },
        }
        setContour(defaultContour)
      }
      
      // Mark as initialized
      initializedRef.current = true
    }
    img.src = imageUrl
  }, [imageUrl, initialContour]) // Only depend on imageUrl and initialContour

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

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!canvasRef.current || !contour) return

      const canvas = canvasRef.current
      const rect = canvas.getBoundingClientRect()
      const x = (e.clientX - rect.left) * (canvas.width / rect.width)
      const y = (e.clientY - rect.top) * (canvas.height / rect.height)

      // Find closest point
      const points = [contour.p1, contour.p2, contour.p3, contour.p4, contour.p5, contour.p6]
      let minDist = Infinity
      let closestIdx = -1

      for (let i = 0; i < points.length; i++) {
        const dist = Math.sqrt((x - points[i].x) ** 2 + (y - points[i].y) ** 2)
        if (dist < minDist && dist < 20) {
          minDist = dist
          closestIdx = i
        }
      }

      if (closestIdx >= 0) {
        setDraggingPoint(points[closestIdx].id)
      }
    },
    [contour],
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!canvasRef.current || !contour || draggingPoint === null) return

      const canvas = canvasRef.current
      const rect = canvas.getBoundingClientRect()
      let x = (e.clientX - rect.left) * (canvas.width / rect.width)
      let y = (e.clientY - rect.top) * (canvas.height / rect.height)

      // Snap to edges if enabled
      if (snapToEdge) {
        // Simple edge snapping (can be enhanced)
        if (Math.abs(x) < snapDistance) x = 0
        if (Math.abs(x - canvas.width) < snapDistance) x = canvas.width
        if (Math.abs(y) < snapDistance) y = 0
        if (Math.abs(y - canvas.height) < snapDistance) y = canvas.height
      }

      // Update point
      const updatedContour = { ...contour }
      const pointKey = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'][draggingPoint - 1] as keyof Contour6Points
      updatedContour[pointKey] = { ...updatedContour[pointKey], x, y }

      setContour(updatedContour)
      onContourChange(updatedContour)

      // Validate
      const validation = onValidate(updatedContour)
      setValidationErrors(validation.errors)
    },
    [contour, draggingPoint, snapToEdge, snapDistance, onContourChange, onValidate],
  )

  const handleMouseUp = useCallback(() => {
    setDraggingPoint(null)
  }, [])

  const handleReset = useCallback(() => {
    if (canvasRef.current) {
      const canvas = canvasRef.current
      const defaultContour: Contour6Points = {
        p1: { x: canvas.width * 0.1, y: canvas.height * 0.1, id: 1 },
        p2: { x: canvas.width * 0.9, y: canvas.height * 0.1, id: 2 },
        p3: { x: canvas.width * 0.9, y: canvas.height * 0.5, id: 3 },
        p4: { x: canvas.width * 0.9, y: canvas.height * 0.9, id: 4 },
        p5: { x: canvas.width * 0.1, y: canvas.height * 0.9, id: 5 },
        p6: { x: canvas.width * 0.1, y: canvas.height * 0.5, id: 6 },
      }
      setContour(defaultContour)
      onContourChange(defaultContour)
    }
  }, [onContourChange])

  if (!contour) {
    return <div>Loading...</div>
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
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onTouchStart={(e) => {
              // Handle touch events for mobile
              const touch = e.touches[0]
              if (touch && canvasRef.current) {
                const rect = canvasRef.current.getBoundingClientRect()
                const x = (touch.clientX - rect.left) * (canvasRef.current.width / rect.width)
                const y = (touch.clientY - rect.top) * (canvasRef.current.height / rect.height)
                
                if (contour) {
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
                  }
                }
              }
            }}
            onTouchMove={(e) => {
              if (draggingPoint !== null && canvasRef.current && contour) {
                e.preventDefault()
                const touch = e.touches[0]
                if (touch) {
                  const rect = canvasRef.current.getBoundingClientRect()
                  let x = (touch.clientX - rect.left) * (canvasRef.current.width / rect.width)
                  let y = (touch.clientY - rect.top) * (canvasRef.current.height / rect.height)
                  
                  // Snap to edges if enabled
                  if (snapToEdge) {
                    if (Math.abs(x) < snapDistance) x = 0
                    if (Math.abs(x - canvasRef.current.width) < snapDistance) x = canvasRef.current.width
                    if (Math.abs(y) < snapDistance) y = 0
                    if (Math.abs(y - canvasRef.current.height) < snapDistance) y = canvasRef.current.height
                  }
                  
                  const updatedContour = { ...contour }
                  const pointKey = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'][draggingPoint - 1] as keyof Contour6Points
                  updatedContour[pointKey] = { ...updatedContour[pointKey], x, y }
                  
                  setContour(updatedContour)
                  onContourChange(updatedContour)
                  
                  const validation = onValidate(updatedContour)
                  setValidationErrors(validation.errors)
                }
              }
            }}
            onTouchEnd={() => {
              setDraggingPoint(null)
            }}
            className="w-full max-h-[calc(100vh-200px)] border border-white/20 rounded-lg bg-white"
            style={{ touchAction: 'none' }}
          />

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
                if (validation.valid) {
                  onConfirm?.(contour)
                } else {
                  setValidationErrors(validation.errors)
                }
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

