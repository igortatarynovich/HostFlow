import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { createPublicScanSession, getPublicScanSession, uploadPublicScanPdf, type ScanSession, type ScanPage } from '../../api/scanner'
import axios from 'axios'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { CameraPane, type CaptureMetadata, type CaptureResult, type PermissionState } from '../../components/public-scanner/CameraPane'
import { ContourEditorModal } from '../../components/public-scanner/ContourEditorModal'
import type { Contour6Points } from '../../modules/public-intake/scan/contourEditor'
import { getScannerPreset } from '../../modules/scannerPresets'
import { presetForDocType } from '../../modules/public-intake/scan/presets'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import type { ScanPresetKey } from '../../modules/public-intake/scan/analyzer'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'

type FilterName = 'standard' | 'document' | 'photo' | 'grayscale' | 'contrast_boost' | 'photo_soft'
type FrameKind = 'DRIVER_LICENSE' | 'ID_CARD' | 'CODE95' | 'PASSPORT_SPREAD' | 'PASSPORT_ID_PAGE' | 'A4'

function aspectForKind(kind?: FrameKind): number {
  switch ((kind || '').toUpperCase()) {
    case 'DRIVER_LICENSE':
    case 'ID_CARD':
    case 'CODE95':
      return 1.586
    case 'PASSPORT_SPREAD':
      return 1.408
    case 'PASSPORT_ID_PAGE':
      return 0.70
    case 'A4':
      return 0.707
    default:
      return 1.586
  }
}

const ScanState = {
  SCAN: 'scan',
  EDIT: 'edit',
  PROCESSING: 'processing',
  REVIEW: 'review',
  DONE_PAGE: 'done_page',
  DONE_DOCUMENT: 'done_document',
} as const
type ScanState = (typeof ScanState)[keyof typeof ScanState]

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

// Quality preset mapping for camera/analyzer (limited set of keys)
function qualityPresetForDocType(docType?: string | null): ScanPresetKey {
  const normalized = (docType || '').toLowerCase().trim()
  if (!normalized) return 'default'
  // Code95 and similar certificates are usually ID-card format for scanning UX
  if (normalized === 'code95' || normalized === 'qualification_code95' || normalized === 'code_95') {
    return 'driving_license'
  }
  const preset = presetForDocType(normalized)
  // presetForDocType already returns a ScanPresetKey
  return preset
}

