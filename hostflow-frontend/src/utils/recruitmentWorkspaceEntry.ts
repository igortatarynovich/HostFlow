import { api } from '../api/client'
import { getOnboardingStatus } from '../api/client'
import { listVacancies } from '../api/vacancies'
import { CRM_APP_PATHS, recruitmentSearchPath } from '../app/crmAppPaths'
import {
  clearLastLaunchSearchId,
  persistLastLaunchSearchId,
  readLastLaunchSearchId,
} from '../services/launchSearchSession'
import { parseLaunchSearchVacancyExtra } from './searchHomeContext'
import { resolveDefaultAppHomeHref, resolveDefaultAppHomeSegment } from './defaultAppHome'

function isLaunchSearchVacancy(extra: unknown): boolean {
  return parseLaunchSearchVacancyExtra(extra).launch_search === true
}

async function listActiveLaunchSearches() {
  const vacancies = await listVacancies({
    limit: 100,
    order_by: 'updated_at',
    desc: true,
    is_archived: false,
  })
  const launchOnly = vacancies.filter((row) =>
    isLaunchSearchVacancy((row as { extra?: unknown }).extra),
  )
  return launchOnly.length > 0 ? launchOnly : vacancies
}

async function vacancyExists(vacancyId: string): Promise<boolean> {
  try {
    await api.get(`/vacancies/${encodeURIComponent(vacancyId)}`)
    return true
  } catch (err) {
    if ((err as { response?: { status?: number } })?.response?.status === 404) return false
    return true
  }
}

/**
 * After login / `/app` index: land in recruitment workspace when the tenant already runs подборы.
 * Launchpad stays for first-time users without any подбор.
 */
export async function resolveRecruitmentWorkspaceEntryHref(canOpenTasks: boolean): Promise<string> {
  const lastId = readLastLaunchSearchId()
  if (lastId) {
    if (await vacancyExists(lastId)) {
      return recruitmentSearchPath(lastId)
    }
    clearLastLaunchSearchId()
  }

  try {
    const status = await getOnboardingStatus()
    if (!status?.steps?.first_vacancy_created) {
      return resolveDefaultAppHomeHref(canOpenTasks)
    }

    const searches = await listActiveLaunchSearches()
    if (searches.length === 0) {
      if (status?.steps?.first_vacancy_created) {
        return CRM_APP_PATHS.recruitmentSearches
      }
      return resolveDefaultAppHomeHref(canOpenTasks)
    }

    const targetId = String(searches[0]?.id ?? '').trim()
    if (!targetId) {
      return resolveDefaultAppHomeHref(canOpenTasks)
    }

    persistLastLaunchSearchId(targetId)
    return recruitmentSearchPath(targetId)
  } catch {
    return resolveDefaultAppHomeHref(canOpenTasks)
  }
}

export async function resolveRecruitmentWorkspaceEntrySegment(canOpenTasks: boolean): Promise<string> {
  const href = await resolveRecruitmentWorkspaceEntryHref(canOpenTasks)
  const prefix = `${CRM_APP_PATHS.appShellPrefix}/`
  if (href.startsWith(prefix)) {
    return href.slice(prefix.length)
  }
  return href.replace(/^\//, '')
}
