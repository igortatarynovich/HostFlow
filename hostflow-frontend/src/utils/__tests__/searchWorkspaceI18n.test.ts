import { describe, expect, it } from 'vitest'
import type { TranslateFn } from '../../i18n'
import {
  localizeSearchDayItem,
  resolveSearchDayCopyCode,
  searchWorkspaceStatusLabel,
} from '../searchWorkspaceI18n'

const t: TranslateFn = (key, options) => {
  const vals = options?.values ? `:${JSON.stringify(options.values)}` : ''
  return `${key}${vals}`
}

describe('searchWorkspaceI18n', () => {
  it('maps later_setup ids and audience_setup to copy codes', () => {
    expect(resolveSearchDayCopyCode({ id: 'later_setup_abc', kind: '' })).toBe('later_setup')
    expect(resolveSearchDayCopyCode({ id: 'audience_setup' })).toBe('audience_setup')
    expect(resolveSearchDayCopyCode({ id: 'acq_x', kind: 'acquisition_launch' })).toBe(
      'acquisition_launch',
    )
  })

  it('translates launch-ads pulse copy instead of the API Russian strings', () => {
    const localized = localizeSearchDayItem(
      {
        id: 'acquisition_launch',
        kind: 'acquisition_launch',
        severity: 'error',
        headline: 'Запустить рекламу',
        message: 'Поток откликов слабый',
        reason: 'Нужен приток новых откликов.',
        action_label: 'Запустить',
        target: 'acquisition',
        href: '/x',
      },
      t,
      { searchTitle: 'Kierowca C+E' },
    )
    expect(localized.headline).toBe('app.search_pulse.acquisition_launch.headline')
    expect(localized.reason).toBe('app.search_pulse.reason.acquisition_launch')
    expect(localized.action_label).toBe('app.search_pulse.action.launch')
    expect(localized.message).toContain('Kierowca C+E')
  })

  it('maps vacancy status to workspace labels', () => {
    expect(searchWorkspaceStatusLabel(t, 'open', false)).toBe('app.search_workspace.status.active')
    expect(searchWorkspaceStatusLabel(t, 'paused', false)).toBe('app.search_workspace.status.on_hold')
    expect(searchWorkspaceStatusLabel(t, 'open', true)).toBe('app.search_workspace.status.archived')
  })
})
