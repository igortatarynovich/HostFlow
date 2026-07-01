import type { CommunicationThread } from '../api/communications'
import {
  threadHoursWaitingForReply,
  threadNeedsOutboundReply,
} from './communicationThreadDecision'
import { noReplyNeededFromThread, slaMutedFromThread } from './communicationsOpsMode'

type TI18n = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

function noReplyNeededOf(th: CommunicationThread): boolean {
  return noReplyNeededFromThread(th)
}

function slaMutedOf(th: CommunicationThread): boolean {
  return slaMutedFromThread(th)
}

/** One line: CHANNEL • wait • status — for rail / compact headers. */
export function threadDetailMetaLine(th: CommunicationThread, t: TI18n): string {
  const parts: string[] = [String(th.channel || '').toUpperCase()]
  if (threadNeedsOutboundReply(th) && !noReplyNeededOf(th) && !slaMutedOf(th)) {
    const h = threadHoursWaitingForReply(th)
    if (h !== null && h >= 1) {
      parts.push(t('app.communications_messages.list.wait_hours', { defaultValue: '{n}ч без ответа', values: { n: h } }))
    } else {
      parts.push(t('app.communications_messages.list.waiting_reply', { defaultValue: 'ждёт ответа' }))
    }
  }
  parts.push(String(th.status || 'open'))
  return parts.join(' • ')
}
