import { describe, expect, it } from 'vitest'

import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import type { CandidateProfile } from '../../api/candidate_profiles'
import {
  getCardSectionOrder,
  hasActiveEffectiveLayout,
  isCardSectionVisible,
  layoutFieldLabel,
  layoutFieldRequired,
  layoutFieldVisible,
  resolveLayoutField,
} from '../fieldLayoutUtils'
import { isFieldRequired, isFieldVisible } from '../profileUtils'

const mockLayout: EffectiveCardLayout = {
  entity_type: 'candidate',
  layout_code: 'recruitment.candidate.default',
  resolution_source: 'platform_layout',
  sections: [
    {
      code: 'basic',
      order: 10,
      fields: [
        {
          id: '1',
          qualified_code: 'recruitment.candidate.first_name',
          module: 'recruitment',
          entity_type: 'candidate',
          field_type: 'text',
          name: 'Given name',
          ownership: 'recruitment',
          legacy_aliases: ['first_name'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'basic',
          sort_order: 10,
          visible: true,
          required: true,
          label_override: 'Registry first name',
        },
        {
          id: '2',
          qualified_code: 'recruitment.candidate.contacts.email',
          module: 'recruitment',
          entity_type: 'candidate',
          field_type: 'email',
          name: 'Email',
          ownership: 'recruitment',
          legacy_aliases: ['email'],
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
      code: 'personal',
      order: 20,
      fields: [
        {
          id: '3',
          qualified_code: 'platform.identity.birth_date',
          module: 'platform',
          entity_type: 'candidate',
          field_type: 'date',
          name: 'Birth date',
          ownership: 'platform',
          legacy_aliases: ['birth_date'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'personal',
          sort_order: 10,
          visible: true,
          required: false,
        },
      ],
    },
    {
      code: 'experience',
      order: 30,
      fields: [
        {
          id: '4',
          qualified_code: 'recruitment.candidate.experience.years_ce',
          module: 'recruitment',
          entity_type: 'candidate',
          field_type: 'integer',
          name: 'Years CE',
          ownership: 'recruitment',
          legacy_aliases: ['experience_eu_years', 'years_ce'],
          registry_version: 'field_registry_v1',
          status: 'active',
          section_code: 'experience',
          sort_order: 10,
          visible: true,
          required: true,
        },
      ],
    },
  ],
  fields: [],
}

mockLayout.fields = mockLayout.sections.flatMap((section) => section.fields)

const profileWithHiddenEmail: CandidateProfile = {
  id: 'profile-1',
  code: 'custom_profile',
  name: 'Custom',
  config: {
    field_configs: [
      {
        field_key: 'email',
        field_type: 'email',
        required: true,
        order: 1,
        visible: true,
      },
    ],
  },
} as CandidateProfile

describe('fieldLayoutUtils', () => {
  it('detects active registry layout', () => {
    expect(hasActiveEffectiveLayout(mockLayout)).toBe(true)
    expect(hasActiveEffectiveLayout(null)).toBe(false)
    expect(
      hasActiveEffectiveLayout({
        entity_type: 'candidate',
        resolution_source: 'not_found',
        sections: [],
        fields: [],
      }),
    ).toBe(false)
  })

  it('resolves legacy field keys from qualified codes and aliases', () => {
    expect(resolveLayoutField(mockLayout, 'first_name')?.qualified_code).toBe(
      'recruitment.candidate.first_name',
    )
    expect(resolveLayoutField(mockLayout, 'experience_eu_years')?.required).toBe(true)
  })

  it('uses registry visibility/required/label before profile config', () => {
    expect(layoutFieldVisible(profileWithHiddenEmail, 'email', mockLayout, () => true)).toBe(false)
    expect(layoutFieldRequired(profileWithHiddenEmail, 'first_name', mockLayout, () => false)).toBe(true)
    expect(
      layoutFieldLabel(profileWithHiddenEmail, 'first_name', 'Default', mockLayout, () => 'Profile label'),
    ).toBe('Registry first name')
  })

  it('falls back to profileUtils when layout is missing', () => {
    expect(isFieldVisible(profileWithHiddenEmail, 'email', null)).toBe(true)
    expect(isFieldRequired(profileWithHiddenEmail, 'email', null)).toBe(true)
  })

  it('closure: registry layout takes precedence over profile when API layout is active', () => {
    expect(isFieldVisible(profileWithHiddenEmail, 'email', mockLayout)).toBe(false)
    expect(isFieldRequired(profileWithHiddenEmail, 'email', mockLayout)).toBe(false)
    expect(isFieldVisible(profileWithHiddenEmail, 'first_name', mockLayout)).toBe(true)
    expect(isFieldRequired(profileWithHiddenEmail, 'first_name', mockLayout)).toBe(true)
  })

  it('derives section order and visibility from registry sections', () => {
    expect(getCardSectionOrder(mockLayout)).toEqual(['basic', 'personal', 'experience'])
    expect(isCardSectionVisible('basic', mockLayout)).toBe(true)
    expect(isCardSectionVisible('operations', mockLayout)).toBe(false)
  })

  it('returns default section order when layout is missing', () => {
    expect(getCardSectionOrder(null)).toBeNull()
    expect(isCardSectionVisible('basic', null)).toBe(true)
  })
})

describe('fieldRegistry API smoke constants', () => {
  it('exports default layout codes for vacancy and client read integration', async () => {
    const mod = await import('../../api/fieldRegistry')
    expect(mod.DEFAULT_VACANCY_LAYOUT_CODE).toBe('recruitment.vacancy.default')
    expect(mod.DEFAULT_CLIENT_LAYOUT_CODE).toBe('crm.client.default')
    expect(mod.DEFAULT_CANDIDATE_LAYOUT_CODE).toBe('recruitment.candidate.default')
  })
})
