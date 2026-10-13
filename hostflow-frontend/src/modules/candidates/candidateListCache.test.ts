import { describe, expect, it } from 'vitest'
import { parseStoredCandidateList } from './candidateListCache'

const NOW = 1_700_000_000_000
const TTL = 24 * 60 * 60 * 1000

function snapshot(cacheKey: string, id = 'cand-1') {
  return JSON.stringify({
    cacheKey,
    items: [{ id, first_name: 'Jan', last_name: 'Kowalski' }],
    total: 1,
    timestamp: NOW - 1_000,
  })
}

describe('parseStoredCandidateList', () => {
  it('restores a snapshot only for the same filter cache key', () => {
    const entry = parseStoredCandidateList(snapshot('candidates:list:t:abc:p0'), 'candidates:list:t:abc:p0', NOW, TTL)
    expect(entry?.items).toHaveLength(1)
    expect(entry?.items[0]?.id).toBe('cand-1')
  })

  it('ignores a search snapshot when the search box is cleared', () => {
    const searchKey = 'candidates:list:t:search:p0'
    const openKey = 'candidates:list:t:open:p0'
    expect(parseStoredCandidateList(snapshot(searchKey), openKey, NOW, TTL)).toBeNull()
  })

  it('ignores legacy blobs that have no cache key', () => {
    const legacy = JSON.stringify({
      items: [{ id: 'cand-1', first_name: 'Jan', last_name: 'Kowalski' }],
      total: 1,
      timestamp: NOW - 1_000,
    })
    expect(parseStoredCandidateList(legacy, 'candidates:list:t:open:p0', NOW, TTL)).toBeNull()
  })

  it('ignores an expired snapshot', () => {
    const raw = JSON.stringify({
      cacheKey: 'candidates:list:t:open:p0',
      items: [{ id: 'cand-1' }],
      total: 1,
      timestamp: NOW - TTL - 1,
    })
    expect(parseStoredCandidateList(raw, 'candidates:list:t:open:p0', NOW, TTL)).toBeNull()
  })
})
