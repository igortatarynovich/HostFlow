import api from './client'
import type { Candidate } from './types'

type Entry = { value: Candidate; ts: number }

const cache = new Map<string, Entry>()
const inflight = new Map<string, Promise<void>>()

const TTL_MS = 2 * 60 * 1000

const isFresh = (entry: Entry | undefined): entry is Entry =>
  Boolean(entry && Date.now() - entry.ts < TTL_MS)

export function getCachedCandidate(id: string): Candidate | null {
  const entry = cache.get(id)
  if (isFresh(entry)) return entry.value
  return null
}

export function setCachedCandidate(id: string, value: Candidate) {
  cache.set(id, { value, ts: Date.now() })
}

export async function prefetchCandidate(id: string): Promise<void> {
  if (!id) return
  if (getCachedCandidate(id)) return
  if (inflight.has(id)) return inflight.get(id)

  const req = api
    .get(`/candidates/${id}`)
    .then(({ data }) => {
      if (data) setCachedCandidate(id, data as Candidate)
    })
    .catch(() => {
      /* ignore prefetch errors */
    })
    .finally(() => {
      inflight.delete(id)
    })

  inflight.set(id, req)
  return req
}
