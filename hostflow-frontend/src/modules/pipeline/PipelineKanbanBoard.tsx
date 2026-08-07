/**
 * Kanban board shell: dnd-kit context + horizontal column strip.
 */

import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import type { MutableRefObject } from 'react';
import type { PipelineOut, Vacancy } from '../../api/types';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import { PipelineKanbanColumn, type DragRegistryEntry } from './PipelineKanbanColumn';
import type { ManagerItem } from './types';

export type PipelineKanbanBoardProps = {
  canManage: boolean;
  onDragStart: (e: DragStartEvent) => void;
  onDragEnd: (e: DragEndEvent) => void;
  columnsOrder: string[];
  resolveColumnStage: (code: string) => string;
  vacancyId: string;
  filteredColumns: Record<string, unknown[]> | undefined;
  data: PipelineOut | null;
  columnStages: Record<string, string[]>;
  /** Vacancy funnel SoT labels from profile_stages.stage_labels */
  stageLabels?: Record<string, Record<string, string>> | null;
  selectedIds: string[];
  onToggleAllInColumn: (colIds: string[], select: boolean) => void;
  dragRegistry: MutableRefObject<Record<string, DragRegistryEntry>>;
  savingIds: Record<string, boolean>;
  isSelected: (id: string) => boolean;
  onToggleSelected: (id: string) => void;
  onCardContextMenu: (clientX: number, clientY: number, candidateId: string) => void;
  managers: ManagerItem[];
  vacancies: Vacancy[];
  canViewTasks: boolean;
  shouldSuppressLinkClick: (id: string) => boolean;
};

export function PipelineKanbanBoard({
  canManage,
  onDragStart,
  onDragEnd,
  columnsOrder,
  resolveColumnStage,
  vacancyId,
  filteredColumns,
  data,
  columnStages,
  stageLabels,
  selectedIds,
  onToggleAllInColumn,
  dragRegistry,
  savingIds,
  isSelected,
  onToggleSelected,
  onCardContextMenu,
  managers,
  vacancies,
  canViewTasks,
  shouldSuppressLinkClick,
}: PipelineKanbanBoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  return (
    <DndContext
      sensors={canManage ? sensors : undefined}
      collisionDetection={closestCenter}
      onDragStart={canManage ? onDragStart : undefined}
      onDragEnd={canManage ? onDragEnd : undefined}
    >
      <div className="grid grid-flow-col auto-cols-[280px] gap-3 overflow-x-auto pb-2">
        {(columnsOrder || []).map((code) => {
          const stageForFilter = resolveColumnStage(code);
          const viewInListParams = new URLSearchParams();
          if (stageForFilter) viewInListParams.set('stage', stageForFilter);
          if (vacancyId) viewInListParams.set('vacancy_id', vacancyId);
          const viewInListHref = viewInListParams.toString()
            ? `${CRM_APP_PATHS.candidates}?${viewInListParams.toString()}`
            : CRM_APP_PATHS.candidates;
          const colItems = filteredColumns?.[code] || [];
          return (
            <PipelineKanbanColumn
              key={code}
              code={code}
              columnStages={columnStages}
              stageLabels={stageLabels}
              colItems={colItems}
              totalUnfilteredCount={data?.columns?.[code]?.length || 0}
              viewInListHref={viewInListHref}
              canManage={canManage}
              selectedIds={selectedIds}
              onToggleAllInColumn={onToggleAllInColumn}
              dragRegistry={dragRegistry}
              savingIds={savingIds}
              isSelected={isSelected}
              onToggleSelected={onToggleSelected}
              onCardContextMenu={onCardContextMenu}
              managers={managers}
              vacancies={vacancies}
              vacancyId={vacancyId}
              canViewTasks={canViewTasks}
              shouldSuppressLinkClick={shouldSuppressLinkClick}
            />
          );
        })}
      </div>
    </DndContext>
  );
}
