/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { CRM_APP_PATHS } from '../crmAppPaths'

const ROOT = path.resolve(__dirname, '../../..')

describe('C-3 Sources scope guards', () => {
  it('MarketingSourcesPage deep-links to existing mapping / test / settings paths', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    expect(src).toContain('row.mapping_path')
    expect(src).toContain('row.test_lead_path')
    expect(src).toContain('row.settings_path')
    expect(src).toContain('row.setup_campaign_flight_path')
    expect(src).toContain('waiting_submissions')
    expect(src).toContain('listMarketingSources')
    // No Form Builder / Searches ownership move in this page
    expect(src).not.toContain('settingsLeadFormBuilderPath')
    expect(src).not.toContain('recruitmentSearches')
  })

  it('does not introduce write client helpers for Sources', () => {
    const api = readFileSync(path.join(ROOT, 'src/api/marketingSources.ts'), 'utf8')
    expect(api).toContain("'/platform/marketing/sources'")
    expect(api).not.toMatch(/\.(post|put|patch|delete)\(/i)
    expect(CRM_APP_PATHS.marketingSources).toBe('/app/marketing/sources')
  })
})
