import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PublicLogo } from '../../../components/public/PublicLogo'
import { PublicCookieBanner } from '../../../components/public/PublicCookieBanner'
import { PublicLocaleSwitcher } from '../../../components/public/PublicLocaleSwitcher'
import { useI18n } from '../../../i18n'

type PublicPageShellProps = {
  children: ReactNode
  maxWidth?: 'lg' | 'xl' | 'md' | '3xl' | '5xl' | '6xl' | '7xl'
  className?: string
  headerExtra?: ReactNode
  showBrand?: boolean
  headerSub?: ReactNode
  /** Optional notice above main content (e.g. client vs candidate intake). */
  topBanner?: ReactNode
  /**
   * `marketing` — HostFlow landing palette (navy / teal / #F7F8FA).
   * `default` — legacy light intake/portal shell.
   */
  variant?: 'default' | 'marketing'
}

const WIDTH_CLASS: Record<NonNullable<PublicPageShellProps['maxWidth']>, string> = {
  md: 'max-w-3xl',
  '3xl': 'max-w-3xl',
  lg: 'max-w-4xl',
  xl: 'max-w-5xl',
  '5xl': 'max-w-5xl',
  '6xl': 'max-w-6xl',
  '7xl': 'max-w-7xl',
}

function MarketingChrome({
  children,
  maxWidth,
  className,
  headerSub,
  topBanner,
}: {
  children: ReactNode
  maxWidth: NonNullable<PublicPageShellProps['maxWidth']>
  className?: string
  headerSub?: ReactNode
  topBanner?: ReactNode
}) {
  const { t } = useI18n()

  const links = [
    { to: '/#trust', label: t('public.crm_landing.nav.trust', { defaultValue: 'Why us' }) },
    { to: '/#story', label: t('public.crm_landing.nav.story', { defaultValue: 'How we close' }) },
    { to: '/#case', label: t('public.crm_landing.nav.case', { defaultValue: 'Case' }) },
    { to: '/#pricing', label: t('public.crm_landing.nav.pricing', { defaultValue: 'Pricing' }) },
    { to: '/demo', label: t('public.crm_landing.nav.demo', { defaultValue: 'Try it free' }) },
    { to: '/faq', label: t('public.crm_landing.nav.faq', { defaultValue: 'FAQ' }) },
  ]

  return (
    <div className="min-h-screen bg-[#F7F8FA] text-slate-900 antialiased">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-[#0B0E14]/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:gap-4 sm:px-6 sm:py-3">
          <Link to="/" className="shrink-0" aria-label="HostFlow">
            <PublicLogo showWordmark white size={34} />
          </Link>
          <nav
            className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-[12px] font-medium text-slate-400 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden sm:gap-4 sm:text-[13px]"
            aria-label="Primary"
          >
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="shrink-0 rounded-md px-2 py-1.5 transition hover:bg-white/5 hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <div className="hidden md:block">
              <PublicLocaleSwitcher className="text-slate-400" />
            </div>
            <Link
              to="/login"
              className="hidden text-[13px] font-semibold text-slate-300 transition hover:text-white sm:inline"
            >
              {t('public.crm_landing.nav.login', { defaultValue: 'Log in' })}
            </Link>
            <Link
              to="/demo"
              className="inline-flex items-center justify-center rounded-lg bg-[#00C2A8] px-3 py-2 text-[12px] font-semibold text-[#04201C] transition hover:bg-[#1ad4bb] sm:px-3.5 sm:text-[13px]"
            >
              {t('public.crm_landing.nav.demo', { defaultValue: 'Try it free' })}
            </Link>
          </div>
        </div>
      </header>

      <div className={clsx('relative mx-auto w-full px-4 pb-10 pt-20 sm:px-6 sm:pt-24', WIDTH_CLASS[maxWidth], className)}>
        {headerSub ? <div className="mb-4">{headerSub}</div> : null}
        {topBanner ? <div className="mb-4">{topBanner}</div> : null}
        {children}
      </div>
      <PublicCookieBanner />
    </div>
  )
}

export function PublicPageShell({
  children,
  maxWidth = 'lg',
  className,
  headerExtra,
  showBrand = true,
  headerSub,
  topBanner,
  variant = 'default',
}: PublicPageShellProps) {
  if (variant === 'marketing') {
    return (
      <MarketingChrome maxWidth={maxWidth} className={className} headerSub={headerSub} topBanner={topBanner}>
        {children}
      </MarketingChrome>
    )
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#F7F8FA] px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(0,194,168,0.12),transparent_55%),radial-gradient(circle_at_85%_0%,rgba(11,14,20,0.08),transparent_65%),linear-gradient(180deg,rgba(255,255,255,0.92)_0%,#F7F8FA_45%,#F7F8FA_100%)]" />
      <div className={clsx('relative mx-auto w-full', WIDTH_CLASS[maxWidth], className)}>
        {showBrand && (
          <div className="mb-6 flex items-center justify-between gap-4">
            <Link to="/" aria-label="HostFlow">
              <PublicLogo showWordmark />
            </Link>
            {headerExtra ?? <PublicLocaleSwitcher />}
          </div>
        )}
        {headerSub && <div className="-mx-2 mb-4">{headerSub}</div>}
        {topBanner ? <div className="mb-4">{topBanner}</div> : null}
        {children}
      </div>
      <PublicCookieBanner />
    </div>
  )
}
