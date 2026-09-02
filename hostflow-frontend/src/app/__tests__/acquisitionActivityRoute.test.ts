/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from '../../nav/appShellNav'
import {
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_HUB_NAV_ITEM_KEYS,
} from '../../nav/sidebarRailBuckets'

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

  it('C-1: stays off the primary rail (Marketing hub deep link, not Automations / hub-only)', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).not.toContain('acquisition-activity')
    expect(APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS).toContain('acquisition-activity')
    expect([...SIDEBAR_AGENCY_AUTOMATIONS_ORDER]).not.toContain('acquisition-activity')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('acquisition-activity')
  })
})
