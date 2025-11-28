import { useEffect, useState } from 'react'
import type { DocumentQuad } from '../../modules/public-intake/scan/documentDetector'

type ScanningOverlayProps = {
  qualityReport: {
    passed: boolean
    hints: string[]
  } | null
  stabilityCount: number
  isCapturing: boolean
  aspectRatio: number
  documentQuad: DocumentQuad | null
  videoWidth: number
  videoHeight: number
}

const STABILITY_THRESHOLD = 3

export function ScanningOverlay({
  qualityReport,
  stabilityCount,
  isCapturing,
  aspectRatio,
  documentQuad,
  videoWidth,
  videoHeight,
}: ScanningOverlayProps) {
  const isStable = stabilityCount >= STABILITY_THRESHOLD
  const isReady = isStable && qualityReport?.passed

  // FALLBACK: Use container dimensions if video dimensions are 0 (common on mobile)
  const effectiveWidth = videoWidth > 0 ? videoWidth : (typeof window !== 'undefined' ? window.innerWidth : 1920)
  const effectiveHeight = videoHeight > 0 ? videoHeight : (typeof window !== 'undefined' ? window.innerHeight : 1080)

  // CRITICAL DEBUG: Log all inputs
  console.log('[ScanningOverlay] Render:', {
    hasDocumentQuad: !!documentQuad,
    documentQuad: documentQuad ? {
      confidence: documentQuad.confidence,
      fill: documentQuad.fill,
      topLeft: documentQuad.topLeft,
      topRight: documentQuad.topRight,
      bottomRight: documentQuad.bottomRight,
      bottomLeft: documentQuad.bottomLeft,
    } : null,
    videoWidth,
    videoHeight,
    effectiveWidth,
    effectiveHeight,
    isReady,
    isStable,
    qualityReport: qualityReport ? { passed: qualityReport.passed, hints: qualityReport.hints } : null,
    stabilityCount,
  })

  // Calculate guide frame dimensions - responsive for mobile
  // On mobile (portrait), use wider frame; on desktop, use square-ish frame
  const isMobile = effectiveWidth < effectiveHeight && effectiveWidth < 768
  const frameWidthPercent = isMobile ? 85 : 70
  const frameHeightPercent = isMobile ? 60 : 70
  const frameX = isMobile ? 7.5 : 15
  const frameY = isMobile ? 20 : 15
  
  // If document is detected, use its bounds, otherwise show guide frame
  let detectedPath: string | null = null
  let guideFramePath: string | null = null
  
  if (documentQuad && effectiveWidth > 0 && effectiveHeight > 0) {
    // Convert document quad coordinates to SVG path
    const { topLeft, topRight, bottomRight, bottomLeft } = documentQuad
    
    // Validate coordinates are within reasonable bounds
    const allPoints = [topLeft, topRight, bottomRight, bottomLeft]
    const allValid = allPoints.every(p => 
      !isNaN(p.x) && !isNaN(p.y) && 
      isFinite(p.x) && isFinite(p.y) &&
      p.x >= -effectiveWidth * 0.5 && p.x <= effectiveWidth * 1.5 &&
      p.y >= -effectiveHeight * 0.5 && p.y <= effectiveHeight * 1.5
    )
    
    if (allValid) {
      detectedPath = `M ${topLeft.x} ${topLeft.y} L ${topRight.x} ${topRight.y} L ${bottomRight.x} ${bottomRight.y} L ${bottomLeft.x} ${bottomLeft.y} Z`
      
      console.log('[ScanningOverlay] ✅ Creating detectedPath:', {
        confidence: documentQuad.confidence.toFixed(3),
        fill: documentQuad.fill.toFixed(3),
        viewBox: `${effectiveWidth}x${effectiveHeight}`,
        topLeft: `${topLeft.x},${topLeft.y}`,
        topRight: `${topRight.x},${topRight.y}`,
        bottomRight: `${bottomRight.x},${bottomRight.y}`,
        bottomLeft: `${bottomLeft.x},${bottomLeft.y}`,
        path: detectedPath,
      })
    } else {
      console.warn('[ScanningOverlay] ⚠️ Invalid coordinates, using guide frame:', {
        topLeft,
        topRight,
        bottomRight,
        bottomLeft,
        effectiveWidth,
        effectiveHeight,
      })
    }
  }
  
  if (!detectedPath && effectiveWidth > 0 && effectiveHeight > 0) {
    // Show guide frame when document not detected (as per TZ)
    const guideX1 = (frameX / 100) * effectiveWidth
    const guideY1 = (frameY / 100) * effectiveHeight
    const guideX2 = ((frameX + frameWidthPercent) / 100) * effectiveWidth
    const guideY2 = ((frameY + frameHeightPercent) / 100) * effectiveHeight
    guideFramePath = `M ${guideX1} ${guideY1} L ${guideX2} ${guideY1} L ${guideX2} ${guideY2} L ${guideX1} ${guideY2} Z`
    console.log('[ScanningOverlay] Using guide frame (no detection)')
  }

  // Always show overlay - either detected document or guide frame
  const shouldShowOverlay = true

  return (
    <div 
      className="absolute inset-0 pointer-events-none" 
      style={{ 
        zIndex: 10, 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        width: '100%', 
        height: '100%',
        pointerEvents: 'none'
      }}
    >
      {/* Document frame overlay - ALWAYS VISIBLE (as per TZ) */}
      {shouldShowOverlay && effectiveWidth > 0 && effectiveHeight > 0 && (
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox={`0 0 ${effectiveWidth} ${effectiveHeight}`}
          preserveAspectRatio="none"
          style={{ 
            zIndex: 10, 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            width: '100%', 
            height: '100%', 
            pointerEvents: 'none',
            overflow: 'visible'
          }}
        >
          {/* Show detected document OR guide frame */}
          {detectedPath ? (
            <>
              {/* Semi-transparent mask outside detected document */}
              <defs>
                <mask id="document-mask">
                  <rect width="100%" height="100%" fill="white" />
                  <path d={detectedPath} fill="black" />
                </mask>
              </defs>
              <rect
                width="100%"
                height="100%"
                fill="rgba(0, 0, 0, 0.5)"
                mask="url(#document-mask)"
              />
              
              {/* Detected document outline - THICK and VISIBLE - FORCE VISIBILITY */}
              <path
                d={detectedPath}
                fill="none"
                stroke={isReady ? "#10b981" : documentQuad && documentQuad.confidence >= 0.05 ? "#fbbf24" : "#ef4444"}
                strokeWidth="20"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={isReady ? "0" : "10 5"}
                strokeOpacity="1"
                style={{ 
                  filter: 'drop-shadow(0 0 8px rgba(255,255,255,1))',
                  vectorEffect: 'non-scaling-stroke'
                }}
              />
              
              {/* Corner markers for detected document - LARGE AND VISIBLE */}
              {documentQuad && (() => {
                const { topLeft, topRight, bottomRight, bottomLeft } = documentQuad
                const corners = [topLeft, topRight, bottomRight, bottomLeft]
                const strokeColor = isReady ? "#10b981" : documentQuad.confidence >= 0.05 ? "#fbbf24" : "#ef4444"
                return corners.map((corner, idx) => (
                  <circle
                    key={idx}
                    cx={corner.x}
                    cy={corner.y}
                    r="20"
                    fill={strokeColor}
                    stroke="white"
                    strokeWidth="6"
                    style={{ 
                      filter: 'drop-shadow(0 0 8px rgba(0,0,0,1))',
                      vectorEffect: 'non-scaling-stroke'
                    }}
                  />
                ))
              })()}
            </>
          ) : guideFramePath ? (
            <>
              {/* Guide frame when document not detected - RED (as per TZ) */}
              <rect
                width="100%"
                height="100%"
                fill="rgba(0, 0, 0, 0.5)"
              />
              <path
                d={guideFramePath}
                fill="none"
                stroke="#ef4444"
                strokeWidth="8"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray="15 10"
                strokeOpacity="1"
                style={{ 
                  filter: 'drop-shadow(0 0 8px rgba(255,255,255,1))',
                  vectorEffect: 'non-scaling-stroke'
                }}
              />
              {/* Corner markers for guide frame */}
              {(() => {
                const guideX1 = (frameX / 100) * effectiveWidth
                const guideY1 = (frameY / 100) * effectiveHeight
                const guideX2 = ((frameX + frameWidthPercent) / 100) * effectiveWidth
                const guideY2 = ((frameY + frameHeightPercent) / 100) * effectiveHeight
                const corners = [
                  { x: guideX1, y: guideY1 },
                  { x: guideX2, y: guideY1 },
                  { x: guideX2, y: guideY2 },
                  { x: guideX1, y: guideY2 },
                ]
                return corners.map((corner, idx) => (
                  <circle
                    key={idx}
                    cx={corner.x}
                    cy={corner.y}
                    r="15"
                    fill="#ef4444"
                    stroke="white"
                    strokeWidth="4"
                    style={{ 
                      filter: 'drop-shadow(0 0 8px rgba(255,255,255,1))',
                      vectorEffect: 'non-scaling-stroke'
                    }}
                  />
                ))
              })()}
            </>
          ) : null}
        </svg>
      )}

      {/* Status indicator - show different states (as per TZ) */}
      <div 
        className="absolute top-2 left-1/2 -translate-x-1/2 md:top-4" 
        style={{ pointerEvents: 'none', zIndex: 20 }}
      >
        {(() => {
          // Determine status based on document detection
          if (documentQuad && documentQuad.confidence >= 0.05) {
            if (isReady) {
              console.log('[ScanningOverlay] Status: READY (green)', { confidence: documentQuad.confidence, isStable, qualityPassed: qualityReport?.passed })
              return (
                <div className="rounded-full px-3 py-1.5 text-xs font-medium shadow-lg backdrop-blur-sm bg-emerald-500/90 text-white md:px-4 md:py-2 md:text-sm">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-white animate-pulse" />
                    <span>Готово к съёмке</span>
                  </span>
                </div>
              )
            } else {
              console.log('[ScanningOverlay] Status: ALMOST READY (yellow)', { confidence: documentQuad.confidence, isStable, qualityPassed: qualityReport?.passed })
              return (
                <div className="rounded-full px-3 py-1.5 text-xs font-medium shadow-lg backdrop-blur-sm bg-yellow-500/90 text-white md:px-4 md:py-2 md:text-sm">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-white" />
                    <span>Почти готово</span>
                  </span>
                </div>
              )
            }
          } else {
            console.log('[ScanningOverlay] Status: NOT FOUND (red)', { hasDocumentQuad: !!documentQuad, confidence: documentQuad?.confidence })
            return (
              <div className="rounded-full px-3 py-1.5 text-xs font-medium shadow-lg backdrop-blur-sm bg-red-500/90 text-white md:px-4 md:py-2 md:text-sm">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-white" />
                  <span>Документ не найден</span>
                </span>
              </div>
            )
          }
        })()}
      </div>
      
      {/* Hints - always visible (as per TZ) */}
      <div 
        className="absolute bottom-20 left-1/2 -translate-x-1/2 text-center" 
        style={{ pointerEvents: 'none', zIndex: 20 }}
      >
        <div className="rounded-lg px-4 py-2 text-sm font-medium shadow-lg backdrop-blur-sm bg-black/60 text-white max-w-md">
          {!documentQuad ? (
            <span>Поместите документ в рамку</span>
          ) : !isStable ? (
            <span>Держите телефон неподвижно</span>
          ) : !qualityReport?.passed ? (
            <span>Улучшите освещение</span>
          ) : (
            <span>Готово к съёмке</span>
          )}
        </div>
      </div>

      {/* Capture animation */}
      {isCapturing && (
        <div className="absolute inset-0 bg-white/80 animate-pulse flex items-center justify-center">
          <div className="text-2xl font-bold text-slate-900">Capturing...</div>
        </div>
      )}
    </div>
  )
}

