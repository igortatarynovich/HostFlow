/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { APP_ROUTES } from '../routes'
import { CRM_APP_PATHS, crmAppRouteSegment } from '../crmAppPaths'
import { settingsChromeActiveTab } from '../../nav/settingsChromeNav'

describe('requirement policy overlay route', () => {
  it('registers the RPM-2 operator page under Settings CRM setup', () => {
    const route = APP_ROUTES.find((item) => item.key === 'settings-requirement-policy')
    expect(route?.path).toBe(crmAppRouteSegment(CRM_APP_PATHS.settingsRequirementPolicy))
    expect(route?.permission).toBe('admin.users')
    expect(CRM_APP_PATHS.settingsRequirementPolicy).toBe('/app/settings/requirement-policy')
    expect(settingsChromeActiveTab(CRM_APP_PATHS.settingsRequirementPolicy, '')).toBe(
      'recruitment_setup',
    )
  })
})
