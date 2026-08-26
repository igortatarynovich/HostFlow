import { listCandidateProfiles } from '../api/candidate_profiles'
import { listCompanies, settings } from '../api/client'
import { funnelHasReadyForHandoff, listFunnels } from '../api/funnels'
import { isHandoffEnabledForCompany, listTenantLinks } from '../api/tenantLinks'
import { updateVacancy } from '../api/vacancies'
import {
  launchSearchRoleDefaults,
  type SearchRole,
} from './launchSearchRoleDefaults'

export type SetupVacancyDefaultsResult = {
  funnelId: string | null
  funnelName: string | null
  profileId: string | null
  profileName: string | null
}

function pickDefaultFunnel(
  funnels: Awaited<ReturnType<typeof listFunnels>>,
  requireHandoffReady = false,
) {
  const candidateFunnels = funnels.filter((f) => f.type === 'candidate')
  const pool = requireHandoffReady
    ? candidateFunnels.filter((funnel) => funnelHasReadyForHandoff(funnel))
    : candidateFunnels
  return pool.find((f) => f.is_default) ?? pool[0] ?? null
}

function pickRoleProfile(
  profiles: Awaited<ReturnType<typeof listCandidateProfiles>>,
  role: SearchRole,
) {
  const spec = launchSearchRoleDefaults(role)
  return (
    profiles.find((p) => p.code === spec.candidateProfileCode) ??
    profiles.find((p) => p.code === 'driver_ce_default') ??
    profiles.find((p) => p.is_system) ??
    profiles[0] ??
    null
  )
}

function pickRoleFunnel(
  funnels: Awaited<ReturnType<typeof listFunnels>>,
  role: SearchRole,
  profile: Awaited<ReturnType<typeof listCandidateProfiles>>[number] | null,
  requireHandoffReady = false,
) {
  const spec = launchSearchRoleDefaults(role)
  const candidateFunnels = funnels.filter((f) => f.type === 'candidate')
  const eligible = requireHandoffReady
    ? candidateFunnels.filter((funnel) => funnelHasReadyForHandoff(funnel))
    : candidateFunnels
  const byName = eligible.find((f) => f.name === spec.funnelName)
  if (byName) return byName
  if (profile?.funnel_id) {
    const linked = eligible.find((f) => f.id === profile.funnel_id)
    if (linked) return linked
  }
  return pickDefaultFunnel(funnels, requireHandoffReady)
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

async function resolveOperatingCompanyId(): Promise<string | null> {
  const companiesRaw = await listCompanies({ limit: 100 }).catch(() => [])
  const companiesList = Array.isArray(companiesRaw)
    ? companiesRaw
    : ((companiesRaw as { items?: Array<Record<string, unknown>> })?.items ?? [])
  const operating = companiesList.find((row) => companyRole(row.extra) === 'operating')
  return operating?.id ? String(operating.id) : null
}

export async function applySetupVacancyDefaults(
  vacancyId: string,
  companyId: string,
  role: SearchRole = 'driver',
): Promise<SetupVacancyDefaultsResult> {
  let funnelCompanyId = companyId
  const tenantId = String(settings.get() || '').trim()
  const [funnelsInitial, profiles, links] = await Promise.all([
    listFunnels({ companyId: funnelCompanyId, type: 'candidate', moduleKey: 'recruitment' }).catch(() => []),
    listCandidateProfiles({ is_active: true }).catch(() => []),
    tenantId ? listTenantLinks(tenantId).catch(() => []) : Promise.resolve([]),
  ])
  let funnels = funnelsInitial
  const requireHandoffReady = isHandoffEnabledForCompany(links, companyId)

  const profile = pickRoleProfile(profiles, role)
  let funnel = pickRoleFunnel(funnels, role, profile, requireHandoffReady)

  if (!funnel) {
    const operatingCompanyId = await resolveOperatingCompanyId()
    if (operatingCompanyId && operatingCompanyId !== funnelCompanyId) {
      funnelCompanyId = operatingCompanyId
      funnels = await listFunnels({
        companyId: funnelCompanyId,
        type: 'candidate',
        moduleKey: 'recruitment',
      }).catch(() => [])
      funnel = pickRoleFunnel(funnels, role, profile, requireHandoffReady)
    }
  }

  if (!funnel) {
    funnel = pickDefaultFunnel(funnels, requireHandoffReady)
  }

  const patch: Record<string, string | null> = {}
  if (funnel?.id) patch.funnel_id = funnel.id
  if (profile?.id) patch.candidate_profile_id = profile.id

  if (Object.keys(patch).length > 0) {
    await updateVacancy(vacancyId, patch)
  }

  return {
    funnelId: funnel?.id ?? null,
    funnelName: funnel?.name ?? null,
    profileId: profile?.id ?? null,
    profileName: profile?.name ?? null,
  }
}
