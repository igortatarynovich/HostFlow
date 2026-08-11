import { useNavigate } from 'react-router-dom'
import type { ClientChannelDayItem, ClientChannelWorkspacePulse } from '../../api/clientChannelWorkspace'
import { useI18n } from '../../i18n'
import { useToast } from '../Toast'
import { clientAcquisitionChannelPath } from '../../app/clientAcquisitionPaths'
import { buildPublicClientInquiryUrl } from '../../utils/clientInquiryUrl'
import { leadHref, startSalesWorkSession } from '../../services/salesWorkSession'

function AfterThatList({ items }: { items: ClientChannelDayItem[] }) {
  if (items.length === 0) return null
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.id} className="flex items-center justify-between gap-3 text-sm text-slate-700">
          <span>
            {item.icon ? `${item.icon} ` : null}
            {item.headline}
            {item.count != null ? ` (${item.count})` : null}
          </span>
        </li>
      ))}
    </ul>
  )
}

type ClientNextActionPanelProps = {
  pulse: ClientChannelWorkspacePulse | null
  channelId: string
  publicUrl?: string | null
  loading?: boolean
  onShareLink?: () => void
}

export function ClientNextActionPanel({
  pulse,
  channelId,
  publicUrl,
  loading,
  onShareLink,
}: ClientNextActionPanelProps) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { notify } = useToast()
  const next = pulse?.next_action ?? null
  const afterThat = pulse?.after_that ?? []
  const later = pulse?.later ?? []

  if (loading) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
      </section>
    )
  }

  async function copyPublicUrl() {
    const url =
      publicUrl ||
      (pulse?.status?.public_slug ? buildPublicClientInquiryUrl(pulse.status.public_slug) : '')
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      notify({
        title: t('app.client_channel_home.link_copied', { defaultValue: 'Link copied' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('app.client_channel_home.link_copy_failed', { defaultValue: 'Could not copy' }),
        variant: 'error',
      })
    }
  }

  function handleStart() {
    if (!next) return
    if (next.work_kind === 'share') {
      if (onShareLink) {
        onShareLink()
        return
      }
      void copyPublicUrl()
      return
    }
    const queue = next.queue ?? []
    if (queue.length > 0 && next.work_kind) {
      startSalesWorkSession({
        channelId,
        kind: next.work_kind,
        queue,
        returnPath: clientAcquisitionChannelPath(channelId),
      })
      navigate(leadHref(queue[0]))
      return
    }
    navigate(next.href)
  }

  if (!next && later.length === 0) {
    return (
      <section className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.sales_next.all_clear_title', { defaultValue: 'All done for today' })}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          {t('app.sales_next.all_clear_body', {
            defaultValue: 'Watch for new company inquiries — HostFlow will suggest the next step.',
          })}
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-4" data-testid="m1-sales-next-action">
      {next ? (
        <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">
            {t('app.sales_next.title', { defaultValue: 'Next action' })}
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-900">
            {next.icon ? `${next.icon} ` : null}
            {next.headline}
          </h2>
          <p className="mt-2 text-sm text-slate-700">{next.reason || next.message}</p>
          <button
            type="button"
            onClick={handleStart}
            className="mt-4 rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {next.action_label || t('app.sales_next.start', { defaultValue: 'Start' })}
          </button>
        </div>
      ) : null}

      {afterThat.length > 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.sales_next.after_that', { defaultValue: 'After that' })}
          </h3>
          <div className="mt-3">
            <AfterThatList items={afterThat} />
          </div>
        </div>
      ) : null}

      {later.length > 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-4">
          <h3 className="text-sm font-semibold text-slate-700">
            {t('app.sales_next.later_title', { defaultValue: 'Later' })}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {t('app.sales_next.later_hint', {
              defaultValue: 'Integrations and expansion — once operations are covered.',
            })}
          </p>
          <div className="mt-3">
            <AfterThatList items={later} />
          </div>
        </div>
      ) : null}
    </section>
  )
}
