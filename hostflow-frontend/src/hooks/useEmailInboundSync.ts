import { useCallback, useEffect, useRef, useState } from 'react'
import { runCommunicationEmailPollWorker } from '../api/communications'
import { useCommunicationsSetupStatus } from './useCommunicationsSetupStatus'

const LS_POLL_KEY = 'hf:email-workspace:last-poll-at'

function dt(value?: string | null): number {
  if (!value) return 0
  const t = Date.parse(value)
  return Number.isNaN(t) ? 0 : t
}

function nowIso(): string {
  return new Date().toISOString()
}

function shouldAutoPoll(lastPollAt: string | null, minMinutes: number): boolean {
  if (!lastPollAt) return true
  const last = dt(lastPollAt)
  if (!last) return true
  return Date.now() - last > minMinutes * 60_000
}

export function useEmailInboundSync(opts: {
  enabled: boolean
  /** Hub list loading — skip auto poll until initial load done */
  listLoading: boolean
  busy: boolean
  onAfterPoll: () => void | Promise<void>
}) {
  const onAfterPollRef = useRef(opts.onAfterPoll)
  onAfterPollRef.current = opts.onAfterPoll
  const commSetup = useCommunicationsSetupStatus()
  const [pollBusy, setPollBusy] = useState(false)
  const [pollErrors, setPollErrors] = useState<string[]>([])
  const [lastPollAt, setLastPollAt] = useState<string | null>(() => {
    try {
      const raw = window.localStorage.getItem(LS_POLL_KEY)
      return raw ? String(raw) : null
    } catch {
      return null
    }
  })
  const pollInFlightRef = useRef(false)
  const pollCooldownUntilRef = useRef(0)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    try {
      if (lastPollAt) window.localStorage.setItem(LS_POLL_KEY, lastPollAt)
    } catch {
      /* ignore */
    }
  }, [lastPollAt])

  const fetchInboundNow = useCallback(async (silent?: boolean) => {
    if (pollInFlightRef.current) return
    pollInFlightRef.current = true
    setPollBusy(true)
    try {
      await runCommunicationEmailPollWorker({ limit_per_account: 50 })
      if (!mountedRef.current) return
      setLastPollAt(nowIso())
      setPollErrors([])
      pollCooldownUntilRef.current = 0
      await onAfterPollRef.current()
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      if (mountedRef.current) {
        setPollErrors((prev) => [...prev.slice(-4), message])
      }
      if (silent) pollCooldownUntilRef.current = Date.now() + 120_000
    } finally {
      setPollBusy(false)
      pollInFlightRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!opts.enabled) return
    if (opts.listLoading || opts.busy) return
    if (pollBusy) return
    if (commSetup.loading || !commSetup.isComplete) return
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
    if (Date.now() < pollCooldownUntilRef.current) return
    if (!shouldAutoPoll(lastPollAt, 2)) return
    void fetchInboundNow(true)
  }, [commSetup.isComplete, commSetup.loading, fetchInboundNow, lastPollAt, opts.busy, opts.enabled, opts.listLoading, pollBusy])

  useEffect(() => {
    if (!opts.enabled) return
    const timer = window.setInterval(() => {
      if (pollBusy || opts.busy) return
      if (commSetup.loading || !commSetup.isComplete) return
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      if (Date.now() < pollCooldownUntilRef.current) return
      if (!shouldAutoPoll(lastPollAt, 5)) return
      void fetchInboundNow(true)
    }, 60_000)
    return () => window.clearInterval(timer)
  }, [commSetup.isComplete, commSetup.loading, fetchInboundNow, lastPollAt, opts.busy, opts.enabled, pollBusy])

  return { pollBusy, lastPollAt, pollErrors, fetchInboundNow: () => void fetchInboundNow(false) }
}
