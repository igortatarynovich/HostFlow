/** Base interval for shell badge pollers (handoffs, topbar reminders). */
export const POLL_BASE_MS = 60_000
export const POLL_BACKOFF_CAP_MS = 5 * 60_000

/**
 * Delay until the next poll. Success (consecutiveFailures = 0) stays at 60s.
 * Timeouts / network errors back off 2x / 4x / 8x, capped at 5 minutes.
 */
export function nextPollDelayMs(consecutiveFailures: number): number {
  if (consecutiveFailures <= 0) return POLL_BASE_MS
  const exp = Math.min(consecutiveFailures, 3)
  return Math.min(POLL_BASE_MS * 2 ** exp, POLL_BACKOFF_CAP_MS)
}

/** Tab-focus / unread-sync must not start a new request while one is in flight or backoff is active. */
export function shouldDeferPollWake(consecutiveFailures: number, inFlight: boolean): boolean {
  return inFlight || consecutiveFailures > 0
}
