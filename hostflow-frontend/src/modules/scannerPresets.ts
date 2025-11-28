export type ScannerPresetStep = {
  code: string
  label: string
  optional?: boolean
}

export type ScannerPreset = {
  code: string
  title: string
  aspectRatio: number
  orientation: 'portrait' | 'landscape'
  minResolution: number
  steps: ScannerPresetStep[]
}

const COMMON_CARD_STEPS: ScannerPresetStep[] = [
  { code: 'front', label: 'Front side' },
  { code: 'back', label: 'Back side' },
]

const PASSPORT_EXTRA_STEPS: ScannerPresetStep[] = [
  { code: 'page_1', label: 'Page 1', optional: true },
  { code: 'page_2', label: 'Page 2', optional: true },
  { code: 'page_3', label: 'Page 3', optional: true },
  { code: 'page_4', label: 'Page 4', optional: true },
]

export const SCANNER_PRESETS: Record<string, ScannerPreset> = {
  // Identity documents
  identity_document: {
    code: 'identity_document',
    title: 'Identity document',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  id_card: {
    code: 'id_card',
    title: 'ID card',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  national_id: {
    code: 'national_id',
    title: 'National ID',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  residence_permit: {
    code: 'residence_permit',
    title: 'Residence permit',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  residence_card: {
    code: 'residence_card',
    title: 'Residence card',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  // Driver licenses
  driver_license: {
    code: 'driver_license',
    title: 'Driver license',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  driver_license_exchange: {
    code: 'driver_license_exchange',
    title: 'Driver license exchange',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  // Passports
  passport: {
    code: 'passport',
    title: 'Passport',
    aspectRatio: 125 / 88,
    orientation: 'landscape',
    minResolution: 1200,
    steps: [{ code: 'spread', label: 'Passport spread' }],
  },
  passport_main: {
    code: 'passport_main',
    title: 'Passport main spread',
    aspectRatio: 125 / 88,
    orientation: 'landscape',
    minResolution: 1200,
    steps: [{ code: 'spread', label: 'Passport spread' }],
  },
  passport_all: {
    code: 'passport_all',
    title: 'Passport all pages',
    aspectRatio: 125 / 88,
    orientation: 'landscape',
    minResolution: 1200,
    steps: [{ code: 'spread', label: 'Passport spread' }, ...PASSPORT_EXTRA_STEPS],
  },
  // Visas
  visa: {
    code: 'visa',
    title: 'Visa',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: [{ code: 'front', label: 'Visa page' }, { code: 'back', label: 'Back side', optional: true }],
  },
  // Tachograph
  tachograph_card: {
    code: 'tachograph_card',
    title: 'Tachograph card',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  tacho_card: {
    code: 'tacho_card',
    title: 'Tachograph card',
    aspectRatio: 85.6 / 54,
    orientation: 'landscape',
    minResolution: 1000,
    steps: COMMON_CARD_STEPS,
  },
  // Certificates
  qualification_code95: {
    code: 'qualification_code95',
    title: 'Code 95',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  code95: {
    code: 'code95',
    title: 'Code 95',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  adr_certificate: {
    code: 'adr_certificate',
    title: 'ADR certificate',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  adr: {
    code: 'adr',
    title: 'ADR certificate',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  swiadectwo_kierowcy: {
    code: 'swiadectwo_kierowcy',
    title: 'Świadectwo kierowcy',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  driver_certificate: {
    code: 'driver_certificate',
    title: 'Driver certificate',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  // Medical and tests
  medical_certificate: {
    code: 'medical_certificate',
    title: 'Medical certificate',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  criminal_record: {
    code: 'criminal_record',
    title: 'Criminal record',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  psychology_test: {
    code: 'psychology_test',
    title: 'Psychological tests',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Test result' }],
  },
  psych_tests: {
    code: 'psych_tests',
    title: 'Psychological tests',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Test result' }],
  },
  // Work permits
  work_permit: {
    code: 'work_permit',
    title: 'Work permit',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Permit' }, { code: 'back', label: 'Back side', optional: true }],
  },
  decision: {
    code: 'decision',
    title: 'Decision',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Decision document' }],
  },
  // A4 documents
  contract: {
    code: 'contract',
    title: 'Contract',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'page_1', label: 'Page 1' }, { code: 'page_2', label: 'Page 2', optional: true }],
  },
  employment_contract: {
    code: 'employment_contract',
    title: 'Employment contract',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'page_1', label: 'Page 1' }, { code: 'page_2', label: 'Page 2', optional: true }],
  },
  insurance: {
    code: 'insurance',
    title: 'Insurance',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Insurance document' }],
  },
  bhp: {
    code: 'bhp',
    title: 'BHP training',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Certificate' }],
  },
  assignment: {
    code: 'assignment',
    title: 'Assignment',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Assignment document' }],
  },
  accommodation: {
    code: 'accommodation',
    title: 'Accommodation',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Accommodation document' }],
  },
  bank_account_confirmation: {
    code: 'bank_account_confirmation',
    title: 'Bank statement',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Bank document' }],
  },
  pesel: {
    code: 'pesel',
    title: 'PESEL',
    aspectRatio: 148 / 105,
    orientation: 'landscape',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'PESEL document' }],
  },
  // Photo
  photo: {
    code: 'photo',
    title: 'Photo 35x45',
    aspectRatio: 35 / 45,
    orientation: 'portrait',
    minResolution: 800,
    steps: [{ code: 'front', label: 'Photo' }],
  },
  photo_35x45: {
    code: 'photo_35x45',
    title: 'Photo 35x45',
    aspectRatio: 35 / 45,
    orientation: 'portrait',
    minResolution: 800,
    steps: [{ code: 'front', label: 'Photo' }],
  },
  // A4 fallback
  a4_form: {
    code: 'a4_form',
    title: 'A4 document',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1600,
    steps: [{ code: 'front', label: 'Full page' }],
  },
  // Default fallback
  additional_document: {
    code: 'additional_document',
    title: 'Additional document',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Document' }],
  },
  other: {
    code: 'other',
    title: 'Other document',
    aspectRatio: 210 / 297,
    orientation: 'portrait',
    minResolution: 1400,
    steps: [{ code: 'front', label: 'Document' }],
  },
}

const DEFAULT_PRESET: ScannerPreset = {
  code: 'default',
  title: 'Document',
  aspectRatio: 4 / 3,
  orientation: 'portrait',
  minResolution: 1000,
  steps: COMMON_CARD_STEPS,
}

export function getScannerPreset(code?: string | null): ScannerPreset {
  if (!code) return DEFAULT_PRESET
  
  // Try direct match
  if (code in SCANNER_PRESETS) {
    return SCANNER_PRESETS[code]
  }
  
  // Try normalized match
  const normalized = code.toLowerCase().trim()
  if (normalized in SCANNER_PRESETS) {
    return SCANNER_PRESETS[normalized]
  }
  
  // Try aliases mapping
  const aliases: Record<string, string> = {
    // Identity
    'identity_document': 'identity_document',
    'national_id': 'national_id',
    'residence_card': 'residence_card',
    'karta_pobytu': 'residence_card',
    // Driver licenses
    'driver_license_exchange': 'driver_license_exchange',
    'prawo_jazdy': 'driver_license',
    // Passports
    'passport_main': 'passport_main',
    'passport_all': 'passport_all',
    'travel_document': 'passport',
    // Tachograph
    'tachograph_card': 'tachograph_card',
    // Certificates
    'qualification_code95': 'qualification_code95',
    'code95': 'code95',
    'adr': 'adr',
    'adr_certificate': 'adr_certificate',
    'swiadectwo_kierowcy': 'swiadectwo_kierowcy',
    'driver_certificate': 'driver_certificate',
    // Medical
    'medical_certificate': 'medical_certificate',
    'criminal_record': 'criminal_record',
    'psychology_test': 'psychology_test',
    'psych_tests': 'psych_tests',
    // Work permits
    'work_permit': 'work_permit',
    'decision': 'decision',
    // A4
    'contract': 'contract',
    'employment_contract': 'employment_contract',
    'insurance': 'insurance',
    'bhp': 'bhp',
    'assignment': 'assignment',
    'accommodation': 'accommodation',
    'bank_account_confirmation': 'bank_account_confirmation',
    'pesel': 'pesel',
    // Photo
    'photo': 'photo',
    'photo_35x45': 'photo_35x45',
    // Fallback
    'additional_document': 'additional_document',
    'other': 'other',
  }
  
  const mapped = aliases[normalized]
  if (mapped && mapped in SCANNER_PRESETS) {
    return SCANNER_PRESETS[mapped]
  }
  
  return DEFAULT_PRESET
}
