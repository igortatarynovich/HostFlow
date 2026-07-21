/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import { SIDEBAR_AGENCY_SALES_ORDER, SIDEBAR_HUB_NAV_ITEM_KEYS } from '../../nav/sidebarRailBuckets'

describe('marketing workspace route registration', () => {
  it('registers NAV_ITEMS + APP_ROUTES under /app/marketing', () => {
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing')
    expect(nav).toMatchObject({
      path: CRM_APP_PATHS.marketing,
      permission: 'vacancies.view',
      labelKey: 'app.nav.items.marketing',
    })

    const list = APP_ROUTES.find((item) => item.key === 'marketing')
    const setup = APP_ROUTES.find((item) => item.key === 'marketing-new')
    const detail = APP_ROUTES.find((item) => item.key === 'marketing-detail')
    expect(list?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketing))
    expect(setup?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketingNew))
    expect(detail?.path).toBe(`${crmAppRouteSegment(CRM_APP_PATHS.marketing)}/:campaignId`)
    expect(CRM_APP_PATHS.marketing).toBe('/app/marketing')
    expect(CRM_APP_PATHS.marketingNew).toBe('/app/marketing/new')
  })

  it('appears on the Sales primary rail (not hub-only)', () => {
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).toContain('marketing')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('marketing')
  })
})
