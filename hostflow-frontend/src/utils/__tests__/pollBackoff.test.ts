import { describe, expect, it } from 'vitest'
import { isTimeoutError, isTransientRequestError } from '../errorHandling'
import { nextPollDelayMs, POLL_BACKOFF_CAP_MS, POLL_BASE_MS, shouldDeferPollWake } from '../pollBackoff'

describe('nextPollDelayMs', () => {
  it('keeps the base interval after a success', () => {
    expect(nextPollDelayMs(0)).toBe(POLL_BASE_MS)
  })

  it('doubles then caps after consecutive failures', () => {
    expect(nextPollDelayMs(1)).toBe(POLL_BASE_MS * 2)
    expect(nextPollDelayMs(2)).toBe(POLL_BASE_MS * 4)
    expect(nextPollDelayMs(3)).toBe(POLL_BACKOFF_CAP_MS)
    expect(nextPollDelayMs(8)).toBe(POLL_BACKOFF_CAP_MS)
  })
})

describe('isTransientRequestError', () => {
  it('treats axios timeouts as transient', () => {
    expect(isTimeoutError({ code: 'ECONNABORTED', message: 'timeout exceeded' })).toBe(true)
    expect(isTransientRequestError({ code: 'ECONNABORTED', message: 'timeout exceeded' })).toBe(true)
  })

  it('treats Chrome network timeouts as transient', () => {
    expect(isTransientRequestError({ message: 'Network Error' })).toBe(true)
  })

  it('does not treat HTTP 4xx/5xx as transient', () => {
    expect(isTransientRequestError({ response: { status: 500 }, message: 'Request failed' })).toBe(false)
  })
})

describe('shouldDeferPollWake', () => {
  it('defers while a request is in flight or backoff is active', () => {
    expect(shouldDeferPollWake(0, false)).toBe(false)
    expect(shouldDeferPollWake(0, true)).toBe(true)
    expect(shouldDeferPollWake(1, false)).toBe(true)
  })
})
