import type { ScanPresetKey } from './analyzer'

export type ProcessorHint = 'align' | 'distance' | 'lighting' | 'blurry' | 'glare'

export type LiveDetectionMeta = {
  quad?: [number, number, number, number, number, number, number, number]
  bounds?: { x: number; y: number; width: number; height: number; fill: number }
}

export type ProcessedFrameMeta = {
  preset: ScanPresetKey
  enhanced: boolean
  cropped: boolean
  hints: ProcessorHint[]
  metrics?: {
    fill: number
    sharpness: number
    glare: number
  }
  targetSize?: { width: number; height: number }
  quad?: number[]
  detection?: LiveDetectionMeta
}

export type ScanProcessorProcessRequest = {
  type: 'process'
  id: string
  preset: ScanPresetKey
  imageData: ImageData
}

export type ScanProcessorDetectRequest = {
  type: 'detect'
  id: string
  preset: ScanPresetKey
  imageData: ImageData
}

export type ScanProcessorRequest = ScanProcessorProcessRequest | ScanProcessorDetectRequest

export type ScanProcessorProcessSuccess = {
  id: string
  type: 'process'
  success: true
  imageData: ImageData
  meta: ProcessedFrameMeta
}

export type ScanProcessorDetectSuccess = {
  id: string
  type: 'detect'
  success: true
  detection?: LiveDetectionMeta
}

export type ScanProcessorProcessFailure = {
  id: string
  type: 'process'
  success: false
  error: string
}

export type ScanProcessorDetectFailure = {
  id: string
  type: 'detect'
  success: false
  error: string
}

export type ScanProcessorFailure = ScanProcessorProcessFailure | ScanProcessorDetectFailure

export type ScanProcessorResponse =
  | ScanProcessorProcessSuccess
  | ScanProcessorDetectSuccess
  | ScanProcessorFailure

export type ProcessFrameResult = {
  imageData: ImageData
  meta: ProcessedFrameMeta
}

export function emptyFrameMeta(preset: ScanPresetKey): ProcessedFrameMeta {
  return {
    preset,
    enhanced: false,
    cropped: false,
    hints: [],
    detection: undefined,
  }
}
