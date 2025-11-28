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
}

export function ContourEditorModal({
  imageUrl,
  initialContour,
  onConfirm,
  onCancel,
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
    
    // Check angles (simplified)
    for (let i = 0; i < points.length; i++) {
      const p1 = points[i]
      const p2 = points[(i + 1) % points.length]
      const p3 = points[(i + 2) % points.length]
      
      const v1 = { x: p2.x - p1.x, y: p2.y - p1.y }
      const v2 = { x: p3.x - p2.x, y: p3.y - p2.y }
      
      const dot = v1.x * v2.x + v1.y * v2.y
      const len1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y)
      const len2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y)
      
      if (len1 > 0 && len2 > 0) {
        const cosAngle = dot / (len1 * len2)
        const angle = Math.acos(Math.max(-1, Math.min(1, cosAngle))) * (180 / Math.PI)
        
        if (angle < 10 || angle > 170) {
          errors.push(`Угол ${i + 1} слишком острый или тупой (${angle.toFixed(1)}°)`)
        }
      }
    }
    
    return {
      valid: errors.length === 0,
      errors,
    }
  }

  return (
    <ContourEditor
      imageUrl={imageUrl}
      initialContour={initialContour}
      onContourChange={setContour}
      onValidate={validateContour}
      snapToEdge={true}
      snapDistance={10}
      onClose={onCancel}
      onConfirm={(c) => {
        if (c) {
          const validation = validateContour(c)
          if (validation.valid) {
            onConfirm(c)
          } else {
            // Still allow confirmation even with validation errors - user knows what they're doing
            console.warn('Contour validation errors:', validation.errors)
            onConfirm(c)
          }
        } else if (contour) {
          // Use current contour if callback doesn't provide one
          onConfirm(contour)
        }
      }}
    />
  )
}

