import { useEffect, useState } from 'react'
import { listFleetOperatingLines, type FleetOperatingLine } from '../../api/fleet'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type Props = {
  preview?: boolean
}

export default function FleetOperatingLinesSection({ preview }: Props) {
  const { t } = useI18n()
  const [items, setItems] = useState<FleetOperatingLine[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listFleetOperatingLines()
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch((err) => {
        if (!cancelled) setError(getFriendlyErrorInfo(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const title = t('app.fleet.operating_lines.title', { defaultValue: 'Operating lines' })

  if (error) {
    return (
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <ErrorRecoveryBanner
          primary={error.title}
          secondary={friendlyErrorBannerSecondary(error)}
          onRetry={() => window.location.reload()}
        />
      </section>
    )
  }

  const displayItems = preview ? items.slice(0, 5) : items

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      ) : displayItems.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
          {t('app.fleet.operating_lines.empty', { defaultValue: 'No operating lines yet.' })}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
          {displayItems.map((row) => (
            <li key={row.id} className="px-4 py-3 text-sm">
              <span className="font-medium text-slate-900">{row.name}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
