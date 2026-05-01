/**
 * dnd-kit column + card shells for Pipeline kanban (extracted from Pipeline.tsx).
 */

import { type CSSProperties, type MouseEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useDraggable, useDroppable } from '@dnd-kit/core';

export function DroppableColumn({
  id,
  title,
  subtitle,
  count,
  total,
  health,
  healthLabels,
  children,
  headerRight,
  viewInListHref,
  viewInListLabel,
}: {
  id: string;
  title: ReactNode;
  subtitle?: ReactNode;
  count: number;
  total?: number;
  health?: { docsNeedAttention: number; newStage: number };
  healthLabels?: { docs: string; newStage: string };
  children: ReactNode;
  headerRight?: ReactNode;
  viewInListHref?: string;
  viewInListLabel?: string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });
  const showHealth =
    health && healthLabels && (health.docsNeedAttention > 0 || health.newStage > 0);
  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 transition-colors ${isOver ? 'ring-2 ring-brand-300' : ''}`}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-800">{title}</div>
          {subtitle}
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <div className="flex items-center gap-2">
            <div className="text-[11px] text-slate-500">
              {typeof total === 'number' ? `${count} / ${total}` : count}
            </div>
            {headerRight}
          </div>
          {showHealth ? (
            <div className="flex max-w-[200px] flex-wrap justify-end gap-1">
              {health.docsNeedAttention > 0 ? (
                <span
                  className="inline-flex items-center rounded bg-amber-100 px-1 py-0.5 text-[10px] font-medium text-amber-950"
                  title={healthLabels.docs}
                >
                  ⚠ {health.docsNeedAttention} {healthLabels.docs}
                </span>
              ) : null}
              {health.newStage > 0 ? (
                <span className="inline-flex items-center rounded bg-sky-100 px-1 py-0.5 text-[10px] font-medium text-sky-950">
                  {health.newStage} {healthLabels.newStage}
                </span>
              ) : null}
            </div>
          ) : null}
          {viewInListHref && viewInListLabel && (
            <Link
              to={viewInListHref}
              className="text-[10px] text-brand-600 hover:underline whitespace-nowrap"
            >
              {viewInListLabel}
            </Link>
          )}
        </div>
      </div>
      <div className="space-y-2 min-h-[36px]">{children}</div>
    </div>
  );
}

export function DraggableCard({
  id,
  children,
  saving,
  selected,
  onToggleSelect,
  canManage,
  t,
  onContextMenu,
}: {
  id: string;
  children: React.ReactNode;
  saving: boolean;
  selected: boolean;
  onToggleSelect: () => void;
  canManage: boolean;
  t: (key: string) => string;
  onContextMenu?: (e: MouseEvent) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id,
    disabled: !canManage,
  });
  const dragProps = canManage ? { ...attributes, ...listeners } : {};
  const style: CSSProperties = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : {};
  return (
    <div
      ref={setNodeRef}
      {...dragProps}
      style={style}
      onContextMenu={onContextMenu}
      className={`rounded-lg border border-slate-200 bg-white p-2.5 ${canManage ? 'cursor-grab hover:bg-slate-50 active:cursor-grabbing' : 'cursor-default'} ${selected ? 'border-brand-400 ring-1 ring-brand-200' : ''} ${isDragging ? 'opacity-80 shadow' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div />
        {canManage && (
          <label
            className="inline-flex items-center gap-2 select-none text-xs text-slate-500"
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => {
                e.stopPropagation();
                onToggleSelect();
              }}
              onClick={(e) => {
                e.stopPropagation();
              }}
            />
            <span>{t('app.candidates.context.select')}</span>
          </label>
        )}
      </div>
      {children}
      {saving && (
        <div className="flex items-center gap-2 mt-2">
          <span className="text-xs text-slate-400">{t('app.candidates.pipeline.card_saving')}</span>
        </div>
      )}
    </div>
  );
}
