/**
 * Bulk stage / manager actions when one or more pipeline cards are selected.
 */

import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n';
import { CRM_APP_PATHS } from '../../app/crmAppPaths';
import type { ManagerItem } from './types';

export type PipelineBulkSelectionBarProps = {
  selectedCount: number;
  columnsOrder: string[];
  managers: ManagerItem[];
  onMoveStage: (stageCode: string) => void;
  onAssignManager: (managerId: string) => void;
  onClearSelection: () => void;
  onArchive: () => void;
  planTierLoading: boolean;
  allowsTeamFeatures: boolean;
  canViewSettings: boolean;
};

export function PipelineBulkSelectionBar({
  selectedCount,
  columnsOrder,
  managers,
  onMoveStage,
  onAssignManager,
  onClearSelection,
  onArchive,
  planTierLoading,
  allowsTeamFeatures,
  canViewSettings,
}: PipelineBulkSelectionBarProps) {
  const { t } = useI18n();

  return (
    <div className="card space-y-2 p-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-sm">
          {t('app.candidates.pipeline.bulk_selected', { values: { count: selectedCount } })}
        </div>
        <div className="flex items-center gap-2">
          <label className="label m-0">{t('app.candidates.pipeline.bulk_move_stage_label')}</label>
          <select
            className="input"
            onChange={(e) => {
              const v = e.target.value;
              if (v) onMoveStage(v);
              e.currentTarget.selectedIndex = 0;
            }}
          >
            <option value="">{t('app.candidates.pipeline.bulk_move_stage_select')}</option>
            {(columnsOrder || []).map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="label m-0">{t('app.candidates.pipeline.bulk_assign_manager_label')}</label>
          <select
            className="input"
            onChange={(e) => {
              const v = e.target.value;
              if (v) onAssignManager(v);
              e.currentTarget.selectedIndex = 0;
            }}
          >
            <option value="">{t('app.candidates.pipeline.bulk_assign_manager_select')}</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1" />
        <button type="button" className="btn-secondary" onClick={onClearSelection}>
          {t('app.candidates.pipeline.bulk_clear_selection')}
        </button>
        <button type="button" className="btn" onClick={onArchive}>
          {t('app.candidates.pipeline.bulk_archive')}
        </button>
      </div>
      {!planTierLoading && !allowsTeamFeatures && canViewSettings ? (
        <p className="border-t border-slate-100 pt-2 text-[11px] leading-snug text-slate-600">
          {t('app.candidates.pipeline.bulk_plan_hint', {
            defaultValue:
              'Bulk Meta auto-processing and several lead automations need a Team-tier plan — manual moves above still work.',
          })}{' '}
          <Link className="font-semibold text-brand-700 hover:underline" to={CRM_APP_PATHS.settingsBilling}>
            {t('app.candidates.pipeline.bulk_plan_hint_link', { defaultValue: 'Billing' })}
          </Link>
        </p>
      ) : null}
    </div>
  );
}
