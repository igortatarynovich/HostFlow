import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { createPublicScanSession, getPublicScanSession, type ScanSession } from '@api/scanner'
import { getScannerPreset } from '@modules/scannerPresets'
import type { TranslateFn } from '@i18n'

export function useScanSession(
  token: string,
  docCode: string,
  scannerPresetCode: string,
  translate: TranslateFn
) {
  const location = useLocation()
  const search = new URLSearchParams(location.search)
  const preloadedSessionId = search.get('session') ?? ''

  const [session, setSession] = useState<ScanSession | null>(null)
  const [sessionId, setSessionId] = useState(preloadedSessionId)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const bootstrappedRef = useRef(false)
  const bootstrapSessionIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError(translate('public.scan.errors.missing_token', 'Link is missing required token'))
      setLoading(false)
      return
    }

    // Prevent re-bootstrap if we already have a session and it matches
    if (bootstrappedRef.current && sessionId && bootstrapSessionIdRef.current === sessionId) {
      return
    }

    let cancelled = false
    async function bootstrap() {
      setLoading(true)
      try {
        let nextSession: ScanSession
        if (sessionId) {
          nextSession = await getPublicScanSession(sessionId)
          bootstrapSessionIdRef.current = sessionId
        } else {
          if (!docCode) throw new Error(translate('public.scan.errors.missing_doc', 'Document type is required'))
          const currentPreset = getScannerPreset(scannerPresetCode)
          const expectedPages = currentPreset?.steps ? currentPreset.steps.length : undefined
          nextSession = await createPublicScanSession({
            token,
            document_type: docCode,
            preset_code: currentPreset.code,
            expected_pages: expectedPages,
          })
          const params = new URLSearchParams(location.search)
          params.set('session', nextSession.id)
          window.history.replaceState({}, '', `${location.pathname}?${params.toString()}`)
          setSessionId(nextSession.id)
          bootstrapSessionIdRef.current = nextSession.id
        }
        if (!cancelled) {
          setSession(nextSession)
          setError(null)
          bootstrappedRef.current = true
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err?.message || translate('public.scan.errors.start_failed', 'Failed to start scanner'))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
  }, [docCode, token, scannerPresetCode, sessionId, location.search, location.pathname, translate])

  // Poll session status while in progress
  useEffect(() => {
    if (!session?.id) return
    if (session.status === 'done' || session.status === 'failed') return

    const interval = window.setInterval(async () => {
      try {
        const refreshed = await getPublicScanSession(session.id)
        const statusChanged = refreshed.status !== session.status
        const pagesChanged = refreshed.pages?.length !== session.pages?.length
        const pageStatusChanged = refreshed.pages?.some((p, idx) => 
          session.pages?.[idx]?.status !== p.status
        )
        
        if (statusChanged || pagesChanged || pageStatusChanged) {
          setSession(refreshed)
        }
      } catch (err) {
        console.error('Failed to refresh scan session', err)
      }
    }, 15000) // 15 seconds
    return () => window.clearInterval(interval)
  }, [session?.id, session?.status])

  return {
    session,
    setSession,
    sessionId,
    loading,
    error,
  }
}

