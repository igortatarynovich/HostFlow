/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { APP_ROUTES } from '../routes'
import {
  CRM_APP_PATHS,
  crmAppRouteSegment,
  marketingSourceMappingPath,
} from '../crmAppPaths'

const ROOT = path.resolve(__dirname, '../../..')
const seg = crmAppRouteSegment

describe('C-5 Mapping workspace UI shell', () => {
  it('registers MarketingSourceMappingPage under /marketing/sources/:sourceId/mapping', () => {
    const route = APP_ROUTES.find((r) => r.key === 'marketing-source-mapping')
    expect(route?.path).toBe(`${seg(CRM_APP_PATHS.marketingSources)}/:sourceId/mapping`)
    expect(marketingSourceMappingPath('src-1')).toBe('/app/marketing/sources/src-1/mapping')
  })

  it('page wires get/put mapping, projection, and applied evidence', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceMappingPage.tsx'),
      'utf8',
    )
    expect(src).toContain('getMarketingSourceMapping')
    expect(src).toContain('putMarketingSourceMapping')
    expect(src).toContain('marketing-mapping-rules-table')
    expect(src).toContain('marketing-mapping-save')
    expect(src).toContain('marketing-mapping-summary')
    expect(src).toContain('marketing-mapping-projection')
    expect(src).toContain('marketing-mapping-applied')
    expect(src).toContain('applied_evidence')
    expect(src).toContain('marketing-mapping-schema-identity')
    expect(src).toContain('marketing-mapping-sample-latest')
    expect(src).toContain('marketing-mapping-sample-wait')
    expect(src).toContain('postMarketingSourceMappingSampleLatest')
    expect(src).toContain('postMarketingSourceMappingSampleCaptureNext')
    expect(src).toContain('setInterval')
    expect(src).toContain('capture_next_until')
    expect(src).not.toContain('marketing-mapping-to-test-lead')
    expect(src).not.toContain('postMarketingSourceSampleFromPayload')
    expect(src).not.toContain('postMarketingSourceSamplePreview')
    expect(src).not.toContain('marketing-mapping-rules-source')
    expect(src).toContain('app.marketing.mapping.drift.')
    expect(src).not.toContain('>{row.destination_code}<')
    expect(src).not.toContain('postMarketingSourceRoutingPreview')
    expect(src).not.toContain('marketing-mapping-routing-run')
    expect(src).toContain('app.marketing.mapping.sample.ask')
    expect(src).toContain('app.marketing.mapping.applied.next')
    expect(src).toContain('marketing-mapping-sample-prompt')
    expect(src).toContain('marketing-mapping-applied-next')
    expect(src).toContain('latestPrimary')
    expect(src).toContain('waitPrimary')
  })

  it('Sources list Mapping CTA still uses server mapping_path', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    expect(src).toContain('row.mapping_path')
    expect(src).toContain('marketing-source-mapping-')
    expect(src).not.toContain('row.test_lead_path')
    expect(src).not.toContain('marketing-source-test-lead-')
  })
})
