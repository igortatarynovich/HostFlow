/**
 * Vacancy + search + secondary filters in Pipeline right drawer.
 */

import type { Dispatch, SetStateAction } from 'react';
import { Link } from 'react-router-dom';
import type { Vacancy } from '../../api/types';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import { useI18n } from '../../i18n';
import type { ManagerItem } from './types';
import type { PipelineColumnFiltersState } from './filterPipelineColumns';

export type PipelineSidebarFiltersProps = {
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

export function PipelineSidebarFilters({
  vacancyId,
  onVacancyChange,
  vacancies,
  filters,
  setFilters,
  managers,
  onRefresh,
  loading,
  canManage,
}: PipelineSidebarFiltersProps) {
  const { t } = useI18n();

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="pipeline-vacancy">
            {t('app.candidates.pipeline.vacancy_label')}
          </label>
          <select
            id="pipeline-vacancy"
            className="input w-full text-sm"
            value={vacancyId}
            onChange={(e) => onVacancyChange(e.target.value)}
          >
            {vacancies.map((v) => (
              <option key={v.id} value={v.id}>
                {(v as { title?: string }).title || t('app.candidates.pipeline.vacancy_untitled')}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-600 mb-1.5" htmlFor="pipeline-search">
            {t('app.candidates.search.label')}
          </label>
          <input
            id="pipeline-search"
            className="input w-full text-sm py-2 px-3 border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            placeholder={t('app.candidates.search.placeholder')}
          />
          <p className="mt-1.5 text-[10px] text-slate-400 leading-relaxed">{t('app.candidates.search.hint')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
          <button
            type="button"
            className="btn-secondary text-xs py-1.5 px-2"
            onClick={() => onRefresh()}
            disabled={loading || !vacancyId}
            title={t('app.candidates.actions.refresh_title')}
          >
            {loading ? t('app.candidates.actions.refreshing') : t('app.candidates.actions.refresh')}
          </button>
          {canManage && (
            <Link
              className="btn-primary text-xs py-1.5 px-2.5 font-medium"
              to={CRM_APP_PATHS.candidateNew}
              title={t('app.candidates.actions.new_candidate_title')}
            >
              {t('app.candidates.actions.new_candidate')}
            </Link>
          )}
        </div>
      </div>

      <div className="pt-2.5 border-t border-slate-200 space-y-3">
        <h3 className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wide">
          {t('app.candidates.filters.menu_label')}
        </h3>

        <div>
          <div className="label text-xs">{t('app.candidates.pipeline.manager_label')}</div>
          <select
            className="input text-sm"
            value={filters.manager}
            onChange={(e) => setFilters((f) => ({ ...f, manager: e.target.value }))}
          >
            <option value="">{t('app.candidates.pipeline.manager_any')}</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="label text-xs">{t('app.candidates.pipeline.citizenship_label')}</div>
          <input
            className="input text-sm w-full"
            placeholder={t('app.candidates.pipeline.citizenship_placeholder')}
            value={filters.citizenship}
            onChange={(e) => setFilters((f) => ({ ...f, citizenship: e.target.value.toUpperCase() }))}
          />
        </div>

        <div>
          <div className="label text-xs">{t('app.candidates.pipeline.docs_label')}</div>
          <select
            className="input text-sm"
            value={filters.docs}
            onChange={(e) => setFilters((f) => ({ ...f, docs: e.target.value }))}
          >
            <option value="">{t('app.candidates.pipeline.docs_any')}</option>
            <option value="yes">{t('app.candidates.pipeline.docs_ready')}</option>
            <option value="partial">{t('app.candidates.pipeline.docs_partial')}</option>
            <option value="no">{t('app.candidates.pipeline.docs_none')}</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <div className="label text-xs">{t('app.candidates.pipeline.date_from_label')}</div>
            <input
              type="date"
              className="input text-sm"
              value={filters.from}
              onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value }))}
            />
          </div>
          <div>
            <div className="label text-xs">{t('app.candidates.pipeline.date_to_label')}</div>
            <input
              type="date"
              className="input text-sm"
              value={filters.to}
              onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value }))}
            />
          </div>
        </div>

        <button
          type="button"
          className="btn-secondary w-full text-xs py-1.5"
          onClick={() =>
            setFilters({ search: '', manager: '', citizenship: '', docs: '', from: '', to: '' })
          }
        >
          {t('app.candidates.pipeline.reset_filters')}
        </button>
      </div>
    </section>
  );
}
