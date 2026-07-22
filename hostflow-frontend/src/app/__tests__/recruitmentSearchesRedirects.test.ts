import { describe, expect, it } from 'vitest'
import { NAV_ITEMS, APP_ROUTES } from '../routes'
import { CRM_APP_PATHS } from '../crmAppPaths'
import { SIDEBAR_AGENCY_RECRUITMENT_ORDER } from '../../nav/sidebarRailBuckets'
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from '../../nav/appShellNav'

describe('recruitment searches deprecation', () => {
  it('removes Подборы from primary NAV_ITEMS', () => {
    expect(NAV_ITEMS.find((item) => item.key === 'recruitment-searches')).toBeUndefined()
  })

  it('keeps legacy list/new routes as redirect components (not Searches pages)', () => {
    const list = APP_ROUTES.find((item) => item.key === 'recruitment-searches')
    const create = APP_ROUTES.find((item) => item.key === 'recruitment-searches-new')
    expect(list?.path).toBe('recruitment/searches')
    expect(create?.path).toBe('recruitment/searches/new')
    expect(list?.Component).toBeTruthy()
    expect(create?.Component).toBeTruthy()
    expect(list?.Component.name).toContain('MarketingRedirect')
    expect(create?.Component.name).toContain('MarketingRedirect')
  })

  it('places vacancies (not searches) on the recruitment rail and unhides vacancies', () => {
    expect([...SIDEBAR_AGENCY_RECRUITMENT_ORDER]).toEqual(
      expect.arrayContaining(['vacancies', 'recruitment-inbox', 'candidates']),
    )
    expect(SIDEBAR_AGENCY_RECRUITMENT_ORDER).not.toContain('recruitment-searches')
    expect(APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS).not.toContain('vacancies')
  })

  it('keeps Marketing as the attraction NAV entry', () => {
    const marketing = NAV_ITEMS.find((item) => item.key === 'marketing')
    expect(marketing?.path).toBe(CRM_APP_PATHS.marketing)
  })
})
