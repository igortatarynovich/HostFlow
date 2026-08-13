// src/modules/candidates/hooks/useCandidatesCatalogs.ts
//
// Side-effect-only hooks that load three independent catalogs needed by the
// Candidates page:
//   * recruiter managers (for filter + bulk-assign modal),
//   * vacancies (for filter + bulk-assign modal),
//   * "available client" tenants (lazy-loaded only when the bulk-handoff
//     modal opens).
//
// Extracted from `src/pages/Candidates.tsx` as Phase 1 #4 step 2 of the
// god-component split. Each hook owns its own loading lifecycle and tolerates
// transient API failures silently — these are best-effort caches whose only
// consumer is the bulk-action UI.
//
// See `docs/HOSTFLOW_AUDIT_AND_PLAN.md` (Phase 1 #4).

import { useEffect } from 'react'

import api from '../../../api/client'
import { getAvailableClients, type AvailableClientOut } from '../../../api/handoffs'
import { RECRUITMENT_ASSIGNEE_CATALOG_ROLES } from '../../../auth/trustRoles'
import type { Vacancy } from '../../../api/types'
import type { ManagerItem } from '../types'

interface MeShape {
  sub?: string | null
  id?: string | null
  full_name?: string | null
  email?: string | null
}

/**
 * Fetch the recruiter-manager catalog and append the current user as a
 * fallback row if the backend omitted them (happens for restricted catalogs).
 */
export function useCandidatesManagersCatalog(
  me: MeShape | null | undefined,
  setManagers: (m: ManagerItem[]) => void,
): void {
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { data } = await api.get('/catalogs/managers', {
          params: { roles: RECRUITMENT_ASSIGNEE_CATALOG_ROLES },
        })
        const list: unknown[] = Array.isArray(data) ? data : ((data as { items?: unknown[] })?.items || [])
        const mapped: ManagerItem[] = list
          .map((it: unknown) => {
            const o = (it ?? {}) as Record<string, unknown>
            return {
              id: String(o.id ?? o.user_id ?? o.uid ?? o.uuid ?? ''),
              name: String(o.label ?? o.full_name ?? o.name ?? o.email ?? '—'),
            }
          })
          .filter((m) => m.id)

        const selfId = me?.sub || me?.id || null
        const selfName = me?.full_name || me?.email || null
        if (selfId && !mapped.some((m) => m.id === selfId)) {
          mapped.push({ id: String(selfId), name: String(selfName || selfId) })
        }

        if (!cancelled) setManagers(mapped)
      } catch {
        /* ignore */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [me, setManagers])
}

/** Load the vacancy catalog used by the filter + bulk-vacancy assign modal. */
export function useCandidatesVacanciesCatalog(setVacancies: (v: Vacancy[]) => void): void {
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { data } = await api.get('/vacancies/')
        const list: unknown[] = Array.isArray(data) ? data : ((data as { items?: unknown[] })?.items || [])
        if (!cancelled) setVacancies(list as Vacancy[])
      } catch {
        /* ignore */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setVacancies])
}

/**
 * Lazy-load the "available client" tenant list only when the bulk-handoff
 * modal opens. Resets the selected client every time the modal opens.
 */
export function useCandidatesHandoffClientsLazy(
  bulkHandoffOpen: boolean,
  setHandoffClients: (c: AvailableClientOut[]) => void,
  setHandoffClientsLoading: (b: boolean) => void,
  setBulkHandoffClientId: (s: string) => void,
): void {
  useEffect(() => {
    if (!bulkHandoffOpen) return
    setHandoffClientsLoading(true)
    getAvailableClients()
      .then(setHandoffClients)
      .catch(() => setHandoffClients([]))
      .finally(() => setHandoffClientsLoading(false))
    setBulkHandoffClientId('')
  }, [bulkHandoffOpen, setHandoffClients, setHandoffClientsLoading, setBulkHandoffClientId])
}
