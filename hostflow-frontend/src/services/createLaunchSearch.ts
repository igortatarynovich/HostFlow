import { createClientCompany, createCompany, listCompanies, listOwnCompanies } from '../api/client'
import { createVacancy, updateVacancy } from '../api/vacancies'
import { createIntakeForm, type PresentationFieldInput } from '../api/intakeForms'
import { declareManualCandidateIntake } from '../api/onboarding'
import { setupLaunchSearchVacancy } from '../api/vacancies'
import { buildPublicIntakeUrl } from '../utils/publicIntakeUrl'
import {
  launchSearchRoleDefaults,
  type SearchRole,
} from '../utils/launchSearchRoleDefaults'
import { buildLaunchSearchTitle } from '../utils/launchSearchI18n'
import { detectStoredLocale } from '../i18n'
import { launchSearchIntakeFields } from '../utils/launchSearchIntakeFields'

export type { SearchRole }

export type CreateLaunchSearchInput = {
  role: SearchRole
  roleOtherLabel?: string
  target: 'own' | 'client'
  clientName?: string
  /** When set, skips creating a new client company and uses this CRM client id. */
  existingClientId?: string
}

export type LaunchSearchResult = {
  searchId: string
  name: string
  companyId: string
  companyName: string
  leadFormId: string
  publicSlug: string
  publicUrl: string
  searchRole: SearchRole
}

function buildSearchTitle(role: SearchRole, companyName: string, otherLabel?: string): string {
  return buildLaunchSearchTitle(role, companyName, detectStoredLocale(), otherLabel)
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48)
}

function buildPublicSlug(companyName: string, role: SearchRole): string {
  const base = slugify(`${companyName}-${role}`) || 'search'
  return `${base}-${Date.now().toString(36).slice(-5)}`
}

async function rolePresentationFields(role: SearchRole): Promise<PresentationFieldInput[]> {
  return launchSearchIntakeFields(role)
}

function companyRole(extra: unknown): string {
  if (!extra || typeof extra !== 'object') return ''
  return String(
    (extra as Record<string, unknown>).company_role ??
      (extra as Record<string, unknown>).company_kind ??
      '',
  )
    .trim()
    .toLowerCase()
}

export async function resolveOperatingCompanyId(): Promise<{ companyId: string; companyName: string }> {
  const own = await listOwnCompanies()
  const ownCompany = own.items?.[0]
  if (!ownCompany?.id) {
    throw new Error('own_company_missing')
  }

  const companiesRaw = await listCompanies({ limit: 100 }).catch(() => [])
  const companiesList = Array.isArray(companiesRaw)
    ? companiesRaw
    : ((companiesRaw as { items?: Array<Record<string, unknown>> })?.items ?? [])

  const operating = companiesList.find((row) => companyRole(row.extra) === 'operating')
  if (operating?.id) {
    return {
      companyId: String(operating.id),
      companyName: String(operating.name ?? ownCompany.name ?? operating.id),
    }
  }

  const ownExtra =
    ownCompany.extra && typeof ownCompany.extra === 'object'
      ? (ownCompany.extra as Record<string, unknown>)
      : {}
  const created = await createCompany({
    name: String(ownCompany.name ?? 'Company'),
    company_role: 'operating',
    company_type: String(ownExtra.business_type ?? 'employer'),
    extra: {
      company_role: 'operating',
      company_type: ownExtra.business_type ?? 'employer',
      setup_source: 'launch_search',
      mirrored_own_company_id: String(ownCompany.id),
    },
  })

  const companyId = String((created as { id?: string })?.id ?? '')
  if (!companyId) throw new Error('operating_company_create_failed')

  return {
    companyId,
    companyName: String((created as { name?: string })?.name ?? ownCompany.name ?? companyId),
  }
}

export async function createLaunchSearch(input: CreateLaunchSearchInput): Promise<LaunchSearchResult> {
  const roleSpec = launchSearchRoleDefaults(input.role)
  let companyId = ''
  let companyName = ''

  if (input.existingClientId) {
    companyId = input.existingClientId
    companyName = (input.clientName || '').trim() || 'Клиент'
    if (!companyId) throw new Error('client_id_required')
  } else if (input.target === 'client') {
    const clientLabel = (input.clientName || '').trim()
    if (!clientLabel) throw new Error('client_name_required')
    const created = await createClientCompany({
      name: clientLabel,
      extra: { company_role: 'client', setup_source: 'launch_search' },
    })
    companyId = String(created?.id ?? '')
    companyName = clientLabel
    if (!companyId) throw new Error('client_create_failed')
  } else {
    const operating = await resolveOperatingCompanyId()
    companyId = operating.companyId
    companyName = operating.companyName
  }

  const title = buildSearchTitle(input.role, companyName, input.roleOtherLabel)
  const vacancy = await createVacancy({
    company_id: companyId,
    title,
    employment_type: 'full_time',
    extra: {
      launch_search: true,
      search_role: input.role,
      setup_source: 'launch_search',
    },
  })
  const vacancyId = String((vacancy as { id?: string })?.id ?? '')
  if (!vacancyId) throw new Error('vacancy_create_failed')

  const setup = await setupLaunchSearchVacancy(vacancyId, input.role)
  if (!setup.funnel_id) {
    throw new Error('launch_search_funnel_missing')
  }

  const publicSlug = buildPublicSlug(companyName, input.role)
  const fields = await rolePresentationFields(input.role)
  const intake = await createIntakeForm({
    title: title,
    public_slug: publicSlug,
    entity_profile_code: roleSpec.entityProfileCode,
    fields,
    is_active: true,
  })

  const leadFormId = String(intake.form?.id ?? '')
  const slug = String(intake.form?.public_slug ?? publicSlug)
  const publicUrl = buildPublicIntakeUrl({ leadFormSlug: slug, vacancyId })

  await updateVacancy(vacancyId, {
    extra: {
      launch_search: true,
      search_role: input.role,
      setup_source: 'launch_search',
      lead_form_id: leadFormId,
      lead_form_slug: slug,
    },
  })

  try {
    await declareManualCandidateIntake()
  } catch {
    // Intake form may already satisfy G6; non-fatal for money path.
  }

  return {
    searchId: vacancyId,
    name: title,
    companyId,
    companyName,
    leadFormId,
    publicSlug: slug,
    publicUrl,
    searchRole: input.role,
  }
}
