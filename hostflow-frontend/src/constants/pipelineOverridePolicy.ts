/**
 * Doc types that cannot be waived (pipeline / handoff). Must stay in sync with
 * `backend/app/services/pipeline_override_policy.py` → NON_OVERRIDABLE_DOC_TYPES.
 * Includes common alias strings returned by rulesets / UI so filtering matches the API.
 */
const RAW_NON_OVERRIDABLE_DOC_TYPES = [
  // national_id (+ aliases)
  'national_id',
  'identity_document',
  'id_card',
  'dowod_osobisty',
  // passport
  'passport',
  'travel_document',
  'passport_non_eu',
  // residence
  'residence_permit',
  'residence_card',
  'karta_pobytu',
  // visa
  'visa',
  'visa_d',
  'visa_c',
  'entry_permit',
  'entry_permit_or_visa',
  // work authorization
  'work_permit',
  // legal / voivodeship
  'decision',
  'decyzja',
  'voivodeship_decision',
] as const

const NON_OVERRIDABLE_SET = new Set<string>(
  RAW_NON_OVERRIDABLE_DOC_TYPES.map((c) => c.toLowerCase()),
)

/**
 * When the API returned `effective_non_overridable_doc_types` (global + tenant extras),
 * use that set; otherwise fall back to the static catalog mirror.
 */
export function effectiveNonOverridableDocTypesSet(effectiveFromApi?: string[] | null): Set<string> {
  if (effectiveFromApi && Array.isArray(effectiveFromApi)) {
    const s = new Set<string>()
    for (const x of effectiveFromApi) {
      const k = String(x || '')
        .trim()
        .toLowerCase()
      if (k) s.add(k)
    }
    if (s.size) return s
  }
  return NON_OVERRIDABLE_SET
}

export function isNonOverridableDocTypeCode(
  code: string | null | undefined,
  effectiveSet?: Set<string> | null,
): boolean {
  const k = String(code || '')
    .trim()
    .toLowerCase()
  if (!k) return false
  const set = effectiveSet ?? NON_OVERRIDABLE_SET
  return set.has(k)
}
