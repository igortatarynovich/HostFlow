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
import {
  listCandidateStages,
  createCandidateStage,
  updateCandidateStage,
  deleteCandidateStage,
  type CandidateStage,
} from '../../api/candidate_stages'
import { Modal } from '../Modal'

export interface StageConfig {
  stage_code: string
  stage_label: string
  order: number
  active: boolean
  stage_id?: number // ID from CandidateStageDict if it's a custom stage
}

interface StageConstructorProps {
  value: StageConfig[]
  onChange: (stages: StageConfig[]) => void
  disabled?: boolean
}

function SortableStageItem({
  stage,
  index,
  onToggleActive,
  onEdit,
  onRemove,
  disabled,
}: {
  stage: StageConfig
  index: number
  onToggleActive: () => void
  onEdit: () => void
  onRemove: () => void
  disabled?: boolean
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: stage.stage_code })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-lg border p-3 bg-white ${
        isDragging ? 'shadow-lg' : 'shadow-sm'
      } ${disabled ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3">
        <div
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8h16M4 16h16"
            />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-900">{stage.stage_label}</span>
            <span className="text-xs text-slate-500 font-mono">({stage.stage_code})</span>
            {!stage.active && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                Неактивен
              </span>
            )}
            {stage.stage_id && (
              <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                Кастомный
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={stage.active}
              onChange={onToggleActive}
              disabled={disabled}
              className="rounded border-slate-300"
            />
            <span className="text-xs text-slate-600">Активен</span>
          </label>
          <button
            type="button"
            onClick={onEdit}
            disabled={disabled}
            className="btn-secondary btn-xs"
          >
            Редактировать
          </button>
          {stage.stage_id && (
            <button
              type="button"
              onClick={onRemove}
              disabled={disabled}
              className="btn-danger btn-xs"
            >
              Удалить
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function StageConstructor({
  value,
  onChange,
  disabled = false,
}: StageConstructorProps) {
  const [customStages, setCustomStages] = useState<CandidateStage[]>([])
  const [loading, setLoading] = useState(true)
  const [editingStage, setEditingStage] = useState<StageConfig | null>(null)
  const [showCreateStageModal, setShowCreateStageModal] = useState(false)
  const [creatingStage, setCreatingStage] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  useEffect(() => {
    const loadStages = async () => {
      try {
        const stages = await listCandidateStages({ active: undefined })
        setCustomStages(stages)
      } catch (err) {
        console.error('Failed to load candidate stages', err)
      } finally {
        setLoading(false)
      }
    }
    void loadStages()
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id) return

      const oldIndex = value.findIndex((s) => s.stage_code === active.id)
      const newIndex = value.findIndex((s) => s.stage_code === over.id)

      if (oldIndex !== -1 && newIndex !== -1) {
        const newStages = arrayMove(value, oldIndex, newIndex)
        // Update order numbers
        const reordered = newStages.map((stage, idx) => ({
          ...stage,
          order: idx + 1,
        }))
        onChange(reordered)
      }
    },
    [value, onChange]
  )

  const handleToggleActive = useCallback(
    (index: number) => {
      const newStages = [...value]
      newStages[index] = { ...newStages[index], active: !newStages[index].active }
      onChange(newStages)
    },
    [value, onChange]
  )

  const handleEdit = useCallback(
    (index: number) => {
      setEditingStage(value[index])
      setShowCreateStageModal(true)
    },
    [value]
  )

  const handleRemove = useCallback(
    async (index: number) => {
      const stage = value[index]
      if (!stage.stage_id) return

      if (!confirm(`Удалить этап "${stage.stage_label}"?`)) return

      try {
        await deleteCandidateStage(stage.stage_id)
        // Reload custom stages
        const stages = await listCandidateStages({ active: undefined })
        setCustomStages(stages)
        // Remove from profile config
        const newStages = value.filter((_, i) => i !== index)
        const reordered = newStages.map((stage, idx) => ({
          ...stage,
          order: idx + 1,
        }))
        onChange(reordered)

        // Notify that stages have been updated (to refresh meta cache)
        window.dispatchEvent(new CustomEvent('candidate-stage-updated'))
      } catch (err: any) {
        alert(`Не удалось удалить этап: ${err?.message || 'Неизвестная ошибка'}`)
      }
    },
    [value, onChange]
  )

  const handleCreateStage = useCallback(
    async (stageData: { code: string; label: string; order?: number; active?: boolean }) => {
      setCreatingStage(true)
      try {
        // Create custom stage definition
        const newStageDef = await createCandidateStage({
          code: stageData.code,
          label: stageData.label,
          order: stageData.order || value.length + 1,
          active: stageData.active !== false,
        })

        // Reload custom stages list
        const stages = await listCandidateStages({ active: undefined })
        setCustomStages(stages)

        // Add stage to profile config
        const newStage: StageConfig = {
          stage_code: newStageDef.code,
          stage_label: newStageDef.label,
          order: newStageDef.order,
          active: newStageDef.active,
          stage_id: newStageDef.id,
        }

        onChange([...value, newStage])
        setShowCreateStageModal(false)
        setEditingStage(null)

        // Notify that stages have been updated (to refresh meta cache)
        window.dispatchEvent(new CustomEvent('candidate-stage-updated'))
      } catch (err: any) {
        alert(`Не удалось создать этап: ${err?.message || 'Неизвестная ошибка'}`)
      } finally {
        setCreatingStage(false)
      }
    },
    [value, onChange]
  )

  const handleUpdateStage = useCallback(
    async (stageData: { code: string; label: string; order?: number; active?: boolean }) => {
      if (!editingStage?.stage_id) return

      setCreatingStage(true)
      try {
        // Update custom stage definition
        const updatedStageDef = await updateCandidateStage(editingStage.stage_id, {
          code: stageData.code,
          label: stageData.label,
          order: stageData.order || editingStage.order,
          active: stageData.active !== false,
        })

        // Reload custom stages list
        const stages = await listCandidateStages({ active: undefined })
        setCustomStages(stages)

        // Update stage in profile config
        const newStages = value.map((stage) =>
          stage.stage_code === editingStage.stage_code
            ? {
                ...stage,
                stage_code: updatedStageDef.code,
                stage_label: updatedStageDef.label,
                order: updatedStageDef.order,
                active: updatedStageDef.active,
              }
            : stage
        )
        onChange(newStages)
        setShowCreateStageModal(false)
        setEditingStage(null)

        // Notify that stages have been updated (to refresh meta cache)
        window.dispatchEvent(new CustomEvent('candidate-stage-updated'))
      } catch (err: any) {
        alert(`Не удалось обновить этап: ${err?.message || 'Неизвестная ошибка'}`)
      } finally {
        setCreatingStage(false)
      }
    },
    [editingStage, value, onChange]
  )

  const availableSystemStages = useMemo(() => {
    // System stages that are not yet in the profile
    const usedCodes = new Set(value.map((s) => s.stage_code))
    const systemStages: Array<{ code: string; label: string }> = [
      { code: 'new', label: 'Новый' },
      { code: 'contacted', label: 'Контакт установлен' },
      { code: 'docs_wait', label: 'Ожидаем документы' },
      { code: 'docs_got', label: 'Документы получены' },
      { code: 'permit_ordered', label: 'Заказ разрешения на работу' },
      { code: 'permit_got', label: 'Разрешение на работу получено' },
      { code: 'visa', label: 'Виза' },
      { code: 'red_paper_ordered', label: 'Красная бумага заказана' },
      { code: 'arrival_planned', label: 'Планируем приезд' },
      { code: 'on_client_base', label: 'На базе клиента' },
      { code: 'left_to_trip', label: 'Выехал в рейс' },
      { code: 'probation_passed', label: 'Прошел пробный период' },
      { code: 'employed', label: 'Трудоустроен' },
      { code: 'rejected', label: 'Отклонён' },
    ]

    return systemStages.filter((stage) => !usedCodes.has(stage.code))
  }, [value])

  const handleAddSystemStage = useCallback(
    (code: string, label: string) => {
      const newStage: StageConfig = {
        stage_code: code,
        stage_label: label,
        order: value.length + 1,
        active: true,
      }
      onChange([...value, newStage])
    },
    [value, onChange]
  )

  const handleRemoveFromProfile = useCallback(
    (index: number) => {
      const newStages = value.filter((_, i) => i !== index)
      const reordered = newStages.map((stage, idx) => ({
        ...stage,
        order: idx + 1,
      }))
      onChange(reordered)
    },
    [value, onChange]
  )

  if (loading) {
    return <div className="text-sm text-slate-500">Загрузка...</div>
  }

  return (
    <div className="space-y-4">
      {/* Create new custom stage button */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => {
            setEditingStage(null)
            setShowCreateStageModal(true)
          }}
          disabled={disabled}
          className="btn-secondary text-sm"
        >
          + Создать новый кастомный этап
        </button>
      </div>

      {/* Active stages (sortable) */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">Этапы в воронке</h3>
        {value.length === 0 ? (
          <p className="text-sm text-slate-500">Нет этапов. Добавьте этапы из списка ниже.</p>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={value.map((s) => s.stage_code)} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {value.map((stage, index) => (
                  <SortableStageItem
                    key={stage.stage_code}
                    stage={stage}
                    index={index}
                    onToggleActive={() => handleToggleActive(index)}
                    onEdit={() => handleEdit(index)}
                    onRemove={() => handleRemove(index)}
                    disabled={disabled}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>

      {/* Available system stages */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-900">Доступные системные этапы</h3>
        {availableSystemStages.length === 0 ? (
          <p className="text-sm text-slate-500">Все системные этапы добавлены</p>
        ) : (
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
            {availableSystemStages.map((stage) => (
              <button
                key={stage.code}
                type="button"
                onClick={() => handleAddSystemStage(stage.code, stage.label)}
                disabled={disabled}
                className="rounded-lg border border-slate-200 bg-white p-2 text-left text-sm transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="font-medium text-slate-900">{stage.label}</div>
                <div className="text-xs text-slate-500 font-mono">{stage.code}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Custom stages from database */}
      {customStages.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-900">Доступные кастомные этапы</h3>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
            {customStages
              .filter((cs) => !value.some((s) => s.stage_id === cs.id))
              .map((stage) => (
                <button
                  key={stage.id}
                  type="button"
                  onClick={() => {
                    const newStage: StageConfig = {
                      stage_code: stage.code,
                      stage_label: stage.label,
                      order: value.length + 1,
                      active: stage.active,
                      stage_id: stage.id,
                    }
                    onChange([...value, newStage])
                  }}
                  disabled={disabled || !stage.active}
                  className={`rounded-lg border p-2 text-left text-sm transition-colors ${
                    stage.active
                      ? 'border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50'
                      : 'border-slate-100 bg-slate-50 opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div className="font-medium text-slate-900">{stage.label}</div>
                  <div className="text-xs text-slate-500 font-mono">{stage.code}</div>
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Create/Edit stage modal */}
      {showCreateStageModal && (
        <CreateStageModal
          stage={editingStage}
          onClose={() => {
            setShowCreateStageModal(false)
            setEditingStage(null)
          }}
          onSave={editingStage ? handleUpdateStage : handleCreateStage}
          disabled={creatingStage || disabled}
        />
      )}
    </div>
  )
}

// Modal for creating/editing a custom stage
function CreateStageModal({
  stage,
  onClose,
  onSave,
  disabled,
}: {
  stage?: StageConfig | null
  onClose: () => void
  onSave: (data: { code: string; label: string; order?: number; active?: boolean }) => Promise<void>
  disabled?: boolean
}) {
  const [code, setCode] = useState(stage?.stage_code || '')
  const [label, setLabel] = useState(stage?.stage_label || '')
  const [order, setOrder] = useState(stage?.order || 0)
  const [active, setActive] = useState(stage?.active !== false)

  const handleSubmit = async () => {
    if (!code.trim() || !label.trim()) {
      alert('Код и название обязательны')
      return
    }

    await onSave({
      code: code.trim(),
      label: label.trim(),
      order: order || 0,
      active,
    })
  }

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={stage ? 'Редактировать этап' : 'Создать новый кастомный этап'}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Название этапа (пользовательское название) *
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => {
              setLabel(e.target.value)
              // Auto-generate code from label if code is empty
              if (!code.trim()) {
                const autoCode = e.target.value
                  .trim()
                  .toLowerCase()
                  .replace(/\s+/g, '_')
                  .replace(/[^a-z0-9_]/g, '')
                setCode(autoCode)
              }
            }}
            className="input w-full"
            placeholder="Например: Первичное собеседование"
            disabled={disabled}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Код этапа (техническое имя) *
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
            className="input w-full font-mono text-sm"
            placeholder="initial_interview"
            disabled={disabled || !!stage}
          />
          <p className="mt-1 text-xs text-slate-500">
            Используется для технической идентификации этапа {stage && '(нельзя изменить)'}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Порядок сортировки
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
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              disabled={disabled}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">Активен</span>
          </label>
        </div>

        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onClose} disabled={disabled} className="btn-secondary">
            Отмена
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !label.trim() || !code.trim()}
            className="btn-primary"
          >
            {disabled ? 'Сохранение...' : stage ? 'Сохранить' : 'Создать этап'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
