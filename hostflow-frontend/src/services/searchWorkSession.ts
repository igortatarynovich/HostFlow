import { CRM_APP_PATHS } from '../app/crmAppPaths'

const STORAGE_KEY = 'hf:search-work-session'

export type SearchWorkKind = 'call' | 'docs' | 'interview'

export type SearchWorkSession = {
  searchId: string
  kind: SearchWorkKind | string
  queue: string[]
  index: number
  returnPath: string
}

function readRaw(): SearchWorkSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as SearchWorkSession
    if (!parsed?.searchId || !Array.isArray(parsed.queue) || parsed.queue.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

function write(session: SearchWorkSession | null) {
  if (typeof window === 'undefined') return
  try {
    if (!session) window.sessionStorage.removeItem(STORAGE_KEY)
    else window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    /* ignore */
  }
}

export function getSearchWorkSession(): SearchWorkSession | null {
  return readRaw()
}

export function startSearchWorkSession(input: {
  searchId: string
  kind: SearchWorkKind | string
  queue: string[]
  returnPath: string
}): SearchWorkSession {
  const session: SearchWorkSession = {
    searchId: input.searchId,
    kind: input.kind,
    queue: input.queue.filter(Boolean),
    index: 0,
    returnPath: input.returnPath,
  }
  write(session)
  return session
}

export function getCurrentWorkCandidateId(session: SearchWorkSession | null = getSearchWorkSession()): string | null {
  if (!session) return null
  return session.queue[session.index] ?? null
}

export function advanceSearchWorkSession(): string | null {
  const session = readRaw()
  if (!session) return null
  const nextIndex = session.index + 1
  if (nextIndex >= session.queue.length) {
    write(null)
    return null
  }
  const updated = { ...session, index: nextIndex }
  write(updated)
  return updated.queue[nextIndex] ?? null
}

export function cancelSearchWorkSession() {
  write(null)
}

export function candidateHref(candidateId: string): string {
  return `${CRM_APP_PATHS.candidates}/${encodeURIComponent(candidateId)}`
}

export function isActiveWorkSessionForCandidate(candidateId: string): boolean {
  const session = getSearchWorkSession()
  if (!session) return false
  return session.queue[session.index] === candidateId
}
