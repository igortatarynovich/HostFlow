import clsx from 'clsx'
import type { IconProps } from '@tabler/icons-react'
import {
  getVisualAsset,
  hasThemedVisualAssetSvg,
  resolveIconSize,
  resolveVisualAssetSvg,
  type VisualAssetSizeToken,
  type VisualAssetTheme,
} from './visualAssets.generated'
import { resolveTablerIcon } from './tablerIconMap'

export type PlatformIconVariant = 'default' | 'filled' | 'brand'
export type PlatformIconTheme = VisualAssetTheme | 'auto'

export type PlatformIconProps = {
  id: string
  size?: VisualAssetSizeToken | number
  variant?: PlatformIconVariant
  theme?: PlatformIconTheme
  className?: string
  stroke?: number
  title?: string
}

function shouldUseBrandSvg(variant: PlatformIconVariant, hasSvg: boolean): boolean {
  return variant === 'brand' && hasSvg
}

function themedImgClass(theme: PlatformIconTheme, surface: VisualAssetTheme): string {
  if (theme === 'auto') {
    return surface === 'light' ? 'dark:hidden' : 'hidden dark:inline-block'
  }
  return theme === surface ? 'inline-block' : 'hidden'
}

function ThemedSvgImg({
  asset,
  variant,
  theme,
  px,
  className,
  title,
}: {
  asset: NonNullable<ReturnType<typeof getVisualAsset>>
  variant: PlatformIconVariant
  theme: PlatformIconTheme
  px: number
  className?: string
  title?: string
}) {
  const filled = variant === 'filled'
  const lightSrc = resolveVisualAssetSvg(asset, filled ? 'filled' : 'default', 'light')
  const darkSrc = resolveVisualAssetSvg(asset, filled ? 'filled' : 'default', 'dark')
  const sharedClass = clsx('shrink-0 object-contain', className)

  if (!lightSrc && !darkSrc) return null

  if (theme !== 'auto' || !hasThemedVisualAssetSvg(asset) || lightSrc === darkSrc) {
    const src = resolveVisualAssetSvg(asset, filled ? 'filled' : 'default', theme === 'dark' ? 'dark' : 'light')
    if (!src) return null
    return (
      <img
        src={src}
        width={px}
        height={px}
        alt=""
        title={title ?? asset.label}
        className={clsx('inline-block', sharedClass)}
        aria-hidden={title ? undefined : true}
      />
    )
  }

  return (
    <>
      {lightSrc ? (
        <img
          src={lightSrc}
          width={px}
          height={px}
          alt=""
          title={title ?? asset.label}
          className={clsx('inline-block', sharedClass, themedImgClass(theme, 'light'))}
          aria-hidden={title ? undefined : true}
        />
      ) : null}
      {darkSrc ? (
        <img
          src={darkSrc}
          width={px}
          height={px}
          alt=""
          title={title ?? asset.label}
          className={clsx('inline-block', sharedClass, themedImgClass(theme, 'dark'))}
          aria-hidden={title ? undefined : true}
        />
      ) : null}
    </>
  )
}

export function PlatformIcon({
  id,
  size = 'sm',
  variant = 'default',
  theme = 'auto',
  className,
  stroke = 1.75,
  title,
}: PlatformIconProps) {
  const asset = getVisualAsset(id)
  if (!asset) return null

  const px = resolveIconSize(size)
  const filled = variant === 'filled'
  const lightSvg = resolveVisualAssetSvg(asset, filled ? 'filled' : 'default', 'light')
  const darkSvg = resolveVisualAssetSvg(asset, filled ? 'filled' : 'default', 'dark')
  const hasSvg = Boolean(lightSvg || darkSvg)

  if (shouldUseBrandSvg(variant, hasSvg)) {
    return (
      <ThemedSvgImg
        asset={asset}
        variant={variant}
        theme={theme}
        px={px}
        className={className}
        title={title}
      />
    )
  }

  const tablerName = filled ? asset.tabler_filled ?? asset.tabler : asset.tabler
  const TablerIcon = resolveTablerIcon(tablerName)

  if (TablerIcon) {
    const iconProps: IconProps = {
      size: px,
      stroke,
      className: clsx(
        'shrink-0',
        theme === 'auto' && 'text-slate-700 dark:text-slate-200',
        theme === 'light' && 'text-slate-700',
        theme === 'dark' && 'text-slate-200',
        className,
      ),
      'aria-hidden': title ? undefined : true,
      title,
    }
    return <TablerIcon {...iconProps} />
  }

  if (hasSvg) {
    return (
      <ThemedSvgImg
        asset={asset}
        variant={variant}
        theme={theme}
        px={px}
        className={className}
        title={title}
      />
    )
  }

  return null
}

export function platformIconUrl(
  id: string,
  variant: PlatformIconVariant = 'default',
  theme: PlatformIconTheme = 'light',
): string | undefined {
  const asset = getVisualAsset(id)
  if (!asset) return undefined
  const resolvedTheme: VisualAssetTheme = theme === 'dark' ? 'dark' : 'light'
  return resolveVisualAssetSvg(asset, variant === 'filled' ? 'filled' : 'default', resolvedTheme)
}
