/**
 * Right-click context menu on a pipeline kanban card.
 */

import type { Ref } from 'react';
import { useI18n } from '../../i18n';
import type { AnyObj } from './types';

export type PipelineCardContextMenuPosition = { x: number; y: number; candidateId: string };

export type PipelineCardContextMenuProps = {
  menu: PipelineCardContextMenuPosition | null;
  menuRef: Ref<HTMLDivElement>;
  filteredColumns: Record<string, unknown[]>;
  canManage: boolean;
  onDismiss: () => void;
  onOpenCandidate: (candidateId: string) => void;
  onToggleSelect: (candidateId: string) => void;
  isSelected: (id: string) => boolean;
  onBeginBulkStage: (candidateId: string) => void;
  onBeginBulkManager: (candidateId: string, item: unknown) => void;
  onBeginBulkVacancy: (candidateId: string) => void;
};

function findColumnItem(
  filteredColumns: Record<string, unknown[]>,
  candidateId: string,
): unknown | undefined {
  return Object.values(filteredColumns || {})
    .flat()
    .find((c: unknown) => {
      const row = c as AnyObj;
      return String(row?.candidate?.id || row?.candidate_id) === candidateId;
    });
}

export function PipelineCardContextMenu({
  menu,
  menuRef,
  filteredColumns,
  canManage,
  onDismiss,
  onOpenCandidate,
  onToggleSelect,
  isSelected,
  onBeginBulkStage,
  onBeginBulkManager,
  onBeginBulkVacancy,
}: PipelineCardContextMenuProps) {
  const { t } = useI18n();

  if (!menu) return null;

  const candidateId = menu.candidateId;
  const item = findColumnItem(filteredColumns, candidateId);
  const showActions = Boolean(item && canManage);

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={onDismiss}
        onContextMenu={(e) => {
          e.preventDefault();
          onDismiss();
        }}
      />
      <div
        ref={menuRef}
        className="fixed z-50 w-56 rounded-lg border border-slate-200 bg-white p-2 shadow-xl"
        style={{ left: menu.x, top: menu.y }}
        onClick={(e) => e.stopPropagation()}
      >
        {showActions ? (
          <div className="space-y-1">
            <button
              type="button"
              className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
              onClick={() => onOpenCandidate(candidateId)}
            >
              {t('app.candidates.context.open_card')}
            </button>
            <button
              type="button"
              className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
              onClick={() => onToggleSelect(candidateId)}
            >
              {isSelected(candidateId)
                ? t('app.candidates.context.deselect')
                : t('app.candidates.context.select')}
            </button>
            <div className="border-t border-slate-200 my-1" />
            <button
              type="button"
              className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
              onClick={() => onBeginBulkStage(candidateId)}
            >
              {t('app.candidates.context.change_stage')}
            </button>
            <button
              type="button"
              className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
              onClick={() => onBeginBulkManager(candidateId, item)}
            >
              {t('app.candidates.context.assign_manager')}
            </button>
            <button
              type="button"
              className="btn-secondary w-full text-left text-xs py-1.5 px-2 hover:bg-slate-100"
              onClick={() => onBeginBulkVacancy(candidateId)}
            >
              {t('app.candidates.context.assign_vacancy')}
            </button>
          </div>
        ) : null}
      </div>
    </>
  );
}
