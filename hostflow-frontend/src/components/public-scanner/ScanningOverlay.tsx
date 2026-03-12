type ScanningOverlayProps = {
  qualityReport: {
    passed: boolean
    hints: string[]
  } | null
  stabilityCount: number
  isCapturing: boolean
  aspectRatio: number
  documentQuad: any
  videoWidth: number
  videoHeight: number
}

/**
 * Visual guide frame: fully transparent interior, thin turquoise stroke, 85% viewport width.
 * No detection/analysis; purely a visual helper.
 */
export function ScanningOverlay({
  aspectRatio,
  videoWidth,
  videoHeight,
}: ScanningOverlayProps) {
  const effectiveWidth = videoWidth > 0 ? videoWidth : (typeof window !== 'undefined' ? window.innerWidth : 1920)
  const effectiveHeight = videoHeight > 0 ? videoHeight : (typeof window !== 'undefined' ? window.innerHeight : 1080)

  const frameWidth = effectiveWidth * 0.85
  let frameHeight = frameWidth / aspectRatio
  if (frameHeight > effectiveHeight * 0.85) {
    frameHeight = effectiveHeight * 0.85
  }
  const frameX = (effectiveWidth - frameWidth) / 2
  const frameY = (effectiveHeight - frameHeight) / 2
  const path = `M ${frameX} ${frameY} L ${frameX + frameWidth} ${frameY} L ${frameX + frameWidth} ${frameY + frameHeight} L ${frameX} ${frameY + frameHeight} Z`

  const corners: Array<[number, number]> = [
    [frameX, frameY],
    [frameX + frameWidth, frameY],
    [frameX + frameWidth, frameY + frameHeight],
    [frameX, frameY + frameHeight],
  ]

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
        pointerEvents: 'none',
      }}
    >
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox={`0 0 ${effectiveWidth} ${effectiveHeight}`}
        preserveAspectRatio="none"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      >
        <path
          d={path}
          fill="none"
          stroke="#00C2FF"
          strokeWidth="2"
          strokeOpacity="0.7"
          vectorEffect="non-scaling-stroke"
        />
        {corners.map(([x, y], idx) => (
          <g key={idx} stroke="#00C2FF" strokeWidth="3" strokeOpacity="0.8" vectorEffect="non-scaling-stroke">
            <line x1={x} y1={y} x2={x + (idx === 1 || idx === 2 ? -40 : 40)} y2={y} />
            <line x1={x} y1={y} x2={x} y2={y + (idx >= 2 ? -40 : 40)} />
          </g>
        ))}
      </svg>
    </div>
  )
}
