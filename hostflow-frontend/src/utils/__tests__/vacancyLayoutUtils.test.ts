import { describe, expect, it } from 'vitest'

import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import {
  getVacancyFieldsRenderOrder,
  vacancyFieldKeyFromQualified,
  vacancyFieldLabel,
  vacancyFieldRequired,
  vacancyFieldVisible,
} from '../vacancyLayoutUtils'

const mockVacancyLayout: EffectiveCardLayout = {
  entity_type: 'vacancy',
  layout_code: 'recruitment.vacancy.default',
  resolution_source: 'platform_layout',
  sections: [
    {
      code: 'basic',
      order: 10,
      fields: [
        {
          id: 'v1',
          qualified_code: 'recruitment.vacancy.title',
          module: 'recruitment',
          entity_type: 'vacancy',
          field_type: 'text',
          name: 'Title',
          ownership: 'recruitment',
          legacy_aliases: ['title'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'basic',
          sort_order: 10,
          visible: true,
          required: true,
          label_override: 'Registry title',
        },
        {
          id: 'v2',
          qualified_code: 'recruitment.vacancy.location',
          module: 'recruitment',
          entity_type: 'vacancy',
          field_type: 'text',
          name: 'Location',
          ownership: 'recruitment',
          legacy_aliases: ['location'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'basic',
          sort_order: 20,
          visible: false,
          required: false,
        },
      ],
    },
    {
      code: 'details',
      order: 20,
      fields: [
        {
          id: 'v3',
          qualified_code: 'recruitment.vacancy.description',
          module: 'recruitment',
          entity_type: 'vacancy',
          field_type: 'textarea',
          name: 'Description',
          ownership: 'recruitment',
          legacy_aliases: ['description'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'details',
          sort_order: 10,
          visible: true,
          required: false,
        },
      ],
    },
  ],
  fields: [],
}

mockVacancyLayout.fields = mockVacancyLayout.sections.flatMap((section) => section.fields)

describe('vacancyLayoutUtils', () => {
  it('maps qualified codes to vacancy field keys', () => {
    expect(vacancyFieldKeyFromQualified('recruitment.vacancy.title')).toBe('title')
    expect(vacancyFieldKeyFromQualified('recruitment.vacancy.headcount_target')).toBe('headcount_target')
  })

  it('respects registry visibility and labels', () => {
    expect(vacancyFieldVisible('title', mockVacancyLayout)).toBe(true)
    expect(vacancyFieldVisible('location', mockVacancyLayout)).toBe(false)
    expect(vacancyFieldLabel('title', 'Название', mockVacancyLayout)).toBe('Registry title')
    expect(vacancyFieldRequired('title', mockVacancyLayout)).toBe(true)
  })

  it('orders fields from layout sections', () => {
    expect(getVacancyFieldsRenderOrder(mockVacancyLayout)).toEqual(['title', 'location', 'description'])
  })

  it('falls back to default order without active layout', () => {
    const order = getVacancyFieldsRenderOrder(null)
    expect(order[0]).toBe('title')
    expect(order).toContain('description')
  })
})
