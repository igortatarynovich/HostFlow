/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import {
  CRM_APP_PATHS,
  crmAppRouteSegment,
  marketingFormBuilderPath,
  marketingFormDetailPath,
  settingsLeadFormDetailPath,
} from '../crmAppPaths'
import { SIDEBAR_AGENCY_MARKETING_ORDER } from '../../nav/sidebarRailBuckets'

const seg = crmAppRouteSegment

describe('C-6 Marketing Forms IA', () => {
  it('registers Forms on Marketing rail and /app/marketing/forms routes', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toContain('marketing-forms')
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing-forms')
    expect(nav?.path).toBe(CRM_APP_PATHS.marketingForms)

    const list = APP_ROUTES.find((r) => r.key === 'marketing-forms')
    const detail = APP_ROUTES.find((r) => r.key === 'marketing-form-detail')
    const builder = APP_ROUTES.find((r) => r.key === 'marketing-forms-builder')
    expect(list?.path).toBe(seg(CRM_APP_PATHS.marketingForms))
    expect(detail?.path).toBe(`${seg(CRM_APP_PATHS.marketingForms)}/:formId`)
    expect(builder?.path).toBe(`${seg(CRM_APP_PATHS.marketingForms)}/:formId/builder`)
  })

  it('Settings lead-forms routes redirect into Marketing Forms', () => {
    const list = APP_ROUTES.find((r) => r.key === 'settings-lead-forms')
    const detail = APP_ROUTES.find((r) => r.key === 'settings-intake-form-detail')
    const builder = APP_ROUTES.find((r) => r.key === 'settings-forms-builder')
    expect(list?.Component?.name).toMatch(/Redirect/)
    expect(detail?.Component?.name).toMatch(/Redirect/)
    expect(builder?.Component?.name).toMatch(/Redirect/)
  })

  it('detail/builder helpers resolve under Marketing Forms', () => {
    expect(CRM_APP_PATHS.marketingForms).toBe('/app/marketing/forms')
    expect(marketingFormDetailPath('f1')).toBe('/app/marketing/forms/f1')
    expect(marketingFormBuilderPath('f1')).toBe('/app/marketing/forms/f1/builder')
    expect(settingsLeadFormDetailPath('f1')).toBe('/app/marketing/forms/f1')
  })
})
