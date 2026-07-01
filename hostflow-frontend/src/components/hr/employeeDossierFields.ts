import type { WorkforceEmployee, WorkforceEmployeeOperationalProfile } from '../../api/workforce'

export type DossierFieldDef = {
  key: string
  labelKey: string
  defaultLabel: string
}

export const DOSSIER_IDENTITY_FIELDS: DossierFieldDef[] = [
  { key: 'legal_name', labelKey: 'app.hr.dossier.fields.legal_name', defaultLabel: 'Full name (as in documents)' },
  { key: 'birth_date', labelKey: 'app.hr.dossier.fields.birth_date', defaultLabel: 'Date of birth' },
  { key: 'citizenship', labelKey: 'app.hr.dossier.fields.citizenship', defaultLabel: 'Citizenship' },
  { key: 'phone', labelKey: 'app.hr.dossier.fields.phone', defaultLabel: 'Phone' },
  { key: 'email', labelKey: 'app.hr.dossier.fields.email', defaultLabel: 'Email' },
  { key: 'address', labelKey: 'app.hr.dossier.fields.address', defaultLabel: 'Address' },
  { key: 'pesel', labelKey: 'app.hr.dossier.fields.pesel', defaultLabel: 'PESEL' },
  { key: 'passport_number', labelKey: 'app.hr.dossier.fields.passport_number', defaultLabel: 'Passport number' },
  { key: 'passport_expiry', labelKey: 'app.hr.dossier.fields.passport_expiry', defaultLabel: 'Passport valid until' },
  { key: 'driver_license_number', labelKey: 'app.hr.dossier.fields.driver_license_number', defaultLabel: 'Driver license number' },
  { key: 'driver_license_expiry', labelKey: 'app.hr.dossier.fields.driver_license_expiry', defaultLabel: 'Driver license valid until' },
  { key: 'code95_expiry', labelKey: 'app.hr.dossier.fields.code95_expiry', defaultLabel: 'Code 95 valid until' },
  { key: 'tachograph_expiry', labelKey: 'app.hr.dossier.fields.tachograph_expiry', defaultLabel: 'Tachograph card valid until' },
  { key: 'medical_expiry', labelKey: 'app.hr.dossier.fields.medical_expiry', defaultLabel: 'Medical exam valid until' },
  { key: 'language', labelKey: 'app.hr.dossier.fields.language', defaultLabel: 'Languages' },
  { key: 'emergency_contact', labelKey: 'app.hr.dossier.fields.emergency_contact', defaultLabel: 'Emergency contact' },
]

export const DOSSIER_LEGAL_FIELDS: DossierFieldDef[] = [
  { key: 'work_country', labelKey: 'app.hr.dossier.fields.work_country', defaultLabel: 'Work country' },
  { key: 'legal_status', labelKey: 'app.hr.dossier.fields.legal_status', defaultLabel: 'Legal stay basis' },
  { key: 'eligibility_status', labelKey: 'app.hr.dossier.fields.eligibility_status', defaultLabel: 'Work eligibility' },
  { key: 'work_permit_valid_to', labelKey: 'app.hr.dossier.fields.work_permit_valid_to', defaultLabel: 'Work permit valid until' },
  { key: 'legal_stay_valid_to', labelKey: 'app.hr.dossier.fields.legal_stay_valid_to', defaultLabel: 'Legal stay valid until' },
]

export function buildDossierIdentityValues(
  profile: WorkforceEmployeeOperationalProfile,
  employee: WorkforceEmployee,
): Record<string, string> {
  const dossierIdentity = ((profile as Record<string, unknown>).employee_dossier as Record<string, unknown> | undefined)?.identity as
    | Record<string, unknown>
    | undefined
  const dossierLegal = ((profile as Record<string, unknown>).employee_dossier as Record<string, unknown> | undefined)?.legal as
    | Record<string, unknown>
    | undefined
  const snapshotPersonal = ((profile.hire_snapshot || {}) as Record<string, unknown>).personal_data as Record<string, unknown> | undefined
  const metaPersonal = ((employee.meta || {}) as Record<string, unknown>).personal_data as Record<string, unknown> | undefined
  const recruiterSummary = (profile.recruiter_summary || {}) as Record<string, unknown>
  const merged = {
    ...(snapshotPersonal || {}),
    ...(dossierIdentity || {}),
    ...(metaPersonal || {}),
  } as Record<string, unknown>
  const addressRaw = merged.address
  const address =
    typeof addressRaw === 'string'
      ? addressRaw
      : addressRaw && typeof addressRaw === 'object'
        ? JSON.stringify(addressRaw)
        : ''

  const identity: Record<string, string> = {
    legal_name: String(merged.legal_name || employee.display_name || ''),
    birth_date: String(merged.birth_date || ''),
    citizenship: String(merged.citizenship || recruiterSummary.citizenship || ''),
    phone: String(merged.phone || recruiterSummary.phone || ''),
    email: String(merged.email || recruiterSummary.email || ''),
    address,
    pesel: String(merged.pesel || ''),
    passport_number: String(merged.passport_number || ''),
    passport_expiry: String(merged.passport_expiry || merged.passport_valid_to || ''),
    driver_license_number: String(merged.driver_license_number || merged.license_number || ''),
    driver_license_expiry: String(
      merged.driver_license_expiry || merged.driver_license_valid_to || merged.license_valid_to || '',
    ),
    code95_expiry: String(merged.code95_expiry || merged.code_95_expiry || ''),
    tachograph_expiry: String(merged.tachograph_expiry || merged.tachograph_card_expiry || merged.tacho_card_expiry || ''),
    medical_expiry: String(merged.medical_expiry || merged.medical_valid_to || merged.medical_exam_expiry || ''),
    language: String(merged.language || ''),
    emergency_contact: String(merged.emergency_contact || ''),
  }

  const legal: Record<string, string> = {
    work_country: String(dossierLegal?.work_country || recruiterSummary.work_country || ''),
    legal_status: String(dossierLegal?.legal_status || recruiterSummary.legal_status || ''),
    eligibility_status: String(dossierLegal?.eligibility_status || ''),
    work_permit_valid_to: String(dossierLegal?.work_permit_valid_to || ''),
    legal_stay_valid_to: String(dossierLegal?.legal_stay_valid_to || ''),
  }

  return { ...identity, ...legal }
}
