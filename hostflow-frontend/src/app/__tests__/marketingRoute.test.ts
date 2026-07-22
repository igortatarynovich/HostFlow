/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import {
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_HUB_NAV_ITEM_KEYS,
} from '../../nav/sidebarRailBuckets'
import registry from '@shared/module_deploy_hosts.json'

describe('marketing workspace route registration', () => {
  it('registers NAV_ITEMS + APP_ROUTES under /app/marketing with acquisition.view', () => {
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing')
    expect(nav).toMatchObject({
      path: CRM_APP_PATHS.marketing,
      permission: 'acquisition.view',
      labelKey: 'app.nav.items.marketing',
    })

    const list = APP_ROUTES.find((item) => item.key === 'marketing')
    const setup = APP_ROUTES.find((item) => item.key === 'marketing-new')
    const detail = APP_ROUTES.find((item) => item.key === 'marketing-detail')
    expect(list?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketing))
    expect(setup?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketingNew))
    expect(detail?.path).toBe(`${crmAppRouteSegment(CRM_APP_PATHS.marketing)}/:campaignId`)
    expect(list?.permission).toBe('acquisition.view')
    expect(CRM_APP_PATHS.marketing).toBe('/app/marketing')
    expect(CRM_APP_PATHS.marketingNew).toBe('/app/marketing/new')
  })

  it('is a platform shell surface — not Sales rail / sales host', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toContain('marketing')
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).not.toContain('marketing')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('marketing')
    expect(registry.nav_key_to_host.marketing).toBe('shell')
    expect(registry.shell_shared_nav_keys).toContain('marketing')
    expect(registry.shell_platform_path_prefixes).toContain('/app/marketing')
    expect(registry.app_path_prefixes.some((p) => p.prefix === '/app/marketing')).toBe(false)
  })
})
