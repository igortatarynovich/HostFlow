import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  createPublicScanSession,
  getPublicScanSession,
  processPublicScanSession,
  uploadPublicScanPage,
  type ScanSession,
  type ScanPage,
} from '../../api/scanner'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { CameraPane, type CaptureMetadata, type PermissionState } from '../../components/public-scanner/CameraPane'
import { ContourEditorModal } from '../../components/public-scanner/ContourEditorModal'
import { PreviewModal } from '../../components/public-scanner/PreviewModal'
import type { Contour6Points } from '../../modules/public-intake/scan/contourEditor'
import { getScannerPreset } from '../../modules/scannerPresets'
import { presetForDocType } from '../../modules/public-intake/scan/presets'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'

function statusBadgeTone(status: string): string {
  switch (status) {
    case 'ok':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'needs_review':
      return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'rejected':
    case 'error':
      return 'bg-rose-100 text-rose-700 border-rose-200'
    case 'uploaded':
    case 'processing':
      return 'bg-blue-100 text-blue-700 border-blue-200'
    default:
      return 'bg-slate-100 text-slate-600 border-slate-200'
  }
}

export default function PublicScanPage() {
  const location = useLocation()
  const search = useMemo(() => new URLSearchParams(location.search), [location.search])
  const token = search.get('token') ?? ''
  const docCode = search.get('doc') ?? ''
  const preloadedSessionId = search.get('session') ?? ''
  const [session, setSession] = useState<ScanSession | null>(null)
  const [sessionId, setSessionId] = useState(preloadedSessionId)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pendingCapture, setPendingCapture] = useState<{
    blob: Blob
    url: string
    metadata: CaptureMetadata
  } | null>(null)
  const [permissionState, setPermissionState] = useState<PermissionState>('pending')
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment')
  const [captureMode, setCaptureMode] = useState<'camera' | 'fallback'>('camera')
  const [selectedPageCode, setSelectedPageCode] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [captureKey, setCaptureKey] = useState(0) // Force CameraPane remount on retake
  const [viewingImage, setViewingImage] = useState<{ url: string; pageCode: string; label: string } | null>(null)
  const [showContourEditor, setShowContourEditor] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [manualContour, setManualContour] = useState<any>(null)
  const [selectedFilter, setSelectedFilter] = useState<'standard' | 'strong' | 'photo'>('standard')
  const { notify } = useToast()
  const { t } = useI18n()
  const translate = (key: string, fallback: string, values?: Record<string, string | number>) =>
    t(key, { defaultValue: fallback, values })
  const preset = useMemo(() => getScannerPreset(docCode), [docCode])
  // Stable presetStepCodes - use docCode instead of preset object to prevent unnecessary recalculations
  const presetStepCodes = useMemo(() => {
    if (!docCode) return []
    const currentPreset = getScannerPreset(docCode)
    if (!currentPreset?.steps) return []
    return currentPreset.steps.map((step) => step.code)
  }, [docCode]) // Only depend on docCode, not preset object
  const formatStepStatus = (statusKey?: string | null) => {
    const key = statusKey ?? 'pending'
    return {
      key,
      text: translate(`public.scan.status.${key}`, key),
      tone: statusBadgeTone(key),
    }
  }

  // Use ref to track if we've already bootstrapped to prevent infinite loops
  const bootstrappedRef = useRef(false)
  const bootstrapSessionIdRef = useRef<string | null>(null)
  
  useEffect(() => {
    if (!token) {
      setError(translate('public.scan.errors.missing_token', 'Link is missing required token'))
      setLoading(false)
      return
    }
    
    // Prevent re-bootstrap if we already have a session and it matches
    // Also check if we're in preview/uploading state - don't bootstrap during user interaction
    if (bootstrappedRef.current && sessionId && bootstrapSessionIdRef.current === sessionId) {
      if (showPreview || uploading || processing || pendingCapture) {
        return  // Don't bootstrap if user is actively working
      }
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
          // Calculate presetStepCodes inline to avoid dependency issues
          const currentPreset = getScannerPreset(docCode)
          const expectedPages = currentPreset?.steps && currentPreset.steps.length > 0 
            ? currentPreset.steps.map((step) => step.code) 
            : undefined
          nextSession = await createPublicScanSession({
            token,
            document_type: docCode,
            preset_code: docCode,
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
  }, [docCode, token]) // Removed sessionId and presetStepCodes - use ref to track and calculate inline to prevent infinite loops

  // Poll session status while in progress to update thumbnails/statuses.
  // CRITICAL: Completely disable polling during user interaction to prevent page refreshes
  useEffect(() => {
    if (!session?.id) return
    if (session.status === 'done' || session.status === 'failed') return
    
    // COMPLETELY DISABLE polling if user is actively working
    // This prevents any page refreshes during user interaction
    if (showPreview || uploading || processing || pendingCapture) {
      return  // Don't set up polling at all
    }
    
    // Only poll when user is NOT actively working (waiting for next action)
    // Use longer interval to reduce load
    const interval = window.setInterval(async () => {
      // Double-check state hasn't changed (user might have started working)
      if (showPreview || uploading || processing || pendingCapture) {
        return
      }
      try {
        const refreshed = await getPublicScanSession(session.id)
        // Only update if session actually changed significantly (prevent unnecessary re-renders)
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
    }, 15000) // Increased to 15 seconds to reduce load even more
    return () => window.clearInterval(interval)
  }, [session?.id, session?.status, showPreview, uploading, processing, pendingCapture])

  const stepMeta = useMemo(() => {
    const map = new Map<string, { optional: boolean; label: string }>()
    preset.steps.forEach((step) => {
      map.set(step.code, { optional: Boolean(step.optional), label: step.label })
    })
    return map
  }, [preset])
  const orderedStepCodes = session?.expected_pages?.length ? session.expected_pages : presetStepCodes
  const wizardSteps = orderedStepCodes.map((code, index) => {
    const page = session?.pages?.find((p) => p.page_code === code)
    const meta = stepMeta.get(code)
    return {
      code,
      index,
      optional: meta?.optional ?? false,
      label: translate(`public.scan.pages.${code}`, meta?.label ?? code),
      page,
    }
  })
  const isReadyPage = (page?: ScanPage) => {
    if (!page) return false
    return page.status === 'ok' || page.status === 'needs_review'
  }
  const hasSteps = wizardSteps.length > 0
  const firstBlockingStep = wizardSteps.find((step) => !isReadyPage(step.page) && !step.optional)
  const firstPendingStep = wizardSteps.find((step) => !isReadyPage(step.page))
  const activePageCode = selectedPageCode || firstBlockingStep?.code || firstPendingStep?.code || wizardSteps[0]?.code || null
  const activeStep = wizardSteps.find((step) => step.code === activePageCode)
  const requiredSteps = wizardSteps.filter((step) => !step.optional)
  const canProcess =
    hasSteps &&
    (requiredSteps.length > 0
      ? requiredSteps.every((step) => isReadyPage(step.page))
      : wizardSteps.every((step) => isReadyPage(step.page)))
  const allPagesComplete =
    hasSteps && wizardSteps.every((step) => isReadyPage(step.page) || step.optional)

  const handlePendingCapture = (blob: Blob, metadata: CaptureMetadata) => {
    if (pendingCapture?.url) {
      URL.revokeObjectURL(pendingCapture.url)
    }
    const url = URL.createObjectURL(blob)
    setPendingCapture({ blob, url, metadata })
    // Show preview modal after capture (user can edit contour and choose filter)
    setShowPreview(true)
  }

  const confirmCapture = async () => {
    if (!session || !activePageCode || !pendingCapture) return
    setUploading(true)
    try {
      const next = await uploadPublicScanPage({
        sessionId: session.id,
        page_code: activePageCode,
        file: pendingCapture.blob,
        rotation: 0,
        filter: 'original',
        meta: {
          source: 'public_scan',
          capture_mode: pendingCapture.metadata.captureMode,
          facing_mode: pendingCapture.metadata.facingMode,
          width: pendingCapture.metadata.width,
          height: pendingCapture.metadata.height,
          manual_contour: manualContour ? {
            p1: manualContour.p1,
            p2: manualContour.p2,
            p3: manualContour.p3,
            p4: manualContour.p4,
            p5: manualContour.p5,
            p6: manualContour.p6,
          } : null,
        },
      })
      setSession(next)
      URL.revokeObjectURL(pendingCapture.url)
      setPendingCapture(null)
      setManualContour(null)
      setSelectedPageCode(null)
      
      // Check if there are more pages to scan
      const updatedWizardSteps = (next.expected_pages || []).map((code) => {
        const page = next.pages?.find((p) => p.page_code === code)
        return { code, page }
      })
      const remainingSteps = updatedWizardSteps.filter((step) => !isReadyPage(step.page))
      
      if (remainingSteps.length > 0) {
        // Ask if user wants to scan next page
        const nextPageCode = remainingSteps[0].code
        const nextStep = stepMeta.get(nextPageCode)
        const shouldContinue = window.confirm(
          translate(
            'public.scan.next_page',
            `Хотите снять следующую страницу? ${nextStep?.label || nextPageCode}`,
            { page: nextStep?.label || nextPageCode }
          )
        )
        if (shouldContinue) {
          setSelectedPageCode(nextPageCode)
          setCaptureKey((prev: number) => prev + 1)
        }
        notify({
          title: translate('public.scan.notifications.page_uploaded', 'Страница загружена'),
          variant: 'success',
        })
      } else {
        // All pages scanned, auto-process
        notify({
          title: translate('public.scan.notifications.all_pages_uploaded', 'Все страницы загружены'),
          variant: 'success',
        })
        // Auto-process after a short delay
        setTimeout(async () => {
          try {
            setProcessing(true)
            const processed = await processPublicScanSession(next.id)
            setSession(processed)
            const refreshed = await getPublicScanSession(processed.id)
            setSession(refreshed)
            notify({
              title: translate('public.scan.notifications.processed', 'Обработка завершена'),
              variant: 'success',
            })
          } catch (processErr: any) {
            notify({
              title: processErr?.response?.data?.detail || processErr?.message || translate('public.scan.errors.process_failed', 'Ошибка обработки'),
              variant: 'error',
            })
          } finally {
            setProcessing(false)
          }
        }, 1000)
      }
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || translate('public.scan.errors.upload_failed', 'Ошибка загрузки'),
        variant: 'error',
      })
    } finally {
      setUploading(false)
    }
  }

  const discardCapture = () => {
    if (pendingCapture?.url) {
      URL.revokeObjectURL(pendingCapture.url)
    }
    setPendingCapture(null)
    // Reset auto-capture flag when user discards capture
    // This is handled by CameraPane component unmounting/remounting
  }

  const handleProcess = async () => {
    if (!session) return
    setProcessing(true)
    try {
      const next = await processPublicScanSession(session.id)
      setSession(next)
      notify({
        title: translate('public.scan.notifications.processed', 'Processing complete'),
        variant: 'success',
      })
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || translate('public.scan.errors.process_failed', 'Processing failed, please retry'),
        variant: 'error',
      })
    } finally {
      setProcessing(false)
    }
  }

  useEffect(() => {
    return () => {
      if (pendingCapture?.url) {
        URL.revokeObjectURL(pendingCapture.url)
      }
    }
  }, [pendingCapture])

  const progressLabel = () => {
    if (!activePageCode || wizardSteps.length === 0) return ''
    const index = wizardSteps.findIndex((step) => step.code === activePageCode)
    if (index === -1) return ''
    return translate('public.scan.steps.pages_progress', 'Step {current} of {total}', {
      current: index + 1,
      total: wizardSteps.length,
    })
  }

  const stepHints = () => {
    if (!activePageCode) return []
    const defaultHints = [
      translate('public.scan.hints.steady', 'Hold the phone steady for 2 seconds.'),
      translate('public.scan.hints.frame', 'Keep the entire document inside the frame.'),
    ]
    const hintsByCode: Record<string, string[]> = {
      front: [
        translate('public.scan.hints.front_light', 'Avoid glare on the front side.'),
        translate('public.scan.hints.front_text', 'Ensure text is readable.'),
      ],
      back: [
        translate('public.scan.hints.back_stamp', 'Capture stamps and QR codes entirely.'),
      ],
      spread: [
        translate('public.scan.hints.spread', 'Lay the passport flat and capture both pages.'),
      ],
    }
    return hintsByCode[activePageCode] ?? defaultHints
  }



  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-gradient-to-br from-brand-50 via-white to-slate-100 px-4 py-12 text-slate-600">
        {translate('public.scan.loading', 'Connecting to scanner...')}
      </div>
    )
  }

  if (error) {
    return (
      <div className="grid min-h-screen place-items-center bg-gradient-to-br from-brand-50 via-white to-slate-100 px-4 py-12">
        <div className="max-w-md rounded-xl border border-rose-200 bg-rose-50 px-6 py-4 text-center text-rose-700 shadow-sm">
          <p className="font-medium">{translate('public.scan.errors.title', 'Something went wrong')}</p>
          <p className="mt-2 text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!session || !activePageCode) {
    return (
      <div className="grid min-h-screen place-items-center bg-gradient-to-br from-brand-50 via-white to-slate-100 px-4 py-12 text-slate-600">
        {translate('public.scan.errors.unexpected', 'Unable to start scanner, please reopen the link.')}
      </div>
    )
  }

  const heading = preset.title || translate('public.scan.heading', 'Document scanner')

  // Calculate progress
  const progressPercent = wizardSteps.length > 0
    ? Math.round((wizardSteps.filter((step) => step.page && step.page.status !== 'pending').length / wizardSteps.length) * 100)
    : 0

  return (
    <>
      <PublicPageShell maxWidth="5xl" headerExtra={<PublicLocaleSwitcher />}>
        {/* Minimal header - only on desktop */}
        <div className="mb-4 hidden md:block">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-bold text-slate-900">{heading}</h1>
            <span className="text-sm font-medium text-slate-600">{progressPercent}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        <div className="rounded-3xl border border-brand-100 bg-white/95 px-4 py-4 md:px-6 md:py-8 shadow-card">
        {/* Step indicators - minimal, only on desktop */}
        <section className="mb-4 hidden md:block">
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {wizardSteps.map((step, idx) => {
              const status = formatStepStatus(step.page?.status)
              const isActive = activePageCode === step.code
              const isComplete = step.page && step.page.status !== 'pending'
              
              return (
                <div key={step.code} className="flex items-center gap-2 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => setSelectedPageCode(step.code)}
                    className={`relative flex items-center gap-3 rounded-xl border-2 px-4 py-3 transition-all ${
                      isActive
                        ? 'border-brand-500 bg-brand-50 shadow-md scale-105'
                        : isComplete
                        ? 'border-emerald-300 bg-emerald-50'
                        : 'border-slate-200 bg-white'
                    } ${isActive ? 'ring-2 ring-brand-200' : ''}`}
                  >
                    {/* Step number */}
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                        isComplete
                          ? 'bg-emerald-500 text-white'
                          : isActive
                          ? 'bg-brand-500 text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {isComplete ? '✓' : idx + 1}
                    </div>
                    <div className="text-left">
                      <p className={`text-sm font-semibold ${
                        isActive ? 'text-brand-900' : isComplete ? 'text-emerald-900' : 'text-slate-700'
                      }`}>
                        {step.label}
                      </p>
                      <p className={`text-xs ${
                        isActive ? 'text-brand-600' : isComplete ? 'text-emerald-600' : 'text-slate-500'
                      }`}>
                        {status.text}
                      </p>
                    </div>
                  </button>
                  {/* Connector line */}
                  {idx < wizardSteps.length - 1 && (
                    <div className={`h-0.5 w-8 ${
                      isComplete ? 'bg-emerald-300' : 'bg-slate-200'
                    }`} />
                  )}
                </div>
              )
            })}
          </div>
        </section>

        {/* Capture section - full screen on mobile, like iPhone camera */}
        <section className="w-full -mx-4 md:mx-0">
          <div className="relative">
            <CameraPane
              key={`camera-${activePageCode}-${captureKey}`}
              mode={captureMode}
              facingMode={facingMode}
              overlayRatio={preset.aspectRatio}
              autoCapture={true}
              preset={presetForDocType(docCode) || 'default'}
              onCapture={handlePendingCapture}
              onError={(message) =>
                notify({
                  title: message,
                  variant: 'error',
                })
              }
              onPermissionChange={(state: PermissionState) => {
                setPermissionState(state)
                if ((state === 'denied' || state === 'unsupported') && captureMode !== 'fallback') {
                  setCaptureMode('fallback')
                }
                if (state === 'denied') {
                  notify({
                    title: translate('public.scan.capture.permission', 'Camera blocked. Upload a photo instead.'),
                    variant: 'info',
                  })
                }
              }}
            />
          </div>
        </section>
        </div>
      </PublicPageShell>

      {/* Full-size image viewer modal - mobile optimized */}
      {viewingImage && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-black"
          onClick={() => setViewingImage(null)}
        >
          {/* Mobile header */}
          <div className="flex items-center justify-between border-b border-white/10 bg-black/80 px-4 py-3 sm:hidden">
            <h3 className="text-base font-semibold text-white">{viewingImage.label}</h3>
            <button
              type="button"
              onClick={() => setViewingImage(null)}
              className="rounded-full bg-white/20 p-2 text-white active:bg-white/30"
              aria-label={translate('public.scan.viewer.close', 'Close')}
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Image container - full screen on mobile */}
          <div
            className="flex flex-1 items-center justify-center overflow-auto p-2 sm:p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="relative w-full max-w-full">
              {/* Desktop close button */}
              <button
                type="button"
                onClick={() => setViewingImage(null)}
                className="absolute -right-2 -top-2 z-10 hidden rounded-full bg-white p-2 shadow-lg transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-white sm:block"
                aria-label={translate('public.scan.viewer.close', 'Close')}
              >
                <svg
                  className="h-6 w-6 text-slate-900"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>

              {/* Image wrapper */}
              <div className="rounded-lg bg-white p-2 shadow-2xl sm:p-4">
                {/* Desktop header */}
                <div className="mb-3 hidden text-center sm:block">
                  <h3 className="text-lg font-semibold text-slate-900">{viewingImage.label}</h3>
                  <p className="text-xs text-slate-500">
                    {translate('public.scan.viewer.processed', 'Processed image')}
                  </p>
                </div>
                
                {/* Image */}
                <div className="max-h-[calc(100vh-200px)] max-w-[95vw] overflow-auto rounded-lg border border-slate-200 sm:max-h-[80vh] sm:max-w-[90vw]">
                  <img
                    src={viewingImage.url}
                    alt={viewingImage.label}
                    className="h-auto w-full object-contain"
                    onError={(e) => {
                      // Fallback to original if processed fails
                      const step = wizardSteps.find((s) => s.code === viewingImage.pageCode)
                      if (step?.page?.original_url && e.currentTarget.src !== step.page.original_url) {
                        e.currentTarget.src = step.page.original_url
                      }
                    }}
                  />
                </div>

                {/* Action buttons */}
                <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:justify-center">
                  <a
                    href={viewingImage.url}
                    download
                    className="min-h-[44px] flex items-center justify-center gap-2 rounded-full border border-brand-200 bg-white px-4 py-2.5 text-sm font-medium text-brand-700 active:scale-95 active:bg-brand-50 sm:min-h-[auto] sm:py-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    {translate('public.scan.viewer.download', 'Download')}
                  </a>
                  <button
                    type="button"
                    onClick={() => setViewingImage(null)}
                    className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white active:scale-95 active:bg-brand-700 sm:min-h-[auto] sm:py-2"
                  >
                    {translate('public.scan.viewer.close', 'Close')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview modal with filter selection and re-edit option */}
      {showPreview && pendingCapture && (
        <PreviewModal
          imageUrl={pendingCapture.url}
          initialContour={manualContour}
          uploading={uploading}
          onRetake={() => {
            console.log('[scanner] PreviewModal: Retake button clicked')
            setShowPreview(false)
            setPendingCapture(null)
            setManualContour(null)
            setSelectedFilter('standard')
            setCaptureKey((prev: number) => prev + 1)
          }}
          onConfirm={async (filter, contour) => {
            console.log('[scanner] PreviewModal onConfirm called:', { filter, contour: contour ? 'present' : 'null' })
            setSelectedFilter(filter)
            setManualContour(contour)
            setShowPreview(false)
            
            // Upload with selected filter and contour
            if (session && activePageCode) {
              setUploading(true)
              try {
                const filterMap: Record<string, string> = {
                  standard: 'standard',
                  strong: 'strong',
                  photo: 'photo',
                }
                
                const metaPayload = {
                  source: 'public_scan',
                  capture_mode: pendingCapture.metadata.captureMode,
                  facing_mode: pendingCapture.metadata.facingMode,
                  width: pendingCapture.metadata.width,
                  height: pendingCapture.metadata.height,
                  enhancement_mode: filter,
                  manual_contour: contour ? {
                    p1: contour.p1,
                    p2: contour.p2,
                    p3: contour.p3,
                    p4: contour.p4,
                    p5: contour.p5,
                    p6: contour.p6,
                  } : null,
                }
                
                console.log('[scanner] Uploading with meta:', JSON.stringify(metaPayload, null, 2))
                
                const next = await uploadPublicScanPage({
                  sessionId: session.id,
                  page_code: activePageCode,
                  file: pendingCapture.blob,
                  rotation: 0,
                  filter: filterMap[filter] || 'original',
                  meta: metaPayload,
                })
                setSession(next)
                URL.revokeObjectURL(pendingCapture.url)
                setPendingCapture(null)
                setManualContour(null)
                setSelectedPageCode(null)
                
                // Check if there are more pages to scan
                const updatedWizardSteps = (next.expected_pages || []).map((code) => {
                  const page = next.pages?.find((p) => p.page_code === code)
                  return { code, page }
                })
                const remainingSteps = updatedWizardSteps.filter((step) => !isReadyPage(step.page))
                
                if (remainingSteps.length > 0) {
                  // Ask if user wants to scan next page
                  const nextPageCode = remainingSteps[0].code
                  const nextStep = stepMeta.get(nextPageCode)
                  const shouldContinue = window.confirm(
                    translate(
                      'public.scan.next_page',
                      `Хотите снять следующую страницу? ${nextStep?.label || nextPageCode}`,
                      { page: nextStep?.label || nextPageCode }
                    )
                  )
                  if (shouldContinue) {
                    setSelectedPageCode(nextPageCode)
                    setCaptureKey((prev: number) => prev + 1)
                    setShowPreview(false)  // Close preview when moving to next page
                  }
                } else {
                  // All pages scanned, auto-process
                  notify({
                    title: translate('public.scan.notifications.all_pages_uploaded', 'Все страницы загружены'),
                    variant: 'success',
                  })
                  // Auto-process after a short delay
                  setTimeout(async () => {
                    try {
                      setProcessing(true)
                      const processed = await processPublicScanSession(next.id)
                      setSession(processed)
                      const refreshed = await getPublicScanSession(processed.id)
                      setSession(refreshed)
                      notify({
                        title: translate('public.scan.notifications.processed', 'Обработка завершена'),
                        variant: 'success',
                      })
                    } catch (processErr: any) {
                      notify({
                        title: processErr?.response?.data?.detail || processErr?.message || translate('public.scan.errors.process_failed', 'Ошибка обработки'),
                        variant: 'error',
                      })
                    } finally {
                      setProcessing(false)
                    }
                  }, 1000)
                }
              } catch (err: any) {
                notify({
                  title: err?.response?.data?.detail || err?.message || translate('public.scan.errors.upload_failed', 'Ошибка загрузки'),
                  variant: 'error',
                })
              } finally {
                setUploading(false)
              }
            }
          }}
        />
      )}
    </>
  )
}
