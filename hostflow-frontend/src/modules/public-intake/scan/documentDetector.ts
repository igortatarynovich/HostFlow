/**
 * Document edge detection using simplified Canny-like algorithm
 * Detects rectangular document boundaries in real-time
 */

export type DocumentQuad = {
  topLeft: { x: number; y: number }
  topRight: { x: number; y: number }
  bottomRight: { x: number; y: number }
  bottomLeft: { x: number; y: number }
  confidence: number
  fill: number // 0-1, how much of frame is filled
}

/**
 * Convert RGB to grayscale
 */
function rgbToGray(data: Uint8ClampedArray, width: number, height: number): Uint8Array {
  const gray = new Uint8Array(width * height)
  for (let i = 0, j = 0; i < data.length; i += 4, j++) {
    const r = data[i]
    const g = data[i + 1]
    const b = data[i + 2]
    gray[j] = Math.round(0.2126 * r + 0.7152 * g + 0.0722 * b)
  }
  return gray
}

/**
 * Apply Gaussian blur (optimized - skip edges for performance)
 */
function gaussianBlur(gray: Uint8Array, width: number, height: number): Uint8Array {
  const blurred = new Uint8Array(width * height)
  const kernel = [1, 2, 1, 2, 4, 2, 1, 2, 1]
  const kernelSum = 16

  // Optimize: process only inner pixels, copy edges
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (y === 0 || y === height - 1 || x === 0 || x === width - 1) {
        // Copy edge pixels as-is
        blurred[y * width + x] = gray[y * width + x]
      } else {
        // Apply blur kernel
        let sum = 0
        let ki = 0
        for (let ky = -1; ky <= 1; ky++) {
          for (let kx = -1; kx <= 1; kx++) {
            const idx = (y + ky) * width + (x + kx)
            sum += gray[idx] * kernel[ki++]
          }
        }
        blurred[y * width + x] = Math.round(sum / kernelSum)
      }
    }
  }
  return blurred
}

/**
 * Sobel edge detection
 */
function sobelEdge(gray: Uint8Array, width: number, height: number, threshold: number): Uint8Array {
  const edges = new Uint8Array(width * height)
  const sobelX = [-1, 0, 1, -2, 0, 2, -1, 0, 1]
  const sobelY = [-1, -2, -1, 0, 0, 0, 1, 2, 1]

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      let gx = 0
      let gy = 0
      let ki = 0
      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          const idx = (y + ky) * width + (x + kx)
          const val = gray[idx]
          gx += val * sobelX[ki]
          gy += val * sobelY[ki]
          ki++
        }
      }
      const magnitude = Math.sqrt(gx * gx + gy * gy)
      edges[y * width + x] = magnitude > threshold ? 255 : 0
    }
  }
  return edges
}

/**
 * Find lines using improved algorithm that handles gaps better
 */
function findLines(edges: Uint8Array, width: number, height: number): Array<{ x1: number; y1: number; x2: number; y2: number }> {
  const lines: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  const minLineLength = Math.min(width, height) * 0.08  // Very low for better detection of small documents
  const gapTolerance = 5  // Allow small gaps in lines

  // Horizontal lines - improved algorithm
  for (let y = 0; y < height; y++) {
    let segments: Array<{ start: number; end: number }> = []
    let currentStart = -1
    
    for (let x = 0; x < width; x++) {
      if (edges[y * width + x] > 128) {
        if (currentStart === -1) {
          currentStart = x
        }
      } else {
        if (currentStart !== -1) {
          // Check if we can merge with previous segment
          if (segments.length > 0) {
            const last = segments[segments.length - 1]
            if (currentStart - last.end <= gapTolerance) {
              // Merge segments
              last.end = x - 1
            } else {
              segments.push({ start: currentStart, end: x - 1 })
            }
          } else {
            segments.push({ start: currentStart, end: x - 1 })
          }
          currentStart = -1
        }
      }
    }
    // Handle line at end of row
    if (currentStart !== -1) {
      if (segments.length > 0) {
        const last = segments[segments.length - 1]
        if (currentStart - last.end <= gapTolerance) {
          last.end = width - 1
        } else {
          segments.push({ start: currentStart, end: width - 1 })
        }
      } else {
        segments.push({ start: currentStart, end: width - 1 })
      }
    }
    
    // Add lines that meet minimum length
    for (const seg of segments) {
      if (seg.end - seg.start >= minLineLength) {
        lines.push({ x1: seg.start, y1: y, x2: seg.end, y2: y })
      }
    }
  }

  // Vertical lines - improved algorithm
  for (let x = 0; x < width; x++) {
    let segments: Array<{ start: number; end: number }> = []
    let currentStart = -1
    
    for (let y = 0; y < height; y++) {
      if (edges[y * width + x] > 128) {
        if (currentStart === -1) {
          currentStart = y
        }
      } else {
        if (currentStart !== -1) {
          // Check if we can merge with previous segment
          if (segments.length > 0) {
            const last = segments[segments.length - 1]
            if (currentStart - last.end <= gapTolerance) {
              // Merge segments
              last.end = y - 1
            } else {
              segments.push({ start: currentStart, end: y - 1 })
            }
          } else {
            segments.push({ start: currentStart, end: y - 1 })
          }
          currentStart = -1
        }
      }
    }
    // Handle line at end of column
    if (currentStart !== -1) {
      if (segments.length > 0) {
        const last = segments[segments.length - 1]
        if (currentStart - last.end <= gapTolerance) {
          last.end = height - 1
        } else {
          segments.push({ start: currentStart, end: height - 1 })
        }
      } else {
        segments.push({ start: currentStart, end: height - 1 })
      }
    }
    
    // Add lines that meet minimum length
    for (const seg of segments) {
      if (seg.end - seg.start >= minLineLength) {
        lines.push({ x1: x, y1: seg.start, x2: x, y2: seg.end })
      }
    }
  }

  return lines
}

