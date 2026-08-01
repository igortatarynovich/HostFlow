/** @vitest-environment node */
import { describe, expect, it } from 'vitest'
import { marketingCampaignPath, marketingConnectSourcePath } from '../crmAppPaths'
import { parseMetaAdvertisingIds } from '../../api/platformCampaigns'
import {
  canConnectAnySource,
  canConnectSourceKind,
  nextMetaIntakeRole,
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

describe('canConnectSourceKind (public primary gate; Meta multi-form)', () => {
  it('allows Meta and public form when empty', () => {
    const f = flight({})
    expect(canConnectSourceKind(f, 'meta')).toBe(true)
    expect(canConnectSourceKind(f, 'public_form')).toBe(true)
    expect(canConnectAnySource(f)).toBe(true)
  })

  it('blocks only HostFlow public primary; Meta stays open as secondary', () => {
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
    expect(canConnectSourceKind(withMeta, 'meta')).toBe(true)
    expect(canConnectSourceKind(withMeta, 'public_form')).toBe(true)
    expect(canConnectAnySource(withMeta)).toBe(true)
    expect(nextMetaIntakeRole(withMeta)).toBe('secondary')
  })

  it('still allows Meta when both primary slots filled', () => {
    const full = flight({
      forms: [{ id: 'l1', form_id: 'form-1', role: 'primary', is_active: true }],
      intake_sources: [
        { id: 'l2', intake_source_profile_id: 'p1', role: 'primary', is_active: true },
      ],
    })
    expect(canConnectSourceKind(full, 'public_form')).toBe(false)
    expect(canConnectSourceKind(full, 'meta')).toBe(true)
    expect(canConnectAnySource(full)).toBe(true)
    expect(nextMetaIntakeRole(full)).toBe('secondary')
  })
})

describe('parseMetaAdvertisingIds', () => {
  it('parses raw campaign id and Ads Manager URL', () => {
    expect(parseMetaAdvertisingIds('120253341522370547')).toEqual({
      meta_campaign_id: '120253341522370547',
    })
    expect(
      parseMetaAdvertisingIds(
        'https://adsmanager.facebook.com/adsmanager/manage/campaigns?campaign_id=120253341522370547&adset_id=120253342594270547',
      ),
    ).toEqual({
      meta_campaign_id: '120253341522370547',
      meta_adset_id: '120253342594270547',
    })
  })
})
