/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import { SIDEBAR_HUB_NAV_ITEM_KEYS } from '../../nav/sidebarRailBuckets'

describe('acquisition activity route registration', () => {
  it('registers NAV_ITEMS + APP_ROUTES under canonical path with Acquisition read permission', () => {
    const nav = NAV_ITEMS.find((item) => item.key === 'acquisition-activity')
    expect(nav).toMatchObject({
      path: CRM_APP_PATHS.acquisitionActivity,
      permission: 'vacancies.view',
      labelKey: 'app.nav.items.acquisition_activity',
    })

    const route = APP_ROUTES.find((item) => item.key === 'acquisition-activity')
    expect(route).toBeTruthy()
    expect(route?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.acquisitionActivity))
    expect(route?.permission).toBe('vacancies.view')
    expect(CRM_APP_PATHS.acquisitionActivity).toBe('/app/acquisition/activity')
  })

  it('is accounted for as hub nav (not primary rail drift)', () => {
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).toContain('acquisition-activity')
  })
})
