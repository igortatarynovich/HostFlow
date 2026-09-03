/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { CRM_APP_PATHS } from '../crmAppPaths'
import {
  getFirstVacancySetupPath,
  getHiringSetupEntryPath,
  type ActivationStatusLike,
} from '../activationRoutes'

function status(
  overrides: Partial<ActivationStatusLike> & {
    steps?: Partial<ActivationStatusLike['steps']>
  } = {},
): ActivationStatusLike {
  return {
    business_type: overrides.business_type ?? 'agency',
    onboarding_required: overrides.onboarding_required ?? false,
    activation_required: overrides.activation_required ?? true,
    steps: {
      company_created: true,
      first_client_created: false,
      first_vacancy_created: false,
      first_campaign_created: false,
      first_service_order_created: false,
      next_action_created: false,
      ...overrides.steps,
    },
  }
}

describe('getHiringSetupEntryPath', () => {
  it('sends an agency without a client to setup client first', () => {
    expect(getHiringSetupEntryPath(status())).toBe(CRM_APP_PATHS.setupClient)
  })

  it('sends an agency with a client but no vacancy to setup vacancy', () => {
    expect(
      getHiringSetupEntryPath(status({ steps: { first_client_created: true } })),
    ).toBe(CRM_APP_PATHS.setupVacancy)
  })

  it('sends an agency with client and vacancy to create campaign', () => {
    expect(
      getHiringSetupEntryPath(
        status({
          steps: { first_client_created: true, first_vacancy_created: true },
        }),
      ),
    ).toBe(CRM_APP_PATHS.marketingNew)
  })

  it('does not send an agency back to client setup once a vacancy exists', () => {
    expect(
      getHiringSetupEntryPath(status({ steps: { first_vacancy_created: true } })),
    ).toBe(CRM_APP_PATHS.marketingNew)
  })

  it('skips client for employers and starts at vacancy', () => {
    expect(getHiringSetupEntryPath(status({ business_type: 'employer' }))).toBe(
      CRM_APP_PATHS.setupVacancy,
    )
  })
})

describe('getFirstVacancySetupPath', () => {
  it('asks agencies to name a client before the vacancy', () => {
    expect(getFirstVacancySetupPath(status())).toBe(CRM_APP_PATHS.setupClient)
  })

  it('opens vacancy setup once a client exists', () => {
    expect(
      getFirstVacancySetupPath(status({ steps: { first_client_created: true } })),
    ).toBe(CRM_APP_PATHS.setupVacancy)
  })
})
