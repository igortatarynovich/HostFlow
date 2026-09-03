import { describe, expect, it } from 'vitest'

import type { Application } from '../../api/types/application'
import {
  applicationCallOutcome,
  applicationMatchesSearch,
  applicationNeedsFirstContact,
} from '../applicationDisplay'

function application(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    module: 'recruitment',
    contact: { name: 'Ada Kowalska', phone: '+48500111222', email: 'ada@example.com' },
    title: 'Ada Kowalska',
    status: 'new',
    tab_bucket: 'new',
    extensions: {},
    ...overrides,
  }
}

describe('applicationDisplay call outcome', () => {
  it('reads latest call result from extensions', () => {
    expect(
      applicationCallOutcome(
        application({
          extensions: { call_result_v1: { result: 'no_answer', note: 'try later' } },
        }),
      ),
    ).toBe('no_answer')
  })

  it('treats a saved call as first contact already done', () => {
    const called = application({
      status: 'in_progress',
      tab_bucket: 'in_progress',
      extensions: { call_result_v1: { result: 'interested' } },
    })
    expect(applicationNeedsFirstContact(called)).toBe(false)
    expect(applicationNeedsFirstContact(application())).toBe(true)
  })

  it('matches search by name or phone', () => {
    const row = application()
    expect(applicationMatchesSearch(row, 'kowalska')).toBe(true)
    expect(applicationMatchesSearch(row, '500111')).toBe(true)
    expect(applicationMatchesSearch(row, 'nobody')).toBe(false)
  })
})
