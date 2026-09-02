import { describe, expect, it } from 'vitest'

import type { Application } from '../../../api/types/application'
import { applicationFormAnswerRows } from '../applicationFormAnswers'

function application(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    module: 'recruitment',
    contact: {
      name: 'Kudakwashe Tapfumaneyi',
      phone: '+48503499897',
      email: 'kudakwashetapfumaneyi5@gmail.com',
    },
    title: 'Kudakwashe Tapfumaneyi',
    status: 'in_progress',
    tab_bucket: 'in_progress',
    extensions: {},
    ...overrides,
  }
}

describe('applicationFormAnswerRows', () => {
  it('keeps only human questions and formats answers for reading', () => {
    const rows = applicationFormAnswerRows(
      application({
        extensions: {
          meta_form_answers: [
            {
              name: 'какой у вас опыт работы водителем c+e в международных перевозках по ес?',
              values: ['1–2_года'],
            },
            { name: 'у вас есть действующее водительское удостоверение категории c+e?', values: ['да'] },
            {
              name: 'вы ознакомились с условиями работы и принимаете основные условия предложения?',
              values: ['да'],
            },
            { name: 'full_name', values: ['Kudakwashe Tapfumaneyi'] },
            { name: 'phone', values: ['+48503499897'] },
            {
              name: 'как долго еще будет действовать документ или статус, позволяющий вам легально работать в польше?',
              values: ['____от_6_до_12_месяцев'],
            },
            {
              name: 'какой у вас сейчас статус, позволяющий легально находиться и работать в польше?',
              values: ['________действующая_карта_побыту_с_доступом_к_рынку_труда'],
            },
            { name: 'email', values: ['kudakwashetapfumaneyi5@gmail.com'] },
            {
              name: 'inbox_url',
              values: ['https://business.facebook.com/latest/28393661780251008?nav_ref=thread_view_by_psid'],
            },
            { name: 'campaign_name', values: ['Leads RU C/CE Driver'] },
            { name: 'ad_id', values: ['120233'] },
          ],
        },
      }),
    )

    expect(rows.map((r) => r.label)).toEqual([
      'Какой у вас опыт работы водителем c+e в международных перевозках по ес?',
      'У вас есть действующее водительское удостоверение категории c+e?',
      'Вы ознакомились с условиями работы и принимаете основные условия предложения?',
      'Как долго еще будет действовать документ или статус, позволяющий вам легально работать в польше?',
      'Какой у вас сейчас статус, позволяющий легально находиться и работать в польше?',
    ])
    expect(rows.map((r) => r.value)).toEqual([
      '1–2 года',
      'Да',
      'Да',
      'От 6 до 12 месяцев',
      'Действующая карта побыту с доступом к рынку труда',
    ])
  })

  it('does not fall back to contact identity when the form has no questions', () => {
    const rows = applicationFormAnswerRows(
      application({
        extensions: {
          meta_form_answers: [
            { name: 'full_name', values: ['Kudakwashe Tapfumaneyi'] },
            { name: 'inbox_url', values: ['https://business.facebook.com/latest/thread'] },
          ],
        },
      }),
    )
    expect(rows).toEqual([])
  })
})
