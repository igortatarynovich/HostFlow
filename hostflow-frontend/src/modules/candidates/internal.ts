// src/modules/candidates/internal.ts
//
// Page-level helpers + module-scoped state previously declared at the top of
// `src/pages/Candidates.tsx`. Extracted as the first step of the Phase 1 #4
// god-component split (5731 → smaller chunks). Everything here is internal
// plumbing for the Candidates page; it is **not** part of any public API.
//
// See `docs/HOSTFLOW_AUDIT_AND_PLAN.md` (Phase 1 #4).

import api, { withTenant } from '../../api/client'
import type {
  CandidateListCacheEntry,
  CandidatesListInsights,
} from './types'

/**
 * Module-scoped LRU-ish cache shared across mounts of the Candidates page so
 * navigating away and back does not refetch the same key. Cleared on logout
 * via the `tenantScopeKey` we splice into the cache key inside the page.
 */
export const candidateListCache = new Map<string, CandidateListCacheEntry>()

/** Coerce a raw `list_insights` payload (possibly missing/null) into a strict object. */
export function normalizeListInsights(raw: unknown): CandidatesListInsights | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  return {
    total: Number(o.total) || 0,
    new_count: Number(o.new_count) || 0,
    docs_ready: Number(o.docs_ready) || 0,
    docs_attention: Number(o.docs_attention) || 0,
    docs_ordered: Number(o.docs_ordered) || 0,
  }
}

/**
 * Universal list fetcher with pagination-shape fallbacks.
 *
 * The candidates list endpoint accepts ``limit/offset`` but historically also
 * tolerated ``skip`` and ``page/per_page`` shapes; some tenants are still
 * pinned to older API behaviour and we cannot break their saved-views.
 *
 * Re-tries on HTTP 422 only (= "you sent the wrong query shape"), bubbles up
 * any other status. ``tenantId`` becomes the ``X-Tenant-Id`` header so the
 * list aligns with analytics calls when impersonating a client tenant.
 */
export async function getWithFallbacks<T = unknown>(
  path: string,
  params: Record<string, unknown>,
  tenantId?: string | null,
): Promise<{ data: T }> {
  const client = tenantId ? withTenant(tenantId) : api
  const limit = (params.limit as number | undefined) ?? 50
  const offset = (params.offset as number | undefined) ?? 0
  const baseParams = { ...params }

  const attempts = [
    { ...baseParams, limit, offset },
    { ...baseParams, limit, skip: offset },
    { ...baseParams, page: Math.floor(offset / limit) + 1, per_page: limit },
    { ...baseParams, limit },
    { ...baseParams },
  ]

  let lastErr: unknown = null
  for (const p of attempts) {
    try {
      const res = await client.get<T>(path, { params: p })
      return res
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status && status !== 422) throw e
      lastErr = e
    }
  }
  throw lastErr
}

/** Set of risk-band tokens accepted by the digest-shadow query string. */
const RISK_SHADOW_MIN_BANDS = new Set<string>(['low', 'medium', 'high', 'critical'])

/** Validate + normalize a `?shadow_min_band=` query value. */
export function parseRiskShadowMinBand(raw: string | null | undefined): string | null {
  if (raw == null || raw === '') return null
  const v = String(raw).trim().toLowerCase()
  return RISK_SHADOW_MIN_BANDS.has(v) ? v : null
}

/** Align with Reminders inbox: managers can load team-scoped candidate reminders in the work panel. */
export const TEAM_WORK_PANEL_ASSIGNEE_ROLES = new Set([
  'administrator',
  'supervisor',
  'superadmin',
  'admin',
  'manager',
])

/** localStorage key for the work-panel "mine vs team" scope toggle. */
export const WP_ASSIGNEE_STORAGE_KEY = 'hf:candidates:workPanelAssigneeScope'