export default function PublicScanPage() {
  const SCANNER_DISABLED = false
  const location = useLocation()
  const search = useMemo(() => new URLSearchParams(location.search), [location.search])
  const token = search.get('token') ?? ''
  const docCode = search.get('doc') ?? ''
  const preloadedSessionId = search.get('session') ?? ''
  const [session, setSession] = useState<ScanSession | null>(null)
  const [sessionId, setSessionId] = useState(preloadedSessionId)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pendingCapture, setPendingCapture] = useState<CaptureResult | null>(null)
  const [permissionState, setPermissionState] = useState<PermissionState>('pending')
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment')
  const [captureMode, setCaptureMode] = useState<'camera' | 'fallback'>('camera')
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [captureKey, setCaptureKey] = useState(0) // Force CameraPane remount on retake
  const [manualContour, setManualContour] = useState<Contour6Points | null>(null)
  const [reviewCapture, setReviewCapture] = useState<CaptureResult | null>(null)
  const [reviewContour, setReviewContour] = useState<Contour6Points | null>(null)
  const [selectedFilter, setSelectedFilter] = useState<FilterName>('standard')
  const [scanState, setScanState] = useState<ScanState>(ScanState.SCAN)
  const [processedUrl, setProcessedUrl] = useState<string | null>(null)
  const [reviewImageLabel, setReviewImageLabel] = useState<string>('')
  const [currentPageIndex, setCurrentPageIndex] = useState<number>(0)
  // Preview modal visibility (EDIT state)
  const [showPreview, setShowPreview] = useState<boolean>(false)
  const [selectedPageCode, setSelectedPageCode] = useState<string | null>(null)
  const [viewingImage, setViewingImage] = useState<{ url: string; pageCode: string; label: string } | null>(null)
  const [hasManualChanges, setHasManualChanges] = useState<boolean>(false)
  const [detectingContour, setDetectingContour] = useState<boolean>(false)
  const { notify } = useToast()
  const { t } = useI18n()
  const translate = (key: string, fallback: string, values?: Record<string, string | number>) =>
    t(key, { defaultValue: fallback, values })
  const qualityPreset = useMemo(() => qualityPresetForDocType(docCode), [docCode])
  const scannerPresetCode = useMemo(() => docCode || qualityPreset, [docCode, qualityPreset])
  const preset = useMemo(() => getScannerPreset(scannerPresetCode), [scannerPresetCode])
  // Stable presetStepCodes - use normalized presetKey to prevent unnecessary recalculations
  const presetStepCodes = useMemo(() => {
    if (!scannerPresetCode) return []
    const currentPreset = getScannerPreset(scannerPresetCode)
    if (!currentPreset?.steps) return []
    return currentPreset.steps.map((step) => step.code)
  }, [scannerPresetCode]) // Only depend on preset code, not preset object
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
  // Note: do NOT add sessionId/presetStepCodes to deps to avoid invalid hook call loops in production bundles.
  // Bootstrap only on token/doc change.
  }, [docCode, token])

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
  const READY_STATUSES: Array<ScanPage['status']> = ['ok', 'needs_review', 'uploaded', 'done']
  const isReadyPage = (page?: ScanPage) => {
    if (!page) return false
    return READY_STATUSES.includes(page.status)
  }
  const updatePageStatus = (code: string, status: ScanPage['status'], processed_url?: string | null) => {
    if (!session?.pages) return
    const updatedPages = session.pages.map((p) =>
      p.page_code === code
        ? {
            ...p,
            status,
            processed_url: processed_url !== undefined ? processed_url : p.processed_url,
          }
        : p,
    )
    setSession({ ...session, pages: updatedPages })
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

  const mapContourFromBackend = (contour?: Array<[number, number]> | null): Contour6Points | null => {
    if (!contour || contour.length < 4) return null
    // Backend returns TL, TR, BR, BL, MT, MB (6 points) when detect_only
    const tl = contour[0]
    const tr = contour[1] || contour[0]
    const br = contour[2] || contour[1] || contour[0]
    const bl = contour[3] || contour[2] || contour[0]
    const mt = contour[4] || [
      (tl[0] + tr[0]) / 2,
      (tl[1] + tr[1]) / 2,
    ]
    const mb = contour[5] || [
      (bl[0] + br[0]) / 2,
      (bl[1] + br[1]) / 2,
    ]
    return {
      p1: { x: tl[0], y: tl[1], id: 1 },
      p2: { x: tr[0], y: tr[1], id: 2 },
      p3: { x: mt[0], y: mt[1], id: 3 },
      p4: { x: br[0], y: br[1], id: 4 },
      p5: { x: mb[0], y: mb[1], id: 5 },
      p6: { x: bl[0], y: bl[1], id: 6 },
    }
  }

  const handlePendingCapture = async (capture: CaptureResult) => {
    if (pendingCapture?.previewUrl) {
      URL.revokeObjectURL(pendingCapture.previewUrl)
    }
    // Base contour = full cropped image rectangle
    const w = capture.croppedSize.width
    const h = capture.croppedSize.height
    const baseContour: Contour6Points = {
      p1: { x: 0, y: 0, id: 1 },
      p2: { x: w, y: 0, id: 2 },
      p3: { x: w, y: h, id: 3 },
      p4: { x: 0, y: h, id: 4 },
      p5: { x: w / 2, y: 0, id: 5 },
      p6: { x: w / 2, y: h, id: 6 },
    }
    setPendingCapture(capture)
    setHasManualChanges(false)
    setManualContour(baseContour)
    setDetectingContour(false)
    setShowPreview(true)
    setScanState(ScanState.EDIT)
  }

  const confirmCapture = async () => {
    if (!session || !activePageCode || !pendingCapture) return
    setScanState(ScanState.PROCESSING)
    setUploading(true)
    try {
      const form = new FormData()
      form.append('original', pendingCapture.original, 'original.jpg')
      form.append('cropped', pendingCapture.cropped, 'cropped.jpg')
      form.append('original_size', JSON.stringify(pendingCapture.originalSize))
      form.append('cropped_size', JSON.stringify(pendingCapture.croppedSize))
      if (manualContour) {
        form.append('manual_contour', JSON.stringify(manualContour))
      } else {
        // Без автодетекта обязательно отправляем прямоугольник рамки
        const w = pendingCapture.croppedSize.width
        const h = pendingCapture.croppedSize.height
        const fallbackRect = {
          p1: { x: 0, y: 0 },
          p2: { x: w, y: 0 },
          p3: { x: w, y: h },
          p4: { x: 0, y: h },
          mTop: { x: w / 2, y: 0 },
          mBottom: { x: w / 2, y: h },
        }
        form.append('manual_contour', JSON.stringify(fallbackRect))
      }
      form.append('filter', selectedFilter)
      form.append('document_kind', docCode)
      form.append('document_type_id', docCode)
      form.append('page_code', activePageCode)
      form.append('page_index', String(wizardSteps.findIndex((s) => s.code === activePageCode)))
      form.append('expected_pages', String(wizardSteps.length))

      const processed = await axios.post<{ processed_url: string; page_index?: number; width?: number; height?: number }>('/scan/process-page', form).then(res => res.data)

      URL.revokeObjectURL(pendingCapture.previewUrl)
      setReviewCapture(pendingCapture)
      setReviewContour(manualContour)
      setPendingCapture(null)
      setManualContour(null)
      // keep selectedPageCode to know which step we processed

      if (processed?.processed_url) {
        setViewingImage({
          url: processed.processed_url,
          pageCode: activePageCode,
          label: translate('public.scan.viewer.processed', 'Processed image'),
        })
        updatePageStatus(activePageCode, 'done', processed.processed_url)
      }

      setScanState(ScanState.REVIEW)
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || translate('public.scan.errors.upload_failed', 'Ошибка загрузки/обработки'),
        variant: 'error',
      })
      setScanState(ScanState.EDIT)
    } finally {
      setUploading(false)
    }
  }

  const discardCapture = () => {
    if (pendingCapture?.previewUrl) {
      URL.revokeObjectURL(pendingCapture.previewUrl)
    }
    setPendingCapture(null)
    // Reset auto-capture flag when user discards capture
    // This is handled by CameraPane component unmounting/remounting
  }

  const handleProcess = async () => {
    if (!session) return
    try {
      const pdfForm = new FormData()
      pdfForm.append('session_id', session.id)
      pdfForm.append('document_kind', docCode)
      pdfForm.append('document_type_id', docCode)
      const pdf = await axios.post<{ pdf_url: string }>('/scan/build-pdf', pdfForm).then((r) => r.data)
      if (pdf?.pdf_url) {
        const pdfBlob = await axios.get(pdf.pdf_url, { responseType: 'blob' }).then((r) => r.data as Blob)
        setViewingImage({
          url: pdf.pdf_url,
          pageCode: 'pdf',
          label: translate('public.scan.viewer.processed', 'Обработанный документ (PDF)'),
        })
        const nextSession = await uploadPublicScanPdf({
          sessionId: session.id,
          file: pdfBlob,
          meta: { source: 'public_scan', document_kind: docCode, document_type_id: docCode },
        })
        setSession(nextSession)
      }
      notify({
        title: translate('public.scan.notifications.processed', 'Processing complete'),
        variant: 'success',
      })
      setScanState(ScanState.DONE_DOCUMENT)
    } catch (err: any) {
      notify({
        title: err?.response?.data?.detail || err?.message || translate('public.scan.errors.process_failed', 'Ошибка обработки PDF'),
        variant: 'error',
      })
    }
  }

  const pendingSteps = useMemo(
    () => wizardSteps.filter((step) => !isReadyPage(step.page)),
    [wizardSteps],
  )
  const currentProcessedPreview = viewingImage

  useEffect(() => {
    return () => {
      if (pendingCapture?.previewUrl) {
        URL.revokeObjectURL(pendingCapture.previewUrl)
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

  // Автопереход после DONE_PAGE: если остались страницы — следующая, иначе строим PDF
  useEffect(() => {
    if (scanState !== ScanState.DONE_PAGE) return
    const remaining = wizardSteps.filter((step) => !isReadyPage(step.page))
    if (remaining.length > 0) {
      const nextPageCode = remaining[0].code
      setSelectedPageCode(nextPageCode)
      setCaptureKey((prev) => prev + 1)
      setViewingImage(null)
      setScanState(ScanState.SCAN)
    } else {
      handleProcess()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanState])

  const heading = preset.title || translate('public.scan.heading', 'Document scanner')

  // Calculate progress
  const progressPercent = wizardSteps.length > 0
    ? Math.round((wizardSteps.filter((step) => step.page && step.page.status !== 'pending').length / wizardSteps.length) * 100)
    : 0

  const goToNextPageOrFinish = async () => {
    const remainingSteps = wizardSteps.filter((step) => !isReadyPage(step.page))
    if (remainingSteps.length > 0) {
      const nextPageCode = remainingSteps[0].code
      setSelectedPageCode(nextPageCode)
      setCaptureKey((prev) => prev + 1)
      setViewingImage(null)
      setScanState(ScanState.SCAN)
    } else {
      await handleProcess()
    }
  }

  // Автопереход после DONE_PAGE: если остались страницы — сразу следующая, иначе строим PDF
  useEffect(() => {
    if (scanState !== ScanState.DONE_PAGE) return
    const remaining = wizardSteps.filter((step) => !isReadyPage(step.page))
    if (remaining.length > 0) {
      const nextPageCode = remaining[0].code
      setSelectedPageCode(nextPageCode)
      setCaptureKey((prev) => prev + 1)
      setViewingImage(null)
      setScanState(ScanState.SCAN)
    } else {
      handleProcess()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanState])

  if (SCANNER_DISABLED) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-md">
          <h1 className="text-xl font-semibold text-slate-900">Сканер временно недоступен</h1>
          <p className="mt-3 text-sm text-slate-600">
            Автосканер отключён. Пожалуйста, загрузите документы вручную в анкете.
          </p>
          <div className="mt-4 flex justify-center">
            <a
              href="/public"
              className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
            >
              Вернуться
            </a>
          </div>
        </div>
      </div>
    )
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
        <div className="max-w-md">
          <ErrorRecoveryBanner
            info={{
              title: translate('public.scan.errors.title', 'Something went wrong'),
              detail: error,
              hint: translate('public.scan.errors.unexpected', 'Unable to start scanner, please reopen the link.'),
            }}
            compact
          />
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
        {scanState === ScanState.SCAN && (
          <section className="w-full -mx-4 md:mx-0">
            <div className="relative">
              <CameraPane
                key={`camera-${activePageCode}-${captureKey}`}
                mode={captureMode}
                facingMode={facingMode}
                overlayRatio={aspectForKind(docCode as FrameKind)}
                autoCapture={false}
                preset={qualityPreset || 'default'}
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
                frameOverlay={{
                  aspectRatio: aspectForKind(docCode as FrameKind),
                  widthPct: 0.85,
                  stroke: 'rgba(0,194,255,0.7)',
                }}
              />
            </div>
          </section>
        )}
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

      {/* EDIT: контур + выбор фильтра */}
      {showPreview && pendingCapture && (
        <>
          {/* Небольшая панель выбора фильтра (внизу слева, чтобы не перекрывать точки) */}
          <div className="fixed bottom-4 left-4 z-[60] rounded-xl border border-slate-200 bg-white/95 p-3 shadow-lg">
            <p className="mb-2 text-xs font-semibold text-slate-700">Фильтр</p>
            <div className="flex flex-col gap-1 text-xs text-slate-700">
              {(['standard', 'document', 'photo'] as FilterName[]).map((f) => (
                <label key={f} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="filter"
                    value={f}
                    checked={selectedFilter === f}
                    onChange={() => setSelectedFilter(f)}
                  />
                  {f}
                </label>
              ))}
            </div>
          </div>

          <ContourEditorModal
            imageUrl={pendingCapture.previewUrl}
            initialContour={manualContour}
            loading={detectingContour}
            onCancel={() => {
              setShowPreview(false)
              setPendingCapture(null)
              setManualContour(null)
              setSelectedFilter('standard')
              setHasManualChanges(false)
              setCaptureKey((prev: number) => prev + 1)
              setScanState(ScanState.SCAN)
            }}
            onConfirm={async (contour) => {
              setManualContour(contour)
              setHasManualChanges(true)
              setShowPreview(false)
              await confirmCapture()
            }}
          />
        </>
      )}

      {/* REVIEW / DONE_PAGE preview block */}
      {currentProcessedPreview && scanState === ScanState.REVIEW && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-900">
                {translate('public.scan.viewer.processed', 'Обработанный результат')}
              </p>
              <div className="mt-2 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
                <img
                  src={currentProcessedPreview.url}
                  alt={currentProcessedPreview.label}
                  className="max-h-[50vh] w-full object-contain"
                />
              </div>
            </div>
            <div className="flex flex-col gap-2 sm:w-48">
              <button
                type="button"
                className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 active:scale-95"
                onClick={() => {
                  // Исправить границы: вернуться в EDIT с тем же кадром
                  if (reviewCapture) {
                    updatePageStatus(activePageCode, 'pending', null)
                    setPendingCapture(reviewCapture)
                    setManualContour(reviewContour)
                    setShowPreview(true)
                    setScanState(ScanState.EDIT)
                    setViewingImage(null)
                  } else {
                    updatePageStatus(activePageCode, 'pending', null)
                    setCaptureKey((prev) => prev + 1)
                    setScanState(ScanState.SCAN)
                  }
                }}
              >
                {translate('public.scan.actions.edit_contour', 'Исправить границы')}
              </button>
              <button
                type="button"
                className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 active:scale-95"
                onClick={() => {
                  setViewingImage(null)
                  updatePageStatus(activePageCode, 'pending', null)
                  setCaptureKey((prev) => prev + 1)
                  setScanState(ScanState.SCAN)
                }}
              >
                {translate('public.scan.actions.reshoot', 'Переснять страницу')}
              </button>
              <button
                type="button"
                className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
                onClick={async () => {
                  const remaining = wizardSteps.filter((s) => !isReadyPage(s.page))
                  if (remaining.length > 0) {
                    setScanState(ScanState.DONE_PAGE)
                  } else {
                    await handleProcess()
                  }
                }}
              >
                {translate('public.scan.actions.finish_doc', 'Подтвердить страницу')}
              </button>
            </div>
          </div>
        </div>
      )}

      {scanState === ScanState.DONE_PAGE && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                {translate('public.scan.status.done_page', 'Страница сохранена')}
              </p>
              <p className="text-xs text-slate-500">
                {pendingSteps.length > 0
                  ? translate('public.scan.status.more_pages', 'Осталось страниц: {count}', { count: pendingSteps.length })
                  : translate('public.scan.status.all_pages', 'Все страницы добавлены')}
              </p>
            </div>
            <div className="flex gap-2">
              {pendingSteps.length > 0 && (
                <button
                  type="button"
                  className="min-h-[44px] rounded-full border border-brand-200 bg-white px-4 py-2 text-sm font-semibold text-brand-700 active:scale-95"
                  onClick={() => {
                    const nextPageCode = pendingSteps[0].code
                    setSelectedPageCode(nextPageCode)
                    setCaptureKey((prev) => prev + 1)
                    setScanState(ScanState.SCAN)
                  }}
                >
                  {translate('public.scan.actions.add_page', 'Добавить страницу')}
                </button>
              )}
              <button
                type="button"
                className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
                onClick={handleProcess}
              >
                {translate('public.scan.actions.finish_doc', 'Завершить документ')}
              </button>
            </div>
          </div>
        </div>
      )}

      {scanState === ScanState.DONE_DOCUMENT && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-emerald-900">
                {translate('public.scan.status.done_document', 'Документ готов')}
              </p>
              {viewingImage?.url && (
                <a
                  href={viewingImage.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-brand-700 underline"
                >
                  {translate('public.scan.actions.open_pdf', 'Открыть PDF')}
                </a>
              )}
            </div>
            <div className="flex gap-2">
              {viewingImage?.url && (
                <a
                  href={viewingImage.url}
                  download
                  className="min-h-[44px] rounded-full border border-emerald-200 bg-white px-4 py-2 text-sm font-semibold text-emerald-700 active:scale-95"
                >
                  {translate('public.scan.viewer.download', 'Скачать PDF')}
                </a>
              )}
              <button
                type="button"
                className="min-h-[44px] rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white active:scale-95"
                onClick={() => {
                  // Здесь должен быть возврат в CRM, пока просто закрываем превью
                  setViewingImage(null)
                }}
              >
                {translate('public.scan.actions.done', 'Готово / Вернуться')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
