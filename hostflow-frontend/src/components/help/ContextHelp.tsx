import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconHelpCircle, IconX } from '@tabler/icons-react'
import { useI18n } from '../../i18n'

export type ContextHelpTermId =
  | 'vacancy'
  | 'lead'
  | 'candidate'
  | 'order'
  | 'flight'
  | 'campaign'
  | 'meta'

const FAQ_ANCHOR: Record<ContextHelpTermId, string> = {
  vacancy: '/faq#recruitment',
  lead: '/faq#recruitment',
  candidate: '/faq#recruitment',
  order: '/faq#recruitment',
  flight: '/faq#meta',
  campaign: '/faq#meta',
  meta: '/faq#meta',
}

type ContextHelpProps = {
  term: ContextHelpTermId
  className?: string
}

/**
 * Inline “what is this?” help — keeps the user on the screen (Success Path canon).
 */
export function ContextHelp({ term, className = '' }: ContextHelpProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const rootRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const title = t(`app.context_help.terms.${term}.title`, { defaultValue: term })
  const body = t(`app.context_help.terms.${term}.body`, { defaultValue: '' })

  return (
    <span ref={rootRef} className={`relative inline-flex align-middle ${className}`}>
      <button
        type="button"
        className="inline-flex h-6 w-6 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-brand-700"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={t('app.context_help.open_aria', {
          defaultValue: 'What is {term}?',
          values: { term: title },
        })}
        data-testid={`context-help-${term}`}
        onClick={() => setOpen((v) => !v)}
      >
        <IconHelpCircle size={16} stroke={1.8} aria-hidden />
      </button>
      {open ? (
        <span
          id={panelId}
          role="dialog"
          aria-label={title}
          className="absolute left-0 top-full z-40 mt-2 w-72 rounded-xl border border-slate-200 bg-white p-3 text-left shadow-lg sm:w-80"
        >
          <span className="flex items-start justify-between gap-2">
            <span className="text-sm font-semibold text-slate-900">{title}</span>
            <button
              type="button"
              className="rounded p-0.5 text-slate-400 hover:bg-slate-50 hover:text-slate-700"
              aria-label={t('common.close', { defaultValue: 'Close' })}
              onClick={() => setOpen(false)}
            >
              <IconX size={14} stroke={1.8} />
            </button>
          </span>
          <span className="mt-1 block text-xs leading-relaxed text-slate-600">{body}</span>
          <Link
            to={FAQ_ANCHOR[term]}
            className="mt-2 inline-flex text-xs font-semibold text-brand-700 hover:underline"
            onClick={() => setOpen(false)}
          >
            {t('app.context_help.more_faq', { defaultValue: 'More in FAQ' })}
          </Link>
        </span>
      ) : null}
    </span>
  )
}

export default ContextHelp
