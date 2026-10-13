// Snapshot of GET /candidates kept in localStorage between visits.
// The blob is one slot per tenant, so it must remember which filter
// signature produced it. Restoring a search hit into the unfiltered
// cache key made the list stick on that one candidate after the search
// box was cleared.

import type { CandidateListCacheEntry, CandidatesListInsights, UICandidate } from './types'

export type StoredCandidateList = CandidateListCacheEntry & {
  cacheKey: string
}

function normalizeListInsights(raw: unknown): CandidatesListInsights | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  return {
    total: Number(o.total) || 0,
    new_count: Number(o.new_count) || 0,
    docs_ready: Number(o.docs_ready) || 0,
    docs_attention: Number(o.docs_attention) || 0,
    docs_ordered: Number(o.docs_ordered) || 0,
    docs_incomplete: Number(o.docs_incomplete) || 0,
    ops_in_work: Number(o.ops_in_work) || 0,
    bottleneck_no_contact: Number(o.bottleneck_no_contact) || 0,
    bottleneck_docs_wait: Number(o.bottleneck_docs_wait) || 0,
    bottleneck_interview_pending: Number(o.bottleneck_interview_pending) || 0,
    unassigned_recruiter: Number(o.unassigned_recruiter) || 0,
  }
}

export function parseStoredCandidateList(
  raw: string | null,
  expectedCacheKey: string,
  now: number,
  ttlMs: number,
): CandidateListCacheEntry | null {
  if (!raw || !expectedCacheKey) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  if (!parsed || typeof parsed !== 'object') return null
  const row = parsed as Record<string, unknown>
  // Legacy blobs have no cacheKey. They were written for whatever filter
  // was active at the time (often a search) and must not fill another view.
  if (typeof row.cacheKey !== 'string' || row.cacheKey !== expectedCacheKey) return null
  if (typeof row.total === 'number' && row.total === 0) return null
  if (
    typeof row.total === 'number' &&
    row.total > 0 &&
    (!Array.isArray(row.items) || row.items.length === 0)
  ) {
    return null
  }
  const ts = typeof row.timestamp === 'number' ? row.timestamp : 0
  if (now - ts > ttlMs) return null
  if (!Array.isArray(row.items)) return null
  const insights = normalizeListInsights(row.insights)
  return {
    items: row.items as UICandidate[],
    total: typeof row.total === 'number' ? row.total : row.items.length,
    timestamp: ts,
    ...(insights ? { insights } : {}),
  }
}
