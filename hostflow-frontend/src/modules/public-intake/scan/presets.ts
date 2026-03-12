import type { ScanPresetKey } from './analyzer'

export type ScanPresetSpec = {
  widthMm: number
  heightMm: number
  dpi: number
  aspect: number
  aspectTolerance: number
  quality: {
    fill: number
    sharpness: number
    glare: number
  }
  orientation: 'landscape' | 'portrait'
  pages: 1 | 2
}

const mm = (w: number, h: number) => ({ widthMm: w, heightMm: h, aspect: w / h })
const A4 = mm(210, 297)
const ID1 = mm(85.6, 54)
const PASS = mm(125, 88)
const PHOTO = mm(35, 45)

const Q_SOFT = { fill: 0.6, sharpness: 110, glare: 0.2 }
const Q_MID = { fill: 0.7, sharpness: 120, glare: 0.15 }
const Q_STRICT = { fill: 0.8, sharpness: 140, glare: 0.12 }

const PRESETS: Record<ScanPresetKey, ScanPresetSpec> = {
  // Identity documents (ID-1 format: 85.6 x 54 mm)
  id_card: {
    ...ID1,
    dpi: 300,
    aspectTolerance: 0.06,
    quality: Q_MID,
    orientation: 'landscape',
    pages: 2,
  },
  // Driver licenses (same format as ID cards)
  driving_license: {
    ...ID1,
    dpi: 300,
    aspectTolerance: 0.06,
    quality: Q_MID,
    orientation: 'landscape',
    pages: 2,
  },
  // Passports (spread: ~125 x 88 mm)
  passport: {
    ...PASS,
    dpi: 300,
    aspectTolerance: 0.08,
    quality: Q_MID,
    orientation: 'landscape',
    pages: 1, // Main spread
  },
  // Visas (usually in passport, but can be separate card)
  visa: {
    ...ID1,
    dpi: 300,
    aspectTolerance: 0.08,
    quality: Q_MID,
    orientation: 'landscape',
    pages: 1,
  },
  // A4 documents (210 x 297 mm)
  page_a4: {
    ...A4,
    dpi: 300,
    aspectTolerance: 0.04,
    quality: Q_STRICT,
    orientation: 'portrait',
    pages: 1,
  },
  // Contracts (A4, usually 2+ pages)
  contract_a4: {
    ...A4,
    dpi: 300,
    aspectTolerance: 0.04,
    quality: Q_STRICT,
    orientation: 'portrait',
    pages: 2,
  },
  // Photo 35x45 mm
  photo_35x45: {
    ...PHOTO,
    dpi: 300,
    aspectTolerance: 0.05,
    quality: Q_SOFT,
    orientation: 'portrait',
    pages: 1,
  },
  // Default fallback
  default: {
    widthMm: 210,
    heightMm: 148,
    dpi: 220,
    aspect: 210 / 148,
    aspectTolerance: 0.1,
    quality: Q_SOFT,
    orientation: 'landscape',
    pages: 1,
  },
}

const MAX_LONG_EDGE = 2400

function roundEven(value: number): number {
  const rounded = Math.round(value)
  return (rounded & 1) === 0 ? rounded : rounded + 1
}

export function mmToPx(mmValue: number, dpi: number): number {
  return Math.max(1, Math.round((mmValue / 25.4) * dpi))
}

export function getPresetSpec(preset?: ScanPresetKey): ScanPresetSpec {
  return PRESETS[preset ?? 'default'] ?? PRESETS.default
}

export function getPresetPixelSize(preset?: ScanPresetKey): { width: number; height: number } {
  const spec = getPresetSpec(preset)
  let width = roundEven(mmToPx(spec.widthMm, spec.dpi))
  let height = roundEven(mmToPx(spec.heightMm, spec.dpi))
  const long = Math.max(width, height)
  if (long > MAX_LONG_EDGE) {
    const scale = MAX_LONG_EDGE / long
    width = Math.max(2, roundEven(width * scale))
    height = Math.max(2, roundEven(height * scale))
  }
  if (width === 0) width = 2
  if (height === 0) height = 2
  return { width, height }
}

export function getPresetAspectTolerance(preset?: ScanPresetKey): number {
  return getPresetSpec(preset).aspectTolerance
}

export function getPresetThresholds(preset?: ScanPresetKey) {
  return getPresetSpec(preset).quality
}

export function presetAspect(preset?: ScanPresetKey): number {
  return getPresetSpec(preset).aspect
}

export const presetAspectRatio = presetAspect

export function presetOrientation(preset?: ScanPresetKey): 'landscape' | 'portrait' {
  return getPresetSpec(preset).orientation
}

export function presetPages(preset?: ScanPresetKey): 1 | 2 {
  return getPresetSpec(preset).pages
}

export type DocType =
  | 'id_card'
  | 'driving_license'
  | 'passport'
  | 'visa'
  | 'a4_page'
  | 'a4_contract'
  | 'photo_35x45'

