import type { ReactNode } from 'react'
import clsx from 'clsx'
import { IconBrandWhatsapp, IconMail, IconPhone } from '@tabler/icons-react'
import type {
  EntityContextRailBlockId,
  EntityContextRailContactAction,
  EntityContextRailModel,
  EntityWorkspaceShellLabels,
} from './types'
import { DEFAULT_ENTITY_CONTEXT_RAIL_WIDTH_PX, DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS, ENTITY_CONTEXT_RAIL_BLOCK_ORDER } from './types'
import { useI18n } from '../../i18n'

type EntityWorkspaceContextRailProps = {
  model: EntityContextRailModel
  labels?: EntityWorkspaceShellLabels['contextRail']
  widthPx?: number
}

function ContactIcon({ icon }: { icon: EntityContextRailContactAction['icon'] }) {
  if (icon === 'phone') return <IconPhone size={18} stroke={1.8} />
  if (icon === 'whatsapp') return <IconBrandWhatsapp size={18} stroke={1.8} />
  return <IconMail size={18} stroke={1.8} />
}

export function EntityWorkspaceContextRail({
  model,
  labels = DEFAULT_ENTITY_WORKSPACE_SHELL_LABELS.contextRail,
  widthPx = DEFAULT_ENTITY_CONTEXT_RAIL_WIDTH_PX,
}: EntityWorkspaceContextRailProps) {
  const { t } = useI18n()
  const blocks: Partial<Record<EntityContextRailBlockId, ReactNode>> = {}

  const nextActionBlock = model.decisionTitle || model.actions?.primary ? (
    <div className="rounded-lg border border-brand-200 bg-brand-50/70 p-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-brand-700/80">
        {labels?.next_actions ?? t('app.platform.context_rail.next_action')}
      </p>
      {model.decisionTitle ? <p className="mt-1 text-sm font-semibold text-slate-900">{model.decisionTitle}</p> : null}
      {model.decisionWhy ? <p className="mt-0.5 text-xs leading-snug text-slate-600">{model.decisionWhy}</p> : null}
      {model.actions?.primary ? (
        model.actions.primary.href ? (
          <a
            href={model.actions.primary.href}
            className="mt-2 inline-flex w-full items-center justify-center rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-800"
          >
            {model.actions.primary.label}
          </a>
        ) : (
          <button
            type="button"
            onClick={model.actions.primary.onClick}
            className="mt-2 w-full rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-800"
          >
            {model.actions.primary.label}
          </button>
        )
      ) : null}
      {model.onCreateTask ? (
        <button
          type="button"
          onClick={model.onCreateTask}
          className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {model.createTaskLabel ?? t('app.platform.entity_workspace.create_task')}
        </button>
      ) : null}
      {model.actions?.secondary?.length ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {model.actions.secondary.slice(0, 2).map((action) =>
            action.href ? (
              <a
                key={action.id}
                href={action.href}
                className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                {action.label}
              </a>
            ) : (
              <button
                key={action.id}
                type="button"
                onClick={action.onClick}
                className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                {action.label}
              </button>
            ),
          )}
        </div>
      ) : null}
      {model.afterActionHint ? <p className="mt-2 text-xs text-slate-500">{model.afterActionHint}</p> : null}
    </div>
  ) : null

  const quickContactsBlock = model.quickContacts?.length ? (
    <div className={nextActionBlock ? 'mt-4' : undefined}>
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        {t('app.platform.entity_workspace.quick_contacts')}
      </p>
      <div className="grid grid-cols-3 gap-2">
        {model.quickContacts.map((contact) =>
          contact.href ? (
            <a
              key={contact.id}
              href={contact.href}
              className="flex flex-col items-center gap-1 rounded-xl border border-slate-200 bg-white px-2 py-3 text-center text-[11px] font-medium text-slate-700 hover:bg-slate-50"
            >
              <ContactIcon icon={contact.icon} />
              <span className="truncate">{contact.icon === 'phone' ? t('app.platform.entity_workspace.call') : contact.icon === 'whatsapp' ? 'WA' : 'Email'}</span>
            </a>
          ) : (
            <button
              key={contact.id}
              type="button"
              onClick={contact.onClick}
              className="flex flex-col items-center gap-1 rounded-xl border border-slate-200 bg-white px-2 py-3 text-center text-[11px] font-medium text-slate-700 hover:bg-slate-50"
            >
              <ContactIcon icon={contact.icon} />
              <span className="truncate">{contact.label}</span>
            </button>
          ),
        )}
      </div>
    </div>
  ) : null

  if (nextActionBlock || quickContactsBlock) {
    blocks.next_actions = (
      <>
        {nextActionBlock}
        {quickContactsBlock}
      </>
    )
  }

  if (model.tasks?.length) {
    blocks.tasks = (
      <ul className="space-y-2 text-sm">
        {model.tasks.map((t) => (
          <li
            key={t.id}
            className={clsx(
              'flex items-start gap-3 rounded-xl border px-3 py-3',
              t.overdue ? 'border-rose-200 bg-rose-50/60' : 'border-slate-200 bg-white',
            )}
          >
            <span
              className={clsx(
                'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px]',
                t.done ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white',
              )}
              aria-hidden
            >
              {t.done ? '✓' : ''}
            </span>
            <div className="min-w-0">
              <p className="font-medium text-slate-900">{t.title}</p>
              {t.dueAt ? <p className="text-xs text-slate-500">{t.dueAt}</p> : null}
            </div>
          </li>
        ))}
      </ul>
    )
  }

  if (model.reminders?.length) {
    blocks.reminders = (
      <ul className="space-y-2 text-sm">
        {model.reminders.map((t) => (
          <li key={t.id} className="rounded-xl border border-slate-200 bg-white px-3 py-3">
            <p className="font-medium text-slate-900">{t.title}</p>
          </li>
        ))}
      </ul>
    )
  }

  if (model.processes?.length) {
    blocks.processes = (
      <ul className="space-y-2 text-sm">
        {model.processes.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3">
            <span className="font-medium text-slate-900">{p.label}</span>
            {p.statusLabel ? <span className="text-xs text-slate-500">{p.statusLabel}</span> : null}
          </li>
        ))}
      </ul>
    )
  }

  if (model.recentEvents?.length) {
    blocks.recent_events = (
      <>
        <ul className="space-y-2 text-sm">
          {model.recentEvents.map((ev) => (
            <li key={ev.id} className="rounded-xl border border-slate-200 bg-white px-3 py-3">
              <p className="font-medium text-slate-800">{ev.title}</p>
              {ev.description ? <p className="text-xs text-slate-600">{ev.description}</p> : null}
              <p className="mt-1 text-[10px] text-slate-400">{ev.at}</p>
            </li>
          ))}
        </ul>
        {model.onShowAllEvents ? (
          <button
            type="button"
            onClick={model.onShowAllEvents}
            className="mt-2 text-xs font-medium text-brand-700 hover:underline"
          >
            {t('app.platform.entity_workspace.show_full_history')}
          </button>
        ) : null}
      </>
    )
  }

  const blockTitles: Partial<Record<EntityContextRailBlockId, string | undefined>> = {
    next_actions: undefined,
    tasks: labels?.tasks,
    reminders: labels?.reminders,
    processes: labels?.processes,
    recent_events: labels?.recent_events,
  }

  const visibleBlocks = ENTITY_CONTEXT_RAIL_BLOCK_ORDER.filter((id) => blocks[id])

  if (!visibleBlocks.length) {
    return (
      <aside
        className="flex shrink-0 flex-col border-l border-slate-200 bg-white p-3 text-sm text-slate-500"
        style={{ width: widthPx, minWidth: widthPx, maxWidth: widthPx }}
        data-entity-workspace-zone="context-rail"
        data-entity-workspace-slot="context-rail"
      >
        {t('app.platform.entity_workspace.no_context')}
      </aside>
    )
  }

  return (
    <aside
      className="flex min-h-0 shrink-0 flex-col overflow-y-auto overscroll-contain border-l border-slate-200 bg-white"
      style={{ width: widthPx, minWidth: widthPx, maxWidth: widthPx }}
      data-entity-workspace-zone="context-rail"
      data-entity-workspace-slot="context-rail"
    >
      <div className="space-y-3 px-3 py-2">
        {visibleBlocks.map((blockId) => (
          <section key={blockId}>
            {blockTitles[blockId] ? (
              <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{blockTitles[blockId]}</h4>
            ) : null}
            {blocks[blockId]}
          </section>
        ))}
      </div>
    </aside>
  )
}
