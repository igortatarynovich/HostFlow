import type { PresentationFieldInput } from '../api/intakeForms'
import { launchSearchRoleDefaults, type SearchRole } from './launchSearchRoleDefaults'

export { INTAKE_SECTION_ORDER } from './intakePresentationFieldOptions'

type IntakeSpec = {
  qualified_code: string
  sort_order: number
  intake_level: 'required' | 'optional' | 'hidden'
  widget_hint?: string | null
}

const OFFICE_SPECS: IntakeSpec[] = [
  { qualified_code: 'recruitment.candidate.first_name', sort_order: 10, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.last_name', sort_order: 20, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.contacts.phone', sort_order: 30, intake_level: 'required', widget_hint: 'phone' },
  { qualified_code: 'recruitment.candidate.contacts.email', sort_order: 40, intake_level: 'required', widget_hint: 'email' },
  { qualified_code: 'platform.identity.citizenship', sort_order: 50, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'platform.identity.birth_date', sort_order: 60, intake_level: 'optional', widget_hint: 'date' },
  { qualified_code: 'recruitment.candidate.personal.current_location', sort_order: 70, intake_level: 'optional', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.experience.years_similar_role', sort_order: 80, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.personal.residency_status', sort_order: 90, intake_level: 'optional', widget_hint: 'select' },
]

const WAREHOUSE_SPECS: IntakeSpec[] = [
  { qualified_code: 'recruitment.candidate.first_name', sort_order: 10, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.last_name', sort_order: 20, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.contacts.phone', sort_order: 30, intake_level: 'required', widget_hint: 'phone' },
  { qualified_code: 'recruitment.candidate.contacts.email', sort_order: 40, intake_level: 'optional', widget_hint: 'email' },
  { qualified_code: 'platform.identity.citizenship', sort_order: 50, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.personal.current_location', sort_order: 60, intake_level: 'optional', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.personal.residency_status', sort_order: 70, intake_level: 'optional', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.qualifications.forklift_license', sort_order: 80, intake_level: 'required', widget_hint: 'yes_no' },
]

const DRIVER_SPECS: IntakeSpec[] = [
  { qualified_code: 'recruitment.candidate.first_name', sort_order: 10, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.last_name', sort_order: 20, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.contacts.phone', sort_order: 30, intake_level: 'required', widget_hint: 'phone' },
  { qualified_code: 'recruitment.candidate.contacts.email', sort_order: 40, intake_level: 'optional', widget_hint: 'email' },
  { qualified_code: 'platform.identity.citizenship', sort_order: 50, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'platform.identity.birth_date', sort_order: 60, intake_level: 'optional', widget_hint: 'date' },
  { qualified_code: 'recruitment.candidate.personal.residency_status', sort_order: 70, intake_level: 'optional', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.experience.years_ce', sort_order: 80, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.experience.trailer_types[]', sort_order: 90, intake_level: 'required', widget_hint: 'multiselect' },
  { qualified_code: 'recruitment.candidate.qualifications.eu_license_with_code_95', sort_order: 100, intake_level: 'required', widget_hint: 'yes_no' },
  { qualified_code: 'recruitment.candidate.qualifications.tachograph_card', sort_order: 110, intake_level: 'required', widget_hint: 'yes_no' },
  { qualified_code: 'recruitment.candidate.personal.has_adr', sort_order: 120, intake_level: 'optional', widget_hint: 'yes_no' },
]

const GENERAL_SPECS: IntakeSpec[] = [
  { qualified_code: 'recruitment.candidate.first_name', sort_order: 10, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.last_name', sort_order: 20, intake_level: 'required' },
  { qualified_code: 'recruitment.candidate.contacts.phone', sort_order: 30, intake_level: 'required', widget_hint: 'phone' },
  { qualified_code: 'recruitment.candidate.contacts.email', sort_order: 40, intake_level: 'optional', widget_hint: 'email' },
  { qualified_code: 'platform.identity.citizenship', sort_order: 50, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.personal.current_location', sort_order: 60, intake_level: 'optional', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.personal.residency_status', sort_order: 70, intake_level: 'required', widget_hint: 'select' },
  { qualified_code: 'recruitment.candidate.experience.years_similar_role', sort_order: 80, intake_level: 'optional', widget_hint: 'select' },
]

const SPECS_BY_ROLE: Record<SearchRole, IntakeSpec[]> = {
  driver: DRIVER_SPECS,
  warehouse: WAREHOUSE_SPECS,
  office: OFFICE_SPECS,
  other: GENERAL_SPECS,
}

function specsToPresentationFields(specs: IntakeSpec[]): PresentationFieldInput[] {
  return specs.map((row) => ({
    qualified_code: row.qualified_code,
    intake_level: row.intake_level,
    sort_order: row.sort_order,
    widget_hint: row.widget_hint ?? null,
  }))
}

export async function launchSearchIntakeFields(role: SearchRole): Promise<PresentationFieldInput[]> {
  const defaults = launchSearchRoleDefaults(role)
  const specs = SPECS_BY_ROLE[role] ?? SPECS_BY_ROLE.driver
  const fields = specsToPresentationFields(specs)
  if (fields.length > defaults.maxIntakeFields) {
    return fields.slice(0, defaults.maxIntakeFields)
  }
  return fields
}

export function launchSearchIntakeSpecs(role: SearchRole): IntakeSpec[] {
  return SPECS_BY_ROLE[role] ?? SPECS_BY_ROLE.driver
}

type PresentationFieldLike = {
  qualified_code: string
  widget_hint?: string | null
}

/** True when form predates role-specific questionnaires (short form or missing widget hints). */
export function isLaunchSearchFormStale(
  role: SearchRole,
  presentationFields: PresentationFieldLike[],
): boolean {
  const expected = launchSearchIntakeSpecs(role)
  const actualByCode = new Map(
    presentationFields.map((row) => [String(row.qualified_code || '').trim(), row]),
  )
  for (const spec of expected) {
    const actual = actualByCode.get(spec.qualified_code)
    if (!actual) return true
    if (spec.widget_hint && !String(actual.widget_hint || '').trim()) return true
  }
  return actualByCode.size < expected.length
}
