import { describe, expect, it } from 'vitest'
import { isEdgeToEdgeTablePath, ownsCrmWorkspaceScroll } from '../crmWorkspaceLayout'
import { CRM_APP_PATHS as P } from '../crmAppPaths'

describe('crmWorkspaceLayout', () => {
  it('treats native list tables as edge-to-edge', () => {
    expect(isEdgeToEdgeTablePath(P.candidates)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.vacancies)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.clientsDirectory)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.recruitmentInbox)).toBe(true)
    expect(isEdgeToEdgeTablePath(`${P.recruitmentInbox}/app-1`)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.sales)).toBe(true)
    expect(isEdgeToEdgeTablePath(`${P.sales}/inquiries/si-1`)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.salesOrders)).toBe(true)
  })

  it('keeps detail and form pages inset (not edge-to-edge)', () => {
    expect(isEdgeToEdgeTablePath(`${P.candidates}/cand-1`)).toBe(false)
    expect(isEdgeToEdgeTablePath(`${P.vacancies}/vac-1`)).toBe(false)
    expect(isEdgeToEdgeTablePath(P.vacancyNew)).toBe(false)
    expect(isEdgeToEdgeTablePath(`${P.agencyClients}/co-1`)).toBe(false)
    expect(isEdgeToEdgeTablePath(`${P.invoices}/inv-1`)).toBe(false)
    expect(isEdgeToEdgeTablePath(P.profile)).toBe(false)
    expect(isEdgeToEdgeTablePath(P.inbox)).toBe(false)
  })

  it('lets vacancy detail own scroll without going edge-to-edge', () => {
    expect(ownsCrmWorkspaceScroll(`${P.vacancies}/vac-1`)).toBe(true)
    expect(isEdgeToEdgeTablePath(`${P.vacancies}/vac-1`)).toBe(false)
  })

  it('lets recruitment inbox own scroll and stay edge-to-edge', () => {
    expect(ownsCrmWorkspaceScroll(P.recruitmentInbox)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.recruitmentInbox)).toBe(true)
  })

  it('lets marketing forms own inner scroll so PageShell can scroll', () => {
    expect(ownsCrmWorkspaceScroll(P.marketingForms)).toBe(true)
    expect(ownsCrmWorkspaceScroll(`${P.marketingForms}/form-1`)).toBe(true)
    expect(isEdgeToEdgeTablePath(P.marketingForms)).toBe(false)
    expect(ownsCrmWorkspaceScroll(P.marketing)).toBe(false)
  })
})
