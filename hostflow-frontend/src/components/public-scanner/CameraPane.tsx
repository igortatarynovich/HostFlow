import { useEffect, useRef, useState } from 'react'
import { analyzeImageData, type ScanPresetKey, type ScanQualityReport } from '../../modules/public-intake/scan/analyzer'
import { ScanningOverlay } from './ScanningOverlay'
import { useI18n } from '../../i18n'

type CameraPaneProps = {
  mode: 'camera' | 'fallback'
  facingMode?: 'user' | 'environment'
  overlayRatio?: number
  onCapture: (capture: CaptureResult) => void
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

export type FrameRect = { x: number; y: number; width: number; height: number }

export type CaptureResult = {
  original: Blob
  cropped: Blob
  previewUrl: string
  frameRect: FrameRect
  originalSize: { width: number; height: number }
  croppedSize: { width: number; height: number }
  metadata: CaptureMetadata
}

type TorchCapabilities = MediaTrackCapabilities & { torch?: boolean }

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
  const { t } = useI18n()
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
          // Request high resolution for better crop quality
          width: { ideal: 2560, min: 1280 },
          height: { ideal: 1440, min: 720 },
          frameRate: { ideal: 30 },
        },
        audio: false,
      })
      .then((stream) => {
        streamRef.current = stream
        const videoTrack = stream.getVideoTracks()[0]
        if (videoTrack?.getCapabilities) {
          const caps = videoTrack.getCapabilities() as TorchCapabilities & MediaTrackCapabilities
          setTorchSupported(Boolean((caps as any).torch))
          const advancedConstraints: MediaTrackConstraints = {}
          if (caps.width?.max && caps.height?.max) {
            advancedConstraints.width = { ideal: caps.width.max, max: caps.width.max }
            advancedConstraints.height = { ideal: caps.height.max, max: caps.height.max }
          }
          if (caps.frameRate?.max) {
            advancedConstraints.frameRate = { ideal: caps.frameRate.max, max: caps.frameRate.max }
          }
          if (Object.keys(advancedConstraints).length > 0) {
            videoTrack.applyConstraints(advancedConstraints).catch(() => {
              // fallback silently
            })
          }
        } else {
          setTorchSupported(false)
        }
        setTorchEnabled(false)
        retryCountRef.current = 0
        if (videoRef.current) {
          const video = videoRef.current
          video.srcObject = stream
          const handleLoadedMetadata = () => {
            video.removeEventListener('loadedmetadata', handleLoadedMetadata)
            const playPromise = video.play()
            if (playPromise !== undefined) {
              playPromise
                .then(() => {
                  retryCountRef.current = 0
                  setPermission('granted')
                  onPermissionChange?.('granted')
                  if (video && !canvasRef.current) {
                    const canvas = document.createElement('canvas')
                    canvasRef.current = canvas
                  }
                })
                .catch((playErr: Error) => {
                  if (playErr.name === 'AbortError' && retryCountRef.current < 2) {
                    retryCountRef.current++
                    if (video.srcObject === stream && video.paused && !video.ended) {
                      setTimeout(() => {
                        if (video.srcObject === stream && video.paused && !video.ended) {
                          video
                            .play()
                            .then(() => {
                              retryCountRef.current = 0
                              setPermission('granted')
                              onPermissionChange?.('granted')
                            })
                            .catch(() => {
                              retryCountRef.current = 0
                            })
                        }
                      }, 200)
                    } else {
                      retryCountRef.current = 0
                    }
                  } else if (playErr.name === 'NotAllowedError') {
                    setPermission('denied')
                    onPermissionChange?.('denied')
                    onError?.('Camera access denied. Please allow camera access in browser settings.')
                  } else {
                    if (!video.paused && !video.ended && video.readyState >= 1) {
                      setPermission('granted')
                      onPermissionChange?.('granted')
                    } else {
                      setPermission('denied')
                      onPermissionChange?.('denied')
                      onError?.(playErr.message || 'Unable to start camera.')
                    }
                  }
                })
            }
          }

          if (video.readyState >= 1) {
            handleLoadedMetadata()
          } else {
            video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true })
          }
        }
      })
      .catch((err) => {
        setPermission('denied')
        onPermissionChange?.('denied')
        onError?.(err?.message || 'Camera access denied. Please allow camera access in browser settings.')
      })

    return () => {
      retryCountRef.current = 0
      autoCapturedRef.current = false
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
        video.srcObject = null
        video.pause()
      }
    }
  }, [mode, facingMode, onError, onPermissionChange])

  /**
   * Frame analysis: only quality (no autodetect, no auto-capture).
   */
  useEffect(() => {
    if (!onQualityChange) {
      qualityHistoryRef.current = []
      return
    }

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
      return
    }

    let lastFrameTime = 0
    const FRAME_INTERVAL = 300
    const STABILITY_THRESHOLD = 3

    const analyzeFrame = () => {
      const now = Date.now()
      if (now - lastFrameTime < FRAME_INTERVAL) {
        if (typeof video.requestVideoFrameCallback === 'function') {
          frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
        }
        return
      }
      lastFrameTime = now

      const width = video.videoWidth || 0
      const height = video.videoHeight || 0
      if (video.readyState < 1 || (width === 0 && height === 0) || video.paused || video.ended) {
        if (typeof video.requestVideoFrameCallback === 'function') {
          frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
        }
        return
      }

      canvas.width = width || 640
      canvas.height = height || 480
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

      try {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        const report = analyzeImageData(imageData, preset)
        setQualityReport(report)
        onQualityChange?.(report)

        const isGood = report.passed
        qualityHistoryRef.current.push(isGood)
        if (qualityHistoryRef.current.length > STABILITY_THRESHOLD) {
          qualityHistoryRef.current.shift()
        }
        const stableCount = qualityHistoryRef.current.filter(Boolean).length
        setStabilityCount(stableCount)
      } catch (err) {
        console.warn('Frame analysis error', err)
      }

      if (typeof video.requestVideoFrameCallback === 'function') {
        frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
      }
    }

    if (typeof video.requestVideoFrameCallback === 'function') {
      frameCallbackRef.current = video.requestVideoFrameCallback(analyzeFrame)
    } else {
      const interval = setInterval(() => {
        if (video.readyState >= 2) {
          analyzeFrame()
        }
      }, FRAME_INTERVAL)
      return () => clearInterval(interval)
    }

    return () => {
      if (frameCallbackRef.current !== null && typeof (videoRef.current as any)?.cancelVideoFrameCallback === 'function') {
        ;(videoRef.current as any).cancelVideoFrameCallback(frameCallbackRef.current)
      }
    }
  }, [mode, permission, preset, onQualityChange])

  const toggleTorch = () => {
    if (!streamRef.current) return
    const track = streamRef.current.getVideoTracks()[0]
    if (!track) return
    const caps = track.getCapabilities() as TorchCapabilities
    if (!(caps as any).torch) return
    const next = !torchEnabled
    track.applyConstraints({ advanced: [{ torch: next }] }).catch(() => {
      // ignore
    })
    setTorchEnabled(next)
  }

  const handleCapture = async () => {
    if (isCapturing) return
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    setCapturing(true)
    try {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob(
        async (blob) => {
          if (!blob) throw new Error('Unable to capture frame')
          const original = blob
          // Crop by overlay frame
          const frameWidth = canvas.width * 0.85
          const frameHeight = frameWidth / overlayRatio
          const frameX = (canvas.width - frameWidth) / 2
          const frameY = (canvas.height - frameHeight) / 2
          const cropCanvas = document.createElement('canvas')
          cropCanvas.width = frameWidth
          cropCanvas.height = frameHeight
          const cropCtx = cropCanvas.getContext('2d')
          if (!cropCtx) throw new Error('Unable to get crop context')
          cropCtx.drawImage(
            canvas,
            frameX,
            frameY,
            frameWidth,
            frameHeight,
            0,
            0,
            frameWidth,
            frameHeight,
          )
          cropCanvas.toBlob(
            (croppedBlob) => {
              if (!croppedBlob) throw new Error('Unable to crop frame')
              const previewUrl = URL.createObjectURL(croppedBlob)
              const frameRect = { x: frameX, y: frameY, width: frameWidth, height: frameHeight }
              onCapture({
                original,
                cropped: croppedBlob,
                previewUrl,
                frameRect,
                originalSize: { width: canvas.width, height: canvas.height },
                croppedSize: { width: frameWidth, height: frameHeight },
                metadata: {
                  width: canvas.width,
                  height: canvas.height,
                  facingMode,
                  captureMode: mode === 'camera' ? 'camera' : 'upload',
                  timestamp: Date.now(),
                },
              })
            },
            'image/jpeg',
            0.92,
          )
        },
        'image/jpeg',
        0.92,
      )
    } catch (err) {
      onError?.(err instanceof Error ? err.message : 'Failed to capture image. Please try again.')
    } finally {
      setCapturing(false)
      autoCapturedRef.current = false
    }
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const maxDim = Math.max(img.width, img.height)
      const scale = maxDim > 2200 ? 2200 / maxDim : 1
      const targetW = img.width * scale
      const targetH = img.height * scale
      canvas.width = targetW
      canvas.height = targetH
      ctx.drawImage(img, 0, 0, targetW, targetH)
      canvas.toBlob(
        (blob) => {
          if (!blob) return
          const frameWidth = targetW * 0.85
          const frameHeight = frameWidth / overlayRatio
          const frameX = (targetW - frameWidth) / 2
          const frameY = (targetH - frameHeight) / 2
          const cropCanvas = document.createElement('canvas')
          cropCanvas.width = frameWidth
          cropCanvas.height = frameHeight
          const cropCtx = cropCanvas.getContext('2d')
          if (!cropCtx) return
          cropCtx.drawImage(
            canvas,
            frameX,
            frameY,
            frameWidth,
            frameHeight,
            0,
            0,
            frameWidth,
            frameHeight,
          )
          cropCanvas.toBlob(
            (croppedBlob) => {
              if (!croppedBlob) return
              const previewUrl = URL.createObjectURL(croppedBlob)
              const frameRect = { x: frameX, y: frameY, width: frameWidth, height: frameHeight }
              onCapture({
                original: blob,
                cropped: croppedBlob,
                previewUrl,
                frameRect,
                originalSize: { width: targetW, height: targetH },
                croppedSize: { width: frameWidth, height: frameHeight },
                metadata: {
                  width: targetW,
                  height: targetH,
                  facingMode,
                  captureMode: 'upload',
                  timestamp: Date.now(),
                },
              })
            },
            'image/jpeg',
            0.92,
          )
        },
        'image/jpeg',
        0.92,
      )
    }
    img.onerror = () => {
      onError?.('Unable to load image')
    }
    img.src = URL.createObjectURL(file)
  }

  return (
    <div className="relative w-full">
      {mode === 'camera' ? (
        <div className="relative w-full overflow-hidden rounded-2xl bg-black">
          <video
            ref={videoRef}
            className="h-full w-full object-contain"
            playsInline
            muted
          />
          <ScanningOverlay aspectRatio={overlayRatio} />
          <div className="absolute inset-0 flex items-end justify-center pb-4">
            <button
              type="button"
              onClick={handleCapture}
              className="h-14 w-14 rounded-full border-4 border-white bg-white/90 shadow-lg active:scale-95"
              aria-label={t('public.scanner.camera.capture', { defaultValue: 'Capture' })}
            />
          </div>
          {torchSupported && (
            <button
              type="button"
              onClick={toggleTorch}
              className="absolute right-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white"
            >
              {torchEnabled ? 'Torch off' : 'Torch on'}
            </button>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-slate-700">
          <p className="mb-3 text-sm font-semibold">
            {t('public.scanner.camera.upload_photo', { defaultValue: 'Upload a photo of the document' })}
          </p>
          <input type="file" accept={fallbackAccept} onChange={handleFileChange} />
        </div>
      )}
    </div>
  )
}
