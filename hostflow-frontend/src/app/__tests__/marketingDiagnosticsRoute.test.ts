/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import {
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_HUB_NAV_ITEM_KEYS,
} from '../../nav/sidebarRailBuckets'

describe('marketing diagnostics route', () => {
  it('registers Diagnostics under Marketing rail', () => {
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing-diagnostics')
    expect(nav).toMatchObject({
      path: CRM_APP_PATHS.marketingDiagnostics,
    })
    const route = APP_ROUTES.find((item) => item.key === 'marketing-diagnostics')
    expect(route?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketingDiagnostics))
    expect(CRM_APP_PATHS.marketingDiagnostics).toBe('/app/marketing/diagnostics')
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toContain('marketing-diagnostics')
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).not.toContain('marketing-diagnostics')
    expect([...SIDEBAR_AGENCY_RECRUITMENT_ORDER]).not.toContain('marketing-diagnostics')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('marketing-diagnostics')
  })
})
