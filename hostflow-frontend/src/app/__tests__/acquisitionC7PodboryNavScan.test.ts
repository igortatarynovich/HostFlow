/** @vitest-environment node */
/**
 * C-7 scan: Подборы must not remain a primary launch / nav surface.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const FE_ROOT = join(__dirname, '../..')

function read(rel: string): string {
  return readFileSync(join(FE_ROOT, rel), 'utf8')
}

describe('C-7 Подборы nav retire', () => {
  it('SearchesListPage redirects to Marketing', () => {
    const text = read('pages/recruitment/SearchesListPage.tsx')
    expect(text).toMatch(/Navigate/)
    expect(text).toMatch(/CRM_APP_PATHS\.marketing/)
    expect(text).not.toMatch(/listVacancies/)
  })

  it('CreateSearchWizardPage redirects to Marketing new', () => {
    const text = read('pages/recruitment/CreateSearchWizardPage.tsx')
    expect(text).toMatch(/Navigate/)
    expect(text).toMatch(/CRM_APP_PATHS\.marketingNew/)
    expect(text).not.toMatch(/createLaunchSearch/)
  })

  it('AppShell does not mount WorkContextTabs; sidebar owns primary nav', () => {
    const text = read('app/AppShell.tsx')
    expect(text).not.toMatch(/WorkContextTabs/)
    expect(text).toMatch(/WorkspaceBackBar/)
  })

  it('WorkspaceBackBar is history back only (no section tabs)', () => {
    const text = read('components/nav/WorkspaceBackBar.tsx')
    expect(text).not.toMatch(/recruitment-searches/)
    expect(text).not.toMatch(/defaultValue:\s*'Подборы'/)
    expect(text).toMatch(/navigate\(-1\)/)
  })

  it('sidebar hides recruitment-searches and drops it from recruitment rail', () => {
    const hidden = read('nav/appShellNav.ts')
    expect(hidden).toMatch(/'recruitment-searches'/)
    const buckets = read('nav/sidebarRailBuckets.ts')
    expect(buckets).not.toMatch(/SIDEBAR_AGENCY_RECRUITMENT_ORDER = \[[\s\S]*'recruitment-searches'/)
  })
})
