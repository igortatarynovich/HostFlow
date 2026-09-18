import { describe, expect, it } from 'vitest'
import {
  DESTINATION_IGNORE,
  actionSelectValue,
  bindingFromActionSelect,
  bindingFromDestinationSelect,
  destinationSelectValue,
} from '../mappingDestinationSelect'

describe('mappingDestinationSelect', () => {
  it('keeps empty destination Unmapped, not Ignore', () => {
    expect(destinationSelectValue('unmapped', '')).toBe('')
    expect(bindingFromDestinationSelect('')).toEqual({
      binding: 'unmapped',
      destination_code: '',
    })
  })

  it('treats the ignore sentinel as an explicit Ignore decision', () => {
    expect(destinationSelectValue('ignored', '')).toBe(DESTINATION_IGNORE)
    expect(bindingFromDestinationSelect(DESTINATION_IGNORE)).toEqual({
      binding: 'ignored',
      destination_code: '',
    })
  })

  it('maps a HostFlow field as Mapped', () => {
    expect(
      bindingFromDestinationSelect('recruitment.candidate.contacts.email'),
    ).toEqual({
      binding: 'mapped',
      destination_code: 'recruitment.candidate.contacts.email',
    })
  })

  it('does not show Unmapped as Mapuj in the usage control', () => {
    expect(actionSelectValue('unmapped')).toBe('unset')
    expect(actionSelectValue('mapped')).toBe('map')
    expect(actionSelectValue('ignored')).toBe('ignore')
    expect(bindingFromActionSelect('ignore', '')).toBe('ignored')
    expect(bindingFromActionSelect('map', '')).toBe('unmapped')
    expect(bindingFromActionSelect('map', 'recruitment.candidate.contacts.email')).toBe(
      'mapped',
    )
  })
})
