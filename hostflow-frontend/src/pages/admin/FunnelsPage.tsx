import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { CRM_APP_PATHS } from '../../app/crmAppPaths.generated'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useI18n } from '../../i18n'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import {
  listFunnels,
  getFunnel,
  createFunnel,
  updateFunnel,
  deleteFunnel,
  addFunnelStage,
  updateFunnelStage,
  deleteFunnelStage,
  type Funnel,
  type FunnelStage,
  type FunnelStageCreate,
  type FunnelStageContractV1,
  type FunnelCreate,
} from '../../api/funnels'
import { Modal } from '../../components/Modal'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { refreshMetaStagesCache } from '../../store/useMeta'
import { DEFAULT_STAGE_CODES } from '../../modules/dashboard/constants'
import {
  inferRecruitmentPeSystemStageCode,
  RECRUITMENT_MAPPABLE_FUNNEL_STAGE_CODES,
  RECRUITMENT_PE_SYSTEM_STAGE_CODES,
} from '../../constants/recruitmentStageSurface'

function SortableStageRow({
  stage,
  onEdit,
  onDelete,
  disabled,
  showLeadConversionRoot,
}: {
  stage: FunnelStage
  onEdit: () => void
  onDelete: () => void
  disabled?: boolean
  showLeadConversionRoot?: boolean
}) {
  const { t } = useI18n()
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: stage.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`border-t border-slate-100 ${isDragging ? 'bg-white shadow-md' : 'bg-white'} ${disabled ? 'opacity-50' : ''}`}
    >
      <td className="py-2 pr-2">
        <div
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600 inline-flex"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
          </svg>
        </div>
      </td>
      <td className="py-2 pr-2 font-mono text-sm">{stage.code}</td>
      <td className="py-2 pr-2 font-medium">{stage.label}</td>
      <td className="py-2 pr-2">
        <span className="inline-flex rounded-lg bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
          {stage.system_stage}
        </span>
      </td>
      {showLeadConversionRoot ? (
        <td className="py-2 pr-2 text-xs text-slate-600">
          {stage.conversion_root_v1 ? (
            <span className="rounded-lg bg-blue-50 px-2 py-0.5 font-medium text-blue-800">
              {stage.conversion_root_v1}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </td>
      ) : null}
      <td className="py-2 pr-2 text-sm text-slate-500">{stage.order}</td>
      <td className="py-2">
        <span
          className={`inline-flex rounded-lg px-2 py-0.5 text-xs font-medium ${stage.is_terminal ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}
        >
          {stage.is_terminal
            ? t('admin.funnels.status_terminal')
            : t('admin.funnels.status_in_progress')}
        </span>
      </td>
      <td className="py-2 text-right">
        <button
          type="button"
          onClick={onEdit}
          disabled={disabled}
          className="text-brand-600 hover:text-brand-700 text-sm mr-2"
        >
          {t('common.actions.edit')}
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={disabled}
          className="text-rose-600 hover:text-rose-700 text-sm"
        >
          {t('common.actions.delete')}
        </button>
      </td>
    </tr>
  )
}

function StageCreateEditModal({
  stage,
  onClose,
  onSave,
  disabled,
  referenceCodes,
  funnelType,
  saveError,
}: {
  stage?: FunnelStage | null
  onClose: () => void
  onSave: (data: FunnelStageCreate) => Promise<void>
  disabled?: boolean
  referenceCodes?: string[]
  funnelType: 'candidate' | 'lead' | 'deal'
  saveError?: FriendlyErrorInfo | null
}) {
  const { t } = useI18n()
  const isCandidateFunnel = funnelType === 'candidate'
  const [code, setCode] = useState(stage?.code || '')
  const [label, setLabel] = useState(stage?.label || '')
  const [systemStage, setSystemStage] = useState<FunnelStageCreate['system_stage']>(stage?.system_stage || 'in_progress')
  const [peMapsTo, setPeMapsTo] = useState(
    () =>
      stage?.pe_maps_to_code ||
      inferRecruitmentPeSystemStageCode(stage?.code) ||
      (funnelType === 'candidate' ? 'processing_by_client' : ''),
  )
  const [order, setOrder] = useState(stage?.order ?? 0)
  const [isTerminal, setIsTerminal] = useState(stage?.is_terminal ?? false)
  const [ownerRole, setOwnerRole] = useState('')
  const [slaHoursStr, setSlaHoursStr] = useState('')
  const [requiredActionsText, setRequiredActionsText] = useState('')
  const [autoRulesJsonStr, setAutoRulesJsonStr] = useState('')
  const [conversionRoot, setConversionRoot] = useState<string>(() => stage?.conversion_root_v1 ?? '')
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    setConversionRoot(stage?.conversion_root_v1 ?? '')
  }, [stage])

  useEffect(() => {
    const c = stage?.stage_contract
    setOwnerRole(c?.owner_role?.trim() ? String(c.owner_role) : '')
    setSlaHoursStr(
      c?.sla_hours !== undefined && c.sla_hours !== null && Number.isFinite(Number(c.sla_hours))
        ? String(c.sla_hours)
        : ''
    )
    setRequiredActionsText(c?.required_actions?.length ? c.required_actions.join('\n') : '')
    setAutoRulesJsonStr(c?.auto_rules ? JSON.stringify(c.auto_rules, null, 2) : '')
  }, [stage])

  const handleSubmit = async () => {
    if (!label.trim()) {
      alert(t('admin.funnels.validation_stage'))
      return
    }
    const latinSlug = label
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '')
    const resolvedCode = code.trim() || latinSlug || `stage_${order || 0}`
    if (isCandidateFunnel && !peMapsTo.trim()) {
      setLocalError(t('admin.funnels.errors.pe_mapping_required'))
      return
    }
    setLocalError(null)
    const actions = requiredActionsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    let auto_rules: Record<string, unknown> | undefined
    if (autoRulesJsonStr.trim()) {
      try {
        const parsed = JSON.parse(autoRulesJsonStr) as unknown
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
          alert(t('admin.funnels.auto_rules_not_object'))
          return
        }
        auto_rules = parsed as Record<string, unknown>
      } catch {
        alert(t('admin.funnels.invalid_auto_rules_json'))
        return
      }
    }
    let sla_hours: number | undefined
    if (slaHoursStr.trim()) {
      const n = parseInt(slaHoursStr, 10)
      if (!Number.isFinite(n) || n < 0) {
        alert(t('admin.funnels.invalid_sla_hours'))
        return
      }
      sla_hours = n
    }
    const hasContract =
      Boolean(ownerRole.trim()) || actions.length > 0 || sla_hours !== undefined || auto_rules !== undefined

    const payload: FunnelStageCreate = {
      code: resolvedCode,
      label: label.trim(),
      system_stage: systemStage || 'in_progress',
      order: order || 0,
      is_terminal: isTerminal,
    }
    if (isCandidateFunnel) {
      payload.pe_maps_to_module = 'recruitment'
      payload.pe_maps_to_code = peMapsTo.trim()
    }
    if (funnelType === 'lead') {
      const cr = conversionRoot.trim().toLowerCase()
      if (stage) {
        payload.conversion_root_v1 = cr && ['lead', 'qualified', 'active', 'final'].includes(cr) ? cr : null
      } else if (cr && ['lead', 'qualified', 'active', 'final'].includes(cr)) {
        payload.conversion_root_v1 = cr
      }
    }
    if (stage) {
      const contract: FunnelStageContractV1 | null = hasContract
        ? {
            owner_role: ownerRole.trim() || undefined,
            required_actions: actions.length ? actions : undefined,
            sla_hours,
            auto_rules,
          }
        : null
      payload.stage_contract = contract
    } else if (hasContract) {
      payload.stage_contract = {
        owner_role: ownerRole.trim() || undefined,
        required_actions: actions.length ? actions : undefined,
        sla_hours,
        auto_rules,
      }
    }
    await onSave(payload)
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={
        stage ? t('admin.funnels.edit_stage') : t('admin.funnels.create_stage')
      }
    >
      <div className="space-y-4">
        {(saveError || localError) && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {saveError ? (
              <>
                <p className="font-medium">{saveError.title}</p>
                {saveError.detail ? <p className="mt-1 text-xs">{saveError.detail}</p> : null}
              </>
            ) : (
              localError
            )}
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.label_field')} *
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value)
              if (!stage) {
                const slug = e.target.value
                  .trim()
                  .toLowerCase()
                  .replace(/\s+/g, '_')
                  .replace(/[^a-z0-9_]/g, '')
                if (slug) setCode(slug)
              }
            }}
            className="input w-full"
            placeholder={t('admin.funnels.placeholders.stage_label')}
            disabled={disabled}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.code_field')} *
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => {
              const next = e.target.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_')
              setCode(next)
              const mapped = inferRecruitmentPeSystemStageCode(next)
              if (mapped) setPeMapsTo(mapped)
            }}
            className="input w-full font-mono text-sm"
            placeholder={t('admin.funnels.placeholders.stage_code')}
            disabled={disabled || !!stage}
          />
          {stage ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('admin.funnels.code_readonly')}
            </p>
          ) : (
            <p className="mt-1 text-xs text-slate-500">
              {t('admin.funnels.code_hint')}
            </p>
          )}
        </div>
        {!stage && referenceCodes && referenceCodes.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-slate-500 mb-1">
              {t('admin.funnels.pick_existing_code')}
            </p>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-auto">
              {referenceCodes.map((c) => (
                <button
                  key={c}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    setCode(c)
                    const mapped = inferRecruitmentPeSystemStageCode(c)
                    if (mapped) setPeMapsTo(mapped)
                    if (!label.trim()) {
                      setLabel(c)
                    }
                  }}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-0.5 text-xs text-slate-700 hover:border-brand-300 hover:text-brand-700"
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.system_stage')} *
          </label>
          <select
            value={systemStage || 'in_progress'}
            onChange={(e) => setSystemStage(e.target.value as FunnelStageCreate['system_stage'])}
            className="input w-full"
            disabled={disabled}
          >
            <option value="new">{t('admin.funnels.system_stage_new')}</option>
            <option value="in_progress">{t('admin.funnels.system_stage_in_progress')}</option>
            <option value="hired">{t('admin.funnels.system_stage_hired')}</option>
            <option value="declined_rejected">{t('admin.funnels.system_stage_declined_rejected')}</option>
          </select>
          <p className="mt-1 text-xs text-slate-500">
            {t('admin.funnels.system_stage_hint')}
          </p>
        </div>
        {isCandidateFunnel ? (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('admin.funnels.pe_maps_to')} *
            </label>
            <select
              value={peMapsTo}
              onChange={(e) => setPeMapsTo(e.target.value)}
              className="input w-full"
              disabled={disabled}
            >
              {RECRUITMENT_PE_SYSTEM_STAGE_CODES.map((peCode) => (
                <option key={peCode} value={peCode}>
                  {peCode}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">{t('admin.funnels.pe_maps_to_hint')}</p>
          </div>
        ) : null}
        {funnelType === 'lead' ? (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('admin.funnels.conversion_root')}
            </label>
            <select
              value={conversionRoot}
              onChange={(e) => setConversionRoot(e.target.value)}
              className="input w-full"
              disabled={disabled}
            >
              <option value="">{t('admin.funnels.conversion_root_auto')}</option>
              <option value="lead">{t('admin.funnels.conversion_root_lead')}</option>
              <option value="qualified">{t('admin.funnels.conversion_root_qualified')}</option>
              <option value="active">{t('admin.funnels.conversion_root_active')}</option>
              <option value="final">{t('admin.funnels.conversion_root_final')}</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">{t('admin.funnels.conversion_root_hint')}</p>
          </div>
        ) : null}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.order_field')}
          </label>
          <input
            type="number"
            value={order}
            onChange={(e) => setOrder(parseInt(e.target.value) || 0)}
            className="input w-full"
            min={0}
            disabled={disabled}
          />
        </div>
        <div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isTerminal}
              onChange={(e) => setIsTerminal(e.target.checked)}
              disabled={disabled}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">
              {t('admin.funnels.terminal_stage')}
            </span>
          </label>
        </div>
        <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
          <summary className="cursor-pointer select-none text-sm font-medium text-slate-800">
            {t('admin.funnels.stage_contract_section')}
          </summary>
          <p className="mt-2 text-xs text-slate-500">
            {t('admin.funnels.stage_contract_hint')}
          </p>
          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t('admin.funnels.owner_role')}
              </label>
              <input
                type="text"
                value={ownerRole}
                onChange={(e) => setOwnerRole(e.target.value)}
                className="input w-full text-sm"
                placeholder={t('admin.funnels.owner_role_placeholder')}
                disabled={disabled}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t('admin.funnels.sla_hours')}
              </label>
              <input
                type="number"
                min={0}
                value={slaHoursStr}
                onChange={(e) => setSlaHoursStr(e.target.value)}
                className="input w-full text-sm"
                placeholder="48"
                disabled={disabled}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t('admin.funnels.required_actions')}
              </label>
              <textarea
                value={requiredActionsText}
                onChange={(e) => setRequiredActionsText(e.target.value)}
                className="input w-full text-sm font-mono min-h-[72px]"
                placeholder={t('admin.funnels.required_actions_placeholder')}
                disabled={disabled}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t('admin.funnels.auto_rules_json')}
              </label>
              <textarea
                value={autoRulesJsonStr}
                onChange={(e) => setAutoRulesJsonStr(e.target.value)}
                className="input w-full text-sm font-mono min-h-[64px]"
                placeholder='{"automation_rule_ids": []}'
                disabled={disabled}
              />
            </div>
          </div>
        </details>
        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onClose} disabled={disabled} className="btn-secondary">
            {t('common.cancel')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !label.trim() || !code.trim()}
            className="btn-primary"
          >
            {stage ? t('common.save') : t('admin.funnels.create')}
          </button>
        </div>
      </div>
    </Modal>
  )
}

function FunnelCreateModal({
  onClose,
  onSave,
  disabled,
  funnelType,
}: {
  onClose: () => void
  onSave: (data: FunnelCreate) => Promise<void>
  disabled?: boolean
  funnelType: 'candidate' | 'lead'
}) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [isDefault, setIsDefault] = useState(true)

  const handleSubmit = async () => {
    if (!name.trim()) {
      alert(t('admin.funnels.validation_funnel_name'))
      return
    }
    await onSave({ type: funnelType, name: name.trim(), is_default: isDefault })
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('admin.funnels.create_funnel')}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.funnel_name')} *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input w-full"
            placeholder={t('admin.funnels.placeholders.funnel_name')}
            disabled={disabled}
          />
        </div>
        <div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              disabled={disabled}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">
              {funnelType === 'lead'
                ? t('admin.funnels.default_funnel_leads')
                : t('admin.funnels.default_funnel')}
            </span>
          </label>
        </div>
        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onClose} disabled={disabled} className="btn-secondary">
            {t('common.cancel')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !name.trim()}
            className="btn-primary"
          >
            {t('admin.funnels.create')}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default function FunnelsPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [funnelTab, setFunnelTab] = useState<'candidate' | 'lead'>('candidate')
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [selectedFunnel, setSelectedFunnel] = useState<Funnel | null>(null)
  const [stages, setStages] = useState<FunnelStage[]>([])
  const [loading, setLoading] = useState(true)
  const [editingStage, setEditingStage] = useState<FunnelStage | null>(null)
  const [showCreateStageModal, setShowCreateStageModal] = useState(false)
  const [showCreateFunnelModal, setShowCreateFunnelModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [stageModalError, setStageModalError] = useState<FriendlyErrorInfo | null>(null)

  const catalogStageCodes = useMemo(() => {
    if (funnelTab !== 'candidate') return [...DEFAULT_STAGE_CODES]
    const seen = new Set<string>()
    const out: string[] = []
    for (const code of [...RECRUITMENT_MAPPABLE_FUNNEL_STAGE_CODES, ...DEFAULT_STAGE_CODES]) {
      const key = String(code || '').trim().toLowerCase()
      if (!key || seen.has(key)) continue
      seen.add(key)
      out.push(key)
    }
    return out
  }, [funnelTab])

  const referenceStageCodes = useMemo(
    () => catalogStageCodes.filter((code) => !stages.some((s) => s.code === code)),
    [catalogStageCodes, stages],
  )

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const loadFunnels = useCallback(async () => {
    try {
      setPageError(null)
      const list = await listFunnels({ type: funnelTab, moduleKey: 'recruitment' })
      setFunnels(list)
      if (list.length > 0) {
        setSelectedFunnel((prev) => {
          if (prev && list.some((f) => f.id === prev.id)) return prev
          return list.find((f) => f.is_default) || list[0]
        })
      } else {
        setSelectedFunnel(null)
        setStages([])
      }
    } catch (err) {
      console.error('Failed to load funnels', err)
      const fb = t('admin.funnels.errors.load_failed')
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setPageError(getFriendlyErrorInfo(err, fb, t))
      }
      setFunnels([])
      setSelectedFunnel(null)
      setStages([])
    } finally {
      setLoading(false)
    }
  }, [funnelTab, planLimitModal, t])

  useEffect(() => {
    setLoading(true)
    loadFunnels()
  }, [loadFunnels])

  useEffect(() => {
    if (!selectedFunnel) {
      setStages([])
      return
    }
    setStages(selectedFunnel.stages || [])
  }, [selectedFunnel])

  const refreshSelectedFunnel = useCallback(async () => {
    if (!selectedFunnel) return
    try {
      const f = await getFunnel(selectedFunnel.id)
      setSelectedFunnel(f)
      setStages(f.stages || [])
    } catch {
      loadFunnels()
    }
  }, [selectedFunnel, loadFunnels])

  const handleCreateFunnel = useCallback(
    async (data: FunnelCreate) => {
      setSaving(true)
      setPageError(null)
      try {
        const created = await createFunnel(data)
        await loadFunnels()
        setSelectedFunnel(created)
        setShowCreateFunnelModal(false)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const fb = t('admin.funnels.errors.save_failed')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setPageError(getFriendlyErrorInfo(err, fb, t))
        }
      } finally {
        setSaving(false)
      }
    },
    [loadFunnels, planLimitModal, t]
  )

  const handleCreateStage = useCallback(
    async (data: FunnelStageCreate) => {
      if (!selectedFunnel) return
      setSaving(true)
      setPageError(null)
      setStageModalError(null)
      try {
        await addFunnelStage(selectedFunnel.id, data)
        await refreshSelectedFunnel()
        setShowCreateStageModal(false)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const fb = t('admin.funnels.errors.save_failed')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          const info = getFriendlyErrorInfo(err, fb, t)
          setStageModalError(info)
          setPageError(info)
        }
      } finally {
        setSaving(false)
      }
    },
    [planLimitModal, selectedFunnel, refreshSelectedFunnel, t]
  )

  const handleUpdateStage = useCallback(
    async (data: FunnelStageCreate) => {
      if (!editingStage || !selectedFunnel) return
      setSaving(true)
      setPageError(null)
      setStageModalError(null)
      try {
        await updateFunnelStage(selectedFunnel.id, editingStage.id, data)
        await refreshSelectedFunnel()
        setEditingStage(null)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 404) {
          // Stage was removed concurrently (stale local id) — just resync UI.
          await refreshSelectedFunnel()
          setEditingStage(null)
          return
        }
        const fb = t('admin.funnels.errors.save_failed')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          const info = getFriendlyErrorInfo(err, fb, t)
          setStageModalError(info)
          setPageError(info)
        }
      } finally {
        setSaving(false)
      }
    },
    [editingStage, planLimitModal, selectedFunnel, refreshSelectedFunnel, t]
  )

  const handleDeleteStage = useCallback(
    async (stage: FunnelStage) => {
      if (!selectedFunnel) return
      if (
        !confirm(
          t('admin.funnels.confirm_delete', { values: { label: stage.label } })
        )
      )
        return
      try {
        setPageError(null)
        await deleteFunnelStage(selectedFunnel.id, stage.id)
        await refreshSelectedFunnel()
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 404) {
          // Already gone on backend; keep UI consistent and continue.
          await refreshSelectedFunnel()
          return
        }
        const fb = t('admin.funnels.errors.save_failed')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setPageError(getFriendlyErrorInfo(err, fb, t))
        }
      }
    },
    [planLimitModal, selectedFunnel, refreshSelectedFunnel, t]
  )

  const handleDeleteFunnel = useCallback(async () => {
    if (!selectedFunnel) return
    if (
      !confirm(
        t('admin.funnels.confirm_delete_funnel', {
          values: { name: selectedFunnel.name },
          defaultValue: 'Delete funnel "{name}"?',
        })
      )
    ) {
      return
    }
    try {
      setSaving(true)
      setPageError(null)
      await deleteFunnel(selectedFunnel.id)
      await loadFunnels()
      refreshMetaStagesCache()
    } catch (err: unknown) {
      const fb = t('admin.funnels.errors.delete_funnel_failed', {
        defaultValue: 'Could not delete funnel',
      })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setPageError(getFriendlyErrorInfo(err, fb, t))
      }
    } finally {
      setSaving(false)
    }
  }, [loadFunnels, planLimitModal, selectedFunnel, t])

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id || !selectedFunnel) return

      const oldIndex = stages.findIndex((s) => s.id === active.id)
      const newIndex = stages.findIndex((s) => s.id === over.id)
      if (oldIndex === -1 || newIndex === -1) return

      const reordered = arrayMove(stages, oldIndex, newIndex)
      setStages(reordered)

      try {
        setPageError(null)
        // If local state contains stale stage ids, skip them before sending PATCH.
        const existingIds = new Set((await getFunnel(selectedFunnel.id)).stages.map((s) => String(s.id)))
        const staleStageIds: string[] = []
        for (let i = 0; i < reordered.length; i++) {
          const s = reordered[i]
          if (!existingIds.has(String(s.id))) {
            staleStageIds.push(String(s.id))
            continue
          }
          try {
            await updateFunnelStage(selectedFunnel.id, s.id, {
              code: s.code,
              label: s.label,
              system_stage: s.system_stage,
              order: i,
              is_terminal: s.is_terminal,
              conversion_root_v1: s.conversion_root_v1 ?? null,
            })
          } catch (err: unknown) {
            const status = (err as { response?: { status?: number } })?.response?.status
            if (status === 404) {
              staleStageIds.push(String(s.id))
              continue
            }
            throw err
          }
        }
        if (staleStageIds.length > 0) {
          console.warn('[FunnelsPage] skipped stale stage ids during reorder', staleStageIds)
        }
        await refreshSelectedFunnel()
        refreshMetaStagesCache()
      } catch (err) {
        console.error('Failed to reorder stages', err)
        const fb = t('admin.funnels.errors.reorder_failed')
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setPageError(getFriendlyErrorInfo(err, fb, t))
        }
        void refreshSelectedFunnel()
      }
    },
    [planLimitModal, stages, selectedFunnel, refreshSelectedFunnel, t]
  )

  const funnelSubpageHeaderProps = {
    className: 'mb-2',
    backLabel: t('admin.settings.subpage.back_all'),
    kicker: t('admin.funnels.header_kicker'),
    title: funnelTab === 'lead' ? t('admin.funnels.title_leads') : t('admin.funnels.title'),
    subtitle: funnelTab === 'lead' ? t('admin.funnels.subtitle_leads') : t('admin.funnels.subtitle'),
  } as const

  const funnelTabButtons = (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        onClick={() => setFunnelTab('candidate')}
        className={`rounded-lg px-3 py-2 text-sm font-medium ${
          funnelTab === 'candidate'
            ? 'bg-brand-600 text-white'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
        }`}
      >
        {t('admin.funnels.tab_candidates')}
      </button>
      <button
        type="button"
        onClick={() => setFunnelTab('lead')}
        className={`rounded-lg px-3 py-2 text-sm font-medium ${
          funnelTab === 'lead'
            ? 'bg-brand-600 text-white'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
        }`}
      >
        {t('admin.funnels.tab_leads')}
      </button>
    </div>
  )

  const errorBanner = pageError ? (
    <ErrorRecoveryBanner
      info={pageError}
      onRetry={() => {
        setPageError(null)
        void loadFunnels()
      }}
      retryLabel={t('common.actions.refresh')}
      {...friendlyErrorBannerSecondary(pageError, CRM_APP_PATHS.settingsBilling, t('app.settings.billing.badge'))}
    />
  ) : null

  const createFunnelModal = showCreateFunnelModal ? (
    <FunnelCreateModal
      onClose={() => setShowCreateFunnelModal(false)}
      onSave={handleCreateFunnel}
      disabled={saving}
      funnelType={funnelTab}
    />
  ) : null

  if (loading) {
    return (
      <SettingsSubpageHeader {...funnelSubpageHeaderProps}>
        <div className="text-sm text-slate-500">
          {t('common.loading')}
        </div>
      </SettingsSubpageHeader>
    )
  }

  if (funnels.length === 0) {
    return (
      <>
      <SettingsSubpageHeader {...funnelSubpageHeaderProps}>
        {errorBanner}
        <div className="settings-toolbar">{funnelTabButtons}</div>
        <div className="card p-8 text-center">
          <p className="text-slate-600 mb-4">
            {funnelTab === 'lead' ? t('admin.funnels.no_funnels_leads') : t('admin.funnels.no_funnels')}
          </p>
          <button
            type="button"
            onClick={() => setShowCreateFunnelModal(true)}
            className="btn-primary"
          >
            + {t('admin.funnels.create_funnel')}
          </button>
        </div>
      </SettingsSubpageHeader>
      {createFunnelModal}
      </>
    )
  }

  return (
    <>
    <SettingsSubpageHeader {...funnelSubpageHeaderProps}>
      {errorBanner}
      <div className="settings-toolbar">{funnelTabButtons}</div>

      <div className="grid gap-4 lg:grid-cols-[minmax(220px,280px)_minmax(0,1fr)]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between gap-2 border-b border-slate-100 p-3">
            <h2 className="text-sm font-semibold text-slate-900">
              {t('admin.funnels.select_funnel')}
            </h2>
            <button
              type="button"
              onClick={() => setShowCreateFunnelModal(true)}
              className="btn-secondary text-xs"
            >
              + {t('admin.funnels.new_funnel')}
            </button>
          </div>
          <ul className="max-h-[28rem] overflow-y-auto p-2">
            {funnels.map((f) => {
              const active = selectedFunnel?.id === f.id
              return (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedFunnel(f)}
                    className={`mb-1 flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm ${
                      active
                        ? 'bg-brand-50 font-medium text-brand-800'
                        : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <span className="truncate">{f.name}</span>
                    {f.is_default ? <span aria-hidden="true">★</span> : null}
                  </button>
                </li>
              )
            })}
          </ul>
          {selectedFunnel && !selectedFunnel.is_default ? (
            <div className="border-t border-slate-100 p-3">
              <button
                type="button"
                onClick={() => void handleDeleteFunnel()}
                disabled={saving}
                className="btn-danger w-full text-sm"
              >
                {t('admin.funnels.delete_funnel', { defaultValue: 'Delete funnel' })}
              </button>
            </div>
          ) : null}
        </div>

      <div className="card overflow-x-auto">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {selectedFunnel?.name || ''} — {t('admin.funnels.stages')}
            </h2>
            {selectedFunnel ? (
              <p className="mt-1 text-xs text-slate-500">
                {selectedFunnel.is_default
                  ? t('admin.funnels.default_funnel_locked', {
                      defaultValue: 'Default funnel. Create another default funnel before deleting this one.',
                    })
                  : t('admin.funnels.delete_funnel_hint', {
                      defaultValue: 'Only unused non-default funnels can be deleted.',
                    })}
              </p>
            ) : null}
          </div>
          {selectedFunnel && (
            <button
              type="button"
              onClick={() => {
                setStageModalError(null)
                setShowCreateStageModal(true)
              }}
              className="btn-primary text-sm"
            >
              + {t('admin.funnels.add_stage')}
            </button>
          )}
        </div>
        {!selectedFunnel ? (
          <div className="p-8 text-center text-sm text-slate-500">
            {t('admin.funnels.select_funnel_first')}
          </div>
        ) : stages.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            {t('admin.funnels.no_stages')}
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="py-2 px-2 w-8" />
                  <th className="py-2 px-2">{t('admin.funnels.columns.code')}</th>
                  <th className="py-2 px-2">{t('admin.funnels.columns.label')}</th>
                  <th className="py-2 px-2">{t('admin.funnels.columns.system')}</th>
                  {funnelTab === 'lead' ? (
                    <th className="py-2 px-2">{t('admin.funnels.columns.conversion_root')}</th>
                  ) : null}
                  <th className="py-2 px-2">{t('admin.funnels.columns.order')}</th>
                  <th className="py-2 px-2">{t('admin.funnels.columns.status')}</th>
                  <th className="py-2 px-2 text-right">{t('admin.funnels.columns.actions')}</th>
                </tr>
              </thead>
              <tbody>
                <SortableContext
                  items={stages.map((s) => s.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {stages.map((stage) => (
                    <SortableStageRow
                      key={stage.id}
                      stage={stage}
                      onEdit={() => setEditingStage(stage)}
                      onDelete={() => handleDeleteStage(stage)}
                      disabled={saving}
                      showLeadConversionRoot={funnelTab === 'lead'}
                    />
                  ))}
                </SortableContext>
              </tbody>
            </table>
          </DndContext>
        )}
      </div>
      </div>

      <div className="settings-panel">
        <h2 className="text-sm font-semibold text-slate-900 mb-2">
          {t('admin.funnels.reference_stages')}
        </h2>
        <p className="text-xs text-slate-500 mb-3">
          {t('admin.funnels.reference_help')}
        </p>
        <div className="flex flex-wrap gap-2">
          {catalogStageCodes.map((code) => (
            <span
              key={code}
              className="inline-flex rounded-lg bg-slate-100 px-3 py-0.5 text-xs font-medium text-slate-700"
            >
              {code}
            </span>
          ))}
        </div>
      </div>

      {showCreateStageModal && selectedFunnel && (
        <StageCreateEditModal
          stage={null}
          onClose={() => {
            setShowCreateStageModal(false)
            setStageModalError(null)
          }}
          onSave={handleCreateStage}
          disabled={saving}
          referenceCodes={referenceStageCodes}
          funnelType={funnelTab}
          saveError={stageModalError}
        />
      )}
      {editingStage && (
        <StageCreateEditModal
          stage={editingStage}
          onClose={() => {
            setEditingStage(null)
            setStageModalError(null)
          }}
          onSave={handleUpdateStage}
          disabled={saving}
          funnelType={funnelTab}
          saveError={stageModalError}
        />
      )}
      {createFunnelModal}
    </SettingsSubpageHeader>
    </>
  )
}
