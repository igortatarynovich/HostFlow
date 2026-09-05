/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = path.resolve(__dirname, '../../..')

describe('MA-3 leftover mapping surfaces cease to be editors', () => {
  it('Intake form mapping is deep-link or fail-closed, not a writer', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/components/admin/IntakeFormMappingEditor.tsx'),
      'utf8',
    )
    expect(src).not.toContain('putIntakeFormMapping')
    expect(src).not.toContain('previewIntakeFormMapping')
    expect(src).not.toContain('testIntakeFormMappingIngest')
    expect(src).toContain('getIntakeFormMapping')
    expect(src).toContain('marketingSourceMappingPath')
    expect(src).toContain('intake-form-mapping-workspace')
    expect(src).toContain('intake-form-mapping-unbound')
  })

  it('Intake form detail still hosts the leftover fold, not a second editor', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/admin/IntakeFormDetailPage.tsx'),
      'utf8',
    )
    expect(src).toContain('IntakeFormMappingEditor')
    expect(src).not.toContain('putIntakeFormMapping')
  })

  it('Meta Settings field mapping is deep-link, not a writer', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/admin/MetaLeadsAdminPage.tsx'),
      'utf8',
    )
    expect(src).not.toContain('putMetaLeadFormMapping')
    expect(src).not.toContain('handleSaveFieldMapping')
    expect(src).not.toContain('field_mapping: built')
    expect(src).toContain('marketingSourceMappingPath')
    expect(src).toContain('meta-field-mapping-workspace')
    expect(src).toContain('meta-settings-open-mapping')
    expect(src).toContain('form_select_placeholder')
    expect(src).not.toContain('form_select_tenant_default')
    expect(src).not.toContain('setFormNameDraft')
    expect(src).not.toContain('inherits_tenant_banner')
    expect(src).not.toContain('fieldMappingRuleCount')
    expect(src).not.toContain('getMetaLeadFormMapping')
    expect(src).not.toContain('listCustomFieldDefinitions')
    expect(src).not.toContain('createCustomFieldDefinition')
    expect(src).not.toContain('fetchMetaGraphFieldPreview')
  })

  it('Mapping workspace is the editor and does not host leftover routing preview', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceMappingPage.tsx'),
      'utf8',
    )
    expect(src).toContain('putMarketingSourceMapping')
    expect(src).toContain('postMarketingSourceMappingSampleLatest')
    expect(src).toContain('postMarketingSourceMappingSampleCaptureNext')
    expect(src).not.toContain('postMarketingSourceRoutingPreview')
    expect(src).not.toContain('postMarketingSourceSampleFromPayload')
    expect(src).not.toContain('putMetaLeadFormMapping')
    expect(src).not.toContain('putIntakeFormMapping')
  })

  it('legacy mapping write clients are gone, not 410 wrappers', () => {
    const intakeApi = readFileSync(path.join(ROOT, 'src/api/intakeForms.ts'), 'utf8')
    const metaApi = readFileSync(path.join(ROOT, 'src/api/metaLeads.ts'), 'utf8')
    expect(intakeApi).not.toContain('putIntakeFormMapping')
    expect(intakeApi).not.toContain('previewIntakeFormMapping')
    expect(intakeApi).not.toContain('testIntakeFormMappingIngest')
    expect(metaApi).not.toContain('putMetaLeadFormMapping')
  })

  it('Sources, Diagnostics, and Test lead read canonical mapping copy, not leftover ready/broken', () => {
    const sources = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    const diagnostics = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingDiagnosticsPage.tsx'),
      'utf8',
    )
    const testLead = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceTestLeadPage.tsx'),
      'utf8',
    )
    for (const src of [sources, diagnostics, testLead]) {
      expect(src).toContain('mappingAssessmentCopy')
      expect(src).toContain('mappingWorkspaceCta')
      expect(src).not.toContain("app.marketing.sources.health.ready")
      expect(src).not.toContain("app.marketing.sources.health.broken")
      expect(src).not.toContain("case 'ready':")
      expect(src).not.toContain("case 'broken':")
    }
  })

  it('Sources list Mapping is the operator CTA; leftover Test lead is not a Sources action', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourcesPage.tsx'),
      'utf8',
    )
    expect(src).toContain('row.mapping_path')
    expect(src).toContain('mappingWorkspaceCta')
    expect(src).not.toContain('row.test_lead_path')
    expect(src).not.toContain('marketing-source-test-lead-')
  })

  it('leftover Test lead is a diagnostic fold into Mapping, not a second sample flow', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingSourceTestLeadPage.tsx'),
      'utf8',
    )
    expect(src).toContain('marketing-test-lead-workspace')
    expect(src).toContain('mappingWorkspaceCta')
    expect(src).not.toContain('postMarketingSourceCaptureNext')
    expect(src).not.toContain('postMarketingSourceSampleFromPayload')
    expect(src).not.toContain('postMarketingSourceSamplePreview')
  })

  it('Leads inbox and webhook mapping CTAs open Sources, not leftover Meta field mapping', () => {
    const leads = readFileSync(path.join(ROOT, 'src/pages/LeadsPage.tsx'), 'utf8')
    const problem = readFileSync(
      path.join(ROOT, 'src/components/leads/LeadMetaProblemPanel.tsx'),
      'utf8',
    )
    const webhook = readFileSync(
      path.join(ROOT, 'src/pages/admin/IntegrationsWebhookPage.tsx'),
      'utf8',
    )
    expect(leads).toContain('CRM_APP_PATHS.marketingSources')
    expect(leads).not.toContain("settingsIntegrationsMeta}?tab=mapping")
    expect(problem).toContain('CRM_APP_PATHS.marketingSources')
    expect(problem).not.toContain("settingsIntegrationsMeta}?tab=mapping")
    expect(webhook).toContain('CRM_APP_PATHS.marketingSources')
    expect(webhook).toContain('admin.integrations_webhook.mapping_cta')
  })

  it('Connect bind opens Mapping workspace when a source exists', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingConnectSourcePage.tsx'),
      'utf8',
    )
    expect(src).toContain('marketingSourceMappingPath')
    expect(src).toContain('navigate')
  })
})
