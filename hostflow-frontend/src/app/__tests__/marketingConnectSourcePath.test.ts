/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { marketingCampaignPath, marketingConnectSourcePath } from '../crmAppPaths'
import {
  canConnectAnySource,
  canConnectSourceKind,
  type CampaignFlight,
} from '../../pages/marketing/marketingPresentation'

function flight(partial: Partial<CampaignFlight>): CampaignFlight {
  return {
    id: 'f1',
    code: 'flight_1',
    name: 'Flight 1',
    status: 'planned',
    is_current: true,
    forms: [],
    intake_sources: [],
    ...partial,
  }
}

describe('marketingConnectSourcePath', () => {
  it('builds connect-source URL under campaign', () => {
    expect(marketingConnectSourcePath('camp-1')).toBe('/app/marketing/camp-1/sources/new')
    expect(marketingCampaignPath('camp-1')).toBe('/app/marketing/camp-1')
  })
})

describe('canConnectSourceKind (PR1 primary-slot gate)', () => {
  it('allows Meta and public form when empty', () => {
    const f = flight({})
    expect(canConnectSourceKind(f, 'meta')).toBe(true)
    expect(canConnectSourceKind(f, 'public_form')).toBe(true)
    expect(canConnectAnySource(f)).toBe(true)
  })

  it('blocks only the occupied primary endpoint type', () => {
    const withForm = flight({
      forms: [{ id: 'l1', form_id: 'form-1', role: 'primary', is_active: true, title: 'drivers' }],
    })
    expect(canConnectSourceKind(withForm, 'public_form')).toBe(false)
    expect(canConnectSourceKind(withForm, 'meta')).toBe(true)

    const withMeta = flight({
      intake_sources: [
        {
          id: 'l2',
          intake_source_profile_id: 'p1',
          role: 'primary',
          is_active: true,
          name: 'Meta form x',
        },
      ],
    })
    expect(canConnectSourceKind(withMeta, 'meta')).toBe(false)
    expect(canConnectSourceKind(withMeta, 'public_form')).toBe(true)
  })

  it('reports no connect when both primary slots filled', () => {
    const full = flight({
      forms: [{ id: 'l1', form_id: 'form-1', role: 'primary', is_active: true }],
      intake_sources: [
        { id: 'l2', intake_source_profile_id: 'p1', role: 'primary', is_active: true },
      ],
    })
    expect(canConnectAnySource(full)).toBe(false)
  })
})
