/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { APP_ROUTES } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment, marketingSourceTestLeadPath } from '../crmAppPaths'

const ROOT = path.resolve(__dirname, '../../..')
const seg = crmAppRouteSegment

describe('C-4 Test lead UI shell', () => {
  it('registers MarketingSourceTestLeadPage under /marketing/sources/:sourceId/test-lead', () => {
    const route = APP_ROUTES.find((r) => r.key === 'marketing-source-test-lead')
    expect(route?.path).toBe(`${seg(CRM_APP_PATHS.marketingSources)}/:sourceId/test-lead`)
    expect(marketingSourceTestLeadPath('src-1')).toBe('/app/marketing/sources/src-1/test-lead')
  })

  it('page is a leftover diagnostic fold into Mapping, not a second sample/mapping flow', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceTestLeadPage.tsx'),
      'utf8',
    )
    expect(src).toContain('getMarketingSourceSample')
    expect(src).toContain('marketing-test-lead-workspace')
    expect(src).toContain('marketing-test-lead-continue-mapping')
    expect(src).toContain('mappingAssessmentCopy')
    expect(src).toContain('mappingWorkspaceCta')
    expect(src).not.toContain('postMarketingSourceCaptureNext')
    expect(src).not.toContain('postMarketingSourceSampleFromPayload')
    expect(src).not.toContain('postMarketingSourceSamplePreview')
    expect(src).not.toContain('marketing-test-lead-fields-table')
    expect(src).not.toContain('marketing-test-lead-mode-a')
    expect(src).not.toContain('marketing-test-lead-mode-b')
    expect(src).not.toContain('marketing-test-lead-mode-c')
    expect(src).not.toContain("app.marketing.sources.health.ready")
    expect(src).not.toContain("app.marketing.sources.health.broken")
    expect(src).not.toContain('putIntakeFormMapping')
    expect(src).not.toContain('mapping_rules:')
  })

  it('Sources list does not promote leftover Test lead as an operator CTA', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    expect(src).not.toContain('row.test_lead_path')
    expect(src).not.toContain('marketing-source-test-lead-')
    expect(src).toContain('row.mapping_path')
  })
})
