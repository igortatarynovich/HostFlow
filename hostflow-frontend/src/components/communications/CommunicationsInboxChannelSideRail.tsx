import clsx from 'clsx'
import CommunicationsInboxControlPanel from './CommunicationsInboxControlPanel'
import { useCommunicationsThread } from '../../hooks/useCommunicationsThread'
import { useI18n } from '../../i18n'

type Props = {
  threadId: string | null
  backListPath: string
  reloadSignal: number
  onAfterArchiveOrDelete?: () => void
  /** Bump parent thread list (e.g. Messages) after rail updates thread links/assignee. */
  onAfterThreadPatch?: () => void | Promise<void>
  /** Hide candidate/client/order search in rail — used when those forms are in the chat column. */
  hideEntityLinkForms?: boolean
  className?: string
  /** Constrain rail height (e.g. `h-full min-h-0` when the grid row stretches). */
  maxHeightClass?: string
  /** Shorter copy in the control panel (email workspace). */
  compactControlPanel?: boolean
}

export default function CommunicationsInboxChannelSideRail({
  threadId,
  backListPath,
  reloadSignal,
  onAfterArchiveOrDelete,
  onAfterThreadPatch,
  hideEntityLinkForms,
  className,
  maxHeightClass = 'max-h-[calc(100dvh-7rem)] min-h-0',
  compactControlPanel,
}: Props) {
  const { t } = useI18n()
  const model = useCommunicationsThread(threadId || '', {
    backListPathOverride: backListPath,
    reloadSignal,
  })
  const { thread, loading, errorText } = model

  return (
    <section
      className={clsx(
        'hidden flex-col overflow-hidden rounded-lg border border-slate-200 bg-white xl:flex',
        maxHeightClass,
        className,
      )}
    >
      {!threadId && (
        <div className="p-4 text-sm text-slate-500">
          {t('app.communications_inbox_center.channel_rail_empty', {
            defaultValue: 'Select a thread for links, follow-up task, workflow, and archive.',
          })}
        </div>
      )}
      {threadId && loading && !thread && (
        <div className="p-4 text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</div>
      )}
      {threadId && !loading && !thread && errorText && (
        <div className="p-4 text-sm text-rose-700">{errorText}</div>
      )}
      {thread && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <CommunicationsInboxControlPanel
            thread={thread}
            model={model}
            onAfterArchiveOrDelete={onAfterArchiveOrDelete}
            onAfterThreadPatch={onAfterThreadPatch}
            hideEntityLinkForms={hideEntityLinkForms}
            compact={compactControlPanel}
          />
        </div>
      )}
    </section>
  )
}
