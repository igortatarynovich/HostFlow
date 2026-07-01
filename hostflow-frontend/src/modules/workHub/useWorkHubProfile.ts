import { useMemo } from 'react'

import { usePermissions } from '../../hooks/usePermissions'
import { useAuth } from '../../store/useAuth'
import {
  resolveWorkHubProfile,
  type WorkHubProfile,
} from './profile'

/**
 * Resolve the active Work Hub profile for the logged-in user.
 *
 * Solo vs team admin is driven by `GET /users/me` → `is_solo_admin`
 * (G-6 Stage 2e): true when the user is owner-class (administrator/superadmin)
 * and the tenant has exactly one active member. Without that flag we default
 * to `admin_team` (broader counters) — the backend now always sends the flag.
 */
export function useWorkHubProfile(): WorkHubProfile {
  const { role, isClientTenant } = usePermissions()
  const { me } = useAuth()

  return useMemo(() => {
    const isSoloAdmin = Boolean(me?.is_solo_admin)
    return resolveWorkHubProfile({ role, isClientTenant, isSoloAdmin })
  }, [role, isClientTenant, me])
}
