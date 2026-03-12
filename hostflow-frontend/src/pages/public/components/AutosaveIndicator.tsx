import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../../../i18n'

type Props = {
  saving: boolean
  className?: string
}

export function AutosaveIndicator({ saving, className = '' }: Props) {
  const { t } = useI18n()
  const [showSaved, setShowSaved] = useState(false)
  const prevSaving = useRef(false)

  useEffect(() => {
    if (prevSaving.current && !saving) {
      setShowSaved(true)
      const id = window.setTimeout(() => setShowSaved(false), 2500)
      return () => window.clearTimeout(id)
    }
    prevSaving.current = saving
  }, [saving])

  if (!saving && !showSaved) return null

  return (
    <div
      className={`flex items-center gap-2 text-sm ${className}`}
      role="status"
      aria-live="polite"
    >
      {saving ? (
        <>
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <span className="text-slate-600">
            {t('public.intake.new.autosave.saving', { defaultValue: 'Saving…' })}
          </span>
        </>
      ) : showSaved ? (
        <span className="text-green-600">
          ✓ {t('public.intake.new.autosave.saved', { defaultValue: 'Draft saved' })}
        </span>
      ) : null}
    </div>
  )
}
