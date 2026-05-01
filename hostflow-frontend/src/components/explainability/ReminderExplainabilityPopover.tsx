import { useMemo } from 'react'

import type { ReminderRecord } from '../../api/types'
import { useI18n } from '../../i18n'
import { ExplainabilityPopover, ExplainabilityRow } from './ExplainabilityPopover'

/**
 * G-10: explain "why does this reminder exist?" inside `/app/tasks` rows.
 *
 * Surfaces fields that are otherwise buried (`type`, `source`, payload
 * provenance, entity link, SLA dates) so operators can answer "did the
 * system create this on its own, or did I set it up?" without opening
 * devtools.
 *
 * The component is deliberately read-only: edits live in the row's existing
 * Edit button. This is a transparency surface, not a control surface.
 */

interface Props {
  reminder: ReminderRecord
  /** Optional pre-computed deep-link to the entity (e.g. candidate page).
   *  Skipped when null. */
  entityHref?: string | null
}

function pickPayloadString(payload: Record<string, unknown> | null | undefined, key: string): string | null {
  if (!payload) return null
  const v = (payload as Record<string, unknown>)[key]
  if (v == null) return null
  const s = String(v).trim()
  return s.length ? s : null
}

function formatTs(value?: string | null): string | null {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  // Locale-aware short timestamp; matches RemindersPage row style.
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function ReminderExplainabilityPopover({ reminder, entityHref }: Props) {
  const { t } = useI18n()

  const rows = useMemo(() => {
    // `source` only exists on the notification-typed ReminderRecord variant
    // (api/types/notification.ts). The legacy api/types.ts variant doesn't
    // declare it, but the backend ships it on payload anyway, so we read
    // both locations defensively.
    const sourceFromField = (reminder as { source?: string | null }).source ?? null
    const sourceFromPayload = pickPayloadString(reminder.payload, 'source')
    const source = sourceFromField || sourceFromPayload

    const createdBy = pickPayloadString(reminder.payload, 'created_by')
      || pickPayloadString(reminder.payload, 'creator')
      || pickPayloadString(reminder.payload, 'author')

    const policy = pickPayloadString(reminder.payload, 'policy')
      || pickPayloadString(reminder.payload, 'policy_url')
      || pickPayloadString(reminder.payload, 'rule')

    return {
      type: reminder.type || null,
      source: source || null,
      created_at: formatTs(reminder.created_at),
      created_by: createdBy,
      due_at: formatTs(reminder.due_at),
      sla_due_at: formatTs(reminder.sla_due_at),
      sla_status: reminder.sla_status || null,
      entity_label: reminder.entity_type
        ? `${reminder.entity_type} · ${String(reminder.entity_id || '').slice(0, 8)}`
        : null,
      policy,
    }
  }, [reminder])

  return (
    <ExplainabilityPopover
      title={t('app.explain.reminder.title', { defaultValue: 'Why is this task here?' })}
      align="right"
      triggerAriaLabel={t('app.explain.reminder.trigger_aria', {
        defaultValue: 'Show why this task exists',
      })}
    >
      {rows.type && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.type', { defaultValue: 'Type' })}
          value={t(`app.reminders.type.${rows.type}`, { defaultValue: rows.type })}
          mono
        />
      )}
      {rows.source && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.source', { defaultValue: 'Source' })}
          value={t(`app.reminders.source.${rows.source}`, { defaultValue: rows.source })}
          mono
        />
      )}
      {rows.created_at && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.created_at', { defaultValue: 'Created' })}
          value={rows.created_at}
        />
      )}
      {rows.created_by && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.created_by', { defaultValue: 'Created by' })}
          value={rows.created_by}
        />
      )}
      {rows.due_at && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.due_at', { defaultValue: 'Due' })}
          value={rows.due_at}
        />
      )}
      {rows.sla_due_at && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.sla_due_at', { defaultValue: 'SLA deadline' })}
          value={rows.sla_due_at}
        />
      )}
      {rows.sla_status && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.sla_status', { defaultValue: 'SLA status' })}
          value={t(`app.reminders.sla.status.${rows.sla_status}`, { defaultValue: rows.sla_status })}
          mono
        />
      )}
      {(rows.entity_label || entityHref) && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.entity', { defaultValue: 'Linked to' })}
          value={rows.entity_label ?? t('app.explain.reminder.field.entity_open', { defaultValue: 'Open entity' })}
          href={entityHref ?? null}
          mono
        />
      )}
      {rows.policy && (
        <ExplainabilityRow
          label={t('app.explain.reminder.field.policy', { defaultValue: 'Policy' })}
          value={rows.policy}
          href={rows.policy.startsWith('http') ? rows.policy : null}
        />
      )}
      <p className="pt-1 text-[10.5px] italic leading-snug text-slate-500">
        {t('app.explain.reminder.footer', {
          defaultValue: 'This task was generated by the system or set by a user — see the fields above.',
        })}
      </p>
    </ExplainabilityPopover>
  )
}

export default ReminderExplainabilityPopover
