export type PrototypeSearch = {
  id: string
  name: string
  clientName: string
  licenseType: string
  channels: string[]
  assignee: string
  formUrl: string
  createdAt: string
  stats: { leads: number; candidates: number; interviews: number }
}

export const LAUNCH_SEARCH_STORAGE_KEY = 'hostflow-launch-search-prototype'

export function loadPrototypeSearches(): PrototypeSearch[] {
  try {
    const raw = sessionStorage.getItem(LAUNCH_SEARCH_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as PrototypeSearch[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function savePrototypeSearch(search: PrototypeSearch) {
  const existing = loadPrototypeSearches()
  sessionStorage.setItem(LAUNCH_SEARCH_STORAGE_KEY, JSON.stringify([search, ...existing]))
}
