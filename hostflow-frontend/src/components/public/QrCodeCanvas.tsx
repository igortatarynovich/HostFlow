import { useEffect, useRef, useState } from 'react'

declare global {
  interface Window {
    qrcode?: any
  }
}

let qrLibPromise: Promise<any> | null = null

function loadQrLib(): Promise<any> {
  if (typeof window === 'undefined') {
    return Promise.resolve(null)
  }
  if (window.qrcode) {
    return Promise.resolve(window.qrcode)
  }
  if (qrLibPromise) {
    return qrLibPromise
  }
  qrLibPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.js'
    script.async = true
    script.onload = () => resolve(window.qrcode)
    script.onerror = (err) => {
      qrLibPromise = null
      reject(err)
    }
    document.body.appendChild(script)
  })
  return qrLibPromise
}

type QrCodeCanvasProps = {
  value: string
  size?: number
  className?: string
}

export function QrCodeCanvas({ value, size = 176, className }: QrCodeCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const draw = async () => {
      try {
        const qrLib = await loadQrLib()
        if (!qrLib || cancelled) return
        const qr = qrLib(0, 'M')
        qr.addData(value)
        qr.make()
        const count = qr.getModuleCount()
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        canvas.width = size
        canvas.height = size
        ctx.clearRect(0, 0, size, size)
        ctx.fillStyle = '#f8fafc'
        ctx.fillRect(0, 0, size, size)
        ctx.fillStyle = '#0f172a'
        const cell = size / count
        for (let row = 0; row < count; row += 1) {
          for (let col = 0; col < count; col += 1) {
            if (qr.isDark(row, col)) {
              ctx.fillRect(Math.round(col * cell), Math.round(row * cell), Math.ceil(cell), Math.ceil(cell))
            }
          }
        }
        setError(null)
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load QR')
        }
      }
    }
    void draw()
    return () => {
      cancelled = true
    }
  }, [value, size])

  if (error) {
    return <div className="text-xs text-rose-600">{error}</div>
  }

  return <canvas ref={canvasRef} width={size} height={size} className={className} />
}
