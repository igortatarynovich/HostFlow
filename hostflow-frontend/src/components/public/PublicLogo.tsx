import clsx from 'clsx'

type PublicLogoProps = {
  showWordmark?: boolean
  className?: string
  size?: number
  white?: boolean
}

export function PublicLogo({
  showWordmark = true,
  className,
  size = 48,
  white = false,
}: PublicLogoProps) {
  return (
    <div className={clsx('inline-flex items-center', className)}>
      <img
        src={white ? '/logo_hf_white.svg' : '/logo_hf.svg'}
        alt="HostFlow"
        width={showWordmark ? undefined : size}
        height={size}
        style={showWordmark ? { height: size } : undefined}
        className="w-auto"
        loading="lazy"
      />
    </div>
  )
}

type BrandingLogoProps = {
  showWordmark?: boolean
  className?: string
  size?: number
  white?: boolean
}

export function PublicBrandingLogo({
  showWordmark = false,
  className,
  size = 48,
  white = false,
}: BrandingLogoProps) {
  return (
    <PublicLogo
      showWordmark={showWordmark}
      className={className}
      size={size}
      white={white}
    />
  )
}
