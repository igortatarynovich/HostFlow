import { useI18n } from '../../i18n'
import {
  getHandoffToClient,
  getHandoffToInternalHr,
  type TenantLink,
  type TenantLinkUpdate,
} from '../../api/tenantLinks'

type Props = {
  link: TenantLink
  disabled: boolean
  onPatch: (patch: Pick<TenantLinkUpdate, 'handoff_to_client' | 'handoff_to_internal_hr'>) => void | Promise<void>
}

export function TenantLinkHandoffDestinations({ link, disabled, onPatch }: Props) {
  const { t } = useI18n()
  if (!link.handoff_enabled) return null

  const toClient = getHandoffToClient(link)
  const toHr = getHandoffToInternalHr(link)

  return (
    <div className="mt-3 w-full max-w-xl space-y-2 border-l-2 border-slate-200 pl-4">
      <p className="text-xs text-slate-500">
        {t('app.clients.handoff_dest_hint', {
          defaultValue: 'Куда направлять кандидатов при передаче (можно включить оба канала).',
        })}
      </p>
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={toClient}
            disabled={disabled}
            onChange={(e) => {
              const next = e.target.checked
              if (!next && !toHr) return
              void onPatch({ handoff_to_client: next })
            }}
          />
          <span className="text-sm">
            {t('app.clients.handoff_to_client_label', {
              defaultValue: 'Клиенту (портал / Do procesowania)',
            })}
          </span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={toHr}
            disabled={disabled}
            onChange={(e) => {
              const next = e.target.checked
              if (!next && !toClient) return
              void onPatch({ handoff_to_internal_hr: next })
            }}
          />
          <span className="text-sm">
            {t('app.clients.handoff_to_internal_hr_label', {
              defaultValue: 'Внутренний отдел кадров (HR)',
            })}
          </span>
        </label>
      </div>
    </div>
  )
}
