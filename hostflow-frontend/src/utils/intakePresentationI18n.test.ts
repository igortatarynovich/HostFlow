import { describe, expect, it } from 'vitest'
import {
  intakePresentationFieldLabel,
  intakePresentationProfileTitle,
  resolveIntakeQuestionLabel,
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

  it('resolves company driver-hiring field labels', () => {
    const label = intakePresentationFieldLabel(
      t,
      {
        qualified_code: 'service_sales.driver_hiring.driver_categories',
        label: 'fields.service_sales_driver_hiring_driver_categories',
      },
      'ru',
    )
    expect(label).toBe('Какие категории водителей нужны?')
  })

  it('resolves company warehouse-hiring field labels', () => {
    const label = intakePresentationFieldLabel(
      t,
      {
        qualified_code: 'service_sales.warehouse_hiring.worker_roles',
        label: 'fields.service_sales_warehouse_hiring_worker_roles',
      },
      'ru',
    )
    expect(label).toBe('Какие работники нужны?')
  })

  it('resolves company-request sales fields instead of raw i18n keys', () => {
    const label = intakePresentationFieldLabel(
      t,
      {
        qualified_code: 'service_sales.targeted_advertising.need_type',
        label: 'fields.service_sales_need_type',
      },
      'ru',
    )
    expect(label).toBe('Чего касается ваша потребность?')
  })

  it('translates stored Polish template overrides into the UI locale', () => {
    const label = resolveIntakeQuestionLabel(
      t,
      {
        qualified_code: 'service_sales.targeted_advertising.need_type',
        label: 'Czego dotyczy Państwa potrzeba?',
        label_override: 'Czego dotyczy Państwa potrzeba?',
      },
      'en',
    )
    expect(label).toBe('What is your need about?')
  })

  it('resolves recruitment last name in all template locales', () => {
    expect(
      intakePresentationFieldLabel(
        t,
        { qualified_code: 'recruitment.candidate.last_name', label: 'Nazwisko' },
        'en',
      ),
    ).toBe('Last name')
    expect(
      intakePresentationFieldLabel(
        t,
        { qualified_code: 'recruitment.candidate.last_name', label: 'Nazwisko' },
        'ru',
      ),
    ).toBe('Фамилия')
    expect(
      intakePresentationFieldLabel(
        t,
        { qualified_code: 'recruitment.candidate.last_name', label: 'Nazwisko' },
        'pl',
      ),
    ).toBe('Nazwisko')
  })

  it('humanizes leftover catalog keys when no translation exists', () => {
    const label = intakePresentationFieldLabel(
      t,
      {
        qualified_code: 'service_sales.targeted_advertising.unknown_field',
        label: 'fields.service_sales_unknown_field',
      },
      'en',
    )
    expect(label).toBe('unknown field')
  })
})
