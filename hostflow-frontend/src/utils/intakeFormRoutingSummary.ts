/** Operator-facing labels for intake form purpose, profile, and answer routing (ADR-022). */

import { CRM_APP_PATHS } from '../app/crmAppPaths'

export type FormPurposeKey =
  | 'inquiry'
  | 'application'
  | 'survey'
  | 'questionnaire'
  | 'registration'
  | string

export type FormDefinitionLike = {
  purpose?: string | null
  target_entity_profile_code?: string | null
  submission_policy?: {
    mode?: string | null
    match_policy?: Record<string, unknown> | null
  } | null
}

export type PurposeWizardOption = {
  purpose: FormPurposeKey
  label: string
  hint: string
  profilePrefix: string
}

export const PURPOSE_WIZARD_OPTIONS: PurposeWizardOption[] = [
  {
    purpose: 'inquiry',
    label: 'B2B inquiry',
    hint: 'Company asks for a service (e.g. targeted advertising). Answers land in Sales.',
    profilePrefix: 'service_sales.',
  },
  {
    purpose: 'application',
    label: 'Candidate application',
    hint: 'Recruitment questionnaire for drivers and other roles.',
    profilePrefix: 'recruitment.',
  },
  {
    purpose: 'survey',
    label: 'Survey',
    hint: 'Short feedback or qualification survey.',
    profilePrefix: 'service_sales.',
  },
  {
    purpose: 'questionnaire',
    label: 'Service request form',
    hint: 'Structured service intake with follow-up on an existing inquiry.',
    profilePrefix: 'service_sales.',
  },
]

const PURPOSE_LABELS: Record<string, string> = {
  inquiry: 'B2B inquiry',
  application: 'Candidate application',
  survey: 'Survey',
  questionnaire: 'Service request form',
  registration: 'Registration',
  update: 'Update',
  consent: 'Consent',
  document_collection: 'Document collection',
}

const PROFILE_LABELS: Record<string, string> = {
  'service_sales.targeted_advertising': 'Targeted advertising',
  'recruitment.candidate.driver_ce': 'Driver C+E',
  'recruitment.candidate.warehouse_worker': 'Warehouse worker',
}

export function purposeLabel(purpose: string | null | undefined): string {
  const key = String(purpose || 'inquiry').trim()
  return PURPOSE_LABELS[key] || key.replace(/_/g, ' ')
}

export function entityProfileLabel(code: string | null | undefined): string {
  const raw = String(code || '').trim()
  if (!raw) return '—'
  return PROFILE_LABELS[raw] || raw.split('.').slice(-1)[0]?.replace(/_/g, ' ') || raw
}

export function salesModuleLabel(entityProfileCode: string | null | undefined): string {
  const code = String(entityProfileCode || '')
  if (code.startsWith('service_sales.')) return 'Sales'
  if (code.startsWith('recruitment.')) return 'Recruitment'
  return 'CRM'
}

export function salesInboxPath(entityProfileCode: string | null | undefined): string {
  const code = String(entityProfileCode || '')
  if (code.startsWith('service_sales.')) return CRM_APP_PATHS.sales
  if (code.startsWith('recruitment.')) return CRM_APP_PATHS.recruitmentInbox
  return CRM_APP_PATHS.leads
}

export function publicSubmitBehaviorLabel(definition: FormDefinitionLike | null | undefined): string {
  const mode = String(definition?.submission_policy?.mode || 'match_or_create')
  if (mode === 'create') return 'Always create a new inquiry'
  if (mode === 'attach') return 'Always add to the selected inquiry'
  if (mode === 'match_or_create') return 'Find an existing inquiry or create a new one'
  if (mode === 'review') return 'Send to review queue for manual match'
  return mode.replace(/_/g, ' ')
}

export function personalInviteBehaviorLabel(): string {
  return 'Add answers to the inquiry you send the link from'
}

export function answersDestinationLabel(entityProfileCode: string | null | undefined): string {
  const code = String(entityProfileCode || '')
  if (code.startsWith('service_sales.')) return 'Submission + Sales inquiry'
  if (code.startsWith('recruitment.')) return 'Submission + candidate application'
  return 'Submission on lead/application'
}

export function managerDecisionLabel(entityProfileCode: string | null | undefined): string {
  const code = String(entityProfileCode || '')
  if (code.startsWith('service_sales.')) return 'Create client / clarify / reject'
  if (code.startsWith('recruitment.')) return 'Qualify / reject / next stage'
  return 'Manager decision in workspace'
}

export function filterProfilesForPurpose(
  profiles: Array<{ code: string; name: string }>,
  purpose: FormPurposeKey,
): Array<{ code: string; name: string }> {
  const option = PURPOSE_WIZARD_OPTIONS.find((row) => row.purpose === purpose)
  const prefix = option?.profilePrefix || ''
  if (!prefix) return profiles
  return profiles.filter((profile) => profile.code.startsWith(prefix))
}

export function defaultProfileForPurpose(
  profiles: Array<{ code: string; name: string }>,
  purpose: FormPurposeKey,
): string {
  const filtered = filterProfilesForPurpose(profiles, purpose)
  if (purpose === 'inquiry' || purpose === 'questionnaire' || purpose === 'survey') {
    const b2b = filtered.find((p) => p.code === 'service_sales.targeted_advertising')
    if (b2b) return b2b.code
  }
  if (purpose === 'application') {
    const driver = filtered.find((p) => p.code.includes('driver'))
    if (driver) return driver.code
  }
  return filtered[0]?.code || profiles[0]?.code || ''
}

export function slugifyFormTitle(title: string): string {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)
}
