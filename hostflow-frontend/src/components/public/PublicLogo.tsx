import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import { resolveAssetUrl, settings } from '../../api/client'

type PublicLogoProps = {
  showWordmark?: boolean
  className?: string
  wordmarkClassName?: string
  size?: number
}

export function PublicLogo({
  showWordmark = true,
  className,
  wordmarkClassName,
  size = 40,
}: PublicLogoProps) {
  return (
    <div className={clsx('inline-flex items-center gap-2 font-semibold text-brand-900', className)}>
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        aria-hidden
        className="text-current"
      >
        <path
          d="M8 22c0-6.627 5.373-12 12-12h12L16 42H8V22Z"
          fill="currentColor"
          opacity="0.9"
        />
        <path
          d="M56 22c0-6.627-5.373-12-12-12H32l16 32h8V22Z"
          fill="currentColor"
          opacity="0.65"
        />
        <path
          d="M22 34h20l8 16H14l8-16Z"
          fill="currentColor"
          opacity="0.35"
        />
      </svg>
      {showWordmark && <span className={clsx('text-lg tracking-tight', wordmarkClassName)}>HostFlow</span>}
    </div>
  )
}

type BrandingLogoProps = {
  showWordmark?: boolean
  className?: string
  wordmarkClassName?: string
  size?: number
}

export function PublicBrandingLogo({
  showWordmark = false,
  className,
  wordmarkClassName,
  size = 32,
}: BrandingLogoProps) {
  const [logoSrc, setLogoSrc] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    const tenantId = settings.get()
    const candidate = resolveAssetUrl(`/uploads/tenant-logos/${tenantId}/logo.png`)
    if (!candidate) return () => { isMounted = false }

    const img = new Image()
    img.onload = () => {
      if (isMounted) setLogoSrc(candidate)
    }
    img.onerror = () => {
      if (isMounted) setLogoSrc(null)
    }
    img.src = candidate
    return () => {
      isMounted = false
    }
  }, [])

  const fallback = useMemo(
    () => <PublicLogo showWordmark={showWordmark} className={className} wordmarkClassName={wordmarkClassName} size={size} />,
    [className, showWordmark, size, wordmarkClassName]
  )

  if (!logoSrc) {
    return fallback
  }

  return (
    <div className={clsx('inline-flex items-center gap-2', className)}>
      <img
        src={logoSrc}
        alt="HostFlow"
        className="h-10 w-auto"
        style={{ maxHeight: size }}
        loading="lazy"
      />
      {showWordmark && <span className={clsx('text-lg font-semibold text-brand-900', wordmarkClassName)}>HostFlow</span>}
    </div>
  )
}
