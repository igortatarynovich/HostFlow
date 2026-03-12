export type FilterName = 'standard' | 'document' | 'photo' | 'grayscale' | 'contrast_boost' | 'photo_soft'

export type FrameKind = 'DRIVER_LICENSE' | 'ID_CARD' | 'CODE95' | 'PASSPORT_SPREAD' | 'PASSPORT_ID_PAGE' | 'A4'

export const ScanState = {
  SCAN: 'scan',
  EDIT: 'edit',
  PROCESSING: 'processing',
  REVIEW: 'review',
  DONE_PAGE: 'done_page',
  DONE_DOCUMENT: 'done_document',
} as const

export type ScanState = (typeof ScanState)[keyof typeof ScanState]

