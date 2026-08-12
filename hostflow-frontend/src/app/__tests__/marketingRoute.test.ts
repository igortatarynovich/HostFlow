/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import {
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_HUB_NAV_ITEM_KEYS,
} from '../../nav/sidebarRailBuckets'

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
    const connect = APP_ROUTES.find((item) => item.key === 'marketing-connect-source')
    const detail = APP_ROUTES.find((item) => item.key === 'marketing-detail')
    expect(list?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketing))
    expect(setup?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketingNew))
    expect(connect?.path).toBe(`${crmAppRouteSegment(CRM_APP_PATHS.marketing)}/:campaignId/sources/new`)
    expect(detail?.path).toBe(`${crmAppRouteSegment(CRM_APP_PATHS.marketing)}/:campaignId`)
    expect(CRM_APP_PATHS.marketing).toBe('/app/marketing')
    expect(CRM_APP_PATHS.marketingNew).toBe('/app/marketing/new')
  })

  it('registers Connect Source before Campaign detail (more specific path)', () => {
    const connectIdx = APP_ROUTES.findIndex((item) => item.key === 'marketing-connect-source')
    const detailIdx = APP_ROUTES.findIndex((item) => item.key === 'marketing-detail')
    expect(connectIdx).toBeGreaterThanOrEqual(0)
    expect(detailIdx).toBeGreaterThanOrEqual(0)
    expect(connectIdx).toBeLessThan(detailIdx)
  })

  it('C-1: Marketing is a top-level rail section, not under Sales', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toEqual([
      'marketing',
      'marketing-sources',
      'marketing-forms',
      'marketing-diagnostics',
      'acquisition-activity',
    ])
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).toEqual(['sales', 'sales-orders', 'clients'])
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).not.toContain('marketing')
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).not.toContain('acquisition-activity')
    expect([...SIDEBAR_AGENCY_AUTOMATIONS_ORDER]).not.toContain('acquisition-activity')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('marketing')
  })

  it('C-1: Marketing list/setup/detail/connect require vacancies.view (route gate)', () => {
    for (const key of [
      'marketing',
      'marketing-new',
      'marketing-detail',
      'marketing-connect-source',
    ] as const) {
      const route = APP_ROUTES.find((item) => item.key === key)
      expect(route?.permission, key).toBe('vacancies.view')
    }
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing')
    expect(nav?.permission).toBe('vacancies.view')
  })
})
