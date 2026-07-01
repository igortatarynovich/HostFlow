import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactElement,
  type ReactNode,
} from 'react'
import clsx from 'clsx'
import { IconQuestionMark } from '@tabler/icons-react'

import { useI18n } from '../../i18n'

/**
 * Lightweight click-to-open popover used by G-10 explainability surfaces.
 *
 * The codebase has no Radix / Headless UI / Floating UI dependency, so we
 * roll a tiny one. It is intentionally minimal: positioned by CSS, not by a
 * floating-positioning engine. Callers pick the side via the `align` prop.
 *
 * The popover supports:
 * - default trigger: a circular "?" icon button (use when you just need
 *   "explain this row").
 * - custom trigger: pass a `trigger` element and we inject the open/close
 *   handler. Useful when wrapping an existing badge.
 *
 * Closing rules:
 * - click outside the panel and the trigger
 * - Escape key while focus is anywhere in the popover root
 * - explicit close button inside the panel header
 */

interface ExplainabilityPopoverProps {
  /** Content rendered inside the panel. Keep it short — this is "why does
   *  this row exist", not a docs page. */
  children: ReactNode
  /** Optional title shown at the top of the panel. */
  title?: string
  /** Side of the trigger the panel opens on. Defaults to right-aligned with
   *  the trigger so the panel doesn't overflow the viewport on right-side
   *  rows. */
  align?: 'left' | 'right'
  /** Custom trigger element. If omitted, a small circular "?" icon button
   *  is rendered. The custom trigger receives `onClick` injected. */
  trigger?: ReactElement
  /** Accessible label for the default "?" trigger button. */
  triggerAriaLabel?: string
  /** Visual size of the default trigger; ignored when `trigger` is custom. */
  size?: 'sm' | 'md'
}

export function ExplainabilityPopover({
  children,
  title,
  align = 'right',
  trigger,
  triggerAriaLabel,
  size = 'sm',
}: ExplainabilityPopoverProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLSpanElement | null>(null)
  const panelId = useId()

  const close = useCallback(() => setOpen(false), [])
  const toggle = useCallback(() => setOpen((v) => !v), [])

  // Close on outside click / focus shift. We intentionally use mousedown so
  // a user clicking another button doesn't first trigger that button's
  // onClick before the popover closes (which would feel laggy).
  useEffect(() => {
    if (!open) return
    const handler = (event: MouseEvent) => {
      const root = rootRef.current
      if (!root) return
      if (event.target instanceof Node && !root.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLSpanElement>) => {
      if (event.key === 'Escape' && open) {
        event.stopPropagation()
        setOpen(false)
      }
    },
    [open],
  )

  const triggerSizeClass = size === 'md' ? 'h-5 w-5 text-[11px]' : 'h-4 w-4 text-[10px]'

  // Inject onClick into the custom trigger so callers don't have to wire it.
  // We deliberately don't try to style the custom trigger — it is the
  // caller's responsibility.
  const triggerNode = trigger && isValidElement(trigger)
    ? cloneElement(trigger as ReactElement<{ onClick?: () => void; 'aria-expanded'?: boolean; 'aria-controls'?: string }>, {
        onClick: toggle,
        'aria-expanded': open,
        'aria-controls': panelId,
      })
    : (
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          aria-label={triggerAriaLabel ?? t('app.explain.trigger', { defaultValue: 'Why?' })}
          className={clsx(
            'inline-flex items-center justify-center rounded-full border border-slate-300 bg-white text-slate-500 shadow-sm transition hover:border-slate-400 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-300',
            triggerSizeClass,
          )}
        >
          <IconQuestionMark size={size === 'md' ? 12 : 10} stroke={2.5} />
        </button>
      )

  return (
    <span
      ref={rootRef}
      onKeyDown={handleKeyDown}
      className="relative inline-flex"
    >
      {triggerNode}
      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label={title ?? t('app.explain.title', { defaultValue: 'Why is this here?' })}
          className={clsx(
            'absolute z-30 mt-2 w-72 rounded-lg border border-slate-200 bg-white p-3 text-left text-xs text-slate-700 shadow-lg',
            // top-full positions the panel right under the trigger; right-0
            // anchors to the right edge so it stays inside the row on
            // right-side action clusters.
            'top-full',
            align === 'right' ? 'right-0' : 'left-0',
          )}
          // Stop click propagation so an outer Link/button doesn't trigger
          // when the user clicks inside the explanation.
          onClick={(e) => e.stopPropagation()}
        >
          {title && (
            <div className="mb-2 flex items-start justify-between gap-2 border-b border-slate-100 pb-2">
              <h5 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                {title}
              </h5>
              <button
                type="button"
                onClick={close}
                aria-label={t('app.explain.close', { defaultValue: 'Close' })}
                className="text-slate-400 transition hover:text-slate-700"
              >
                ×
              </button>
            </div>
          )}
          <div className="space-y-1.5 leading-relaxed">{children}</div>
        </div>
      )}
    </span>
  )
}

/**
 * Convenience row used inside an explainability panel: a small label + value
 * (or a clickable link). Keeps panels visually consistent across surfaces.
 */
export function ExplainabilityRow({
  label,
  value,
  href,
  mono,
}: {
  label: string
  value: ReactNode
  href?: string | null
  mono?: boolean
}) {
  const valueClass = clsx(
    'text-slate-800',
    mono && 'font-mono text-[10.5px]',
  )
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {href ? (
        <a
          href={href}
          className={clsx(valueClass, 'min-w-0 truncate text-right text-brand-700 hover:underline')}
          title={typeof value === 'string' ? value : undefined}
        >
          {value}
        </a>
      ) : (
        <span className={clsx(valueClass, 'min-w-0 truncate text-right')}>
          {value}
        </span>
      )}
    </div>
  )
}

export default ExplainabilityPopover
