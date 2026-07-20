import { formatDistanceToNow } from 'date-fns'
import { enUS, pl as plFns, ru as ruFns } from 'date-fns/locale'
import type { AcquisitionSnapshot } from '../api/searchAcquisition'
import { useI18n, type LocaleCode } from '../../i18n'

function dateFnsLocale(code: LocaleCode) {
  if (code === 'pl') return plFns
  if (code === 'ru') return ruFns
  return enUS
}

type AcquisitionSyncStatusProps = {
  snapshot: AcquisitionSnapshot | null
  syncing: boolean
}

export function AcquisitionSyncStatus({ snapshot, syncing }: AcquisitionSyncStatusProps) {
  const { t, locale } = useI18n()
  const dfLocale = dateFnsLocale(locale)
  const sync = snapshot?.sync
  const interval = sync?.sync_interval_minutes ?? 15

  if (syncing) {
    return (
      <p className="text-xs text-slate-500">
        {t('app.acquisition.sync_in_progress', { defaultValue: 'Обновляем данные…' })}
      </p>
    )
  }

  if (sync?.last_sync_error) {
    const ago = sync.last_sync_ok_at
      ? formatDistanceToNow(new Date(sync.last_sync_ok_at), { addSuffix: true, locale: dfLocale })
      : null
    return (
      <p className="text-xs text-amber-800">
        {t('app.acquisition.sync_failed_status', {
          defaultValue: 'Не удалось обновить данные Meta.',
        })}
        {ago
          ? ` ${t('app.acquisition.sync_failed_ago', {
              defaultValue: 'Последние данные получены {ago}.',
              values: { ago },
            })}`
          : null}
      </p>
    )
  }

  const last = sync?.last_sync_ok_at || snapshot?.synced_at
  if (last) {
    const ago = formatDistanceToNow(new Date(last), { addSuffix: true, locale: dfLocale })
    return (
      <p className="text-xs text-slate-500">
        {t('app.acquisition.last_updated', {
          defaultValue: 'Последнее обновление: {ago}',
          values: { ago },
        })}
      </p>
    )
  }

  return (
    <p className="text-xs text-slate-500">
      {t('app.acquisition.auto_sync_hint', {
        defaultValue: 'Обновляется автоматически каждые {minutes} минут',
        values: { minutes: interval },
      })}
    </p>
  )
}
