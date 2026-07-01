/** Logical dossier blocks — aligned with backend `VERIFICATION_SLOT_DEFS` / HR dossier. */
export type RecruitmentDossierBlockDef = {
  key: string
  docTypes: string[]
  dataOnly?: boolean
}

export const RECRUITMENT_DOSSIER_BLOCKS: RecruitmentDossierBlockDef[] = [
  {
    key: 'Contacts & address',
    docTypes: [],
    dataOnly: true,
  },
  {
    key: 'Passport / ID',
    docTypes: ['passport', 'national_id', 'identity_document', 'id_card', 'identity_card', 'passport_scan'],
  },
  {
    key: 'Legal stay',
    docTypes: ['legal_stay', 'residence_permit', 'residence_card', 'karta_pobytu', 'visa', 'visa_d'],
  },
  {
    key: 'Work permit',
    docTypes: ['work_permit', 'work_permit_application', 'oswiadczenie', 'zezwolenie_a'],
  },
  {
    key: 'Driver license',
    docTypes: ['driver_license', 'prawo_jazdy', 'eu_driver_license', 'swiadectwo_kierowcy'],
  },
  {
    key: 'Code95',
    docTypes: ['code95', 'qualification_code95'],
  },
  {
    key: 'Tacho card',
    docTypes: ['tacho_card', 'tachograph_card', 'karta_tachografu'],
  },
  {
    key: 'Medical',
    docTypes: ['medical', 'medical_certificate', 'badania_lekarskie'],
  },
  {
    key: 'Psychological',
    docTypes: ['psychological', 'psychological_certificate', 'psychotest'],
  },
  {
    key: 'Work experience',
    docTypes: ['employment_record', 'swiadectwo_pracy', 'work_certificate', 'employment_history'],
  },
]

function normType(raw: string): string {
  return String(raw || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

export type RecruitmentBlockStatus = 'ready' | 'missing' | 'issue' | 'optional' | 'data'

export function recruitmentBlockStatuses(
  blocks: RecruitmentDossierBlockDef[],
  missing: string[],
  problematic: string[],
): Array<{ block: RecruitmentDossierBlockDef; status: RecruitmentBlockStatus }> {
  const missingSet = new Set(missing.map(normType))
  const problematicSet = new Set(problematic.map(normType))

  return blocks.map((block) => {
    if (block.dataOnly) {
      return { block, status: 'data' as const }
    }
    const types = block.docTypes.map(normType)
    if (types.some((t) => problematicSet.has(t))) {
      return { block, status: 'issue' as const }
    }
    if (types.some((t) => missingSet.has(t))) {
      return { block, status: 'missing' as const }
    }
    if (types.length === 0) {
      return { block, status: 'optional' as const }
    }
    return { block, status: 'ready' as const }
  })
}
