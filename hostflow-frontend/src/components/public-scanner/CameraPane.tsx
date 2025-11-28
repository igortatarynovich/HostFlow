import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeImageData, type ScanPresetKey, type ScanQualityReport } from '../../modules/public-intake/scan/analyzer'
import { detectDocument, type DocumentQuad } from '../../modules/public-intake/scan/documentDetector'
import { ScanningOverlay } from './ScanningOverlay'

type CameraPaneProps = {
  mode: 'camera' | 'fallback'
  facingMode?: 'user' | 'environment'
  overlayRatio?: number
  onCapture: (blob: Blob, metadata: CaptureMetadata) => void
  onError?: (message: string) => void
  onPermissionChange?: (state: PermissionState) => void
  fallbackAccept?: string
  autoCapture?: boolean
  preset?: ScanPresetKey
  onQualityChange?: (report: ScanQualityReport | null) => void
}

export type PermissionState = 'pending' | 'granted' | 'denied' | 'unsupported'

export type CaptureMetadata = {
  width: number
  height: number
  facingMode: 'user' | 'environment'
  captureMode: 'camera' | 'upload'
  timestamp: number
}

export function CameraPane({
  mode,
  facingMode = 'environment',
  overlayRatio = 1.6,
  onCapture,
  onError,
  onPermissionChange,
  fallbackAccept = 'image/*',
  autoCapture = false,
  preset = 'default',
  onQualityChange,
}: CameraPaneProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const frameCallbackRef = useRef<number | null>(null)
  const qualityHistoryRef = useRef<boolean[]>([])
  const retryCountRef = useRef<number>(0)
  const autoCapturedRef = useRef<boolean>(false) // Prevent multiple auto-captures
  const [permission, setPermission] = useState<PermissionState>('pending')
  const [isCapturing, setCapturing] = useState(false)
  const [torchSupported, setTorchSupported] = useState(false)
  const [torchEnabled, setTorchEnabled] = useState(false)
  const [qualityReport, setQualityReport] = useState<ScanQualityReport | null>(null)
  const [stabilityCount, setStabilityCount] = useState(0)
  const [documentQuad, setDocumentQuad] = useState<DocumentQuad | null>(null)
  const lastDocumentQuadRef = useRef<DocumentQuad | null>(null)
  const quadHistoryRef = useRef<Array<{ quad: DocumentQuad; timestamp: number }>>([])
  type TorchCapabilities = MediaTrackCapabilities & { torch?: boolean }

  /**
   * Request access to the camera when in camera mode.
   */
  useEffect(() => {
    if (mode !== 'camera') {
      setPermission('granted')
      return
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setPermission('unsupported')
      onPermissionChange?.('unsupported')
      onError?.('Camera API is not supported on this device.')
      return
    }

    setPermission('pending')
    navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: { ideal: facingMode },
          // Request better quality for document scanning
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      })
      .then((stream) => {
        streamRef.current = stream
        const videoTrack = stream.getVideoTracks()[0]
        if (videoTrack?.getCapabilities) {
          const caps = videoTrack.getCapabilities() as TorchCapabilities
          setTorchSupported(Boolean(caps.torch))
        } else {
          setTorchSupported(false)
        }
        setTorchEnabled(false)
        retryCountRef.current = 0
        if (videoRef.current) {
          const video = videoRef.current
          video.srcObject = stream
          
          // Wait for video metadata to load
          const handleLoadedMetadata = () => {
            video.removeEventListener('loadedmetadata', handleLoadedMetadata)
            const playPromise = video.play()
            if (playPromise !== undefined) {
              playPromise
                .then(() => {
                  retryCountRef.current = 0
                  setPermission('granted')
                  onPermissionChange?.('granted')
                  // Setup canvas for frame analysis
                  if (video && !canvasRef.current) {
                    const canvas = document.createElement('canvas')
                    canvasRef.current = canvas
                  }
                })
                .catch((playErr: Error) => {
                  // AbortError is usually harmless - video was interrupted by new load
                  // But we should limit retries to prevent infinite loops
                  if (playErr.name === 'AbortError' && retryCountRef.current < 2) {
                    retryCountRef.current++
                    // Only retry if video is still connected to the same stream and paused
                    if (video.srcObject === stream && video.paused && !video.ended) {
                      setTimeout(() => {
                        if (video.srcObject === stream && video.paused && !video.ended) {
                          video.play()
                            .then(() => {
                              retryCountRef.current = 0
                              setPermission('granted')
                              onPermissionChange?.('granted')
                            })
                            .catch(() => {
                              // Silently fail - AbortError is often harmless
                              retryCountRef.current = 0
                            })
                        }
                      }, 200)
                    } else {
                      retryCountRef.current = 0
                    }
                  } else if (playErr.name === 'NotAllowedError') {
                    console.error('Camera access denied', playErr)
                    setPermission('denied')
                    onPermissionChange?.('denied')
                    onError?.('Camera access denied. Please allow camera access in browser settings.')
                  } else {
                    // For other errors, check if video is actually playing
                    if (!video.paused && !video.ended && video.readyState >= 1) {
                      // Video is actually playing despite the error
                      setPermission('granted')
                      onPermissionChange?.('granted')
                    } else {
                      console.error('Video play error', playErr)
                      setPermission('denied')
                      onPermissionChange?.('denied')
                      onError?.(playErr.message || 'Unable to start camera.')
                    }
                  }
                })
            }
          }
          
          if (video.readyState >= 1) {
            // Metadata already loaded
            handleLoadedMetadata()
          } else {
            video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true })
          }
        }
      })
      .catch((err) => {
        console.error('Camera permission error', err)
        setPermission('denied')
        onPermissionChange?.('denied')
        onError?.(
          err?.message || 'Unable to access camera. Check your browser permissions.',
        )
      })

    return () => {
      retryCountRef.current = 0
      autoCapturedRef.current = false // Reset auto-capture flag
      // Clear any pending auto-capture timeout
      if (typeof window !== 'undefined' && (window as any).__lastAutoCaptureTimeout) {
        clearTimeout((window as any).__lastAutoCaptureTimeout)
        delete (window as any).__lastAutoCaptureTimeout
      }
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setTorchSupported(false)
      setTorchEnabled(false)
      if (frameCallbackRef.current !== null) {
        frameCallbackRef.current = null
      }
      if (videoRef.current) {
        const video = videoRef.current
        video.removeEventListener('loadedmetadata', () => {})
        video.srcObject = null
        video.pause()
      }
    }
  }, [mode, facingMode, onError, onPermissionChange])

  /**
   * Frame analysis: detect document and analyze quality (always runs for visual feedback)
   * Auto-capture: only if autoCapture is enabled
   */
  useEffect(() => {
    if (mode !== 'camera' || permission !== 'granted' || !videoRef.current || !canvasRef.current) {
      if (frameCallbackRef.current !== null) {
        frameCallbackRef.current = null
      }
      return
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) {
      console.warn('[scanner] Canvas context not available')
      return
    }

    let lastFrameTime = 0
    let lastDetectionTime = 0
    const FRAME_INTERVAL = 200 // Analyze quality every 200ms
    const DETECTION_INTERVAL = 300 // Detect document every 300ms (reduced for better responsiveness)
    const STABILITY_THRESHOLD = 3 // Need 3 good frames in a row (very lenient)
    const AUTO_CAPTURE_DELAY = 800 // Wait 800ms after stability before capture
    const CONFIDENCE_THRESHOLD = 0.15 // Very low threshold - show detection early
    const AREA_MIN_RATIO = 0.05 // Document should be at least 5% of frame (very lenient)
    const AREA_MAX_RATIO = 0.95 // Document should be at most 95% of frame (very lenient)
    const MAX_PERSPECTIVE_DISTORTION = 0.35 // Max 35% perspective distortion (more lenient)

      const analyzeFrame = () => {
        const now = Date.now()
        if (now - lastFrameTime < FRAME_INTERVAL) {
          if (typeof video.requestVideoFrameCallback === 'function') {
            frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
          }
          return
        }
        lastFrameTime = now

        // More lenient check for frame analysis - readyState >= 1 is enough
        const width = video.videoWidth || 0
        const height = video.videoHeight || 0
        
        if (video.readyState < 1 || (width === 0 && height === 0) || video.paused || video.ended) {
          if (typeof video.requestVideoFrameCallback === 'function') {
            frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
          }
          return
        }

      // Use actual dimensions or fallback
      canvas.width = width || 640
      canvas.height = height || 480
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

      try {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        
        // Detect document boundaries (throttled - heavier operation)
        if (now - lastDetectionTime >= DETECTION_INTERVAL) {
          lastDetectionTime = now
          try {
            const detectedQuad = detectDocument(imageData)
            // Only show detection with reasonable confidence and valid size
            if (detectedQuad && detectedQuad.confidence >= 0.15) {
              // Additional validation: reject quads that are too large (likely false positives)
              const quadWidth = Math.abs(detectedQuad.topRight.x - detectedQuad.topLeft.x)
              const quadHeight = Math.abs(detectedQuad.bottomLeft.y - detectedQuad.topLeft.y)
              const coverage = (quadWidth * quadHeight) / (canvas.width * canvas.height)
              
              // Reject if coverage is too high (>80%) or too low (<5%)
              if (coverage >= 0.05 && coverage <= 0.80) {
                setDocumentQuad(detectedQuad)
              } else {
                console.log('[scanner] Rejected quad: coverage out of range', { coverage: coverage.toFixed(3), confidence: detectedQuad.confidence.toFixed(3) })
                setDocumentQuad(null)
              }
              // Always log detection for debugging
              console.log('[scanner] Document detected:', {
                confidence: detectedQuad.confidence.toFixed(3),
                fill: detectedQuad.fill.toFixed(3),
                topLeft: detectedQuad.topLeft,
                dimensions: `${canvas.width}x${canvas.height}`
              })
              
              // Track quad for stability check
              quadHistoryRef.current.push({ quad: detectedQuad, timestamp: now })
              // Keep only last 1 second of history
              while (quadHistoryRef.current.length > 0 && now - quadHistoryRef.current[0].timestamp > 1000) {
                quadHistoryRef.current.shift()
              }
              lastDocumentQuadRef.current = detectedQuad
            } else {
              // Clear detection if confidence is too low
              setDocumentQuad(null)
              lastDocumentQuadRef.current = null
            }
          } catch (detectErr) {
            // Log error for debugging
            console.warn('[scanner] Document detection error', detectErr)
            setDocumentQuad(null)
            lastDocumentQuadRef.current = null
          }
        }
        
        // Analyze quality (lighter operation, can run more frequently)
        const report = analyzeImageData(imageData, preset)
        setQualityReport(report)
        onQualityChange?.(report)

        // Track quality history
        const isGood = report.passed
        qualityHistoryRef.current.push(isGood)
        if (qualityHistoryRef.current.length > STABILITY_THRESHOLD) {
          qualityHistoryRef.current.shift()
        }

        // Check if stable and good
        const stableCount = qualityHistoryRef.current.filter(Boolean).length
        setStabilityCount(stableCount)

        // Auto-capture conditions (as per TZ)
        const lastDocumentQuad = lastDocumentQuadRef.current
        const documentFound = lastDocumentQuad !== null && lastDocumentQuad.confidence >= CONFIDENCE_THRESHOLD
        const areaOk = lastDocumentQuad 
          ? (lastDocumentQuad.fill >= AREA_MIN_RATIO && lastDocumentQuad.fill <= AREA_MAX_RATIO)
          : false
        
        // Check perspective (simplified - check if quad is reasonably rectangular)
        let perspectiveOk = true
        if (lastDocumentQuad) {
          const quad = lastDocumentQuad
          const topLength = Math.abs(quad.topRight.x - quad.topLeft.x)
          const bottomLength = Math.abs(quad.bottomRight.x - quad.bottomLeft.x)
          const leftLength = Math.abs(quad.bottomLeft.y - quad.topLeft.y)
          const rightLength = Math.abs(quad.bottomRight.y - quad.topRight.y)
          
          const topBottomDiff = Math.abs(topLength - bottomLength) / Math.max(topLength, bottomLength, 1)
          const leftRightDiff = Math.abs(leftLength - rightLength) / Math.max(leftLength, rightLength, 1)
          
          perspectiveOk = Math.max(topBottomDiff, leftRightDiff) <= MAX_PERSPECTIVE_DISTORTION
        }
        
        // Check stability (document position hasn't changed much)
        let isStable = true
        const quadHistory = quadHistoryRef.current
        if (quadHistory.length >= 5 && lastDocumentQuad) {
          const recentQuads = quadHistory.slice(-5).map(h => h.quad)
          const avgX = recentQuads.reduce((sum, q) => sum + q.topLeft.x, 0) / recentQuads.length
          const avgY = recentQuads.reduce((sum, q) => sum + q.topLeft.y, 0) / recentQuads.length
          
          const currentX = lastDocumentQuad.topLeft.x
          const currentY = lastDocumentQuad.topLeft.y
          
          const movement = Math.sqrt((currentX - avgX) ** 2 + (currentY - avgY) ** 2)
          const maxMovement = Math.min(canvas.width, canvas.height) * 0.05 // 5% of frame
          isStable = movement < maxMovement
        }
        
        // All conditions for auto-capture - very lenient for better UX
        const allConditionsMet = (
          autoCapture &&
          documentFound &&
          areaOk &&
          isStable &&
          stableCount >= STABILITY_THRESHOLD && // Need stable frames
          !isCapturing &&
          !autoCapturedRef.current &&
          report.metrics.sharpness > 30 // Very low minimum sharpness
        )

        if (allConditionsMet) {
          // Mark as captured IMMEDIATELY before any async operations
          autoCapturedRef.current = true
          
          // Use a longer delay and additional checks to prevent rapid re-triggers
          const captureTimeout = setTimeout(() => {
            // Triple-check all conditions before capturing
            if (
              autoCapturedRef.current && // Still marked as captured
              !isCapturing && // Not currently capturing
              qualityHistoryRef.current.every(Boolean) && // All recent frames are good
              video && // Video element exists
              video.readyState >= 1 && // Video is ready
              !video.paused && // Video is playing
              !video.ended && // Video hasn't ended
              video.videoWidth > 0 && // Valid dimensions
              video.videoHeight > 0
            ) {
              handleCapture()
            } else {
              // Reset flag if conditions not met - allow retry later
              autoCapturedRef.current = false
            }
          }, AUTO_CAPTURE_DELAY + 300) // Longer delay to prevent rapid triggers
          
          // Store timeout to clear if component unmounts
          if (typeof window !== 'undefined') {
            (window as any).__lastAutoCaptureTimeout = captureTimeout
          }
        }
      } catch (err) {
        console.warn('Frame analysis error', err)
      }

      if (typeof video.requestVideoFrameCallback === 'function') {
        frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
      }
    }

    // Start frame analysis
    if (typeof video.requestVideoFrameCallback === 'function') {
      frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
    } else {
      // Fallback for browsers without requestVideoFrameCallback
      const interval = setInterval(() => {
        if (video.readyState >= 2) {
          analyzeFrame()
        }
      }, FRAME_INTERVAL)
      return () => clearInterval(interval)
    }

    return () => {
      if (frameCallbackRef.current !== null) {
        frameCallbackRef.current = null
      }
    }
  }, [autoCapture, mode, permission, preset, isCapturing, onQualityChange])


  /**
   * Capture current video frame into a Blob with auto-crop and correction.
   */
  const handleCapture = useCallback(async () => {
    if (mode === 'camera') {
      if (!videoRef.current) {
        onError?.('Camera not available. Please refresh the page.')
        return
      }
      const video = videoRef.current
      
      // More lenient check - readyState >= 1 is enough for capture
      // Use default dimensions if videoWidth/Height are 0 (some devices)
      const width = video.videoWidth || 640
      const height = video.videoHeight || 480
      
      // More lenient check - readyState >= 1 is enough, and allow 0 dimensions (will use defaults)
      if (video.readyState < 1) {
        // Video not ready yet - don't show error, just return silently
        // User can try again when camera is ready
        return
      }
      
      // Use default dimensions if videoWidth/Height are 0 (some mobile devices)
      const finalWidth = width > 0 ? width : 640
      const finalHeight = height > 0 ? height : 480
      
      const canvas = document.createElement('canvas')
      canvas.width = finalWidth
      canvas.height = finalHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        onError?.('Failed to create canvas. Please try again.')
        return
      }
      
      // Prevent multiple simultaneous captures
      if (isCapturing) {
        return
      }
      
      try {
        setCapturing(true)
        // Draw video frame - will scale automatically if dimensions don't match
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        
        // Auto-crop disabled - use original canvas
        // Backend will handle cropping and correction
        const finalCanvas = canvas
        
        // Use setTimeout to ensure canvas is ready
        setTimeout(() => {
          try {
            finalCanvas.toBlob((blob) => {
              setCapturing(false)
              if (blob) {
                // Reset auto-capture flag after successful capture
                autoCapturedRef.current = false
                onCapture(blob, {
                  width: finalCanvas.width,
                  height: finalCanvas.height,
                  facingMode,
                  captureMode: 'camera',
                  timestamp: Date.now(),
                })
              } else {
                setCapturing(false)
                onError?.('Failed to capture image. Please try again.')
                autoCapturedRef.current = false
              }
            }, 'image/jpeg', 0.95)
          } catch (err) {
            setCapturing(false)
            onError?.(err instanceof Error ? err.message : 'Failed to capture image.')
            autoCapturedRef.current = false
          }
        }, 100)
      } catch (err) {
        setCapturing(false)
        autoCapturedRef.current = false // Reset on error
        onError?.(err instanceof Error ? err.message : 'Failed to capture image. Please try again.')
      }
    }
  }, [mode, facingMode, overlayRatio, isCapturing, autoCapture, onCapture, onError])

  /**
   * Fallback file input handler (desktop / camera denied).
   */
  const handleFileChange = useCallback(
    (evt: React.ChangeEvent<HTMLInputElement>) => {
      const file = evt.target.files?.[0]
      if (!file) return
      onCapture(file, {
        width: 0,
        height: 0,
        facingMode,
        captureMode: 'upload',
        timestamp: Date.now(),
      })
      evt.target.value = ''
    },
    [onCapture, facingMode],
  )

  const renderOverlay = () => {
    if (mode !== 'camera') return null
    
    // Get actual video dimensions or fallback to window size
    const actualVideoWidth = videoRef.current?.videoWidth || 0
    const actualVideoHeight = videoRef.current?.videoHeight || 0
    const fallbackWidth = typeof window !== 'undefined' ? window.innerWidth : 1920
    const fallbackHeight = typeof window !== 'undefined' ? window.innerHeight : 1080
    
    // Get canvas dimensions (where detection happens)
    const canvasWidth = canvasRef.current?.width || actualVideoWidth || fallbackWidth
    const canvasHeight = canvasRef.current?.height || actualVideoHeight || fallbackHeight
    
    // Scale documentQuad coordinates if canvas and video/window sizes differ
    let scaledDocumentQuad = documentQuad
    if (documentQuad && canvasWidth > 0 && canvasHeight > 0) {
      const displayWidth = actualVideoWidth > 0 ? actualVideoWidth : fallbackWidth
      const displayHeight = actualVideoHeight > 0 ? actualVideoHeight : fallbackHeight
      
      const scaleX = displayWidth / canvasWidth
      const scaleY = displayHeight / canvasHeight
      
      // Always scale coordinates to match display dimensions
      scaledDocumentQuad = {
        ...documentQuad,
        topLeft: {
          x: documentQuad.topLeft.x * scaleX,
          y: documentQuad.topLeft.y * scaleY,
        },
        topRight: {
          x: documentQuad.topRight.x * scaleX,
          y: documentQuad.topRight.y * scaleY,
        },
        bottomRight: {
          x: documentQuad.bottomRight.x * scaleX,
          y: documentQuad.bottomRight.y * scaleY,
        },
        bottomLeft: {
          x: documentQuad.bottomLeft.x * scaleX,
          y: documentQuad.bottomLeft.y * scaleY,
        },
      }
      
      // Debug logging
      console.log('[scanner] Scaling documentQuad:', {
        canvas: `${canvasWidth}x${canvasHeight}`,
        display: `${displayWidth}x${displayHeight}`,
        scale: `${scaleX.toFixed(2)}x${scaleY.toFixed(2)}`,
        original: documentQuad.topLeft,
        scaled: scaledDocumentQuad.topLeft,
      })
    }
    
    return (
      <ScanningOverlay
        qualityReport={qualityReport ? {
          passed: qualityReport.passed,
          hints: qualityReport.warnings || [],
        } : null}
        stabilityCount={stabilityCount}
        isCapturing={isCapturing}
        aspectRatio={overlayRatio}
        documentQuad={scaledDocumentQuad}
        videoWidth={actualVideoWidth > 0 ? actualVideoWidth : fallbackWidth}
        videoHeight={actualVideoHeight > 0 ? actualVideoHeight : fallbackHeight}
      />
    )
  }

  const renderPermissionState = () => {
    if (mode !== 'camera') return null
    if (permission === 'granted') return null
    const messageMap: Record<PermissionState, string> = {
      pending: 'Requesting camera access…',
      granted: '',
      denied: 'Camera access denied. Allow it in browser settings or upload a photo instead.',
      unsupported: 'Camera is not supported on this device. Upload a photo from your gallery.',
    }
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl bg-slate-900/80 text-center text-white">
        <p className="text-lg font-semibold">{messageMap[permission]}</p>
        <label className="cursor-pointer text-sm underline">
          Upload photo instead
          <input
            type="file"
            accept={fallbackAccept}
            className="hidden"
            onChange={handleFileChange}
          />
        </label>
      </div>
    )
  }

  return (
    <div className="relative w-full">
      {mode === 'camera' ? (
        <>
          {/* Full screen camera view on mobile, like iPhone */}
          <div className="relative w-full bg-black sm:rounded-2xl sm:overflow-hidden" style={{ 
            height: typeof window !== 'undefined' && window.innerWidth < 640 ? 'calc(100vh - 80px)' : 'auto',
            minHeight: typeof window !== 'undefined' && window.innerWidth >= 640 ? '500px' : 'calc(100vh - 80px)',
            aspectRatio: typeof window !== 'undefined' && window.innerWidth >= 640 ? '16/9' : 'auto'
          }}>
            <video
              ref={videoRef}
              className="h-full w-full object-contain"
              playsInline
              muted
              autoPlay
            />
            {renderOverlay()}
            {renderPermissionState()}
            
            {/* Large capture button at bottom (iPhone-style) - mobile */}
            {permission === 'granted' && typeof window !== 'undefined' && window.innerWidth < 640 && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 pointer-events-auto">
                <button
                  type="button"
                  onClick={handleCapture}
                  disabled={isCapturing}
                  className="h-20 w-20 rounded-full bg-white border-4 border-gray-300 shadow-lg active:scale-95 disabled:opacity-50 flex items-center justify-center"
                  aria-label="Capture photo"
                >
                  {isCapturing ? (
                    <div className="h-16 w-16 rounded-full bg-gray-400" />
                  ) : (
                    <div className="h-16 w-16 rounded-full bg-white border-2 border-gray-200" />
                  )}
                </button>
              </div>
            )}
          </div>
          
          {/* Manual capture button for desktop - BELOW camera view, always visible */}
          {permission === 'granted' && typeof window !== 'undefined' && window.innerWidth >= 640 && (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={handleCapture}
                disabled={isCapturing}
                className="rounded-full bg-brand-600 px-8 py-3 text-white font-semibold shadow-lg hover:bg-brand-700 active:scale-95 disabled:opacity-50 transition-all min-h-[48px]"
                aria-label="Capture photo"
              >
                {isCapturing ? 'Съемка...' : 'Снять фото'}
              </button>
            </div>
          )}
        </>
      ) : (
        <label className="flex h-[320px] w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-400 text-slate-200">
          <span className="text-lg font-semibold">Upload from device</span>
          <span className="text-sm">JPEG or PNG, up to 10 MB</span>
          <input
            type="file"
            accept={fallbackAccept}
            className="hidden"
            onChange={handleFileChange}
          />
        </label>
      )}
    </div>
  )
}
