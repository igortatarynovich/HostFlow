/**
 * Universal Composer — driven only by ThreadContext (Workspace read model).
 * Does not resolve capabilities, policy, entity links, or registry rules itself.
 * Backend re-validates intent+channel on send; FE allow-list is display-only.
 */
import clsx from 'clsx'
import type { FormEvent, ReactNode } from 'react'
import type { ThreadContext } from '../../api/communications'
import { useI18n } from '../../i18n'

export type ThreadComposerDraft = {
  text: string
  subject: string
  recipientAddress: string
  intent: string
  channel: string
  internalNote: boolean
  sendImmediately: boolean
  applySignature: boolean
}

type Props = {
  context: ThreadContext
  draft: ThreadComposerDraft
  onDraftChange: (patch: Partial<ThreadComposerDraft>) => void
  onSubmit: (e: FormEvent) => void
  sending?: boolean
  /** Optional template insert UI (still cannot invent intents/channels). */
  templatesSlot?: ReactNode
  compact?: boolean
}

export default function ThreadComposer({
  context,
  draft,
  onDraftChange,
  onSubmit,
  sending,
  templatesSlot,
  compact,
}: Props) {
  const { t } = useI18n()
  const caps = context.capabilities || { allowed_intents: [], allowed_channels: [], defaults: {}, policy_denials: {} }
  const hints = context.workspace?.ui_hints || {}
  const defaults = caps.defaults || {}
  const canCompose = hints.can_compose !== false && Boolean((caps.allowed_intents || []).length)
  const blockedReason = hints.compose_blocked_reason
  const intents = caps.allowed_intents || []
  const channels = caps.allowed_channels || []
  const denials = caps.policy_denials || {}
  const delivery = context.workspace?.delivery_summary

  if (!canCompose) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-600">
        {t('app.communications.composer.blocked', {
          defaultValue: 'Compose is not available for this thread.',
        })}
        {blockedReason ? (
          <span className="mt-1 block text-xs text-slate-500">{blockedReason}</span>
        ) : null}
        {Object.keys(denials).length > 0 ? (
          <ul className="mt-2 list-disc pl-4 text-xs text-slate-500">
            {Object.entries(denials).map(([k, v]) => (
              <li key={k}>
                {k}: {v}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    )
  }

  return (
    <form
      className={clsx('space-y-2', compact ? 'text-sm' : '')}
      onSubmit={onSubmit}
    >
      {delivery?.status ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-950">
          {t('app.communications.delivery_diagnostics.title', { defaultValue: 'Delivery issue' })}
          : {delivery.status}
          {delivery.reason_code ? ` · ${delivery.reason_code}` : null}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <label className="flex min-w-[8rem] flex-1 flex-col gap-0.5 text-[11px] text-slate-500">
          {t('app.communications.labels.channel', { defaultValue: 'Channel' })}
          <select
            className="input py-1 text-xs"
            value={draft.channel}
            onChange={(e) => onDraftChange({ channel: e.target.value })}
          >
            {channels.map((ch) => (
              <option key={ch} value={ch}>
                {ch}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[10rem] flex-1 flex-col gap-0.5 text-[11px] text-slate-500">
          {t('app.communications.composer.intent', { defaultValue: 'Intent' })}
          <select
            className="input py-1 text-xs"
            value={draft.intent}
            onChange={(e) => onDraftChange({ intent: e.target.value })}
            disabled={draft.internalNote}
          >
            {intents.map((intent) => (
              <option key={intent} value={intent}>
                {intent}
              </option>
            ))}
          </select>
        </label>
      </div>

      {String(draft.channel).toLowerCase() === 'email' && !draft.internalNote && (
        <>
          <input
            className="input w-full text-sm"
            value={draft.recipientAddress}
            onChange={(e) => onDraftChange({ recipientAddress: e.target.value })}
            placeholder={t('app.communications.thread.recipient', { defaultValue: 'Recipient' })}
          />
          <input
            className="input w-full text-sm"
            value={draft.subject}
            onChange={(e) => onDraftChange({ subject: e.target.value })}
            placeholder={t('app.communications.thread.subject', { defaultValue: 'Subject' })}
          />
        </>
      )}

      {defaults.internal_note_allowed !== false && (
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={draft.internalNote}
            onChange={(e) => onDraftChange({ internalNote: e.target.checked })}
          />
          {t('app.communications.thread.internal_note', { defaultValue: 'Internal note' })}
        </label>
      )}

      {templatesSlot}

      <textarea
        rows={compact ? 5 : 8}
        value={draft.text}
        onChange={(e) => onDraftChange({ text: e.target.value })}
        className="w-full textarea"
        placeholder={t('app.communications.thread.message')}
      />

      {!draft.internalNote && (
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={draft.sendImmediately}
            onChange={(e) => onDraftChange({ sendImmediately: e.target.checked })}
          />
          {t('app.communications.thread.send_immediately', { defaultValue: 'Send immediately' })}
        </label>
      )}

      {String(draft.channel).toLowerCase() === 'email' && !draft.internalNote && (
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={draft.applySignature}
            onChange={(e) => onDraftChange({ applySignature: e.target.checked })}
          />
          {t('app.communications.email.signature.apply')}
        </label>
      )}

      <button
        type="submit"
        disabled={sending || !draft.text.trim() || intents.length === 0}
        className="w-full btn-primary disabled:cursor-not-allowed disabled:opacity-50"
      >
        {sending ? t('common.loading') : t('app.communications.thread.send')}
      </button>
    </form>
  )
}

export function draftFromThreadContext(context: ThreadContext): ThreadComposerDraft {
  const d = context.capabilities?.defaults || {}
  const draft = context.workspace?.draft || {}
  const intents = context.capabilities?.allowed_intents || []
  const channels = context.capabilities?.allowed_channels || []
  return {
    text: String(draft.body_text || draft.text || ''),
    subject: String(draft.subject || d.subject || context.identity?.thread?.subject || ''),
    recipientAddress: String(draft.recipient_address || d.recipient_address || ''),
    intent: String(draft.intent || d.intent || intents[0] || ''),
    channel: String(
      draft.channel || d.channel || context.identity?.thread?.channel || channels[0] || '',
    ),
    internalNote: Boolean(draft.internal_note),
    sendImmediately: d.send_immediately !== false,
    applySignature: true,
  }
}
