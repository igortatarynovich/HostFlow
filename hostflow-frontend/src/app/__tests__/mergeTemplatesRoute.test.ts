/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'

describe('document merge templates route', () => {
  it('registers /app/settings/document-merge-templates', () => {
    const route = APP_ROUTES.find((item) => item.key === 'settings-merge-templates')
    expect(route).toBeTruthy()
    expect(route?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.settingsMergeTemplates))
    expect(route?.permission).toEqual(['documents.manage', 'settings.view'])
    expect(CRM_APP_PATHS.settingsMergeTemplates).toBe('/app/settings/document-merge-templates')
  })
})