/**
 * Find intersection points of lines to form a quad
 */
function findQuadFromLines(
  lines: Array<{ x1: number; y1: number; x2: number; y2: number }>,
  width: number,
  height: number,
): DocumentQuad | null {
  if (lines.length < 4) return null

  // Group lines by orientation - more lenient tolerance for better detection
  const horizontal = lines.filter((l) => Math.abs(l.y1 - l.y2) < 20)
  const vertical = lines.filter((l) => Math.abs(l.x1 - l.x2) < 20)

  if (horizontal.length < 2 || vertical.length < 2) return null

  // Find top and bottom horizontal lines
  horizontal.sort((a, b) => a.y1 - b.y1)
  const topLine = horizontal[0]
  const bottomLine = horizontal[horizontal.length - 1]

  // Find left and right vertical lines
  vertical.sort((a, b) => a.x1 - b.x1)
  const leftLine = vertical[0]
  const rightLine = vertical[vertical.length - 1]

  // Calculate intersections
  const topLeft = intersectLines(topLine, leftLine)
  const topRight = intersectLines(topLine, rightLine)
  const bottomRight = intersectLines(bottomLine, rightLine)
  const bottomLeft = intersectLines(bottomLine, leftLine)

  if (!topLeft || !topRight || !bottomRight || !bottomLeft) return null

  // Calculate area and fill
  const area = polygonArea([topLeft, topRight, bottomRight, bottomLeft])
  const frameArea = width * height
  const fill = area / frameArea

  // Confidence based on fill - very lenient (3-97% of frame)
  let confidence = 0.5  // Default confidence
  if (fill >= 0.1 && fill <= 0.9) {
    // Good fill range - higher confidence
    confidence = Math.min(1.0, 0.5 + (fill - 0.3) * 0.5)
  } else if (fill >= 0.03 && fill <= 0.97) {
    // Acceptable range - lower but still valid (very lenient)
    confidence = 0.25
  } else {
    // Too small or too large - very low confidence but still allow
    confidence = 0.08
  }

  return {
    topLeft,
    topRight,
    bottomRight,
    bottomLeft,
    confidence,
    fill,
  }
}

function intersectLines(
  line1: { x1: number; y1: number; x2: number; y2: number },
  line2: { x1: number; y1: number; x2: number; y2: number },
): { x: number; y: number } | null {
  // Line 1: from (x1, y1) to (x2, y2)
  // Line 2: from (x3, y3) to (x4, y4)
  const x1 = line1.x1
  const y1 = line1.y1
  const x2 = line1.x2
  const y2 = line1.y2
  const x3 = line2.x1
  const y3 = line2.y1
  const x4 = line2.x2
  const y4 = line2.y2

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
  if (Math.abs(denom) < 1e-10) return null

  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

  // For horizontal/vertical lines, we're more lenient
  const isHorizontal1 = Math.abs(y1 - y2) < 1
  const isVertical1 = Math.abs(x1 - x2) < 1
  const isHorizontal2 = Math.abs(y3 - y4) < 1
  const isVertical2 = Math.abs(x3 - x4) < 1

  if (isHorizontal1 && isVertical2) {
    // Horizontal line 1 intersects vertical line 2
    return { x: x3, y: y1 }
  }
  if (isVertical1 && isHorizontal2) {
    // Vertical line 1 intersects horizontal line 2
    return { x: x1, y: y3 }
  }

  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return {
      x: x1 + t * (x2 - x1),
      y: y1 + t * (y2 - y1),
    }
  }
  return null
}

