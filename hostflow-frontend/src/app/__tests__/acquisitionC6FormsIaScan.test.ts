/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { APP_ROUTES, NAV_ITEMS } from '../routes'
import {
  CRM_APP_PATHS,
  crmAppRouteSegment,
  marketingFormBuilderPath,
  marketingFormDetailPath,
  settingsLeadFormBuilderPath,
  settingsLeadFormDetailPath,
} from '../crmAppPaths'
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from '../../nav/appShellNav'
import { SIDEBAR_AGENCY_MARKETING_ORDER } from '../../nav/sidebarRailBuckets'
import { isNavKeyAllowedOnHost, NAV_KEY_TO_DEPLOY_HOST } from '../../platform/deployHosts'
import { settingsChromeTabHref } from '../../nav/settingsChromeNav'

const ROOT = path.resolve(__dirname, '../../..')
const seg = crmAppRouteSegment

describe('C-6 Marketing Forms IA', () => {
  it('registers Forms inventory under Marketing (hub deep link, not the Form Builder)', () => {
    expect([...SIDEBAR_AGENCY_MARKETING_ORDER]).not.toContain('marketing-forms')
    expect(APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS).toContain('marketing-forms')
    const nav = NAV_ITEMS.find((item) => item.key === 'marketing-forms')
    expect(nav?.path).toBe(CRM_APP_PATHS.marketingForms)

    const list = APP_ROUTES.find((r) => r.key === 'marketing-forms')
    const detail = APP_ROUTES.find((r) => r.key === 'marketing-form-detail')
    const builder = APP_ROUTES.find((r) => r.key === 'marketing-forms-builder')
    expect(list?.path).toBe(seg(CRM_APP_PATHS.marketingForms))
    expect(detail?.path).toBe(`${seg(CRM_APP_PATHS.marketingForms)}/:formId`)
    expect(builder?.path).toBe(`${seg(CRM_APP_PATHS.marketingForms)}/:formId/builder`)
    expect(builder?.Component?.name).toMatch(/Redirect/)
  })

  it('keeps Marketing Forms inventory on the Sales deploy host', () => {
    expect(NAV_KEY_TO_DEPLOY_HOST['marketing-forms']).toBe('sales')
    expect(isNavKeyAllowedOnHost('marketing-forms', 'sales')).toBe(true)
    expect(isNavKeyAllowedOnHost('marketing-forms', 'shell')).toBe(true)
  })

  it('Settings lead-forms is the Forms platform constructor (ADR-007 / P2.5)', () => {
    const list = APP_ROUTES.find((r) => r.key === 'settings-lead-forms')
    const detail = APP_ROUTES.find((r) => r.key === 'settings-intake-form-detail')
    const builder = APP_ROUTES.find((r) => r.key === 'settings-forms-builder')
    const marketingBuilder = APP_ROUTES.find((r) => r.key === 'marketing-forms-builder')
    expect(list?.path).toBe(seg(CRM_APP_PATHS.settingsLeadForms))
    expect(builder?.path).toBe(`${seg(CRM_APP_PATHS.settingsLeadForms)}/:formId/builder`)
    expect(detail?.path).toBe(`${seg(CRM_APP_PATHS.settingsLeadForms)}/:formId`)
    expect(marketingBuilder?.Component?.name).toMatch(/Redirect/)
    expect(builder?.Component).not.toBe(marketingBuilder?.Component)
  })

  it('Settings chrome Sales tab opens the constructor, not Marketing', () => {
    expect(settingsChromeTabHref('sales_setup')).toBe(CRM_APP_PATHS.settingsLeadForms)
  })

  it('detail/builder helpers resolve under Settings, not Marketing', () => {
    expect(CRM_APP_PATHS.marketingForms).toBe('/app/marketing/forms')
    expect(CRM_APP_PATHS.settingsLeadForms).toBe('/app/settings/lead-forms')
    expect(marketingFormDetailPath('f1')).toBe('/app/marketing/forms/f1')
    expect(settingsLeadFormDetailPath('f1')).toBe('/app/settings/lead-forms/f1')
    expect(settingsLeadFormBuilderPath('f1')).toBe('/app/settings/lead-forms/f1/builder')
    expect(marketingFormBuilderPath('f1')).toBe('/app/settings/lead-forms/f1/builder')
  })

  it('Connect Source wires createIntakeForm create-in-setup', () => {
    const src = readFileSync(
      path.join(ROOT, 'src/pages/marketing/MarketingConnectSourcePage.tsx'),
      'utf8',
    )
    expect(src).toContain('createIntakeForm')
    expect(src).toContain('marketing-connect-create-open')
    expect(src).toContain('marketing-connect-create-submit')
    expect(src).toContain('CRM_APP_PATHS.marketingForms')
    expect(src).toContain('CRM_APP_PATHS.settingsIntegrationsMeta')
    expect(src).toContain('marketing-connect-open-meta')
    expect(src).toContain('marketing-connect-meta-empty')
  })

  it('Settings Form Builder library opens the canvas and can archive unused forms', () => {
    const src = readFileSync(path.join(ROOT, 'src/pages/admin/LeadFormsSettingsPage.tsx'), 'utf8')
    expect(src).toContain('admin.forms_builder.library_title')
    expect(src).toContain('settingsLeadFormBuilderPath')
    expect(src).toContain('settingsLeadFormDetailPath')
    expect(src).toContain('default_language')
    expect(src).toContain('admin.lead_forms.wizard.public_language')
    expect(src).toContain("lifecycle_status: 'archived'")
    expect(src).not.toContain("defaultValue: 'Lead forms'")
  })

  it('create wizard asks who fills the form, not Entity Profile first', () => {
    const src = readFileSync(path.join(ROOT, 'src/pages/admin/LeadFormsSettingsPage.tsx'), 'utf8')
    expect(src).toContain('admin.lead_forms.wizard.who_fills')
    expect(src).toContain('hideProfileSelect')
    expect(src).toContain('title_placeholder_company')
    expect(src).not.toContain("defaultValue: '2. Entity profile'")
    expect(src).not.toContain("defaultValue: 'e.g. B2B advertising questionnaire'")
  })
})
