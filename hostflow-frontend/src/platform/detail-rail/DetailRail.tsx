import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconBrandWhatsapp, IconChevronDown, IconChevronUp, IconMail, IconPhone, IconPin, IconPinFilled, IconX } from '@tabler/icons-react'
import type { DetailRailBlockId, DetailRailContactAction, DetailRailProps } from './detailRailTypes'
import {
  DETAIL_RAIL_BLOCK_ORDER,
  DEFAULT_DETAIL_RAIL_WIDTH_PX,
  isDetailRailFixedBlock,
} from './detailRailTypes'
import { ContextRailDecisionZone } from '../context-rail/ContextRailDecisionZone'
import { SemanticBadge } from '../data-table/SemanticBadge'
import { useI18n } from '../../i18n'

function ContactIcon({
  kind,
  variant,
}: {
  kind: DetailRailContactAction['icon']
  variant?: DetailRailContactAction['variant']
}) {
  if (kind === 'phone') return <IconPhone size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
  if (kind === 'whatsapp') return <IconBrandWhatsapp size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
  return <IconMail size={14} stroke={1.8} className={variant === 'primary' ? 'text-white' : undefined} />
}

function BlockSection({
  title,
  children,
  className,
}: {
  title?: string
  children: ReactNode
  className?: string
}) {
  if (!children) return null
  return (
    <section className={clsx('border-b border-slate-100 px-4 py-3', className)}>
      {title ? <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{title}</h4> : null}
      {children}
    </section>
  )
}

function ActionButton({ action, size }: { action: { id: string; label: string; onClick?: () => void; href?: string }; size: 'primary' | 'secondary' | 'link' }) {
  const cls =
    size === 'primary'
      ? 'w-full justify-center rounded-lg bg-brand-700 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800'
      : size === 'secondary'
        ? 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50'
        : 'text-sm text-brand-700 hover:underline'
  const inner = action.label
  if (action.href) {
    return (
      <a key={action.id} href={action.href} className={clsx('inline-flex items-center', cls)}>
        {inner}
      </a>
    )
  }
  return (
    <button key={action.id} type="button" onClick={action.onClick} className={clsx('inline-flex items-center', cls)}>
      {inner}
    </button>
  )
}

/**
 * Universal Detail Rail — independent primitive; opened via Selection Model, not owned by DataTable.
 */
