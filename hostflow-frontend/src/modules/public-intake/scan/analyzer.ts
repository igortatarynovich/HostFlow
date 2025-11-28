import { getPresetThresholds } from './presets'

export type ScanPresetKey =
  | 'id_card'
  | 'driving_license'
  | 'passport'
  | 'visa'
  | 'page_a4'
  | 'contract_a4'
  | 'photo_35x45'
  | 'default'

export type ScanQualityWarning = 'sharpness' | 'glare' | 'fill'

export type ScanQualityMetrics = {
  sharpness: number
  glare: number
  fill: number
  contrast: number
  brightness: number
}

export type ScanQualityReport = {
  preset: ScanPresetKey
  metrics: ScanQualityMetrics
  warnings: ScanQualityWarning[]
  passed: boolean
}

export function analyzeImageData(imageData: ImageData, preset: ScanPresetKey): ScanQualityReport {
  const metrics = computeMetrics(imageData)
  const thresholds = getPresetThresholds(preset)
  const warnings: ScanQualityWarning[] = []
  if (metrics.sharpness < thresholds.sharpness) {
    warnings.push('sharpness')
  }
  if (metrics.glare > thresholds.glare) {
    warnings.push('glare')
  }
  if (metrics.fill < thresholds.fill) {
    warnings.push('fill')
  }
  return {
    preset,
    metrics,
    warnings,
    passed: warnings.length === 0,
  }
}

function computeMetrics(imageData: ImageData): ScanQualityMetrics {
  const { data, width, height } = imageData
  const totalPixels = width * height
  const gray = new Float32Array(totalPixels)
  const histogram = new Uint32Array(256)

  for (let i = 0, px = 0; i < data.length; i += 4, px += 1) {
    const r = data[i]
    const g = data[i + 1]
    const b = data[i + 2]
    const value = Math.round(0.2126 * r + 0.7152 * g + 0.0722 * b)
    gray[px] = value
    histogram[value] += 1
  }

  const brightness = histogram.reduce((sum, count, value) => sum + count * value, 0) / (totalPixels * 255)
  const glarePixels = histogram.slice(230).reduce((sum, count) => sum + count, 0)
  const glare = glarePixels / totalPixels
  const fillPixels = histogram.slice(0, 245).reduce((sum, count) => sum + count, 0)
  const fill = fillPixels / totalPixels
  const p5 = percentile(histogram, totalPixels, 0.05)
  const p95 = percentile(histogram, totalPixels, 0.95)
  const contrast = (p95 - p5) / 255
  const sharpness = laplacianVariance(gray, width, height)

  return {
    sharpness,
    glare,
    fill,
    contrast,
    brightness,
  }
}

function percentile(hist: Uint32Array, total: number, percent: number): number {
  const target = Math.max(0, Math.min(1, percent)) * total
  let cumulative = 0
  for (let value = 0; value < hist.length; value += 1) {
    cumulative += hist[value]
    if (cumulative >= target) {
      return value
    }
  }
  return 255
}

function laplacianVariance(gray: Float32Array, width: number, height: number): number {
  if (width < 3 || height < 3) return 0
  let sum = 0
  let sumSquares = 0
  let count = 0
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x
      const lap =
        -4 * gray[idx] +
        gray[idx - 1] +
        gray[idx + 1] +
        gray[idx - width] +
        gray[idx + width]
      sum += lap
      sumSquares += lap * lap
      count += 1
    }
  }
  if (count === 0) return 0
  const mean = sum / count
  const variance = sumSquares / count - mean * mean
  return Math.max(0, variance)
}
