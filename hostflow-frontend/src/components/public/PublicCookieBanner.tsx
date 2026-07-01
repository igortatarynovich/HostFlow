import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { isCookieConsentGranted, persistCookieConsent } from './cookieConsent'

export function PublicCookieBanner() {
  const { t } = useI18n()
  const [visible, setVisible] = useState(() => !isCookieConsentGranted())

  useEffect(() => {
    if (!visible) {
      window.dispatchEvent(new CustomEvent('hf:cookie-banner-hidden'))
    }
  }, [visible])

  const handleAccept = useCallback(() => {
    persistCookieConsent()
    setVisible(false)
  }, [])

  if (!visible) return null

  return (
    <div className="pointer-events-auto fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-6 md:pb-10">
      <div className="w-full max-w-5xl rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-2xl shadow-slate-900/10 backdrop-blur">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <p className="text-sm leading-relaxed text-slate-700">
            {t('public.cookies.banner.message')}{' '}
            <a
              href="/legal/cookies.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-700 underline-offset-2 hover:underline"
            >
              {t('public.cookies.banner.link')}
            </a>
            .
          </p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
            <a
              href="/legal/cookies.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-center text-sm font-semibold text-brand-700 underline-offset-4 hover:underline"
            >
              {t('public.cookies.banner.more')}
            </a>
            <button
              type="button"
              onClick={handleAccept}
              className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
            >
              {t('public.cookies.banner.accept')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