export function DetailRail({
  open,
  model,
  loading = false,
  onClose,
  widthPx = DEFAULT_DETAIL_RAIL_WIDTH_PX,
  navigation,
  pin,
  blockOverrides,
  emptyTitle = 'Select a row',
  emptyDescription = 'Click a row to open the panel for quick decisions.',
}: DetailRailProps) {
  const { t } = useI18n()
  if (!open) return null

  const blocks: Partial<Record<DetailRailBlockId, React.ReactNode>> = {}

  if (model?.header) {
    const h = model.header
    blocks.header = (
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-1">
            {navigation ? (
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  disabled={!navigation.hasPrevious}
                  onClick={navigation.onPrevious}
                  className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                  aria-label={navigation.previousLabel ?? 'Предыдущий'}
                  title={navigation.previousLabel ?? 'Предыдущий'}
                >
                  <IconChevronUp size={18} />
                </button>
                <button
                  type="button"
                  disabled={!navigation.hasNext}
                  onClick={navigation.onNext}
                  className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
                  aria-label={navigation.nextLabel ?? 'Следующий'}
                  title={navigation.nextLabel ?? 'Следующий'}
                >
                  <IconChevronDown size={18} />
                </button>
              </div>
            ) : null}
            {pin ? (
              <button
                type="button"
                onClick={pin.onTogglePin}
                className={clsx(
                  'rounded-lg p-2 transition-colors',
                  pin.pinned ? 'bg-amber-100 text-amber-800' : 'text-slate-500 hover:bg-slate-100',
                )}
                aria-pressed={pin.pinned}
                title={pin.pinned ? pin.unpinLabel ?? 'Открепить' : pin.pinLabel ?? 'Закрепить'}
              >
                {pin.pinned ? <IconPinFilled size={18} /> : <IconPin size={18} />}
              </button>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Закрыть"
          >
            <IconX size={18} stroke={2} />
          </button>
        </div>
        <div className="min-w-0">
          {h.titleHref ? (
            <Link
              to={h.titleHref}
              className="text-lg font-bold text-brand-700 hover:text-brand-800 hover:underline"
              data-entity-link="primary"
            >
              {h.title}
            </Link>
          ) : (
            <h2 className="text-lg font-bold text-slate-900">{h.title}</h2>
          )}
          {h.subtitle ? <p className="mt-0.5 text-sm text-slate-500">{h.subtitle}</p> : null}
          {h.meta ? <p className="mt-1 text-xs text-slate-400">{h.meta}</p> : null}
          {h.entityWorkspaceHref ? (
            <Link
              to={h.entityWorkspaceHref}
              className="mt-2 inline-flex text-sm font-medium text-brand-700 hover:underline"
              data-entity-link="primary"
            >
              {h.entityWorkspaceLabel ?? 'Открыть полную карточку'}
            </Link>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2">
            {h.statusLabel ? (
              <SemanticBadge label={h.statusLabel} semanticRole={h.statusSemantic ?? 'status'} size="sm" />
            ) : null}
            {h.stageLabel ? (
              <SemanticBadge label={h.stageLabel} semanticRole={h.stageSemantic ?? 'process_stage'} size="sm" />
            ) : null}
            {h.entityId ? <span className="text-xs text-slate-400">{h.entityId}</span> : null}
          </div>
        </div>
      </div>
    )
  }

  if (model?.contacts) {
    const c = model.contacts
    blocks.contacts = (
      <div className={c.compact ? undefined : 'space-y-2'}>
        {!c.compact ? (
          <>
            {c.name ? <p className="font-medium text-slate-900">{c.name}</p> : null}
            {c.phone ? <p className="text-sm text-slate-600">{c.phone}</p> : null}
            {c.email ? <p className="text-sm text-slate-600">{c.email}</p> : null}
          </>
        ) : null}
        {c.actions?.length ? (
          <div className={clsx('flex flex-wrap gap-2', !c.compact && 'pt-1')}>
            {c.actions.map((action) => {
              const cls =
                action.variant === 'primary'
                  ? 'bg-brand-700 text-white hover:bg-brand-800'
                  : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              const inner = (
                <>
                  <ContactIcon kind={action.icon} variant={action.variant} />
                  {action.label}
                </>
              )
              if (action.href) {
                return (
                  <a key={action.id} href={action.href} className={clsx('inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium', cls)}>
                    {inner}
                  </a>
                )
              }
              return (
                <button key={action.id} type="button" onClick={action.onClick} className={clsx('inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium', cls)}>
                  {inner}
                </button>
              )
            })}
          </div>
        ) : null}
      </div>
    )
  }

  if (model?.nextAction) {
    const n = model.nextAction
    const variant = n.variant ?? 'default'
    blocks.next_action = (
      <div
        className={clsx(
          'rounded-xl border p-4',
          variant === 'terminal' && 'border-slate-200 bg-slate-100/80',
          variant === 'blocker' && 'border-amber-200 bg-amber-50/60',
          variant === 'success' && 'border-emerald-200 bg-emerald-50/50',
          variant === 'default' && 'border-brand-200 bg-brand-50/50',
        )}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          Следующее действие
        </p>
        {!n.hideStepper && n.stepLabels?.length ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {n.stepLabels.map((label, i) => (
              <span
                key={label}
                className={clsx(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium',
                  i === (n.activeStepIndex ?? 0) ? 'bg-brand-700 text-white' : 'bg-white text-slate-500 ring-1 ring-slate-200',
                )}
              >
                {i + 1} {label}
              </span>
            ))}
          </div>
        ) : null}
        <p className="mt-3 text-base font-bold leading-tight text-slate-900">{n.title}</p>
        {n.body ? <p className="mt-2 text-sm text-slate-600">{n.body}</p> : null}
        {n.whyBody ? (
          <div className="mt-3 border-l-2 border-slate-300 pl-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              {n.whyTitle ?? 'Почему'}
            </p>
            <p className="mt-0.5 text-sm text-slate-700">{n.whyBody}</p>
          </div>
        ) : null}
        {n.primaryAction ? (
          <button
            type="button"
            onClick={n.primaryAction.onClick}
            className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-brand-700 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-800"
          >
            {n.primaryAction.label}
          </button>
        ) : null}
        {n.outcomeBody ? (
          <div className="mt-3 rounded-lg bg-white/70 px-3 py-2 ring-1 ring-slate-200/80">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              {n.outcomeTitle ?? 'Что будет дальше'}
            </p>
            <p className="mt-0.5 text-xs text-slate-600">{n.outcomeBody}</p>
          </div>
        ) : null}
      </div>
    )
  }

  if (model?.processOutcome) {
    const o = model.processOutcome
    const variant = o.variant ?? 'success'
    blocks.outcome = (
      <div
        className={clsx(
          'rounded-xl border p-4',
          variant === 'terminal' && 'border-slate-200 bg-slate-100/80',
          variant === 'success' && 'border-emerald-200 bg-emerald-50/50',
          variant === 'default' && 'border-brand-200 bg-brand-50/50',
        )}
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t('app.platform.detail_rail.process_outcome')}
        </p>
        <p className="mt-3 text-base font-bold leading-tight text-slate-900">{o.title}</p>
        {o.body ? <p className="mt-2 text-sm text-slate-600">{o.body}</p> : null}
        {o.whyLabel ? (
          <div className="mt-3 border-l-2 border-slate-300 pl-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              {t('app.platform.context_rail.why')}
            </p>
            <p className="mt-0.5 text-sm text-slate-700">{o.whyLabel}</p>
          </div>
        ) : null}
        <dl className="mt-3 space-y-1.5 text-sm">
          {o.ownerLabel ? (
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">{t('app.platform.detail_rail.owner')}</dt>
              <dd className="text-right font-medium text-slate-900">{o.ownerLabel}</dd>
            </div>
          ) : null}
          {o.whenLabel ? (
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">{t('app.platform.detail_rail.when')}</dt>
              <dd className="text-right font-medium text-slate-900">{o.whenLabel}</dd>
            </div>
          ) : null}
        </dl>
      </div>
    )
  }

  const actionsTier = model?.actions
  const legacySecondary = model?.quickActions ?? []
  const legacyMore = model?.moreActions ?? []
  const primary = actionsTier?.primary
  const secondary = actionsTier?.secondary ?? legacySecondary
  const more = actionsTier?.more ?? legacyMore

  if (primary || secondary.length || more.length) {
    blocks.actions = (
      <div className="space-y-3">
        {primary ? <ActionButton action={primary} size="primary" /> : null}
        {secondary.length ? (
          <div className="flex flex-wrap gap-2">
            {secondary.map((a) => (
              <ActionButton key={a.id} action={a} size="secondary" />
            ))}
          </div>
        ) : null}
        {more.length ? (
          <details className="group">
            <summary className="cursor-pointer text-xs font-medium text-slate-600 hover:text-slate-900">
              {t('app.platform.detail_rail.more_actions', { values: { count: more.length } })}
            </summary>
            <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
              {more.map((a) => (
                <li key={a.id}>
                  <ActionButton action={a} size="link" />
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>
    )
  }

  if (model?.summaryFields?.length) {
    blocks.summary = (
      <dl className="space-y-1.5 text-sm">
        {model.summaryFields.map((f) => (
          <div key={f.id} className="flex justify-between gap-3">
            <dt className="text-slate-500">{f.label}</dt>
            <dd className="text-right font-medium text-slate-900">{f.value}</dd>
          </div>
        ))}
        {model.onSummaryExpand ? (
          <button type="button" onClick={model.onSummaryExpand} className="mt-1 text-xs font-medium text-brand-700 hover:underline">
            {model.summaryExpandLabel ?? 'Показать все'}
          </button>
        ) : null}
      </dl>
    )
  }

  if (model?.timeline?.length) {
    blocks.history = (
      <ul className="space-y-2 text-sm">
        {model.timeline.map((item) => (
          <li key={item.id} className="border-l-2 border-slate-200 pl-3">
            <p className="font-medium text-slate-800">{item.title}</p>
            {item.description ? <p className="text-xs text-slate-500">{item.description}</p> : null}
            <p className="text-[10px] text-slate-400">{item.at}</p>
          </li>
        ))}
      </ul>
    )
  }

  if (model?.documents?.length) {
    blocks.documents = (
      <ul className="space-y-1.5 text-sm">
        {model.documents.map((doc) => (
          <li key={doc.id}>
            {doc.href ? (
              <a href={doc.href} className="font-medium text-brand-700 hover:underline">
                {doc.name}
              </a>
            ) : (
              <button type="button" onClick={doc.onOpen} className="font-medium text-brand-700 hover:underline">
                {doc.name}
              </button>
            )}
            {doc.meta ? <p className="text-xs text-slate-400">{doc.meta}</p> : null}
          </li>
        ))}
      </ul>
    )
  }

  if (model?.relations?.length) {
    blocks.relations = (
      <ul className="space-y-1 text-sm">
        {model.relations.map((rel) => (
          <li key={rel.id}>
            {rel.href ? (
              <a href={rel.href} className="text-brand-700 hover:underline">
                {rel.label}
              </a>
            ) : (
              <button type="button" onClick={rel.onClick} className="text-brand-700 hover:underline">
                {rel.label}
              </button>
            )}
          </li>
        ))}
      </ul>
    )
  }

  if (model?.footerActions?.length) {
    blocks.footer_actions = (
      <ul className="space-y-1 text-sm">
        {model.footerActions.map((a) => (
          <li key={a.id}>
            <ActionButton action={a} size="link" />
          </li>
        ))}
      </ul>
    )
  }

  const blockTitles: Partial<Record<DetailRailBlockId, string>> = {
    contacts: 'Контакты',
    next_action: undefined,
    actions: 'Действия',
    summary: 'Основная информация',
    history: 'История',
    documents: 'Документы',
    relations: 'Связанные объекты',
    footer_actions: 'Другие действия',
  }

  const merged = { ...blocks, ...blockOverrides }
  const blockOrder = model?.blockOrder ?? DETAIL_RAIL_BLOCK_ORDER
  const usesDecision = Boolean(model?.decision)

  const fixedBlockIds = usesDecision
    ? blockOrder.filter((id) => id === 'header' && merged[id])
    : blockOrder.filter((id) => isDetailRailFixedBlock(id) && merged[id])

  const scrollBlockIds = usesDecision
    ? blockOrder.filter((id) => id !== 'header' && merged[id])
    : blockOrder.filter((id) => !isDetailRailFixedBlock(id) && merged[id])

  const renderBlock = (blockId: DetailRailBlockId) => {
    const content = merged[blockId]
    if (!content) return null
    if (blockId === 'header') {
      return (
        <div key={blockId} className="shrink-0 border-b border-slate-100 px-4 py-3">
          {content}
        </div>
      )
    }
    if (blockId === 'next_action' || blockId === 'outcome') {
      return (
        <div key={blockId} className="shrink-0 border-b border-slate-100 px-4 py-4">
          {content}
        </div>
      )
    }
    if (blockId === 'contacts' || blockId === 'actions') {
      return (
        <div key={blockId} className="shrink-0 border-b border-slate-100 px-4 py-3">
          {content}
        </div>
      )
    }
    return (
      <BlockSection key={blockId} title={blockTitles[blockId]}>
        {content}
      </BlockSection>
    )
  }

  return (
    <aside
      className="flex h-full min-h-0 shrink-0 flex-col overflow-hidden border-l border-slate-200 bg-slate-50 shadow-[inset_1px_0_0_rgb(226_232_240)]"
      style={{ width: widthPx, minWidth: widthPx, maxWidth: widthPx }}
      data-detail-rail="v1"
      data-detail-rail-readonly="true"
      data-resource-id={model?.resourceId}
    >
      {loading ? (
        <div className="flex flex-1 items-center justify-center p-6 text-sm text-slate-500">{t('common.loading')}</div>
      ) : !model ? (
        <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
          <p className="text-sm font-medium text-slate-700">{emptyTitle}</p>
          <p className="mt-1 text-xs text-slate-500">{emptyDescription}</p>
        </div>
      ) : (
        <>
          <div className="shrink-0">
            {fixedBlockIds.map((blockId) => renderBlock(blockId))}
            {model?.decision ? (
              <div className="shrink-0 border-b border-slate-100 px-4 py-4" data-context-rail-zone="decision">
                <ContextRailDecisionZone decision={model.decision} />
              </div>
            ) : null}
          </div>
          {scrollBlockIds.length ? (
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain" data-context-rail-zone="scroll">
              {scrollBlockIds.map((blockId) => renderBlock(blockId))}
            </div>
          ) : null}
        </>
      )}
    </aside>
  )
}
