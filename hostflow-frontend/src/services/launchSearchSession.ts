import type { LaunchSearchResult } from '../services/createLaunchSearch'

const SEARCH_SESSION_PREFIX = 'hostflow:launch-search:'
const LAST_SEARCH_ID_KEY = 'hostflow:last-launch-search-id'

export function persistLaunchSearch(result: LaunchSearchResult) {
  try {
    sessionStorage.setItem(`${SEARCH_SESSION_PREFIX}${result.searchId}`, JSON.stringify(result))
    localStorage.setItem(LAST_SEARCH_ID_KEY, result.searchId)
  } catch {
    // ignore
  }
}

export function readLastLaunchSearchId(): string | null {
  try {
    const id = localStorage.getItem(LAST_SEARCH_ID_KEY)?.trim()
    return id || null
  } catch {
    return null
  }
}

export function clearLastLaunchSearchId(): void {
  try {
    localStorage.removeItem(LAST_SEARCH_ID_KEY)
  } catch {
    /* ignore */
  }
}

export function persistLastLaunchSearchId(searchId: string): void {
  try {
    const id = searchId.trim()
    if (id) localStorage.setItem(LAST_SEARCH_ID_KEY, id)
  } catch {
    /* ignore */
  }
}

export function loadLaunchSearch(searchId: string): LaunchSearchResult | null {
  try {
    const raw = sessionStorage.getItem(`${SEARCH_SESSION_PREFIX}${searchId}`)
    if (!raw) return null
    return JSON.parse(raw) as LaunchSearchResult
  } catch {
    return null
  }
}
