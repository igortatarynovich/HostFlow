/**
 * Fixed right drawer: pipeline summary + filters.
 */

import type { Dispatch, SetStateAction } from 'react';
import clsx from 'clsx';
import type { Vacancy } from '../../api/types';
import { PipelineDrawerHeader } from './PipelineDrawerHeader';
import { PipelineSidebarFilters } from './PipelineSidebarFilters';
import { PipelineSummaryInsights } from './PipelineSummaryInsights';
import type {
  PipelineColumnFiltersState,
  PipelineColumnInsights,
} from './filterPipelineColumns';
import type { ManagerItem } from './types';

export type PipelineInspectorDrawerProps = {
  open: boolean;
  onClose: () => void;
  onSwitchToTable: () => void;
  insights: PipelineColumnInsights;
  vacancyId: string;
  onVacancyChange: (id: string) => void;
  vacancies: Vacancy[];
  filters: PipelineColumnFiltersState;
  setFilters: Dispatch<SetStateAction<PipelineColumnFiltersState>>;
  managers: ManagerItem[];
  onRefresh: () => void;
  loading: boolean;
  canManage: boolean;
};

export function PipelineInspectorDrawer({
  open,
  onClose,
  onSwitchToTable,
  insights,
  vacancyId,
  onVacancyChange,
  vacancies,
  filters,
  setFilters,
  managers,
  onRefresh,
  loading,
  canManage,
}: PipelineInspectorDrawerProps) {
  return (
    <div
      className={clsx(
        'fixed top-0 right-0 h-full w-full sm:w-96 bg-gradient-to-b from-slate-50 to-white border-l-2 border-slate-300 shadow-2xl z-40 transition-transform duration-300 ease-in-out overflow-y-auto',
        open ? 'translate-x-0' : 'translate-x-full',
      )}
    >
      <div className="p-4 space-y-4 pt-16">
        <PipelineDrawerHeader onClose={onClose} onSwitchToTable={onSwitchToTable} />

        <div className="mb-1">
          <PipelineSummaryInsights insights={insights} />
        </div>

        <PipelineSidebarFilters
          vacancyId={vacancyId}
          onVacancyChange={onVacancyChange}
          vacancies={vacancies}
          filters={filters}
          setFilters={setFilters}
          managers={managers}
          onRefresh={onRefresh}
          loading={loading}
          canManage={canManage}
        />
      </div>
    </div>
  );
}
