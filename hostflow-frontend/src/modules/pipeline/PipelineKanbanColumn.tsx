/**
 * Single kanban column: droppable shell, stage tags, cards, empty state.
 */

import type { MutableRefObject } from 'react';
import StageTag from '../../components/StageTag';
import { useI18n } from '../../i18n';
import type { Vacancy } from '../../api/types';
import { DroppableColumn, DraggableCard } from './PipelineDndPrimitives';
import { PipelineColumnEmptyState } from './PipelineColumnEmptyState';
import { PipelineKanbanCardBody } from './PipelineKanbanCardBody';
import type { ManagerItem } from './types';
import { normalizeStageCode, summarizePipelineColumnHealth } from './utils';

export type DragRegistryEntry = { candidateId: string; fromColumn: string; stage?: string };

export type PipelineKanbanColumnProps = {
  code: string;
  columnStages: Record<string, string[]>;
  colItems: unknown[];
  totalUnfilteredCount: number;
  viewInListHref: string;
  canManage: boolean;
  selectedIds: string[];
  onToggleAllInColumn: (colIds: string[], select: boolean) => void;
  dragRegistry: MutableRefObject<Record<string, DragRegistryEntry>>;
  savingIds: Record<string, boolean>;
  isSelected: (id: string) => boolean;
  onToggleSelected: (id: string) => void;
  onCardContextMenu: (clientX: number, clientY: number, candidateId: string) => void;
  managers: ManagerItem[];
  vacancies: Vacancy[];
  vacancyId: string;
  canViewTasks: boolean;
  shouldSuppressLinkClick: (id: string) => boolean;
};

export function PipelineKanbanColumn({
  code,
  columnStages,
  colItems,
  totalUnfilteredCount,
  viewInListHref,
  canManage,
  selectedIds,
  onToggleAllInColumn,
  dragRegistry,
  savingIds,
  isSelected,
  onToggleSelected,
  onCardContextMenu,
  managers,
  vacancies,
  vacancyId,
  canViewTasks,
  shouldSuppressLinkClick,
}: PipelineKanbanColumnProps) {
  const { t } = useI18n();
  const colHealth = summarizePipelineColumnHealth(colItems);

  const subtitle = (() => {
    const stages = (columnStages?.[code] || []).filter(Boolean);
    if (stages.length <= 1) return null;
    return (
      <div className="mt-1 flex flex-wrap gap-1">
        {stages.map((stageCode) => (
          <StageTag key={`${code}:${stageCode}`} code={stageCode} />
        ))}
      </div>
    );
  })();

  const headerRight = canManage
    ? (() => {
        const colIds = colItems.map((it: unknown) => {
          const row = it as { candidate?: { id?: string }; candidate_id?: string };
          return String(row.candidate?.id || row.candidate_id);
        });
        const selectedInCol = colIds.filter((cid: string) => selectedIds.includes(cid)).length;
        const allInColSelected = colIds.length > 0 && selectedInCol === colIds.length;
        const someSelected = selectedInCol > 0 && !allInColSelected;
        return (
          <label className="inline-flex items-center gap-1 text-xs select-none">
            <input
              type="checkbox"
              checked={allInColSelected}
              ref={(el) => {
                if (el) el.indeterminate = someSelected;
              }}
              onChange={() => onToggleAllInColumn(colIds, !allInColSelected)}
            />
            <span>{t('app.candidates.pipeline.column_select_all')}</span>
          </label>
        );
      })()
    : null;

  return (
    <DroppableColumn
      id={code}
      title={<StageTag code={code} />}
      subtitle={subtitle}
      count={colItems.length}
      total={totalUnfilteredCount}
      health={colHealth}
      healthLabels={{
        docs: t('app.candidates.pipeline.column_health_docs', { defaultValue: 'Docs' }),
        newStage: t('app.candidates.pipeline.column_health_new', { defaultValue: 'New' }),
      }}
      viewInListHref={viewInListHref}
      viewInListLabel={t('app.candidates.pipeline.view_in_list', { defaultValue: 'In list' })}
      headerRight={headerRight}
    >
      {colItems.map((item: unknown) => {
        const row = item as {
          candidate?: { id?: string; stage?: string };
          candidate_id?: string;
          stage?: string;
          status?: string;
        };
        const candidateId = String(row.candidate?.id || row.candidate_id);
        const dragId = `card:${candidateId}`;
        const rawStage =
          row.stage ?? row.status ?? row.candidate?.stage ?? row.candidate?.status;
        const itemStage = normalizeStageCode(rawStage);
        dragRegistry.current[dragId] = { candidateId, fromColumn: code, stage: itemStage };
        const selected = isSelected(candidateId);
        return (
          <DraggableCard
            key={dragId}
            id={dragId}
            saving={!!savingIds[candidateId]}
            selected={selected}
            onToggleSelect={() => onToggleSelected(candidateId)}
            canManage={canManage}
            t={t}
            onContextMenu={(e) => {
              if (canManage) {
                e.preventDefault();
                e.stopPropagation();
                onCardContextMenu(e.clientX, e.clientY, candidateId);
              }
            }}
          >
            <PipelineKanbanCardBody
              item={item}
              candidateId={candidateId}
              managers={managers}
              vacancyId={vacancyId}
              vacancies={vacancies}
              canViewTasks={canViewTasks}
              shouldSuppressLinkClick={shouldSuppressLinkClick}
            />
          </DraggableCard>
        );
      })}
      {colItems.length === 0 && <PipelineColumnEmptyState viewInListHref={viewInListHref} />}
    </DroppableColumn>
  );
}
