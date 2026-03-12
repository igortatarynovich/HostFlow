import { useState } from 'react'
import { Modal } from '../../../components/Modal'
import { useI18n } from '../../../i18n'
import { translateReasonLabel, translateStageLabel } from '../../../utils/stageLabels'
import type { MetaStages } from '../../../api/types'

interface BulkStageModalProps {
  open: boolean
  onClose: () => void
  stageOptions: string[]
  bulkStage: string
  bulkReasons: string[]
  onStageChange: (stage: string) => void
  onReasonsChange: (reasons: string[]) => void
  onApply: () => void
  loading: boolean
  meta?: MetaStages | null
  canManage?: boolean
}

export function BulkStageModal({
  open,
  onClose,
  stageOptions,
  bulkStage,
  bulkReasons,
  onStageChange,
  onReasonsChange,
  onApply,
  loading,
  meta,
  canManage = true,
}: BulkStageModalProps) {
  const { t } = useI18n()
  const reasonOptions = meta?.reason_choices?.[bulkStage] ?? []

  return (
    <Modal
      open={canManage && open}
      onClose={() => {
        if (!loading) {
          onClose()
          onReasonsChange([])
        }
      }}
      title={t('app.candidates.modals.stage.title')}
    >
      <div className="space-y-3">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-brand-600 bg-brand-50 p-2 rounded border border-brand-200">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600"></div>
            <span>{t('app.candidates.messages.bulk_stage_loading')}</span>
          </div>
        )}
        <div>
          <div className="label">{t('app.candidates.modals.stage.new_stage')}</div>
          <select
            className="input"
            value={bulkStage}
            onChange={(e) => onStageChange(e.target.value)}
            disabled={loading}
          >
            {stageOptions.map((c) => (
              <option key={c} value={c}>
                {translateStageLabel(t, c, meta?.labels?.[c] || c)}
              </option>
            ))}
          </select>
        </div>
        {reasonOptions.length > 0 && (
          <div>
            <div className="label">{t('app.candidates.modals.stage.reasons_label')}</div>
            <div className="space-y-1">
              {reasonOptions.map((option) => (
                <label key={option.code} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={bulkReasons.includes(option.code)}
                    onChange={(e) => {
                      const checked = e.target.checked
                      onReasonsChange(
                        checked
                          ? bulkReasons.includes(option.code)
                            ? bulkReasons
                            : [...bulkReasons, option.code]
                          : bulkReasons.filter((code) => code !== option.code)
                      )
                    }}
                    disabled={loading}
                  />
                  <span>{translateReasonLabel(t, option.code, option.label || option.code)}</span>
                </label>
              ))}
            </div>
            {bulkReasons.length === 0 && (
              <div className="text-xs text-red-600">{t('app.candidates.messages.reason_required')}</div>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <button
            className="btn-primary"
            onClick={onApply}
            disabled={loading || !bulkStage || (reasonOptions.length > 0 && bulkReasons.length === 0)}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {t('common.loading') || 'Загрузка...'}
              </>
            ) : (
              t('common.actions.apply')
            )}
          </button>
          <button
            className="btn-ghost"
            onClick={() => {
              onClose()
              onReasonsChange([])
            }}
            disabled={loading}
          >
            {t('common.actions.cancel')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
