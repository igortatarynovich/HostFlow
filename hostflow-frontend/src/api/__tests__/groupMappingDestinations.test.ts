import { describe, expect, it } from 'vitest'
import {
  groupMappingDestinations,
  groupMarketingSourcesByType,
  type MappingDestination,
  type MarketingSourceSummary,
} from '../marketingSources'

function dest(
  code: string,
  label: string,
  group: string,
  group_label: string,
): MappingDestination {
  return {
    code,
    label,
    field_type: 'string',
    choice: false,
    options: [],
    group,
    group_label,
  }
}

describe('groupMappingDestinations', () => {
  it('keeps Field Registry sections in order and does not flatten labels', () => {
    const groups = groupMappingDestinations([
      dest('platform.identity.address', 'Address', 'candidate', 'Candidate'),
      dest('recruitment.candidate.contacts.email', 'Email', 'candidate', 'Candidate'),
      dest('crm.client.address', 'Address', 'client', 'Client'),
    ])
    expect(groups.map((g) => g.key)).toEqual(['candidate', 'client'])
    expect(groups[0].items.map((i) => i.code)).toEqual([
      'platform.identity.address',
      'recruitment.candidate.contacts.email',
    ])
    expect(groups[1].items[0].label).toBe('Address')
  })
})

function source(
  source_id: string,
  destination: string | null,
): MarketingSourceSummary {
  return {
    source_id,
    provider: 'meta',
    display_name: source_id,
    connection_status: 'connected',
    mapping_health: 'valid',
    last_submission_at: null,
    last_error_at: null,
    last_error_code: null,
    campaign_count: 0,
    flight_count: 0,
    mapping_path: `/app/marketing/sources/${source_id}/mapping`,
    test_lead_path: `/app/marketing/sources/${source_id}/test-lead`,
    settings_path: '/app/settings/integrations/meta',
    destination,
  }
}

describe('groupMarketingSourcesByType', () => {
  it('groups by destination type, not vacancy, and keeps Candidate before Sales', () => {
    const groups = groupMarketingSourcesByType([
      source('sales-1', 'sales_inquiry'),
      source('cand-1', 'candidate_application'),
      source('cand-2', 'candidate_application'),
      source('none-1', null),
    ])
    expect(groups.map((g) => g.key)).toEqual([
      'candidate_application',
      'sales_inquiry',
      'unset',
    ])
    expect(groups[0].items.map((i) => i.source_id)).toEqual(['cand-1', 'cand-2'])
  })
})
