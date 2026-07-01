import { Link } from 'react-router-dom'
import { IconAlertTriangle, IconRefresh } from '@tabler/icons-react'
import type { FriendlyErrorInfo } from '../utils/friendlyError'

type ErrorRecoveryBannerProps = {
  info: FriendlyErrorInfo
  onRetry?: () => void
  retryLabel?: string
  secondaryTo?: string
  secondaryLabel?: string
  compact?: boolean
}

export default function ErrorRecoveryBanner({
  info,
  onRetry,
  retryLabel = 'Retry',
  secondaryTo,
  secondaryLabel,
  compact = false,
}: ErrorRecoveryBannerProps) {
  const linkTo = info.secondaryTo ?? secondaryTo
  const linkLabel = info.secondaryLabel ?? secondaryLabel
  return (
    <div className={`rounded-xl border border-rose-200 bg-rose-50 text-rose-900 ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-start gap-2">
        <IconAlertTriangle size={16} className="mt-0.5 shrink-0 text-rose-700" />
        <div className="min-w-0">
          <p className="text-sm font-semibold">{info.title}</p>
          {info.detail && <p className="mt-1 text-xs text-rose-800/90">{info.detail}</p>}
          <p className="mt-1 text-xs text-rose-800">{info.hint}</p>
          {(onRetry || (linkTo && linkLabel)) && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="inline-flex items-center gap-1 rounded-md border border-rose-300 bg-white px-2.5 py-1 text-xs text-rose-800 hover:bg-rose-100"
                >
                  <IconRefresh size={12} />
                  {retryLabel}
                </button>
              )}
              {linkTo && linkLabel && (
                <Link
                  to={linkTo}
                  className="inline-flex items-center rounded-md border border-rose-200 bg-white px-2.5 py-1 text-xs text-rose-700 hover:bg-rose-100"
                >
                  {linkLabel}
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
