import { describe, expect, it } from 'vitest'
import { groupMappingDestinations, type MappingDestination } from '../marketingSources'

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
