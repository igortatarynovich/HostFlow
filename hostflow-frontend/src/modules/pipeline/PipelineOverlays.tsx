/**
 * Pipeline page overlays: card context menu + bulk modals.
 */

import type { RefObject } from 'react';
import type { MetaStages } from '../../api/types';
import type { Vacancy } from '../../api/types';
import {
  BulkManagerModal,
  BulkStageModal,
  BulkVacancyModal,
} from '../candidates/components';
import { PipelineCardContextMenu } from './PipelineCardContextMenu';
import type { PipelineCardContextMenuPosition } from './PipelineCardContextMenu';
import type { ManagerItem } from './types';

export type PipelineOverlaysProps = {
  contextMenu: PipelineCardContextMenuPosition | null;
  contextMenuRef: RefObject<HTMLDivElement | null>;
  filteredColumns: Record<string, unknown[]>;
  canManage: boolean;
  onDismissContextMenu: () => void;
  onOpenCandidateFromMenu: (candidateId: string) => void;
  onToggleSelectFromMenu: (candidateId: string) => void;
  isSelected: (id: string) => boolean;
  onBeginBulkStageFromMenu: (candidateId: string) => void;
  onBeginBulkManagerFromMenu: (candidateId: string, item: unknown) => void;
  onBeginBulkVacancyFromMenu: (candidateId: string) => void;

  bulkStageOpen: boolean;
  onBulkStageClose: () => void;
  stageOptions: string[];
  bulkStage: string;
  bulkReasons: string[];
  onBulkStageChange: (stage: string) => void;
  onBulkReasonsChange: (reasons: string[]) => void;
  onBulkStageApply: () => void;
  bulkStageLoading: boolean;
  meta: MetaStages | null | undefined;

  bulkManagerOpen: boolean;
  onBulkManagerClose: () => void;
  managers: ManagerItem[];
  bulkManagerId: string;
  onBulkManagerIdChange: (id: string) => void;
  onBulkManagerApply: () => void;
  bulkManagerLoading: boolean;

  bulkVacancyOpen: boolean;
  onBulkVacancyClose: () => void;
  vacancies: Vacancy[];
  bulkVacancyId: string;
  onBulkVacancyIdChange: (id: string) => void;
  onBulkVacancyApply: () => void;
  bulkVacancyLoading: boolean;
};

export function PipelineOverlays({
  contextMenu,
  contextMenuRef,
  filteredColumns,
  canManage,
  onDismissContextMenu,
  onOpenCandidateFromMenu,
  onToggleSelectFromMenu,
  isSelected,
  onBeginBulkStageFromMenu,
  onBeginBulkManagerFromMenu,
  onBeginBulkVacancyFromMenu,
  bulkStageOpen,
  onBulkStageClose,
  stageOptions,
  bulkStage,
  bulkReasons,
  onBulkStageChange,
  onBulkReasonsChange,
  onBulkStageApply,
  bulkStageLoading,
  meta,
  bulkManagerOpen,
  onBulkManagerClose,
  managers,
  bulkManagerId,
  onBulkManagerIdChange,
  onBulkManagerApply,
  bulkManagerLoading,
  bulkVacancyOpen,
  onBulkVacancyClose,
  vacancies,
  bulkVacancyId,
  onBulkVacancyIdChange,
  onBulkVacancyApply,
  bulkVacancyLoading,
}: PipelineOverlaysProps) {
  return (
    <>
      <PipelineCardContextMenu
        menu={contextMenu}
        menuRef={contextMenuRef}
        filteredColumns={filteredColumns}
        canManage={canManage}
        onDismiss={onDismissContextMenu}
        onOpenCandidate={onOpenCandidateFromMenu}
        onToggleSelect={onToggleSelectFromMenu}
        isSelected={isSelected}
        onBeginBulkStage={onBeginBulkStageFromMenu}
        onBeginBulkManager={onBeginBulkManagerFromMenu}
        onBeginBulkVacancy={onBeginBulkVacancyFromMenu}
      />

      <BulkStageModal
        open={bulkStageOpen}
        onClose={onBulkStageClose}
        stageOptions={stageOptions}
        bulkStage={bulkStage}
        bulkReasons={bulkReasons}
        onStageChange={onBulkStageChange}
        onReasonsChange={onBulkReasonsChange}
        onApply={onBulkStageApply}
        loading={bulkStageLoading}
        meta={meta}
        canManage={canManage}
      />

      <BulkManagerModal
        open={bulkManagerOpen}
        onClose={onBulkManagerClose}
        managers={managers}
        bulkManagerId={bulkManagerId}
        onManagerIdChange={onBulkManagerIdChange}
        onApply={onBulkManagerApply}
        loading={bulkManagerLoading}
        canManage={canManage}
      />

      <BulkVacancyModal
        open={bulkVacancyOpen}
        onClose={onBulkVacancyClose}
        vacancies={vacancies}
        bulkVacancyId={bulkVacancyId}
        onVacancyIdChange={onBulkVacancyIdChange}
        onApply={onBulkVacancyApply}
        loading={bulkVacancyLoading}
        canManage={canManage}
      />
    </>
  );
}
