// @vitest-environment node
import { describe, expect, it } from 'vitest'
import {
  employmentAcceptBlockerLabel,
  isRitualAcceptForbidden,
  primaryEmploymentAcceptBlocker,
  shouldApplyEmploymentAcceptPolicyOnOpen,
  shouldShowRitualAcceptButton,
} from '../employmentAcceptUi'

describe('employmentAcceptUi (ESO-1 host binding)', () => {
  it('applies policy on awaiting_hr_pickup / pending_review', () => {
    expect(
      shouldApplyEmploymentAcceptPolicyOnOpen({
        handoffStatus: 'pending_review',
        operationalQueue: 'awaiting_hr_pickup',
      }),
    ).toBe(true)
    expect(
      shouldApplyEmploymentAcceptPolicyOnOpen({
        handoffStatus: 'accepted',
        operationalQueue: 'hr_review_in_progress',
      }),
    ).toBe(false)
  })

  it('forbids ritual Accept on auto_accept and after accept', () => {
    expect(
      isRitualAcceptForbidden({
        decision: 'auto_accept',
        ritual_accept_forbidden: true,
        accepted: true,
      }),
    ).toBe(true)
    expect(isRitualAcceptForbidden({ decision: 'review_required', accepted: false })).toBe(false)
  })

  it('never shows ritual Accept button on the ESO-1 host (negative proof)', () => {
    expect(shouldShowRitualAcceptButton({ decision: 'auto_accept', ritual_accept_forbidden: true })).toBe(
      false,
    )
    expect(shouldShowRitualAcceptButton({ decision: 'review_required', blockers: [{ code: 'x' }] })).toBe(
      false,
    )
    expect(shouldShowRitualAcceptButton(null)).toBe(false)
  })

  it('surfaces the primary concrete blocker', () => {
    const policy = {
      decision: 'review_required',
      blockers: [
        { code: 'invalid_package', message: 'Package missing fits_decision' },
        { code: 'other', message: 'second' },
      ],
    }
    expect(primaryEmploymentAcceptBlocker(policy)?.code).toBe('invalid_package')
    expect(employmentAcceptBlockerLabel(primaryEmploymentAcceptBlocker(policy))).toContain('Package missing')
  })
})
