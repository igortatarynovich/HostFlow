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

  it('page wires get/put mapping + routing preview', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceMappingPage.tsx'),
      'utf8',
    )
    expect(src).toContain('getMarketingSourceMapping')
    expect(src).toContain('putMarketingSourceMapping')
    expect(src).toContain('postMarketingSourceRoutingPreview')
    expect(src).toContain('marketing-mapping-rules-table')
    expect(src).toContain('marketing-mapping-save')
    expect(src).toContain('marketing-mapping-routing-run')
    expect(src).toContain('marketing-mapping-summary')
    expect(src).toContain('creates_entities')
  })

  it('Sources list Mapping CTA still uses server mapping_path', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    expect(src).toContain('row.mapping_path')
    expect(src).toContain('marketing-source-mapping-')
  })
})
