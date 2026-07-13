import { describe, expect, it } from 'vitest'
import {
  intakePresentationFieldLabel,
  intakePresentationProfileTitle,
} from './intakePresentationI18n'

const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key

describe('intakePresentationI18n', () => {
  it('resolves dotted qualified field codes via scoped lookup', () => {
    const label = intakePresentationFieldLabel(
      t,
      {
        qualified_code: 'recruitment.candidate.first_name',
        label: 'fields.recruitment_candidate_first_name',
      },
      'ru',
    )
    expect(label).toBe('Имя')
  })

  it('resolves dotted entity profile codes via scoped lookup', () => {
    const title = intakePresentationProfileTitle(
      t,
      {
        entity_profile_code: 'recruitment.candidate.office_worker',
        profile_name: 'Office Worker Candidate',
      },
      'ru',
    )
    expect(title).toBe('Офисный сотрудник')
  })
})
