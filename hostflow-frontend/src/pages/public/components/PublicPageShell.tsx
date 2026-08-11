import clsx from 'clsx'
import type { ReactNode } from 'react'
import { PublicLogo } from '../../../components/public/PublicLogo'
import { PublicCookieBanner } from '../../../components/public/PublicCookieBanner'
import { PublicLocaleSwitcher } from '../../../components/public/PublicLocaleSwitcher'

type PublicPageShellProps = {
  children: ReactNode
  maxWidth?: 'lg' | 'xl' | 'md' | '3xl' | '5xl' | '6xl' | '7xl'
  className?: string
  headerExtra?: ReactNode
  showBrand?: boolean
  headerSub?: ReactNode
  /** Optional notice above main content (e.g. client vs candidate intake). */
  topBanner?: ReactNode
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

export function PublicPageShell({
  children,
  maxWidth = 'lg',
  className,
  headerExtra,
  showBrand = true,
  headerSub,
  topBanner,
}: PublicPageShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(94,186,205,0.35),transparent_55%),radial-gradient(circle_at_85%_0%,rgba(25,78,122,0.2),transparent_65%),linear-gradient(180deg,rgba(255,255,255,0.92)_0%,#f6fbff_45%,#f8fbff_100%)]" />
      <div className={clsx('relative mx-auto w-full', WIDTH_CLASS[maxWidth], className)}>
        {showBrand && (
          <div className="mb-6 flex items-center justify-between gap-4">
            <PublicLogo showWordmark />
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
