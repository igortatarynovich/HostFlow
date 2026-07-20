/**
 * Stage 6C — safe anchor for resolver hrefs (relative in-app or absolute cross-host).
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { canonicalizeAppOrModuleHref } from './entityDeepLinks'

type Props = {
  href: string | null | undefined
  className?: string
  children: ReactNode
  title?: string
  'data-testid'?: string
}

function isAbsoluteHttp(href: string): boolean {
  return /^https?:\/\//i.test(href)
}

export function EntityDeepLink({ href, className, children, title, ...rest }: Props) {
  const raw = String(href || '').trim()
  if (!raw) return <>{children}</>
  const target = canonicalizeAppOrModuleHref(raw)
  if (isAbsoluteHttp(target)) {
    return (
      <a href={target} className={className} title={title} {...rest}>
        {children}
      </a>
    )
  }
  return (
    <Link to={target} className={className} title={title} {...rest}>
      {children}
    </Link>
  )
}