const PRESET_ALIASES: Record<string, ScanPresetKey> = {
  a4: 'page_a4',
  page: 'page_a4',
  page_a4: 'page_a4',
  contract: 'contract_a4',
  a4_contract: 'contract_a4',
  passport: 'passport',
  id: 'id_card',
  id_card: 'id_card',
  driver_license: 'driving_license',
  driving_license: 'driving_license',
  driver: 'driving_license',
  visa: 'visa',
  photo: 'photo_35x45',
  photo_35x45: 'photo_35x45',
  default: 'default',
}

export function normalizePresetKey(value?: string | null): ScanPresetKey | undefined {
  if (!value) return undefined
  const lowered = value.toLowerCase()
  if (lowered in PRESETS) {
    return lowered as ScanPresetKey
  }
  return PRESET_ALIASES[lowered]
}

export function presetForDocType(docType?: string | null): ScanPresetKey {
  const normalized = (docType || '').toLowerCase().trim()
  
  // Identity documents
  if (normalized === 'identity_document' || normalized === 'id_card' || normalized === 'national_id') {
    return 'id_card'
  }
  if (normalized === 'residence_permit' || normalized === 'residence_card' || normalized === 'karta_pobytu') {
    return 'id_card' // Same format as ID card
  }
  
  // Driver licenses
  if (normalized === 'driver_license' || normalized === 'driving_license' || 
      normalized === 'driver_license_exchange' || normalized === 'prawo_jazdy') {
    return 'driving_license'
  }
  // Driver license with code95 suffix - treat as standard license card
  if (normalized === 'driver_license_code95' || normalized === 'driving_license_code95') {
    return 'driving_license'
  }
  
  // Passports
  if (normalized === 'passport' || normalized === 'travel_document') {
    return 'passport'
  }
  
  // Visas
  if (normalized === 'visa' || normalized === 'visa_d' || normalized === 'visa_c' || 
      normalized === 'entry_permit' || normalized === 'entry_permit_or_visa') {
    return 'visa'
  }

  // Certificates (Code95 etc.) - treat as ID-card format for quality thresholds
  if (normalized === 'qualification_code95' || normalized === 'code95' || normalized === 'code_95') {
    return 'driving_license'
  }
  
  // Tachograph
  if (normalized === 'tachograph_card' || normalized === 'tacho_card' || normalized === 'karta_tachografu') {
    return 'driving_license' // Same format
  }
  
  // Certificates
  if (normalized === 'qualification_code95' || normalized === 'code95' || normalized === 'code_95') {
    return 'page_a4' // Usually A5/A4 format
  }
  if (normalized === 'adr' || normalized === 'adr_certificate' || normalized === 'adr_card') {
    return 'page_a4'
  }
  if (normalized === 'swiadectwo_kierowcy' || normalized === 'driver_certificate' || normalized === 'driver_attestation') {
    return 'page_a4'
  }
  
  // Medical and tests
  if (normalized === 'medical_certificate' || normalized === 'medical_cert' || normalized === 'badania_lekarskie') {
    return 'page_a4'
  }
  if (normalized === 'criminal_record' || normalized === 'no_criminal_history') {
    return 'page_a4'
  }
  if (normalized === 'psychology_test' || normalized === 'psych_tests' || 
      normalized === 'psychotest' || normalized === 'psychotests') {
    return 'page_a4'
  }
  
  // Work permits
  if (normalized === 'work_permit' || normalized === 'zezwolenie_na_prace' || 
      normalized === 'oswiadczenie' || normalized === 'zezwolenie_a') {
    return 'page_a4'
  }
  if (normalized === 'decision' || normalized === 'decyzja' || normalized === 'voivodeship_decision') {
    return 'page_a4'
  }
  
  // A4 documents
  if (normalized === 'contract' || normalized === 'employment_contract' || normalized === 'a4_contract') {
    return 'contract_a4'
  }
  if (normalized === 'insurance' || normalized === 'ubezpieczenie' || normalized === 'a4_page') {
    return 'page_a4'
  }
  if (normalized === 'bhp' || normalized === 'safety_training') {
    return 'page_a4'
  }
  if (normalized === 'assignment' || normalized === 'delegation') {
    return 'page_a4'
  }
  if (normalized === 'accommodation' || normalized === 'housing') {
    return 'page_a4'
  }
  if (normalized === 'bank_account_confirmation' || normalized === 'bank_statement') {
    return 'page_a4'
  }
  if (normalized === 'pesel' || normalized === 'national_number') {
    return 'page_a4'
  }
  
  // Photo
  if (normalized === 'photo' || normalized === 'photo_35x45') {
    return 'photo_35x45'
  }
  
  // Fallback
  return 'default'
}

export function listAllPresets(): Array<ScanPresetSpec & { key: ScanPresetKey }> {
  return Object.entries(PRESETS).map(([key, spec]) => ({ key: key as ScanPresetKey, ...spec }))
}
