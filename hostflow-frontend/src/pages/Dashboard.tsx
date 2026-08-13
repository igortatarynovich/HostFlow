import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { resolveDeployHost } from '../platform/deployHosts'
import {
  OverviewModuleTabs,
  parseOverviewModuleTab,
  type OverviewModuleTab,
} from '../modules/dashboard/components/OverviewModuleTabs'
import { isAnalyticsPresentation } from '../components/analytics/analyticsView'
import AnalyticsSummaryDashboard from './AnalyticsSummaryDashboard'
import RecruitmentEfficiencyDashboard from './RecruitmentEfficiencyDashboard'
import MarketingEfficiencyDashboard from './MarketingEfficiencyDashboard'
import SalesEfficiencyDashboard from './SalesEfficiencyDashboard'
import HrEfficiencyDashboard from './HrEfficiencyDashboard'
import FinanceEfficiencyDashboard from './FinanceEfficiencyDashboard'
import FleetEfficiencyDashboard from './FleetEfficiencyDashboard'

const OVERVIEW_QUERY_KEY = 'module'

function defaultTabForHost(): OverviewModuleTab {
  const host = resolveDeployHost()
  if (host === 'recruitment') return 'recruitment'
  if (host === 'sales') return 'sales'
  if (host === 'hr') return 'hr'
  if (host === 'finance') return 'finance'
  if (host === 'fleet') return 'fleet'
  return 'summary'
}

/**
 * System Analytics hub (`overview.hostflow.cc/app/overview`).
 * Tabs = system summary + licensed business modules; each tab owns its metrics.
 */
export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [available, setAvailable] = useState<OverviewModuleTab[] | null>(null)

  const preferred = useMemo(() => {
    const fromQuery = parseOverviewModuleTab(searchParams.get(OVERVIEW_QUERY_KEY))
    return fromQuery || defaultTabForHost()
  }, [searchParams])

  const activeTab = useMemo((): OverviewModuleTab => {
    if (!available || available.length === 0) return preferred
    if (available.includes(preferred)) return preferred
    return available[0]
  }, [available, preferred])

  const onTabsReady = useCallback((tabs: OverviewModuleTab[]) => {
    setAvailable(tabs)
  }, [])

  const onTabChange = useCallback(
    (tab: OverviewModuleTab) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          // Always set module= so Overview host default does not fall back to deploy-host tab.
          next.set(OVERVIEW_QUERY_KEY, tab)
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {!isAnalyticsPresentation(searchParams) ? (
        <OverviewModuleTabs active={activeTab} onChange={onTabChange} onTabsReady={onTabsReady} />
      ) : null}
      {activeTab === 'recruitment' ? (
        <RecruitmentEfficiencyDashboard />
      ) : activeTab === 'marketing' ? (
        <MarketingEfficiencyDashboard />
      ) : activeTab === 'sales' ? (
        <SalesEfficiencyDashboard />
      ) : activeTab === 'hr' ? (
        <HrEfficiencyDashboard />
      ) : activeTab === 'finance' ? (
        <FinanceEfficiencyDashboard />
      ) : activeTab === 'fleet' ? (
        <FleetEfficiencyDashboard />
      ) : (
        <AnalyticsSummaryDashboard />
      )}
    </div>
  )
}