function polygonArea(points: Array<{ x: number; y: number }>): number {
  let area = 0
  for (let i = 0; i < points.length; i++) {
    const j = (i + 1) % points.length
    area += points[i].x * points[j].y
    area -= points[j].x * points[i].y
  }
  return Math.abs(area / 2)
}

/**
 * Detect document boundaries in image
 * Simplified version that's more reliable
 */
/**
 * Try multiple detection strategies for 100% detection rate
 */
function detectDocumentWithFallback(imageData: ImageData, strategy: 'primary' | 'aggressive' | 'minimal'): DocumentQuad | null {
  const { data, width, height } = imageData

  // Optimize: downscale more aggressively for performance (max 400px width)
  const scale = width > 400 ? 400 / width : 1
  const scaledWidth = Math.floor(width * scale)
  const scaledHeight = Math.floor(height * scale)

  if (scaledWidth < 100 || scaledHeight < 100) {
    return null
  }

  let gray: Uint8Array
  if (scale < 1) {
    gray = new Uint8Array(scaledWidth * scaledHeight)
    for (let y = 0; y < scaledHeight; y++) {
      for (let x = 0; x < scaledWidth; x++) {
        const srcX = Math.floor(x / scale)
        const srcY = Math.floor(y / scale)
        const srcIdx = (srcY * width + srcX) * 4
        gray[y * scaledWidth + x] = Math.round(0.2126 * data[srcIdx] + 0.7152 * data[srcIdx + 1] + 0.0722 * data[srcIdx + 2])
      }
    }
  } else {
    gray = rgbToGray(data, width, height)
  }

  // Try different thresholds based on strategy
  const thresholds = strategy === 'primary' ? [15, 10, 20] : strategy === 'aggressive' ? [8, 5, 12, 18, 25] : [5, 3, 8]
  
  for (const threshold of thresholds) {
    // Apply blur
    const blurred = gaussianBlur(gray, scaledWidth, scaledHeight)
    
    // Edge detection
    const edges = sobelEdge(blurred, scaledWidth, scaledHeight, threshold)
    
    // Find lines with different min lengths
    const minLineLengths = strategy === 'primary' ? [0.08] : strategy === 'aggressive' ? [0.05, 0.06, 0.08] : [0.03, 0.05]
    
    for (const minLineRatio of minLineLengths) {
      const minLineLength = Math.min(scaledWidth, scaledHeight) * minLineRatio
      const lines = findLinesWithMinLength(edges, scaledWidth, scaledHeight, minLineLength)
      
      if (lines.length < 2) continue
      
      // Try to find quad with different tolerances
      const tolerances = strategy === 'primary' ? [20] : strategy === 'aggressive' ? [15, 20, 25, 30] : [10, 15, 20, 25, 30]
      
      for (const tolerance of tolerances) {
        const quad = findQuadFromLinesWithTolerance(lines, scaledWidth, scaledHeight, tolerance)
        
        if (quad && validateQuad(quad, scaledWidth, scaledHeight, strategy)) {
          return quad
        }
      }
    }
  }
  
  return null
}

/**
 * Find lines with custom minimum length
 */
