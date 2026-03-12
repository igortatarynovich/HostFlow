import type { FrameKind } from './types'
import type { ScanPresetKey } from '../public-intake/scan/analyzer'
import { presetForDocType } from '../public-intake/scan/presets'

export function aspectForKind(kind?: FrameKind): number {
  switch ((kind || '').toUpperCase()) {
    case 'DRIVER_LICENSE':
    case 'ID_CARD':
    case 'CODE95':
      return 1.586
    case 'PASSPORT_SPREAD':
      return 1.408
    case 'PASSPORT_ID_PAGE':
      return 0.70
    case 'A4':
      return 0.707
    default:
      return 1.586
  }
}

export function statusBadgeTone(status: string): string {
  switch (status) {
    case 'ok':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'needs_review':
      return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'rejected':
    case 'error':
      return 'bg-rose-100 text-rose-700 border-rose-200'
    case 'uploaded':
    case 'processing':
      return 'bg-blue-100 text-blue-700 border-blue-200'
    default:
      return 'bg-slate-100 text-slate-600 border-slate-200'
  }
}

// Quality preset mapping for camera/analyzer (limited set of keys)
export function qualityPresetForDocType(docType?: string | null): ScanPresetKey {
  const normalized = (docType || '').toLowerCase().trim()
  if (!normalized) return 'default'
  // Code95 and similar certificates are usually ID-card format for scanning UX
  if (normalized === 'code95' || normalized === 'qualification_code95' || normalized === 'code_95') {
    return 'driving_license'
  }
  const preset = presetForDocType(normalized)
  // presetForDocType already returns a ScanPresetKey
  return preset
}

