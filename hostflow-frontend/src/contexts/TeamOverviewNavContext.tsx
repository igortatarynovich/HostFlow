import {
  createContext,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
} from 'react'

import { getTeamOverview } from '../api/tenants'
import type { TeamOverviewResponse } from '../api/types'
import { canUseTeamOverviewLane } from '../auth/trustRoles'
import { usePermissions } from '../hooks/usePermissions'

export type TeamOverviewNavContextValue = {
  teamOverview: TeamOverviewResponse | null
  canLoadTeamOverview: boolean
}

const TeamOverviewNavContext = createContext<TeamOverviewNavContextValue>({
  teamOverview: null,
  canLoadTeamOverview: false,
})

export function TeamOverviewNavProvider({
  tenantId,
  children,
}: PropsWithChildren<{ tenantId: string | null }>) {
  const { role, can, rawRole, presetId } = usePermissions()
  const canLoadTeamOverview = canUseTeamOverviewLane({
    role: rawRole || role,
    presetId,
    canAdminUsers: can('admin.users'),
  })
  const [teamOverview, setTeamOverview] = useState<TeamOverviewResponse | null>(null)

  useEffect(() => {
    let mounted = true
    if (!tenantId || !canLoadTeamOverview) {
      setTeamOverview(null)
      return () => {
        mounted = false
      }
    }
    ;(async () => {
      try {
        const data = await getTeamOverview({ tenantId }).catch(() => null)
        if (mounted) setTeamOverview(data)
      } catch {
        if (mounted) setTeamOverview(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [tenantId, canLoadTeamOverview])

  return (
    <TeamOverviewNavContext.Provider value={{ teamOverview, canLoadTeamOverview }}>
      {children}
    </TeamOverviewNavContext.Provider>
  )
}

export function useTeamOverviewNav(): TeamOverviewNavContextValue {
  return useContext(TeamOverviewNavContext)
}