function findLinesWithMinLength(edges: Uint8Array, width: number, height: number, minLineLength: number): Array<{ x1: number; y1: number; x2: number; y2: number }> {
  const lines: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  const gapTolerance = 8  // Increased gap tolerance

  // Horizontal lines
  for (let y = 0; y < height; y++) {
    let segments: Array<{ start: number; end: number }> = []
    let currentStart = -1
    
    for (let x = 0; x < width; x++) {
      if (edges[y * width + x] > 128) {
        if (currentStart === -1) {
          currentStart = x
        }
      } else {
        if (currentStart !== -1) {
          if (segments.length > 0) {
            const last = segments[segments.length - 1]
            if (currentStart - last.end <= gapTolerance) {
              last.end = x - 1
            } else {
              segments.push({ start: currentStart, end: x - 1 })
            }
          } else {
            segments.push({ start: currentStart, end: x - 1 })
          }
          currentStart = -1
        }
      }
    }
    if (currentStart !== -1) {
      if (segments.length > 0) {
        const last = segments[segments.length - 1]
        if (currentStart - last.end <= gapTolerance) {
          last.end = width - 1
        } else {
          segments.push({ start: currentStart, end: width - 1 })
        }
      } else {
        segments.push({ start: currentStart, end: width - 1 })
      }
    }
    
    for (const seg of segments) {
      if (seg.end - seg.start >= minLineLength) {
        lines.push({ x1: seg.start, y1: y, x2: seg.end, y2: y })
      }
    }
  }

  // Vertical lines
  for (let x = 0; x < width; x++) {
    let segments: Array<{ start: number; end: number }> = []
    let currentStart = -1
    
    for (let y = 0; y < height; y++) {
      if (edges[y * width + x] > 128) {
        if (currentStart === -1) {
          currentStart = y
        }
      } else {
        if (currentStart !== -1) {
          if (segments.length > 0) {
            const last = segments[segments.length - 1]
            if (currentStart - last.end <= gapTolerance) {
              last.end = y - 1
            } else {
              segments.push({ start: currentStart, end: y - 1 })
            }
          } else {
            segments.push({ start: currentStart, end: y - 1 })
          }
          currentStart = -1
        }
      }
    }
    if (currentStart !== -1) {
      if (segments.length > 0) {
        const last = segments[segments.length - 1]
        if (currentStart - last.end <= gapTolerance) {
          last.end = height - 1
        } else {
          segments.push({ start: currentStart, end: height - 1 })
        }
      } else {
        segments.push({ start: currentStart, end: height - 1 })
      }
    }
    
    for (const seg of segments) {
      if (seg.end - seg.start >= minLineLength) {
        lines.push({ x1: x, y1: seg.start, x2: x, y2: seg.end })
      }
    }
  }

  return lines
}

/**
 * Find quad with custom tolerance
 */
function findQuadFromLinesWithTolerance(
  lines: Array<{ x1: number; y1: number; x2: number; y2: number }>,
  width: number,
  height: number,
  tolerance: number
): DocumentQuad | null {
  if (lines.length < 4) return null

  const horizontal = lines.filter((l) => Math.abs(l.y1 - l.y2) < tolerance)
  const vertical = lines.filter((l) => Math.abs(l.x1 - l.x2) < tolerance)

  if (horizontal.length < 2 || vertical.length < 2) return null

  horizontal.sort((a, b) => a.y1 - b.y1)
  const topLine = horizontal[0]
  const bottomLine = horizontal[horizontal.length - 1]

  vertical.sort((a, b) => a.x1 - b.x1)
  const leftLine = vertical[0]
  const rightLine = vertical[vertical.length - 1]

  const topLeft = intersectLines(topLine, leftLine)
  const topRight = intersectLines(topLine, rightLine)
  const bottomRight = intersectLines(bottomLine, rightLine)
  const bottomLeft = intersectLines(bottomLine, leftLine)

  if (!topLeft || !topRight || !bottomRight || !bottomLeft) return null

  const area = polygonArea([topLeft, topRight, bottomRight, bottomLeft])
  const frameArea = width * height
  const fill = area / frameArea

  let confidence = 0.5
  if (fill >= 0.1 && fill <= 0.9) {
    confidence = Math.min(1.0, 0.5 + (fill - 0.3) * 0.5)
  } else if (fill >= 0.02 && fill <= 0.98) {
    confidence = 0.2
  } else {
    confidence = 0.05
  }

  return {
    topLeft,
    topRight,
    bottomRight,
    bottomLeft,
    confidence,
    fill,
  }
}

/**
 * Validate quad with strategy-specific rules
 */
