import { describe, expect, it } from 'vitest'

import {
  buildSuccessPathItems,
  isSuccessPathComplete,
  pickSuccessPathNext,
} from '../successPathReadiness'

const emptySteps = {
  company_created: false,
  first_client_created: false,
  first_vacancy_created: false,
  first_lead_created: false,
}

describe('successPathReadiness', () => {
  it('employer path: company → vacancy before lead', () => {
    const items = buildSuccessPathItems({
      businessType: 'employer',
      steps: { ...emptySteps, company_created: true },
      metaConnectedOrDeferred: false,
      metaDeferredOnly: false,
      teammatesInvited: false,
    })
    expect(items.some((i) => i.id === 'client')).toBe(false)
    expect(items.some((i) => i.id === 'contact' as never)).toBe(false)
    expect(pickSuccessPathNext(items, 'employer')?.id).toBe('vacancy')
  })

  it('agency path: client before vacancy', () => {
    const items = buildSuccessPathItems({
      businessType: 'agency',
      steps: { ...emptySteps, company_created: true },
      metaConnectedOrDeferred: false,
      metaDeferredOnly: false,
      teammatesInvited: false,
    })
    expect(pickSuccessPathNext(items, 'agency')?.id).toBe('client')
  })

  it('services path: skips vacancy; client done when lead exists', () => {
    const items = buildSuccessPathItems({
      businessType: 'services',
      steps: { ...emptySteps, company_created: true, first_lead_created: true },
      metaConnectedOrDeferred: true,
      metaDeferredOnly: true,
      teammatesInvited: false,
    })
    expect(items.some((i) => i.id === 'vacancy')).toBe(false)
    expect(items.find((i) => i.id === 'client')?.done).toBe(true)
    expect(pickSuccessPathNext(items, 'services')?.id).toBe('invite')
  })

  it('lead step links to intake when there is no lead yet', () => {
    const items = buildSuccessPathItems({
      businessType: 'employer',
      steps: {
        ...emptySteps,
        company_created: true,
        first_vacancy_created: true,
      },
      metaConnectedOrDeferred: true,
      metaDeferredOnly: false,
      teammatesInvited: false,
    })
    const lead = items.find((i) => i.id === 'lead')
    expect(lead?.href).toContain('/setup/intake')
    expect(pickSuccessPathNext(items, 'employer')?.id).toBe('lead')
  })

  it('optional source step is not next while core path remains', () => {
    const items = buildSuccessPathItems({
      businessType: 'agency',
      steps: { ...emptySteps, company_created: true, first_client_created: true },
      metaConnectedOrDeferred: false,
      metaDeferredOnly: false,
      teammatesInvited: false,
    })
    expect(pickSuccessPathNext(items, 'agency')?.id).toBe('vacancy')
    expect(items.find((i) => i.id === 'meta')?.href).toContain('/settings/integrations')
    expect(items.find((i) => i.id === 'meta')?.href).not.toContain('/meta')
  })

  it('meta and invite stay optional for completion', () => {
    const items = buildSuccessPathItems({
      businessType: 'employer',
      steps: {
        company_created: true,
        first_vacancy_created: true,
        first_lead_created: true,
        first_client_created: false,
      },
      metaConnectedOrDeferred: false,
      metaDeferredOnly: false,
      teammatesInvited: false,
    })
    expect(isSuccessPathComplete(items)).toBe(true)
    expect(pickSuccessPathNext(items, 'employer')?.id).toBe('meta')
  })
})
