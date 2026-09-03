/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from '../../nav/appShellNav'
import {
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_HUB_NAV_ITEM_KEYS,
} from '../../nav/sidebarRailBuckets'

describe('marketing sources route registration (C-3)', () => {
  it('registers NAV_ITEMS + APP_ROUTES under /app/marketing/sources', () => {
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing-sources')
    expect(nav).toMatchObject({
      path: CRM_APP_PATHS.marketingSources,
      permission: 'vacancies.view',
      labelKey: 'app.nav.items.marketing_sources',
    })

    const route = APP_ROUTES.find((item) => item.key === 'marketing-sources')
    expect(route).toBeTruthy()
    expect(route?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.marketingSources))
    expect(route?.permission).toBe('vacancies.view')
    expect(CRM_APP_PATHS.marketingSources).toBe('/app/marketing/sources')
  })

  it('stays off the primary rail (Marketing hub deep link, not Sales / Recruitment / Automations / hub)', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toEqual(['marketing'])
    expect(APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS).toContain('marketing-sources')
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).not.toContain('marketing-sources')
    expect([...SIDEBAR_AGENCY_RECRUITMENT_ORDER]).not.toContain('marketing-sources')
    expect([...SIDEBAR_AGENCY_AUTOMATIONS_ORDER]).not.toContain('marketing-sources')
    expect([...SIDEBAR_HUB_NAV_ITEM_KEYS]).not.toContain('marketing-sources')
  })

  it('CTA path constants stay on existing Settings ownership surfaces', () => {
    expect(CRM_APP_PATHS.settingsIntegrationsMeta).toBe('/app/settings/integrations/meta')
    expect(CRM_APP_PATHS.settingsLeadForms).toBe('/app/settings/lead-forms')
    expect(CRM_APP_PATHS.settingsLeadForms.startsWith('/app/settings/')).toBe(true)
    expect(CRM_APP_PATHS.marketingForms).toBe('/app/marketing/forms')
  })
})
