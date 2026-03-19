import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

type HoverCardProps = {
  content: React.ReactNode
  children: React.ReactElement
  openDelayMs?: number
  closeDelayMs?: number
  maxWidthClassName?: string
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

export default function HoverCard({
  content,
  children,
  openDelayMs = 200,
  closeDelayMs = 150,
  maxWidthClassName = 'max-w-[340px]',
}: HoverCardProps) {
  const triggerRef = useRef<HTMLElement | null>(null)
  const cardRef = useRef<HTMLDivElement | null>(null)
  const openTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)

  const clearTimers = () => {
    if (openTimerRef.current) clearTimeout(openTimerRef.current)
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    openTimerRef.current = null
    closeTimerRef.current = null
  }

  const computePosition = () => {
    const el = triggerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight

    // Preferred: right of trigger; fallback: below.
    const margin = 10
    const preferredLeft = rect.right + margin
    const preferredTop = rect.top - 6

    // Estimate width/height before first paint; re-adjust after open via effect.
    const estW = 340
    const estH = 180
    const left = preferredLeft + estW < vw ? preferredLeft : clamp(rect.left, margin, vw - estW - margin)
    const top = clamp(preferredTop, margin, vh - estH - margin)
    setPos({ top: Math.round(top + window.scrollY), left: Math.round(left + window.scrollX) })
  }

  const scheduleOpen = () => {
    clearTimers()
    openTimerRef.current = setTimeout(() => {
      computePosition()
      setOpen(true)
    }, openDelayMs)
  }

  const scheduleClose = () => {
    clearTimers()
    closeTimerRef.current = setTimeout(() => {
      setOpen(false)
    }, closeDelayMs)
  }

  useEffect(() => {
    return () => {
      clearTimers()
    }
  }, [])

  useEffect(() => {
    if (!open) return
    const onScrollOrResize = () => computePosition()
    window.addEventListener('scroll', onScrollOrResize, true)
    window.addEventListener('resize', onScrollOrResize)
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true)
      window.removeEventListener('resize', onScrollOrResize)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    // Post-open adjustment based on actual size.
    const card = cardRef.current
    const trigger = triggerRef.current
    if (!card || !trigger) return
    const rect = trigger.getBoundingClientRect()
    const cardRect = card.getBoundingClientRect()
    const margin = 10
    const vw = window.innerWidth
    const vh = window.innerHeight

    const preferredLeft = rect.right + margin
    const left = preferredLeft + cardRect.width < vw ? preferredLeft : clamp(rect.left, margin, vw - cardRect.width - margin)
    const top = clamp(rect.top - 6, margin, vh - cardRect.height - margin)
    setPos({ top: Math.round(top + window.scrollY), left: Math.round(left + window.scrollX) })
  }, [open, content])

  const child = (() => {
    const props: Record<string, any> = {
      ref: (node: HTMLElement | null) => {
        triggerRef.current = node
        const anyChild: any = children as any
        const childRef = anyChild?.ref
        if (typeof childRef === 'function') childRef(node)
        // Note: we intentionally do not assign to object refs from children props
        // to keep render/purity rules (and avoid mutating props-derived objects).
      },
      onMouseEnter: (e: any) => {
        children.props.onMouseEnter?.(e)
        scheduleOpen()
      },
      onMouseLeave: (e: any) => {
        children.props.onMouseLeave?.(e)
        scheduleClose()
      },
      onFocus: (e: any) => {
        children.props.onFocus?.(e)
        scheduleOpen()
      },
      onBlur: (e: any) => {
        children.props.onBlur?.(e)
        scheduleClose()
      },
    }
    return { ...children, props: { ...children.props, ...props } }
  })()

  const card =
    open && pos
      ? createPortal(
          <div
            ref={cardRef}
            className={`z-[80] ${maxWidthClassName} rounded-xl border border-slate-200 bg-white shadow-2xl`}
            style={{ position: 'absolute', top: pos.top, left: pos.left }}
            onMouseEnter={() => {
              clearTimers()
              setOpen(true)
            }}
            onMouseLeave={() => scheduleClose()}
          >
            <div className="p-3">{content}</div>
          </div>,
          document.body,
        )
      : null

  return (
    <>
      {child}
      {card}
    </>
  )
}

