import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getSearchAcquisition,
  syncSearchAcquisition,
  type AcquisitionSnapshot,
} from '../api/searchAcquisition'

const SYNC_INTERVAL_MS = 15 * 60 * 1000

function isSyncStale(snapshot: AcquisitionSnapshot | null): boolean {
  const last = snapshot?.sync?.last_sync_ok_at || snapshot?.synced_at
  if (!last) return true
  const ts = new Date(last).getTime()
  if (Number.isNaN(ts)) return true
  return Date.now() - ts > SYNC_INTERVAL_MS
}

export function useAcquisitionData(searchId: string) {
  const [snapshot, setSnapshot] = useState<AcquisitionSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const syncingRef = useRef(false)
  const snapshotRef = useRef<AcquisitionSnapshot | null>(null)

  useEffect(() => {
    snapshotRef.current = snapshot
  }, [snapshot])

  const runSync = useCallback(async () => {
    if (!searchId || syncingRef.current) return
    syncingRef.current = true
    setSyncing(true)
    try {
      const data = await syncSearchAcquisition(searchId)
      setSnapshot(data)
    } catch {
      try {
        const fallback = await getSearchAcquisition(searchId)
        setSnapshot(fallback)
      } catch {
        /* keep previous */
      }
    } finally {
      syncingRef.current = false
      setSyncing(false)
    }
  }, [searchId])

  const refresh = useCallback(async () => {
    if (!searchId) return
    setLoading(true)
    try {
      const data = await getSearchAcquisition(searchId)
      setSnapshot(data)
      if (isSyncStale(data)) {
        await runSync()
      }
    } catch {
      setSnapshot(null)
    } finally {
      setLoading(false)
    }
  }, [runSync, searchId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (isSyncStale(snapshotRef.current)) void runSync()
    }, SYNC_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [runSync])

  return { snapshot, loading, syncing, refresh, runSync }
}
