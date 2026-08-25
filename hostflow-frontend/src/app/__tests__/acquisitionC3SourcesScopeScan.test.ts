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
    // C-3.1 inventory columns
    expect(src).toContain('row.page_id')
    expect(src).toContain('row.provider_form')
    expect(src).toContain('row.destination')
    // No Form Builder / Searches ownership move in this page
    expect(src).not.toContain('settingsLeadFormBuilderPath')
    expect(src).not.toContain('recruitmentSearches')
  })

  it('list helper stays GET; C-4 sample writes are explicit sample/* helpers', () => {
    const api = readFileSync(path.join(ROOT, 'src/api/marketingSources.ts'), 'utf8')
    expect(api).toContain("'/platform/marketing/sources'")
    expect(api).toContain('listMarketingSources')
    expect(api).toMatch(/http\.get<MarketingSourceListResponse>\('\/platform\/marketing\/sources'\)/)
    expect(api).toContain('getMarketingSourceSample')
    expect(api).toContain('postMarketingSourceSamplePreview')
    expect(api).toContain('/sample/preview')
    expect(api).toContain('/sample/from-payload')
    expect(api).toContain('/sample/capture-next')
    expect(CRM_APP_PATHS.marketingSources).toBe('/app/marketing/sources')
  })
})
