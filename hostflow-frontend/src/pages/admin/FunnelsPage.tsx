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
import { useI18n } from '../../i18n'
import {
  listFunnels,
  getFunnel,
  createFunnel,
  updateFunnel,
  addFunnelStage,
  updateFunnelStage,
  deleteFunnelStage,
  type Funnel,
  type FunnelStage,
  type FunnelStageCreate,
  type FunnelCreate,
} from '../../api/funnels'
import { Modal } from '../../components/Modal'
import { refreshMetaStagesCache } from '../../store/useMeta'
import { DEFAULT_STAGE_CODES } from '../../modules/dashboard/constants'

function SortableStageRow({
  stage,
  onEdit,
  onDelete,
  disabled,
}: {
  stage: FunnelStage
  onEdit: () => void
  onDelete: () => void
  disabled?: boolean
}) {
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
      className={`border-t border-slate-100 ${isDragging ? 'bg-white shadow-lg' : 'bg-white'} ${disabled ? 'opacity-50' : ''}`}
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
        <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
          {stage.system_stage}
        </span>
      </td>
      <td className="py-2 pr-2 text-sm text-slate-500">{stage.order}</td>
      <td className="py-2">
        <span
          className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${stage.is_terminal ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}
        >
          {stage.is_terminal ? 'Terminal' : 'In progress'}
        </span>
      </td>
      <td className="py-2 text-right">
        <button
          type="button"
          onClick={onEdit}
          disabled={disabled}
          className="text-brand-600 hover:text-brand-700 text-sm mr-2"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={disabled}
          className="text-rose-600 hover:text-rose-700 text-sm"
        >
          Delete
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
}: {
  stage?: FunnelStage | null
  onClose: () => void
  onSave: (data: FunnelStageCreate) => Promise<void>
  disabled?: boolean
  referenceCodes?: string[]
}) {
  const { t } = useI18n()
  const [code, setCode] = useState(stage?.code || '')
  const [label, setLabel] = useState(stage?.label || '')
  const [systemStage, setSystemStage] = useState<FunnelStageCreate['system_stage']>(stage?.system_stage || 'in_progress')
  const [order, setOrder] = useState(stage?.order ?? 0)
  const [isTerminal, setIsTerminal] = useState(stage?.is_terminal ?? false)

  const handleSubmit = async () => {
    if (!code.trim() || !label.trim()) {
      alert(t('admin.funnels.validation_required', { defaultValue: 'Code and label are required' }))
      return
    }
    await onSave({
      code: code.trim(),
      label: label.trim(),
      system_stage: systemStage || 'in_progress',
      order: order || 0,
      is_terminal: isTerminal,
    })
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={
        stage
          ? t('admin.funnels.edit_stage', { defaultValue: 'Edit stage' })
          : t('admin.funnels.create_stage', { defaultValue: 'Create stage' })
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.label_field', { defaultValue: 'Label' })} *
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value)
              if (!stage && !code.trim()) {
                setCode(
                  e.target.value
                    .trim()
                    .toLowerCase()
                    .replace(/\s+/g, '_')
                    .replace(/[^a-z0-9_]/g, '')
                )
              }
            }}
            className="input w-full"
            placeholder="e.g. Initial interview"
            disabled={disabled}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.code_field', { defaultValue: 'Code' })} *
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) =>
              setCode(e.target.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_'))
            }
            className="input w-full font-mono text-sm"
            placeholder="initial_interview"
            disabled={disabled || !!stage}
          />
          {stage && (
            <p className="mt-1 text-xs text-slate-500">
              {t('admin.funnels.code_readonly', { defaultValue: 'Code cannot be changed' })}
            </p>
          )}
        </div>
        {!stage && referenceCodes && referenceCodes.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-slate-500 mb-1">
              {t('admin.funnels.pick_existing_code', {
                defaultValue: 'Or pick from existing system stages:',
              })}
            </p>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-auto">
              {referenceCodes.map((c) => (
                <button
                  key={c}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    setCode(c)
                    if (!label.trim()) {
                      setLabel(c)
                    }
                  }}
                  className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs text-slate-700 hover:border-brand-300 hover:text-brand-700"
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.system_stage', { defaultValue: 'System stage' })} *
          </label>
          <select
            value={systemStage || 'in_progress'}
            onChange={(e) => setSystemStage(e.target.value as FunnelStageCreate['system_stage'])}
            className="input w-full"
            disabled={disabled}
          >
            <option value="new">{t('admin.funnels.system_stage_new', { defaultValue: 'New' })}</option>
            <option value="in_progress">{t('admin.funnels.system_stage_in_progress', { defaultValue: 'In progress' })}</option>
            <option value="hired">{t('admin.funnels.system_stage_hired', { defaultValue: 'Hired' })}</option>
            <option value="declined_rejected">{t('admin.funnels.system_stage_declined_rejected', { defaultValue: 'Declined / Rejected' })}</option>
          </select>
          <p className="mt-1 text-xs text-slate-500">
            {t('admin.funnels.system_stage_hint', {
              defaultValue: 'Each custom stage must be mapped to one canonical system stage.',
            })}
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.order_field', { defaultValue: 'Order' })}
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
              {t('admin.funnels.terminal_stage', { defaultValue: 'Terminal stage (e.g. Employed, Rejected)' })}
            </span>
          </label>
        </div>
        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onClose} disabled={disabled} className="btn-secondary">
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !label.trim() || !code.trim()}
            className="btn-primary"
          >
            {stage ? t('common.save', { defaultValue: 'Save' }) : t('admin.funnels.create', { defaultValue: 'Create' })}
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
}: {
  onClose: () => void
  onSave: (data: FunnelCreate) => Promise<void>
  disabled?: boolean
}) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const [isDefault, setIsDefault] = useState(true)

  const handleSubmit = async () => {
    if (!name.trim()) {
      alert(t('admin.funnels.validation_required', { defaultValue: 'Name is required' }))
      return
    }
    await onSave({ type: 'candidate', name: name.trim(), is_default: isDefault })
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={t('admin.funnels.create_funnel', { defaultValue: 'Create funnel' })}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            {t('admin.funnels.funnel_name', { defaultValue: 'Funnel name' })} *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input w-full"
            placeholder="e.g. Driver Recruitment"
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
              {t('admin.funnels.default_funnel', { defaultValue: 'Default funnel for candidates' })}
            </span>
          </label>
        </div>
        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onClose} disabled={disabled} className="btn-secondary">
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !name.trim()}
            className="btn-primary"
          >
            {t('admin.funnels.create', { defaultValue: 'Create' })}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default function FunnelsPage() {
  const { t } = useI18n()
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [selectedFunnel, setSelectedFunnel] = useState<Funnel | null>(null)
  const [stages, setStages] = useState<FunnelStage[]>([])
  const [loading, setLoading] = useState(true)
  const [editingStage, setEditingStage] = useState<FunnelStage | null>(null)
  const [showCreateStageModal, setShowCreateStageModal] = useState(false)
  const [showCreateFunnelModal, setShowCreateFunnelModal] = useState(false)
  const [saving, setSaving] = useState(false)

  const referenceStageCodes = useMemo(
    () => DEFAULT_STAGE_CODES.filter((code) => !stages.some((s) => s.code === code)),
    [stages],
  )

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const loadFunnels = useCallback(async () => {
    try {
      const list = await listFunnels({ type: 'candidate' })
      setFunnels(list)
      if (list.length > 0 && !selectedFunnel) {
        const defaultF = list.find((f) => f.is_default) || list[0]
        setSelectedFunnel(defaultF)
      } else if (list.length === 0) {
        setSelectedFunnel(null)
        setStages([])
      }
    } catch (err) {
      console.error('Failed to load funnels', err)
      setFunnels([])
      setSelectedFunnel(null)
      setStages([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
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
      try {
        const created = await createFunnel(data)
        await loadFunnels()
        setSelectedFunnel(created)
        setShowCreateFunnelModal(false)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const msg =
          err &&
          typeof err === 'object' &&
          'response' in err &&
          typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
            ? (err as { response: { data: { detail: string } } }).response.data.detail
            : 'Unknown error'
        alert(msg)
      } finally {
        setSaving(false)
      }
    },
    [loadFunnels]
  )

  const handleCreateStage = useCallback(
    async (data: FunnelStageCreate) => {
      if (!selectedFunnel) return
      setSaving(true)
      try {
        await addFunnelStage(selectedFunnel.id, data)
        await refreshSelectedFunnel()
        setShowCreateStageModal(false)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const msg =
          err &&
          typeof err === 'object' &&
          'response' in err &&
          typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
            ? (err as { response: { data: { detail: string } } }).response.data.detail
            : 'Unknown error'
        alert(msg)
      } finally {
        setSaving(false)
      }
    },
    [selectedFunnel, refreshSelectedFunnel]
  )

  const handleUpdateStage = useCallback(
    async (data: FunnelStageCreate) => {
      if (!editingStage || !selectedFunnel) return
      setSaving(true)
      try {
        await updateFunnelStage(selectedFunnel.id, editingStage.id, data)
        await refreshSelectedFunnel()
        setEditingStage(null)
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const msg =
          err &&
          typeof err === 'object' &&
          'response' in err &&
          typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
            ? (err as { response: { data: { detail: string } } }).response.data.detail
            : 'Unknown error'
        alert(msg)
      } finally {
        setSaving(false)
      }
    },
    [editingStage, selectedFunnel, refreshSelectedFunnel]
  )

  const handleDeleteStage = useCallback(
    async (stage: FunnelStage) => {
      if (!selectedFunnel) return
      if (
        !confirm(
          t('admin.funnels.confirm_delete', {
            values: { label: stage.label },
            defaultValue: `Delete stage "${stage.label}"?`,
          })
        )
      )
        return
      try {
        await deleteFunnelStage(selectedFunnel.id, stage.id)
        await refreshSelectedFunnel()
        refreshMetaStagesCache()
      } catch (err: unknown) {
        const msg =
          err &&
          typeof err === 'object' &&
          'response' in err &&
          typeof (err as { response?: { data?: { detail?: string } } }).response?.data?.detail === 'string'
            ? (err as { response: { data: { detail: string } } }).response.data.detail
            : 'Unknown error'
        alert(msg)
      }
    },
    [selectedFunnel, refreshSelectedFunnel, t]
  )

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
        for (let i = 0; i < reordered.length; i++) {
          const s = reordered[i]
          await updateFunnelStage(selectedFunnel.id, s.id, {
            code: s.code,
            label: s.label,
            order: i,
            is_terminal: s.is_terminal,
          })
        }
        await refreshSelectedFunnel()
        refreshMetaStagesCache()
      } catch (err) {
        console.error('Failed to reorder stages', err)
        refreshSelectedFunnel()
      }
    },
    [stages, selectedFunnel, refreshSelectedFunnel]
  )

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-slate-500">
          {t('common.loading', { defaultValue: 'Loading…' })}
        </div>
      </div>
    )
  }

  if (funnels.length === 0) {
    return (
      <div className="space-y-4">
        <header>
          <h1 className="text-xl font-semibold text-slate-900">
            {t('admin.funnels.title', { defaultValue: 'Candidate funnels' })}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('admin.funnels.subtitle', {
              defaultValue: 'Manage candidate pipeline stages. Pipeline and Dashboard use these stages.',
            })}
          </p>
        </header>
        <div className="card p-8 text-center">
          <p className="text-slate-600 mb-4">
            {t('admin.funnels.no_funnels', {
              defaultValue: 'No candidate funnels yet. Create your first funnel to manage pipeline stages.',
            })}
          </p>
          <button
            type="button"
            onClick={() => setShowCreateFunnelModal(true)}
            className="btn-primary"
          >
            + {t('admin.funnels.create_funnel', { defaultValue: 'Create funnel' })}
          </button>
        </div>
        {showCreateFunnelModal && (
          <FunnelCreateModal
            onClose={() => setShowCreateFunnelModal(false)}
            onSave={handleCreateFunnel}
            disabled={saving}
          />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">
          {t('admin.funnels.title', { defaultValue: 'Candidate funnels' })}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('admin.funnels.subtitle', {
            defaultValue: 'Manage candidate pipeline stages. Pipeline and Dashboard use these stages.',
          })}
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            {t('admin.funnels.select_funnel', { defaultValue: 'Funnel' })}
          </label>
          <select
            value={selectedFunnel?.id || ''}
            onChange={(e) => {
              const f = funnels.find((x) => x.id === e.target.value)
              setSelectedFunnel(f || null)
            }}
            className="input"
          >
            {funnels.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
                {f.is_default ? ' ★' : ''}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateFunnelModal(true)}
          className="btn-secondary text-sm mt-5"
        >
          + {t('admin.funnels.new_funnel', { defaultValue: 'New funnel' })}
        </button>
      </div>

      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">
            {selectedFunnel?.name || ''} — {t('admin.funnels.stages', { defaultValue: 'Stages' })}
          </h2>
          {selectedFunnel && (
            <button
              type="button"
              onClick={() => setShowCreateStageModal(true)}
              className="btn-primary text-sm"
            >
              + {t('admin.funnels.add_stage', { defaultValue: 'Add stage' })}
            </button>
          )}
        </div>
        {!selectedFunnel ? (
          <div className="p-8 text-center text-sm text-slate-500">
            {t('admin.funnels.select_funnel_first', { defaultValue: 'Select a funnel' })}
          </div>
        ) : stages.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            {t('admin.funnels.no_stages', {
              defaultValue: 'No stages. Add your first stage.',
            })}
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
                  <th className="py-2 px-2">Code</th>
                  <th className="py-2 px-2">Label</th>
                  <th className="py-2 px-2">System</th>
                  <th className="py-2 px-2">Order</th>
                  <th className="py-2 px-2">Status</th>
                  <th className="py-2 px-2 text-right">Actions</th>
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
                    />
                  ))}
                </SortableContext>
              </tbody>
            </table>
          </DndContext>
        )}
      </div>

      <div className="card p-4">
        <h2 className="text-sm font-semibold text-slate-900 mb-2">
          {t('admin.funnels.reference_stages', { defaultValue: 'Reference: system stage codes' })}
        </h2>
        <p className="text-xs text-slate-500 mb-3">
          {t('admin.funnels.reference_help', {
            defaultValue: 'You can use these codes or define your own. Pipeline and Dashboard use the stages from your selected funnel.',
          })}
        </p>
        <div className="flex flex-wrap gap-2">
          {DEFAULT_STAGE_CODES.map((code) => (
            <span
              key={code}
              className="inline-flex rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
            >
              {code}
            </span>
          ))}
        </div>
      </div>

      {showCreateStageModal && selectedFunnel && (
        <StageCreateEditModal
          stage={null}
          onClose={() => setShowCreateStageModal(false)}
          onSave={handleCreateStage}
          disabled={saving}
          referenceCodes={referenceStageCodes}
        />
      )}
      {editingStage && (
        <StageCreateEditModal
          stage={editingStage}
          onClose={() => setEditingStage(null)}
          onSave={handleUpdateStage}
          disabled={saving}
        />
      )}
      {showCreateFunnelModal && (
        <FunnelCreateModal
          onClose={() => setShowCreateFunnelModal(false)}
          onSave={handleCreateFunnel}
          disabled={saving}
        />
      )}
    </div>
  )
}
