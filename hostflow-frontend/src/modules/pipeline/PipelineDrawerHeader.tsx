/**
 * Header row for Pipeline right drawer (title + close + switch to table).
 */

import { useI18n } from '../../i18n';

export type PipelineDrawerHeaderProps = {
  onClose: () => void;
  onSwitchToTable: () => void;
};

export function PipelineDrawerHeader({ onClose, onSwitchToTable }: PipelineDrawerHeaderProps) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-100">
      <h2 className="text-lg font-semibold">{t('app.candidates.views.kanban')}</h2>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="btn-secondary text-sm p-1"
          onClick={onClose}
          title={t('app.candidates.pipeline.hide_filters')}
        >
          ×
        </button>
        <button type="button" className="btn-secondary text-sm" onClick={onSwitchToTable}>
          {t('app.candidates.pipeline.switch_to_table')}
        </button>
      </div>
    </div>
  );
}
