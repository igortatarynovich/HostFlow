/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { NAV_ITEMS } from '../../app/routes'
import {
  ALL_AGENCY_PRIMARY_RAIL_KEYS,
  isNavKeyAccountedForInSidebarPlacement,
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_FINANCE_ORDER,
  SIDEBAR_AGENCY_HR_ORDER,
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_AGENCY_SERVICES_ORDER,
} from '../sidebarRailBuckets'

describe('sidebar nav placement integrity', () => {
  it('every NAV_ITEMS entry with a path is on agency rail, client flat list, hidden, hub-only, or standalone', () => {
    const missing: string[] = []
    for (const item of NAV_ITEMS) {
      if (!item.path) continue
      if (item.action === 'logout') continue
      if (isNavKeyAccountedForInSidebarPlacement(item.key)) continue
      missing.push(item.key)
    }
    expect(
      missing,
      `Add keys to sidebarRailBuckets (agency buckets / client flat / hub / standalone) or appShellNav hidden: ${missing.join(', ')}`,
    ).toEqual([])
  })

  it('ADR-023: business module rail buckets do not overlap', () => {
    const buckets = [
      SIDEBAR_AGENCY_RECRUITMENT_ORDER,
      SIDEBAR_AGENCY_HR_ORDER,
      SIDEBAR_AGENCY_MARKETING_ORDER,
      SIDEBAR_AGENCY_SALES_ORDER,
      SIDEBAR_AGENCY_SERVICES_ORDER,
      SIDEBAR_AGENCY_FINANCE_ORDER,
    ]
    const seen = new Set<string>()
    const overlap: string[] = []
    for (const bucket of buckets) {
      for (const key of bucket) {
        if (seen.has(key)) overlap.push(key)
        seen.add(key)
      }
    }
    expect(overlap).toEqual([])
  })

  it('ADR-023 ownership: Employee under HR; Invoice under Finance; not under Recruitment/Sales', () => {
    expect([...SIDEBAR_AGENCY_RECRUITMENT_ORDER]).toEqual(
      expect.arrayContaining(['recruitment-inbox', 'candidates']),
    )
    expect(SIDEBAR_AGENCY_RECRUITMENT_ORDER).not.toContain('recruitment-searches')
    expect(SIDEBAR_AGENCY_RECRUITMENT_ORDER).not.toContain('hr-workspace')
    expect(SIDEBAR_AGENCY_RECRUITMENT_ORDER).not.toContain('sales')
    expect(SIDEBAR_AGENCY_RECRUITMENT_ORDER).not.toContain('invoices')

    expect([...SIDEBAR_AGENCY_HR_ORDER]).toContain('hr-workspace')
    expect([...SIDEBAR_AGENCY_SALES_ORDER]).toEqual(['sales', 'clients'])
    expect(SIDEBAR_AGENCY_SALES_ORDER).not.toContain('marketing')
    expect(SIDEBAR_AGENCY_SALES_ORDER).not.toContain('invoices')
    expect(SIDEBAR_AGENCY_SALES_ORDER).not.toContain('candidates')

    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).toEqual([
      'marketing',
      'marketing-sources',
      'marketing-forms',
      'acquisition-activity',
    ])
    expect(SIDEBAR_AGENCY_AUTOMATIONS_ORDER).not.toContain('acquisition-activity')
    expect(SIDEBAR_AGENCY_MARKETING_ORDER).not.toContain('sales')

    expect([...SIDEBAR_AGENCY_SERVICES_ORDER]).toEqual(expect.arrayContaining(['service-orders', 'services']))
    expect([...SIDEBAR_AGENCY_FINANCE_ORDER]).toContain('invoices')

    expect(ALL_AGENCY_PRIMARY_RAIL_KEYS.has('hr-workspace')).toBe(true)
    expect(ALL_AGENCY_PRIMARY_RAIL_KEYS.has('invoices')).toBe(true)
    expect(ALL_AGENCY_PRIMARY_RAIL_KEYS.has('marketing')).toBe(true)
  })
})
