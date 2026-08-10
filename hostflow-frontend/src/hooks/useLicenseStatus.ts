import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../store/useAuth'
import { usePermissions } from './usePermissions'
import { getTeamOverview } from '../api/tenants'
import { canUseTeamOverviewLane } from '../auth/trustRoles'
import { isPlatformSuperadminRole } from '../utils/platformSuperadmin'

export type LicenseStatus = {
  loading: boolean
  expired: boolean
  validUntil: string | null
  plan: string | null
}

/**
 * Fetches license status for the current tenant.
 * Only administrators and supervisors can fetch team overview (which includes license).
 * Returns expired=true when license.expires_at is in the past.
 */
export function useLicenseStatus(): LicenseStatus {
  const { me } = useAuth()
  const { role, can, rawRole, presetId } = usePermissions()
  const [state, setState] = useState<LicenseStatus>({
    loading: true,
    expired: false,
    validUntil: null,
    plan: null,
  })

  const canFetchLicense = canUseTeamOverviewLane({
    role: rawRole || role,
    presetId,
    canAdminUsers: can('admin.users'),
  })

  const fetchLicense = useCallback(async () => {
    if (!canFetchLicense || !me?.tenant_id) {
      setState((s) => ({ ...s, loading: false }))
      return
    }
    try {
      const overview = await getTeamOverview()
      const license = overview?.license ?? null
      const expiresAt = license?.expires_at ?? null
      const validUntil = typeof expiresAt === 'string' ? expiresAt : null
      const now = new Date()
      const rawExpired = validUntil ? new Date(validUntil) < now : false
      const expired = isPlatformSuperadminRole(me?.role) ? false : rawExpired
      setState({
        loading: false,
        expired,
        validUntil,
        plan: license?.plan ?? null,
      })
    } catch {
      setState((s) => ({ ...s, loading: false }))
    }
  }, [canFetchLicense, me?.tenant_id, me?.role])

  useEffect(() => {
    void fetchLicense()
  }, [fetchLicense])

  return state
}
