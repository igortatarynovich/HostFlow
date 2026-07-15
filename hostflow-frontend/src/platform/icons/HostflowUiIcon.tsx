import clsx from 'clsx'
import { resolveIconSize, type VisualAssetSizeToken } from './visualAssets.generated'
import { resolveUiIconUrl, type UiIconId, type UiIconTheme } from './uiIconPaths'

export type HostflowUiIconTheme = UiIconTheme | 'auto'
export type HostflowUiIconTone = 'default' | 'onPrimary'

export type HostflowUiIconProps = {
  id: UiIconId
  size?: VisualAssetSizeToken | number
  theme?: HostflowUiIconTheme
  /** White glyph on brand/primary buttons (SVG stroke is slate in assets). */
  tone?: HostflowUiIconTone
  className?: string
  title?: string
}

function themedImgClass(theme: HostflowUiIconTheme, surface: UiIconTheme): string {
  if (theme === 'auto') {
    return surface === 'light' ? 'dark:hidden' : 'hidden dark:inline-block'
  }
  return theme === surface ? 'inline-block' : 'hidden'
}

export function HostflowUiIcon({
  id,
  size = 'sm',
  theme = 'auto',
  tone = 'default',
  className,
  title,
}: HostflowUiIconProps) {
  const px = resolveIconSize(size)
  const lightSrc = resolveUiIconUrl(id, 'light')
  const darkSrc = resolveUiIconUrl(id, 'dark')
  const sharedClass = clsx(
    'shrink-0 object-contain',
    tone === 'onPrimary' && 'brightness-0 invert',
    className,
  )

  if (theme !== 'auto' && lightSrc !== darkSrc) {
    const src = theme === 'dark' ? darkSrc : lightSrc
    return (
      <img
        src={src}
        width={px}
        height={px}
        alt=""
        title={title}
        className={clsx('inline-block', sharedClass)}
        aria-hidden={title ? undefined : true}
      />
    )
  }

  if (theme !== 'auto' || lightSrc === darkSrc) {
    const src = theme === 'dark' ? darkSrc : lightSrc
    return (
      <img
        src={src}
        width={px}
        height={px}
        alt=""
        title={title}
        className={clsx('inline-block', sharedClass)}
        aria-hidden={title ? undefined : true}
      />
    )
  }

  return (
    <>
      <img
        src={lightSrc}
        width={px}
        height={px}
        alt=""
        title={title}
        className={clsx('inline-block', sharedClass, themedImgClass(theme, 'light'))}
        aria-hidden={title ? undefined : true}
      />
      <img
        src={darkSrc}
        width={px}
        height={px}
        alt=""
        title={title}
        className={clsx('inline-block', sharedClass, themedImgClass(theme, 'dark'))}
        aria-hidden={title ? undefined : true}
      />
    </>
  )
}