function validateQuad(quad: DocumentQuad, scaledWidth: number, scaledHeight: number, strategy: string): boolean {
  const quadWidth = Math.abs(quad.topRight.x - quad.topLeft.x)
  const quadHeight = Math.abs(quad.bottomLeft.y - quad.topLeft.y)
  const minDimension = Math.min(scaledWidth, scaledHeight)
  
  // CRITICAL: Reject extremely thin quads (likely false positives from frame edges)
  // Minimum absolute size in pixels - reject if height or width is less than 50px
  const MIN_ABSOLUTE_SIZE = 50
  if (quadWidth < MIN_ABSOLUTE_SIZE || quadHeight < MIN_ABSOLUTE_SIZE) {
    return false
  }
  
  // Size check - very lenient for aggressive/minimal strategies
  const minSizeRatio = strategy === 'primary' ? 0.08 : strategy === 'aggressive' ? 0.05 : 0.03
  if (quadWidth < minDimension * minSizeRatio || quadHeight < minDimension * minSizeRatio) {
    return false
  }
  
  // Aspect ratio - reject extremely wide or tall quads (likely false positives)
  const aspectRatio = quadWidth / quadHeight
  if (aspectRatio > 6.0 || aspectRatio < 0.15) {  // Stricter: was 8.0/0.1
    return false
  }
  
  // Reject very square shapes only for primary strategy
  if (strategy === 'primary' && aspectRatio >= 0.85 && aspectRatio <= 1.15) {
    return false
  }
  
  // Confidence - VERY low threshold for maximum detection
  const minConfidence = strategy === 'primary' ? 0.03 : strategy === 'aggressive' ? 0.03 : 0.03
  if (quad.confidence < minConfidence) {
    return false
  }
  
  // Coverage - VERY lenient: only reject obviously wrong quads
  const coverage = (quadWidth * quadHeight) / (scaledWidth * scaledHeight)
  if (coverage < 0.01 || coverage > 0.95) {  // Very lenient: was 0.05/0.80
    return false
  }

  // Check boundaries - VERY lenient: only reject if ALL corners are at the very edge
  const edgeMargin = Math.min(scaledWidth, scaledHeight) * 0.01  // Very small margin (1%)
  const corners = [quad.topLeft, quad.topRight, quad.bottomRight, quad.bottomLeft]
  let cornersAtEdge = 0
  for (const corner of corners) {
    // Count corners at the very edge (within 1% of frame edge)
    if (corner.x < edgeMargin || corner.x > scaledWidth - edgeMargin ||
        corner.y < edgeMargin || corner.y > scaledHeight - edgeMargin) {
      cornersAtEdge++
    }
  }
  // Reject only if ALL 4 corners are at the very edge (definitely detecting frame itself)
  if (cornersAtEdge === 4) {
    return false
  }

  return true
}

export function detectDocument(imageData: ImageData): DocumentQuad | null {
  // Detection is temporarily disabled to focus on manual contour editing and quality.
  return null
}

/**
 * Scale quad back to original size
 */
function scaleQuad(quad: DocumentQuad, scale: number, originalWidth: number, originalHeight: number): DocumentQuad | null {
  if (scale >= 1) {
    // Check boundaries
    const strictMargin = 2
    const corners = [quad.topLeft, quad.topRight, quad.bottomRight, quad.bottomLeft]
    for (const corner of corners) {
      if (corner.x < strictMargin || corner.x > originalWidth - strictMargin ||
          corner.y < strictMargin || corner.y > originalHeight - strictMargin) {
        return null
      }
    }
    return quad
  }
  
  // Scale back
  const scaledQuad = {
    topLeft: { 
      x: Math.round(quad.topLeft.x / scale), 
      y: Math.round(quad.topLeft.y / scale) 
    },
    topRight: { 
      x: Math.round(quad.topRight.x / scale), 
      y: Math.round(quad.topRight.y / scale) 
    },
    bottomRight: { 
      x: Math.round(quad.bottomRight.x / scale), 
      y: Math.round(quad.bottomRight.y / scale) 
    },
    bottomLeft: { 
      x: Math.round(quad.bottomLeft.x / scale), 
      y: Math.round(quad.bottomLeft.y / scale) 
    },
    confidence: quad.confidence,
    fill: quad.fill,
  }
  
  // Check boundaries
  const strictMargin = 2
  const corners = [scaledQuad.topLeft, scaledQuad.topRight, scaledQuad.bottomRight, scaledQuad.bottomLeft]
  for (const corner of corners) {
    if (corner.x < strictMargin || corner.x > originalWidth - strictMargin ||
        corner.y < strictMargin || corner.y > originalHeight - strictMargin) {
      return null
    }
  }
  
  return scaledQuad
}
